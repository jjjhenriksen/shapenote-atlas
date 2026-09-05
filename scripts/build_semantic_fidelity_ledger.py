#!/usr/bin/env python3
"""Build an additive, source-versus-asset semantic fidelity ledger.

This report deliberately sits beside the existing 2025 comparison ledger. It
does not authorize promotion or rewrite the corpus. For retained Shape Note
Music Files witnesses it independently reads the source MXL and compares the
serialized event stream with the generated lazy asset, accounting only for a
recorded source-preserving final-chord trim. Drafts and alternate-edition
witnesses remain review-only even when their own source serialization matches.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from agent_03_semantic_musicxml import parse_source as parse_agent_03_source


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public" / "corpus.json"
MANIFEST = ROOT / "public" / "shapenote-score-manifest.json"
OUTPUT = ROOT / "public" / "semantic-fidelity-ledger.json"
FIELDS = ("scoreByBook", "referenceScoreByBook", "draftScoreByBook")
SUPPLEMENTAL_RETAINED_WITNESSES = {
    "https://shapenote.net/musicxml/CH2010-543.mxl": {
        "rawPath": "work/luna-program-20260904/existing_books/assets/christian-harmony/ch2010-543.mxl",
        "sourceSha256": "ac9855660a59298892329b907a41a916a3acc7364f1ef4b5e18e252b6c54ef57",
        "sourceEdition": "ch7",
        "sourceAuthority": "source-observed-existing-books-witness",
    },
    "https://shapenote.net/musicxml/CH2010-546b.mxl": {
        "rawPath": "work/luna-program-20260904/existing_books/assets/christian-harmony/ch2010-546b.mxl",
        "sourceSha256": "0d815e611aba4e73bee6276d90452e2cbb65b8ac03ecd1ba13ad51acdc9cbf35",
        "sourceEdition": "ch7",
        "sourceAuthority": "source-observed-existing-books-witness",
    },
    "https://shapenote.net/musicxml/CH2010-549b.mxl": {
        "rawPath": "work/luna-program-20260904/existing_books/assets/christian-harmony/ch2010-549b.mxl",
        "sourceSha256": "a888a4c72b004f5e40ee7ff934ff0c2b6b9472c64291ac9cf868a982247555a3",
        "sourceEdition": "ch7",
        "sourceAuthority": "source-observed-existing-books-witness",
    },
    "https://shapenote.net/musicxml/SH-12.mxl": {
        "rawPath": "work/luna-program-20260904/existing_books/assets/southern-harmony/sh-12.mxl",
        "sourceSha256": "280aa4755358122e8282f7a3c156be20bd0207d599ba60b9ffedac48ccfabab7",
        "sourceEdition": "southernharmony",
        "sourceAuthority": "source-observed-existing-books-witness",
    },
}
DIFFERENCE_TAXONOMY = {
    "draft-is-not-authoritative-source": "Draft score is excluded from source-authoritative verification.",
    "event-stream-diff": "Parts, pitch, duration, rests, ties, voice, staff, accidentals, or notehead event serialization differs.",
    "measure-count-diff": "Source and generated event-bearing measure identities differ after recorded transforms.",
    "repeat-ending-semantics-not-modeled-in-generated-asset": "Source has repeat or ending directives not represented in the generated asset.",
    "sound-navigation-semantics-not-modeled-in-generated-asset": "Source has sound navigation directives not represented in the generated asset.",
    "lyrics-not-modeled-in-generated-asset": "Source contains lyrics that are not represented in the generated asset.",
    "shape-notehead-count-differs": "Source and generated shape-notehead counts differ.",
    "key-declaration-differs": "Source key declaration differs from the generated asset declaration.",
    "time-signature-differs": "Source time declaration differs from the generated asset time signature.",
    "retained-source-mxl-unavailable": "No retained independent MusicXML witness is available.",
    "manifest-source-path-missing": "Manifest names a retained source path that is not present.",
    "witness-is-not-exact-edition-source": "The available witness is a reference or alternate-edition source.",
    "source-checksum-drift": "Retained source bytes differ from the manifest checksum.",
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(node: ET.Element, name: str) -> str:
    for child in node:
        if local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def number(value: Any, default: float = 0.0) -> float:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return default


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_xml(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".xml") and "container" not in name]
        if not names:
            raise ValueError("archive contains no score XML")
        return ET.fromstring(archive.read(names[0]))


def parse_source_legacy(path: Path) -> dict[str, Any]:
    """Parse enough MusicXML independently to compare serialized semantics."""
    root = source_xml(path)
    part_names: dict[str, str] = {}
    for node in root.iter():
        if local_name(node.tag) == "score-part":
            part_id = node.attrib.get("id", "")
            if part_id:
                part_names[part_id] = child_text(node, "part-name") or part_id

    parts: list[dict[str, Any]] = []
    key_declarations: list[dict[str, Any]] = []
    time_declarations: list[str] = []
    for part in root:
        if local_name(part.tag) != "part":
            continue
        cursor = 0.0
        divisions = 1.0
        events: list[dict[str, Any]] = []
        measure_numbers: list[str] = []
        repeat_barlines = 0
        ending_barlines = 0
        for measure in part:
            if local_name(measure.tag) != "measure":
                continue
            measure_number = measure.attrib.get("number", "")
            measure_numbers.append(measure_number)
            for barline in (child for child in measure if local_name(child.tag) == "barline"):
                repeat_barlines += sum(1 for child in barline if local_name(child.tag) == "repeat")
                ending_barlines += sum(1 for child in barline if local_name(child.tag) == "ending")
            for item in measure:
                item_name = local_name(item.tag)
                if item_name == "attributes":
                    raw_divisions = child_text(item, "divisions")
                    if raw_divisions:
                        divisions = number(raw_divisions, 1.0) or 1.0
                    key = next((child for child in item if local_name(child.tag) == "key"), None)
                    if key is not None:
                        fifths = child_text(key, "fifths")
                        mode = child_text(key, "mode")
                        if fifths:
                            key_declarations.append({
                                "fifths": fifths,
                                "mode": mode,
                                "modePresent": bool(mode),
                            })
                    time = next((child for child in item if local_name(child.tag) == "time"), None)
                    if time is not None:
                        beats = child_text(time, "beats")
                        beat_type = child_text(time, "beat-type")
                        if beats and beat_type:
                            time_declarations.append(f"{beats}/{beat_type}")
                elif item_name == "backup":
                    cursor -= number(child_text(item, "duration")) / divisions
                elif item_name == "forward":
                    cursor += number(child_text(item, "duration")) / divisions
                elif item_name == "note":
                    duration = number(child_text(item, "duration")) / divisions
                    pitch = next((child for child in item if local_name(child.tag) == "pitch"), None)
                    event: dict[str, Any] = {
                        "onset": round(cursor, 3),
                        "beats": round(max(duration, 0.125), 3),
                        "measure": measure_number,
                        "rest": pitch is None,
                        "voice": child_text(item, "voice"),
                        "staff": child_text(item, "staff") or "1",
                        "type": child_text(item, "type"),
                        "dots": sum(1 for child in item if local_name(child.tag) == "dot"),
                        "accidental": child_text(item, "accidental"),
                        "notehead": child_text(item, "notehead"),
                        "lyrics": [
                            child_text(lyric, "text")
                            for lyric in item
                            if local_name(lyric.tag) == "lyric" and child_text(lyric, "text")
                        ],
                    }
                    if pitch is not None:
                        event.update({
                            "step": child_text(pitch, "step"),
                            "alter": int(child_text(pitch, "alter") or "0"),
                            "octave": int(child_text(pitch, "octave") or "4"),
                        })
                    for tie in (child for child in item if local_name(child.tag) == "tie"):
                        tie_type = tie.attrib.get("type", "")
                        if tie_type in {"start", "stop"}:
                            event[f"tie{tie_type.title()}"] = True
                    events.append(event)
                    if not any(local_name(child.tag) == "chord" for child in item):
                        cursor += duration
        parts.append({
            "name": part_names.get(part.attrib.get("id", ""), part.attrib.get("id", "Part")),
            "events": events,
            "measureNumbers": measure_numbers,
        })

    work_title = ""
    for node in root.iter():
        if local_name(node.tag) == "work-title":
            work_title = (node.text or "").strip()
            break
    return {
        "workTitle": work_title,
        "parts": parts,
        "keyDeclarations": key_declarations,
        "timeDeclarations": list(dict.fromkeys(time_declarations)),
        "repeatBarlines": repeat_barlines,
        "endingBarlines": ending_barlines,
    }


def normalized_event(event: dict[str, Any]) -> dict[str, Any]:
    keys = ("onset", "beats", "measure", "rest", "voice", "staff", "type", "dots", "accidental", "notehead", "step", "alter", "octave", "tieStart", "tieStop", "lyrics", "editorialMarkings")
    normalized: dict[str, Any] = {}
    for key in keys:
        value = event.get(key)
        if key in {"onset", "beats"}:
            value = number(value)
        elif key == "alter":
            value = int(value or 0)
        elif key == "octave":
            value = int(value) if value is not None else None
        elif key in {"rest", "tieStart", "tieStop"}:
            value = bool(value)
        elif key in {"lyrics", "editorialMarkings"}:
            value = value if isinstance(value, list) else []
        elif value is None:
            value = ""
        normalized[key] = value
    return normalized


def compare_events(source: list[dict[str, Any]], asset: list[dict[str, Any]]) -> dict[str, Any]:
    source_norm = [normalized_event(event) for event in source]
    asset_norm = [normalized_event(event) for event in asset]
    mismatches = []
    for index, (left, right) in enumerate(zip(source_norm, asset_norm)):
        if left != right:
            fields = [key for key in left if left.get(key) != right.get(key)]
            mismatches.append({"index": index, "fields": fields, "source": left, "asset": right})
            if len(mismatches) >= 8:
                break
    return {
        "sourceEvents": len(source_norm),
        "assetEvents": len(asset_norm),
        "eventCountDifference": len(asset_norm) - len(source_norm),
        "mismatchCountLowerBound": len(mismatches),
        "mismatches": mismatches,
        "exact": source_norm == asset_norm,
    }


def asset_parts(asset: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"name": part.get("name", ""), "events": part.get("events", [])} for part in asset.get("parts", [])]


def source_match(source: dict[str, Any], asset: dict[str, Any], transform: dict[str, Any]) -> dict[str, Any]:
    source_parts = source.get("parts", [])
    target_parts = asset_parts(asset)
    part_results = []
    for index in range(max(len(source_parts), len(target_parts))):
        left = source_parts[index] if index < len(source_parts) else {"events": []}
        right = target_parts[index] if index < len(target_parts) else {"events": []}
        source_events = left.get("events", [])
        if transform.get("finalChordRemoved"):
            onset = number(transform.get("onset"))
            source_events = [event for event in source_events if number(event.get("onset")) != onset]
        result = compare_events(source_events, right.get("events", []))
        result["partIndex"] = index
        result["sourcePartName"] = left.get("name", "")
        result["assetPartName"] = right.get("name", "")
        source_measure_numbers = [str(value) for value in left.get("measureNumbers", [])]
        source_event_measure_numbers = {
            str(event.get("measure", ""))
            for event in source_events
            if event.get("measure", "") != ""
        }
        asset_measure_numbers = {
            str(event.get("measure", ""))
            for event in right.get("events", [])
            if event.get("measure", "") != ""
        }
        omitted_source_measure_numbers = [
            value for value in source_measure_numbers
            if value not in source_event_measure_numbers
        ]
        transform_measure_numbers = {
            str(value) for value in (transform.get("measures") or [])
        }
        source_measure_omission_reason = "none"
        if omitted_source_measure_numbers:
            if (
                transform.get("finalChordRemoved")
                and transform.get("removedEventCount", 0)
                and set(omitted_source_measure_numbers) == transform_measure_numbers
            ):
                source_measure_omission_reason = "recorded-final-chord-transform"
            else:
                source_measure_omission_reason = "source-part-empty-measures-not-serialized"
        measure_count_transform_accepted = (
            source_event_measure_numbers == asset_measure_numbers
        )
        source_measure_count = len(source_measure_numbers)
        asset_measure_count = len(asset_measure_numbers)
        result["sourceMeasureCount"] = source_measure_count
        result["sourceEventMeasureCountAfterRecordedTransform"] = len(source_event_measure_numbers)
        result["assetMeasureCount"] = asset_measure_count
        result["sourceMeasureNumbers"] = source_measure_numbers
        result["assetMeasureNumbers"] = sorted(asset_measure_numbers)
        result["omittedSourceMeasureNumbers"] = omitted_source_measure_numbers
        result["measureCountEqual"] = source_measure_count == asset_measure_count
        result["measureCountTransformAccepted"] = measure_count_transform_accepted
        result["measureCountDisposition"] = source_measure_omission_reason
        result["measureCountExactAfterRecordedTransform"] = (
            source_measure_count == asset_measure_count or measure_count_transform_accepted
        )
        part_results.append(result)
    return {
        "sourcePartCount": len(source_parts),
        "assetPartCount": len(target_parts),
        "partCountEqual": len(source_parts) == len(target_parts),
        "parts": part_results,
        "eventStreamsExactAfterRecordedTransform": bool(source_parts) and len(source_parts) == len(target_parts) and all(item["exact"] for item in part_results),
        "measureCountsExact": bool(source_parts) and len(source_parts) == len(target_parts) and all(item["measureCountExactAfterRecordedTransform"] for item in part_results),
        "measureCountsExactAfterRecordedTransform": bool(source_parts) and len(source_parts) == len(target_parts) and all(item["measureCountExactAfterRecordedTransform"] for item in part_results),
    }


def semantic_fields(source: dict[str, Any], asset: dict[str, Any], transform: dict[str, Any]) -> dict[str, Any]:
    source_events = [event for part in source.get("parts", []) for event in part.get("events", [])]
    asset_events = [event for part in asset.get("parts", []) for event in part.get("events", [])]
    source_shapes = sum(bool(event.get("notehead")) for event in source_events if not event.get("rest"))
    asset_shapes = sum(bool(event.get("notehead") or event.get("shape")) for event in asset_events if not event.get("rest"))
    source_lyrics = sum(1 for event in source_events if event.get("lyrics"))
    differences: list[str] = []
    if source_lyrics and not asset.get("lyrics"):
        differences.append("lyrics-not-modeled-in-generated-asset")
    if source_shapes and asset_shapes != source_shapes:
        differences.append("shape-notehead-count-differs")
    # Agent 03 retains ``sound`` directives in the compatibility list. Tempo-
    # only sound markings are editorial evidence, not repeat navigation, but
    # navigation-bearing attributes (D.C./D.S./coda/fine/segno) are retained
    # as a distinct semantic dimension below.
    source_repeat_semantics = [
        item for item in source.get("repeatSemantics", [])
        if item.get("kind") in {"repeat", "ending"}
        or (
            item.get("kind") == "sound"
            and any(key in item for key in ("dacapo", "dalsegno", "tocoda", "fine", "segno", "coda"))
        )
    ]
    source_sound_navigation = [item for item in source_repeat_semantics if item.get("kind") == "sound"]
    if source_repeat_semantics and not asset.get("repeatSemantics"):
        differences.append("repeat-ending-semantics-not-modeled-in-generated-asset")
    if source_sound_navigation and not asset.get("soundNavigation"):
        differences.append("sound-navigation-semantics-not-modeled-in-generated-asset")
    source_keys = source.get("keyDeclarations", [])
    asset_keys = asset.get("musicXmlKeyDeclarations", [])
    if source_keys and asset_keys and source_keys != asset_keys:
        differences.append("key-declaration-differs")
    source_times = source.get("timeDeclarations", [])
    if source_times and asset.get("timeSignature") and asset.get("timeSignature") not in source_times:
        differences.append("time-signature-differs")
    return {
        "sourceKeyDeclarations": source.get("keyDeclarations", []),
        "assetKeySignature": asset.get("keySignature", ""),
        "assetKeyEvidence": asset.get("keyEvidence", {}),
        "sourceTimeDeclarations": source.get("timeDeclarations", []),
        "assetTimeSignature": asset.get("timeSignature", ""),
        "sourceShapeNoteheadCount": source_shapes,
        "assetShapeNoteheadCount": asset_shapes,
        "sourceLyricsDetected": source_lyrics,
        "assetLyricsModeled": bool(asset.get("lyrics")),
        "assetRepeatSemanticsModeled": bool(asset.get("repeatSemantics")),
        "sourceRepeatBarlines": source.get("repeatBarlines", 0),
        "sourceEndingBarlines": source.get("endingBarlines", 0),
        "sourceRepeatSemantics": source_repeat_semantics,
        "sourceSoundNavigation": source_sound_navigation,
        "assetSoundNavigationModeled": bool(asset.get("soundNavigation")),
        "sourceEditorialMarkingsDetected": len(source.get("editorialMarkings", [])),
        "assetEditorialMarkingsModeled": bool(asset.get("editorialMarkings")),
        "differences": differences,
    }


def manifest_by_url() -> dict[str, list[dict[str, Any]]]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in payload.get("entries", {}).values():
        grouped.setdefault(str(entry.get("sourceUrl", "")), []).append(entry)
    for url, entry in SUPPLEMENTAL_RETAINED_WITNESSES.items():
        if not grouped.get(url):
            grouped[url] = [dict(entry, sourceUrl=url)]
    return grouped


def main() -> int:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    manifests = manifest_by_url()
    records: list[dict[str, Any]] = []
    asset_cache: dict[str, dict[str, Any]] = {}
    source_cache: dict[str, dict[str, Any] | None] = {}
    errors: list[str] = []

    for song in corpus.get("songs", []):
        for field in FIELDS:
            for book_id, preview in (song.get(field) or {}).items():
                score_ref = str(preview.get("scoreRef", ""))
                if not score_ref:
                    continue
                asset_path = ROOT / "public" / score_ref.lstrip("/")
                mapping_id = f"{song.get('id', '')}::{book_id}/{str(song.get('songNo', '')).lower()}"
                record: dict[str, Any] = {
                    "mappingId": mapping_id,
                    "songId": song.get("id", ""),
                    "songNo": song.get("songNo", ""),
                    "title": song.get("title", ""),
                    "bookId": book_id,
                    "field": field,
                    "assetRef": score_ref,
                    "assetPath": str(asset_path.relative_to(ROOT)),
                    "sourceUrl": preview.get("sourceUrl", ""),
                    "provenance": preview.get("provenance", {}),
                    "safeToPromote": False,
                    "differences": [],
                }
                if not asset_path.is_file():
                    record.update({"status": "blocked-missing-asset", "assetExists": False})
                    errors.append(f"{mapping_id}: missing {score_ref}")
                    records.append(record)
                    continue
                asset_key = str(asset_path)
                if asset_key not in asset_cache:
                    asset_cache[asset_key] = json.loads(asset_path.read_text(encoding="utf-8"))
                asset = asset_cache[asset_key]
                record["assetSha256"] = sha256(asset_path)
                record["assetExists"] = True
                transform = asset.get("playbackTransform", {})
                witnesses = manifests.get(str(preview.get("sourceUrl", "")), [])
                witness = next((item for item in witnesses if item.get("sourceEdition") == book_id), witnesses[0] if witnesses else None)
                if field == "draftScoreByBook" or str(preview.get("sourceUrl", "")).startswith("draft://"):
                    record.update({"status": "review-only-draft", "sourceComparison": "not-authoritative-draft"})
                    record["differences"].append("draft-is-not-authoritative-source")
                elif not witness:
                    record.update({"status": "blocked-no-retained-source", "sourceComparison": "no-independent-retained-mxl"})
                    record["differences"].append("retained-source-mxl-unavailable")
                else:
                    source_path = ROOT / witness.get("rawPath", "")
                    record["sourcePath"] = str(source_path.relative_to(ROOT)) if source_path.is_file() else witness.get("rawPath", "")
                    record["sourceSha256"] = witness.get("sourceSha256", "")
                    record["sourceExists"] = source_path.is_file()
                    record["sourceEdition"] = witness.get("sourceEdition", "")
                    if not source_path.is_file():
                        record.update({"status": "blocked-missing-retained-source", "sourceComparison": "manifest-path-missing"})
                        record["differences"].append("manifest-source-path-missing")
                        errors.append(f"{mapping_id}: missing source {witness.get('rawPath', '')}")
                    else:
                        if witness.get("sourceSha256") and sha256(source_path) != witness.get("sourceSha256"):
                            record["differences"].append("source-checksum-drift")
                            errors.append(f"{mapping_id}: source checksum drift")
                        if str(source_path) not in source_cache:
                            try:
                                source_cache[str(source_path)] = parse_agent_03_source(source_path)
                            except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError) as exc:
                                source_cache[str(source_path)] = None
                                errors.append(f"{mapping_id}: source parse failed: {exc}")
                        source = source_cache[str(source_path)]
                        if source is None:
                            record.update({"status": "blocked-source-parse-failure", "sourceComparison": "unreadable-retained-mxl"})
                        else:
                            comparison = source_match(source, asset, transform)
                            record["sourceComparison"] = comparison
                            record["semanticFields"] = semantic_fields(source, asset, transform)
                            record["differences"].extend(record["semanticFields"]["differences"])
                            if not comparison["eventStreamsExactAfterRecordedTransform"]:
                                record["differences"].append("event-stream-diff")
                            if not comparison["measureCountsExactAfterRecordedTransform"]:
                                record["differences"].append("measure-count-diff")
                            if field == "referenceScoreByBook" or witness.get("sourceEdition") != book_id:
                                record["status"] = "review-only-alternate-witness" if (
                                    comparison["eventStreamsExactAfterRecordedTransform"]
                                    and comparison["measureCountsExactAfterRecordedTransform"]
                                ) else "rejected-source-mismatch"
                                record["differences"].append("witness-is-not-exact-edition-source")
                            elif (
                                comparison["eventStreamsExactAfterRecordedTransform"]
                                and comparison["measureCountsExactAfterRecordedTransform"]
                                and not record["differences"]
                            ):
                                record["status"] = "verified-structured-source-serialization"
                            else:
                                record["status"] = "blocked-semantic-diff"
                records.append(record)

    records.sort(key=lambda item: (item.get("mappingId", ""), item.get("field", ""), item.get("assetRef", "")))
    status_counts: dict[str, int] = {}
    difference_counts: dict[str, int] = {}
    measure_disposition_counts: dict[str, int] = {}
    for record in records:
        status = str(record.get("status", "missing-status"))
        status_counts[status] = status_counts.get(status, 0) + 1
        for difference in record.get("differences", []):
            difference_counts[difference] = difference_counts.get(difference, 0) + 1
        comparison = record.get("sourceComparison", {})
        for part in comparison.get("parts", []) if isinstance(comparison, dict) else []:
            disposition = str(part.get("measureCountDisposition", "not-compared"))
            measure_disposition_counts[disposition] = measure_disposition_counts.get(disposition, 0) + 1
    exact_records = [item for item in records if item.get("status") == "verified-structured-source-serialization"]
    output = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "valid" if not errors else "invalid",
        "policy": "This additive ledger proves serialization against retained source MXL where possible. It never authorizes promotion. Alternate-edition witnesses and OMR drafts remain review-only; unmodeled lyrics/repeats/shapes are explicit semantic limitations.",
        "summary": {
            "mappingRecords": len(records),
            "uniqueAssets": len({item.get("assetRef") for item in records}),
            "retainedSourceComparisons": sum(isinstance(item.get("sourceComparison"), dict) for item in records),
            "nonComparableMappings": sum(not isinstance(item.get("sourceComparison"), dict) for item in records),
            "exactSourceSerializationRecords": len(exact_records),
            "safeToPromote": 0,
            "statusCounts": status_counts,
            "differenceCounts": difference_counts,
            "measureDispositionCounts": measure_disposition_counts,
            "errors": len(errors),
        },
        "coverage": {
            "fields": list(FIELDS),
            "semanticDimensions": ["parts", "measures", "pitch", "duration", "rests", "ties", "lyrics", "repeat-endings", "key-mode", "shapes", "source-measure-count"],
            "differenceTaxonomy": DIFFERENCE_TAXONOMY,
            "unmodeledDimensionsAreListedAsDifferences": True,
        },
        "errors": errors,
        "records": records,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
