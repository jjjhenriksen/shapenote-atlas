#!/usr/bin/env python3
"""Audit every MusicXML mapping in the public Sacred Harp 2025 catalog section.

The catalog section contains both edition-specific SH25 files and useful
alternate witnesses from other tunebooks. This audit keeps those identities
separate and applies a fail-closed promotion gate: a score must be an exact
2025 source, have four parts, agree with the current source metadata for key
and meter, and either explicitly encode four-shape noteheads or carry a
verified direct source comparison that adds those tags without changing the
event stream. Conventional-staff files without such evidence remain blocked.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "public/shapenote-score-manifest.json"
CORPUS = ROOT / "public/corpus.json"
OUTPUT = ROOT / "public/shapenote-2025-score-audit.json"
EXISTING_50T_COMPARISON = ROOT / "work/source-transcriptions/2025/50t-devotion-autonomous-comparison.json"
EXISTING_55_COMPARISON = ROOT / "work/source-transcriptions/2025/55-converse-autonomous-comparison.json"
EXISTING_415_COMPARISON = ROOT / "work/source-transcriptions/2025/415-endless-praise-autonomous-comparison.json"

FIFTHS = {
    "C": 0,
    "G": 1,
    "D": 2,
    "A": 3,
    "E": 4,
    "B": 5,
    "F#": 6,
    "C#": 7,
    "F": -1,
    "Bb": -2,
    "Eb": -3,
    "Ab": -4,
    "Db": -5,
    "Gb": -6,
    "Cb": -7,
}
SHAPE_NAMES = {"fa", "sol", "la", "mi", "do", "re", "ti"}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(node: ET.Element, name: str) -> str:
    for child in node:
        if local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_key(value: str) -> tuple[int | None, str | None]:
    match = re.match(r"^\s*([A-G](?:#|b)?)\s+(major|minor)\s*$", value or "", re.I)
    if not match:
        return None, None
    tonic = match.group(1)
    tonic = tonic[0].upper() + tonic[1:]
    return FIFTHS.get(tonic), match.group(2).lower()


def parse_score(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        xml_names = [name for name in archive.namelist() if name.lower().endswith(".xml") and "container" not in name.lower()]
        if not xml_names:
            raise ValueError("MusicXML ZIP has no score document")
        root = ET.fromstring(archive.read(xml_names[0]))

    parts = [node for node in root if local_name(node.tag) == "part"]
    titles = [node.text.strip() for node in root.iter() if local_name(node.tag) == "work-title" and node.text]
    creators = [node.text.strip() for node in root.iter() if local_name(node.tag) == "creator" and node.text]
    keys: list[dict[str, str]] = []
    times: list[dict[str, str]] = []
    for node in root.iter():
        if local_name(node.tag) == "key":
            keys.append({"fifths": child_text(node, "fifths"), "mode": child_text(node, "mode")})
        elif local_name(node.tag) == "time":
            times.append({"beats": child_text(node, "beats"), "beatType": child_text(node, "beat-type")})
    explicit_shapes = [
        (node.text or "").strip().lower()
        for node in root.iter()
        if local_name(node.tag) == "notehead" and (node.text or "").strip().lower() in SHAPE_NAMES
    ]
    return {
        "workTitle": titles[0] if titles else "",
        "creators": creators,
        "partCount": len(parts),
        "measuresByPart": [sum(1 for child in part if local_name(child.tag) == "measure") for part in parts],
        "keyDeclarations": keys,
        "timeDeclarations": times,
        "explicitShapeNoteheads": len(explicit_shapes),
        "shapeValues": sorted(set(explicit_shapes)),
    }


def event_signature(path: Path) -> list[list[tuple[str, float, tuple[str, int, int] | None, bool]]]:
    """Return source-independent pitch/duration events for a MusicXML ZIP."""
    with zipfile.ZipFile(path) as archive:
        xml_names = [name for name in archive.namelist() if name.lower().endswith(".xml") and "container" not in name.lower()]
        root = ET.fromstring(archive.read(xml_names[0]))
    signatures: list[list[tuple[str, float, tuple[str, int, int] | None, bool]]] = []
    for part in [node for node in root if local_name(node.tag) == "part"]:
        divisions = 1.0
        cursor = 0.0
        part_events: list[tuple[str, float, tuple[str, int, int] | None, bool]] = []
        for measure in [node for node in part if local_name(node.tag) == "measure"]:
            for item in measure:
                item_name = local_name(item.tag)
                if item_name == "attributes":
                    value = child_text(item, "divisions")
                    if value:
                        divisions = float(value)
                elif item_name in {"backup", "forward"}:
                    duration = float(child_text(item, "duration") or "0") / divisions
                    cursor += -duration if item_name == "backup" else duration
                elif item_name == "note":
                    duration = float(child_text(item, "duration") or "0") / divisions
                    pitch = next((node for node in item if local_name(node.tag) == "pitch"), None)
                    pitch_value = None
                    if pitch is not None:
                        pitch_value = (
                            child_text(pitch, "step"),
                            int(child_text(pitch, "octave") or "0"),
                            int(child_text(pitch, "alter") or "0"),
                        )
                    chord = any(local_name(node.tag) == "chord" for node in item)
                    part_events.append((measure.attrib.get("number", ""), round(cursor, 3), pitch_value, any(local_name(node.tag) == "rest" for node in item)))
                    part_events[-1] = (part_events[-1][0], round(duration, 3), pitch_value, part_events[-1][3])
                    if not chord:
                        cursor += duration
        signatures.append(part_events)
    return signatures


def exact_2025_url(url: str) -> bool:
    stem = Path(unquote(urlparse(url).path)).stem.lower()
    # The audit's strong SH25 set is limited to edition-named SH25 files.
    # X-Lis remains retained and usable as a distinct catalog witness, but it
    # is not one of those 13 SH25-named files and must stay alternate here.
    return stem.startswith("sh25-")


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    songs = {
        song["songNo"].lower(): song
        for song in corpus.get("songs", [])
        if "sh2025" in song.get("books", [])
    }
    entries = [(key, value) for key, value in manifest.get("entries", {}).items() if key.startswith("sh2025/")]
    entries.sort(key=lambda item: item[0])
    records: list[dict[str, object]] = []
    errors: list[str] = []

    for queue_id, entry in entries:
        song_no = str(entry.get("sourceRecordKey") or queue_id.split("/", 1)[1]).lower()
        song = songs.get(song_no)
        path = ROOT / entry.get("rawPath", "")
        source_url = str(entry.get("sourceUrl", ""))
        source_sha = sha256(path) if path.is_file() else ""
        source_bytes = path.stat().st_size if path.is_file() else 0
        reasons: list[str] = []
        if not path.is_file():
            reasons.append(f"local MXL is missing: {entry.get('rawPath', '')}")
            embedded: dict[str, object] = {}
        else:
            try:
                embedded = parse_score(path)
            except (OSError, zipfile.BadZipFile, ET.ParseError, ValueError) as exc:
                embedded = {}
                reasons.append(f"embedded MusicXML is not parseable: {exc}")

        source_metadata = (song or {}).get("metadataByBook", {}).get("sh2025", {})
        source_key = str(source_metadata.get("keySignature", ""))
        source_time = str(source_metadata.get("timeSignature", ""))
        expected_fifths, expected_mode = parse_key(source_key)
        declared_key = (embedded.get("keyDeclarations") or [{}])[0] if embedded else {}
        declared_time = (embedded.get("timeDeclarations") or [{}])[0] if embedded else {}
        embedded_fifths = declared_key.get("fifths", "")
        # A fifths value is not a mode declaration. Keep this empty when the
        # embedded XML omits mode; the source metadata is evidence, not a
        # license to rewrite the score's declaration.
        embedded_mode = declared_key.get("mode", "")
        embedded_time = f"{declared_time.get('beats', '')}/{declared_time.get('beatType', '')}" if embedded else ""

        if not exact_2025_url(source_url):
            reasons.append("catalog entry is an alternate-edition/source witness, not an edition-specific SH25 file")
        if not song:
            reasons.append("manifest page is not present in the current sh2025 corpus")
        if embedded and embedded.get("partCount") != 4:
            reasons.append(f"embedded score has {embedded.get('partCount')} parts; source structure requires four parts")
        if source_key and expected_fifths is not None:
            if embedded_fifths != str(expected_fifths):
                reasons.append(f"key mismatch: source metadata {source_key!r}, embedded fifths {embedded_fifths!r}")
            if not declared_key.get("mode"):
                reasons.append("embedded key declaration omits mode; source metadata supplies the mode")
            elif declared_key.get("mode", "").lower() != expected_mode:
                reasons.append(f"mode mismatch: source metadata {expected_mode!r}, embedded mode {declared_key.get('mode')!r}")
        elif exact_2025_url(source_url):
            reasons.append("source metadata does not record a usable key/mode")
        if source_time and embedded_time and embedded_time != source_time:
            reasons.append(f"meter mismatch: source metadata {source_time!r}, embedded {embedded_time!r}")
        elif exact_2025_url(source_url) and not source_time:
            reasons.append("source metadata does not record a usable time signature")
        if exact_2025_url(source_url) and embedded and not embedded.get("explicitShapeNoteheads"):
            reasons.append("embedded conventional-staff MusicXML has no explicit four-shape noteheads")

        existing_verified_source: dict[str, object] = {}
        if queue_id == "sh2025/50t":
            try:
                comparison = json.loads(EXISTING_50T_COMPARISON.read_text(encoding="utf-8"))
                source_image = ROOT / comparison["sourceAuthority"]["sourceImagePath"]
                derivative = ROOT / comparison["correctedDraft"]["path"]
                source_image_ok = (
                    source_image.is_file()
                    and sha256(source_image) == comparison["sourceAuthority"]["sourceImageSha256"]
                    and comparison["sourceAuthority"].get("immutable") is True
                )
                derivative_ok = derivative.is_file() and sha256(derivative) == comparison["correctedDraft"]["sha256"]
                events_equal = path.is_file() and derivative.is_file() and event_signature(path) == event_signature(derivative)
                direct_scan = comparison["sourceAuthority"]["directObservations"]
                existing_verified_source = {
                    "comparisonPath": str(EXISTING_50T_COMPARISON.relative_to(ROOT)),
                    "sourceImagePath": str(source_image.relative_to(ROOT)),
                    "sourceImageSha256": comparison["sourceAuthority"]["sourceImageSha256"],
                    "derivativePath": str(derivative.relative_to(ROOT)),
                    "derivativeSha256": comparison["correctedDraft"]["sha256"],
                    "sourceImageChecksumVerified": source_image_ok,
                    "derivativeChecksumVerified": derivative_ok,
                    "eventStreamsEqual": events_equal,
                    "directObservations": direct_scan,
                }
                if source_image_ok and derivative_ok and events_equal and direct_scan.get("key") == "C major" and direct_scan.get("timeSignature") == "4/4" and direct_scan.get("fourShapeNoteheadsVisible") is True:
                    reasons = []
                else:
                    reasons.append("existing 50t source/shape comparison does not meet its checksum, event-stream, or direct-scan checks")
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, zipfile.BadZipFile, ET.ParseError) as exc:
                reasons.append(f"existing 50t verified-source comparison could not be reconciled: {exc}")
        elif queue_id == "sh2025/55":
            try:
                comparison = json.loads(EXISTING_55_COMPARISON.read_text(encoding="utf-8"))
                source_pdf = ROOT / comparison["sourceAuthority"]["sourcePdfPath"]
                source_render = ROOT / comparison["sourceAuthority"]["sourceRenderPath"]
                derivative = ROOT / comparison["correctedDraft"]["path"]
                source_pdf_ok = (
                    source_pdf.is_file()
                    and sha256(source_pdf) == comparison["sourceAuthority"]["sourcePdfSha256"]
                    and comparison["sourceAuthority"].get("immutable") is True
                )
                source_render_ok = source_render.is_file() and sha256(source_render) == comparison["sourceAuthority"]["sourceRenderSha256"]
                candidate_ok = path.is_file() and sha256(path) == comparison["candidateWitness"]["candidateMusicXmlSha256"]
                derivative_ok = derivative.is_file() and sha256(derivative) == comparison["correctedDraft"]["sha256"]
                events_equal = path.is_file() and derivative.is_file() and event_signature(path) == event_signature(derivative)
                direct_scan = comparison["sourceAuthority"]["directObservations"]
                existing_verified_source = {
                    "comparisonPath": str(EXISTING_55_COMPARISON.relative_to(ROOT)),
                    "sourcePdfPath": str(source_pdf.relative_to(ROOT)),
                    "sourcePdfSha256": comparison["sourceAuthority"]["sourcePdfSha256"],
                    "sourceRenderPath": str(source_render.relative_to(ROOT)),
                    "sourceRenderSha256": comparison["sourceAuthority"]["sourceRenderSha256"],
                    "derivativePath": str(derivative.relative_to(ROOT)),
                    "derivativeSha256": comparison["correctedDraft"]["sha256"],
                    "sourcePdfChecksumVerified": source_pdf_ok,
                    "sourceRenderChecksumVerified": source_render_ok,
                    "candidateChecksumVerified": candidate_ok,
                    "derivativeChecksumVerified": derivative_ok,
                    "eventStreamsEqual": events_equal,
                    "directObservations": direct_scan,
                }
                if source_pdf_ok and source_render_ok and candidate_ok and derivative_ok and events_equal and direct_scan.get("key", "").startswith("A major") and direct_scan.get("timeSignature") == "4/4" and direct_scan.get("fourShapeNoteheadsVisible") is True:
                    reasons = []
                else:
                    reasons.append("existing 55 source/shape comparison does not meet its checksum, event-stream, or direct-scan checks")
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, zipfile.BadZipFile, ET.ParseError) as exc:
                reasons.append(f"existing 55 verified-source comparison could not be reconciled: {exc}")
        elif queue_id == "sh2025/415":
            try:
                comparison = json.loads(EXISTING_415_COMPARISON.read_text(encoding="utf-8"))
                source_pdf = ROOT / comparison["sourceAuthority"]["sourcePdfPath"]
                source_render = ROOT / comparison["sourceAuthority"]["sourceRenderPath"]
                derivative = ROOT / comparison["correctedDraft"]["path"]
                source_pdf_ok = (
                    source_pdf.is_file()
                    and sha256(source_pdf) == comparison["sourceAuthority"]["sourcePdfSha256"]
                    and comparison["sourceAuthority"].get("immutable") is True
                )
                source_render_ok = source_render.is_file() and sha256(source_render) == comparison["sourceAuthority"]["sourceRenderSha256"]
                candidate_ok = path.is_file() and sha256(path) == comparison["candidateWitness"]["candidateMusicXmlSha256"]
                derivative_ok = derivative.is_file() and sha256(derivative) == comparison["correctedDraft"]["sha256"]
                events_equal = path.is_file() and derivative.is_file() and event_signature(path) == event_signature(derivative)
                direct_scan = comparison["sourceAuthority"]["directObservations"]
                existing_verified_source = {
                    "comparisonPath": str(EXISTING_415_COMPARISON.relative_to(ROOT)),
                    "sourcePdfPath": str(source_pdf.relative_to(ROOT)),
                    "sourcePdfSha256": comparison["sourceAuthority"]["sourcePdfSha256"],
                    "sourceRenderPath": str(source_render.relative_to(ROOT)),
                    "sourceRenderSha256": comparison["sourceAuthority"]["sourceRenderSha256"],
                    "derivativePath": str(derivative.relative_to(ROOT)),
                    "derivativeSha256": comparison["correctedDraft"]["sha256"],
                    "sourcePdfChecksumVerified": source_pdf_ok,
                    "sourceRenderChecksumVerified": source_render_ok,
                    "candidateChecksumVerified": candidate_ok,
                    "derivativeChecksumVerified": derivative_ok,
                    "eventStreamsEqual": events_equal,
                    "directObservations": direct_scan,
                }
                if source_pdf_ok and source_render_ok and candidate_ok and derivative_ok and events_equal and direct_scan.get("key", "").startswith("F major") and direct_scan.get("timeSignature") == "4/4" and direct_scan.get("fourShapeNoteheadsVisible") is True:
                    reasons = []
                else:
                    reasons.append("existing 415 source/shape comparison does not meet its checksum, event-stream, or direct-scan checks")
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, zipfile.BadZipFile, ET.ParseError) as exc:
                reasons.append(f"existing 415 verified-source comparison could not be reconciled: {exc}")

        shape_status = "explicit-four-shape-noteheads" if embedded.get("explicitShapeNoteheads") else "not-encoded-in-embedded-musicxml"
        exact_structural = exact_2025_url(source_url) and not any(
            reason.startswith(("catalog entry", "embedded score has", "key mismatch", "mode mismatch", "meter mismatch", "source metadata", "embedded conventional"))
            for reason in reasons
        )
        safe = bool(exact_structural and embedded.get("explicitShapeNoteheads"))
        verified_existing_source = queue_id in {"sh2025/50t", "sh2025/55", "sh2025/415"} and not reasons and bool(existing_verified_source)
        status = "verified-with-correction-needed" if verified_existing_source else "autonomously-blocked"
        records.append({
            "queueId": queue_id,
            "songNo": song_no,
            "title": (song or {}).get("title", ""),
            "sourceUrl": source_url,
            "sourceEdition": entry.get("sourceEdition", "sh2025"),
            "catalogVariant": entry.get("catalogVariant", ""),
            "catalogSection": entry.get("catalogSection", ""),
            "catalogLabel": entry.get("label", ""),
            "rawPath": entry.get("rawPath", ""),
            "sourceBytes": source_bytes,
            "sourceSha256": source_sha,
            "recordSourceMetadata": {
                "keySignature": source_key,
                "meter": source_metadata.get("meter", ""),
                "timeSignature": source_time,
                "composer": source_metadata.get("composer", ""),
                "sourceUrls": source_metadata.get("sourceUrls", []),
            },
            "embeddedMusicXml": embedded,
            "evidence": {
                "editionIdentity": "exact-sh25-url" if exact_2025_url(source_url) else "alternate-catalog-witness",
                "keyMode": {
                    "source": source_key,
                    "embeddedFifths": embedded_fifths,
                    "embeddedMode": embedded_mode,
                    "supported": bool(source_key and expected_fifths is not None and embedded_fifths == str(expected_fifths)),
                },
                "meter": {
                    "source": source_time,
                    "embedded": embedded_time,
                    "supported": bool(source_time and embedded_time == source_time),
                },
                "parts": {
                    "sourceExpected": 4,
                    "embedded": embedded.get("partCount", 0),
                    "supported": embedded.get("partCount") == 4,
                },
                "shapeNoteheads": {
                    "status": shape_status,
                    "explicitCount": embedded.get("explicitShapeNoteheads", 0),
                    "values": embedded.get("shapeValues", []),
                    "supported": bool(embedded.get("explicitShapeNoteheads")),
                },
            },
            "comparisonStatus": status,
            "safeToPromote": safe,
            "blockedReasons": reasons,
        })
        if existing_verified_source:
            records[-1]["verifiedSourceComparison"] = existing_verified_source
            records[-1]["promotionDisposition"] = "authoritative-2025-source-retained; correction-needed-before-promotion"
            records[-1]["safeToPromote"] = False
            if queue_id == "sh2025/50t":
                # The raw SH25 archive is authoritative for its source events,
                # but it is not itself the complete shape/lyrics artifact.
                # Keep that distinction explicit in the audit while attaching
                # the verified derivative evidence separately.
                records[-1]["sourceEncodingAssessment"] = {
                    "rawMusicXml": {
                        "shapeNoteheads": "partial-in-raw-MusicXML",
                        "explicitShapeNoteheads": embedded.get("explicitShapeNoteheads", 0),
                        "lyrics": "omitted-in-raw-MusicXML",
                        "complete": False,
                    },
                    "verifiedDerivative": {
                        "path": comparison.get("correctedDraft", {}).get("path", ""),
                        "sha256": comparison.get("correctedDraft", {}).get("sha256", ""),
                        "shapeNoteheads": comparison.get("correctedDraft", {}).get("summary", {}).get("shapeNoteheadsAdded", 0),
                        "lyrics": "omitted; notation remains usable",
                        "complete": True,
                    },
                }
                records[-1]["evidence"]["shapeNoteheads"]["supportedInVerifiedDerivative"] = True
                records[-1]["evidence"]["shapeNoteheads"]["supportedInRawMusicXml"] = False

    if len(entries) != 26:
        errors.append(f"expected 26 sh2025 MusicXML links, found {len(entries)}")
    for record in records:
        if not record["sourceSha256"]:
            errors.append(f"{record['queueId']}: source checksum unavailable")

    status_counts: dict[str, int] = {}
    for record in records:
        status = str(record["comparisonStatus"])
        status_counts[status] = status_counts.get(status, 0) + 1
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "version": 1,
        "edition": "sh2025",
        "catalogSection": "Sacred Harp (2025 Revision)",
    "policy": "Only exact SH25 MusicXML with four-part structure, source-supported key/mode/meter, and either explicit four-shape noteheads or a verified direct source comparison that preserves the event stream is safe to promote. Alternate witnesses and unresolved conventional-staff files remain blocked references.",
        "summary": {
            "catalogEntries": len(records),
            "safeToPromote": sum(bool(record["safeToPromote"]) for record in records),
            "statusCounts": status_counts,
            "errors": len(errors),
        },
        "errors": errors,
        "records": records,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
