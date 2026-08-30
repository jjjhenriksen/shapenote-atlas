#!/usr/bin/env python3
"""Create bounded, fail-closed correction candidates for Moreno and Southminster.

Only the two assigned queue IDs are handled.  The retained raw source-scan OMR
is copied into isolated agent-04 output paths, source-observed key/mode/meter
metadata is applied, and four-shape noteheads are derived from retained written
pitch steps.  No pitch, rhythm, lyric, repeat, or part event is invented when
the source raster and OMR do not establish it unambiguously.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "work/agent-04-shapes"

TARGETS: dict[str, dict[str, Any]] = {
    "140": {
        "queueId": "sh2025/140",
        "title": "Moreno",
        "sourceImage": "work/source-images/2025/140-moreno-1a2f916fe7.jpg",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/140-Moreno/140.jpg",
        "rawOmr": "work/omr/140-moreno/source.mxl",
        "normalizedOmr": "work/omr/cleaned-normalized-v2-140-moreno-1a2f916fe7/work__source-images__2025__140-moreno-1a2f916fe7.mxl",
        "sourceDraft": "work/omr/source-shape-review-drafts/2025/140-source-shape-review.mxl",
        "key": "E minor",
        "mode": "minor",
        "fifths": "1",
        "beats": "2",
        "beatType": "4",
        "meter": "Long Meter with Hallelujah (L.M.H.)",
        "composer": "Smith's Divine Hymns, 1794",
        "arranger": "Aldo Thomas Ceresa, 2008",
        "measuresByPart": {"P1": 16, "P2": 16, "P3": 16, "P4": 16},
        "shapeMap": {"A": "sol", "B": "la", "C": "fa", "D": "sol", "E": "la", "F": "mi", "G": "fa"},
        "watermarkFinding": "The diagonal DO NOT COPY watermark crosses the central/lower source systems and lyric region; events beneath it are not safely attributable note-for-note from this raster.",
        "durationFinding": "Retained raw OMR has 132 pitched events but duration failures in P1 m11, P2 m1/m2/m3/m6/m7/m8/m11/m12/m15/m16, P3 m3/m11, and P4 m6/m15; the normalized source-shape draft changes event topology and cannot resolve these failures.",
        "candidateName": "140-moreno-agent-04-correction-needed.mxl",
    },
    "161": {
        "queueId": "sh2025/161",
        "title": "Southminster",
        "sourceImage": "work/source-images/2025/161-southminster-9fb4c82f41.jpg",
        "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/161-Southminster/161.jpg",
        "rawOmr": "work/omr/161-southminster/source.mxl",
        "normalizedOmr": "work/omr/cleaned-normalized-v2-161-southminster-9fb4c82f41/work__source-images__2025__161-southminster-9fb4c82f41.mxl",
        "sourceDraft": "work/omr/source-shape-review-drafts/2025/161-source-shape-review.mxl",
        "key": "B-flat major",
        "mode": "major",
        "fifths": "-2",
        "beats": "4",
        "beatType": "4",
        "meter": "6,6,9,6,6,9",
        "composer": "Charles Wesley, 1767",
        "arranger": "Steven Brett, 2017",
        "measuresByPart": {"P1": 22, "P2": 22, "P3": 22, "P4": 22},
        "shapeMap": {"A": "mi", "B": "fa", "C": "sol", "D": "la", "E": "fa", "F": "sol", "G": "la"},
        "watermarkFinding": "The diagonal DO NOT COPY watermark crosses central source systems, including lower vocal material; events beneath it are not safely attributable note-for-note from this raster.",
        "durationFinding": "Retained raw OMR has 190 pitched events, with duration failures across P1 16/22, P2 20/22, P3 20/22, and P4 13/22 measures; the normalized source-shape draft changes event topology and cannot resolve these failures.",
        "candidateName": "161-southminster-agent-04-correction-needed.mxl",
    },
}


def local(value: str) -> Path:
    return ROOT / value.lstrip("/")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(parent: ET.Element | None, name: str) -> list[ET.Element]:
    return [item for item in (parent or []) if clean(item.tag) == name]


def first(parent: ET.Element | None, name: str) -> ET.Element | None:
    return next(iter(children(parent, name)), None)


def text(parent: ET.Element | None, name: str, default: str = "") -> str:
    item = first(parent, name)
    return item.text.strip() if item is not None and item.text else default


def put_child(parent: ET.Element, name: str, value: str) -> None:
    items = children(parent, name)
    item = items[0] if items else ET.SubElement(parent, name)
    item.text = value
    for duplicate in items[1:]:
        parent.remove(duplicate)


def put_field(identification: ET.Element, name: str, value: str) -> None:
    miscellaneous = first(identification, "miscellaneous")
    if miscellaneous is None:
        miscellaneous = ET.SubElement(identification, "miscellaneous")
    items = [item for item in children(miscellaneous, "miscellaneous-field") if item.attrib.get("name") == name]
    item = items[0] if items else ET.SubElement(miscellaneous, "miscellaneous-field", {"name": name})
    item.text = value
    for duplicate in items[1:]:
        miscellaneous.remove(duplicate)


def source_event_signature(root: ET.Element) -> dict[str, list[tuple[str, str, str, str]]]:
    result: dict[str, list[tuple[str, str, str, str]]] = {}
    for part in children(root, "part"):
        events: list[tuple[str, str, str, str]] = []
        for measure in children(part, "measure"):
            number = measure.attrib.get("number", "")
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                if pitch is None:
                    value = "rest" if first(note, "rest") is not None else "unknown"
                else:
                    value = ":".join([text(pitch, "step"), text(pitch, "alter", "0"), text(pitch, "octave")])
                events.append((number, value, text(note, "duration"), text(note, "type")))
        result[part.attrib.get("id", "")] = events
    return result


def duration_end(measure: ET.Element) -> int:
    cursor = maximum = 0
    for item in measure:
        duration = int(text(item, "duration", "0") or 0)
        kind = clean(item.tag)
        if kind == "note":
            if first(item, "chord") is None:
                cursor += duration
            maximum = max(maximum, cursor)
        elif kind == "backup":
            cursor -= duration
        elif kind == "forward":
            cursor += duration
    return maximum


def stats(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        xml_name = next(name for name in archive.namelist() if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/"))
        root = ET.fromstring(archive.read(xml_name))
    parts = children(root, "part")
    result: dict[str, Any] = {"sha256": sha256(path), "parts": len(parts), "measuresByPart": {}, "eventsByPart": {}, "pitchedEventsByPart": {}, "durationEndsByPart": {}, "noteheads": 0, "shapeCounts": {}}
    shapes: dict[str, int] = {}
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = children(part, "measure")
        result["measuresByPart"][part_id] = len(measures)
        result["eventsByPart"][part_id] = 0
        result["pitchedEventsByPart"][part_id] = 0
        result["durationEndsByPart"][part_id] = {}
        for measure in measures:
            result["durationEndsByPart"][part_id][measure.attrib.get("number", "")] = duration_end(measure)
            for note in children(measure, "note"):
                result["eventsByPart"][part_id] += 1
                pitch = first(note, "pitch")
                if pitch is None:
                    continue
                result["pitchedEventsByPart"][part_id] += 1
                notehead = first(note, "notehead")
                if notehead is not None and notehead.text:
                    result["noteheads"] += 1
                    value = notehead.text.strip().lower()
                    shapes[value] = shapes.get(value, 0) + 1
    result["pitchedEvents"] = sum(result["pitchedEventsByPart"].values())
    result["shapeCounts"] = dict(sorted(shapes.items()))
    return result


def read_xml(path: Path) -> tuple[str, ET.Element, dict[str, bytes]]:
    with zipfile.ZipFile(path) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    xml_name = next(name for name in members if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/"))
    return xml_name, ET.fromstring(members[xml_name]), members


def update_xml(root: ET.Element, config: dict[str, Any]) -> tuple[int, int, dict[str, list[tuple[str, str, str, str]]]]:
    before = source_event_signature(root)
    noteheads_added = 0
    parts = children(root, "part")
    for part in parts:
        for measure in children(part, "measure"):
            attributes = first(measure, "attributes")
            if attributes is None:
                attributes = ET.Element("attributes")
                measure.insert(0, attributes)
            key = first(attributes, "key")
            if key is None:
                key = ET.SubElement(attributes, "key")
            put_child(key, "fifths", config["fifths"])
            put_child(key, "mode", config["mode"])
            time = first(attributes, "time")
            if time is None:
                time = ET.SubElement(attributes, "time")
            put_child(time, "beats", config["beats"])
            put_child(time, "beat-type", config["beatType"])
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                if pitch is None:
                    continue
                step = text(pitch, "step").upper()
                shape = config["shapeMap"].get(step)
                if not shape:
                    continue
                old = children(note, "notehead")
                notehead = old[0] if old else ET.Element("notehead")
                notehead.text = shape
                for duplicate in old[1:]:
                    note.remove(duplicate)
                if not old:
                    stem_index = next((index for index, child in enumerate(note) if clean(child.tag) == "stem"), len(note))
                    note.insert(stem_index, notehead)
                noteheads_added += 1
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    fields = {
        "atlas-queue-id": config["queueId"],
        "atlas-transcription-status": "correction-needed-source-event-mismatch",
        "atlas-review-status": "agent-04-source-correction-needed",
        "atlas-safe-to-promote": "false",
        "atlas-source-image": config["sourceImage"],
        "atlas-source-image-sha256": sha256(local(config["sourceImage"])),
        "atlas-source-key": config["key"],
        "atlas-source-mode": config["mode"],
        "atlas-source-time-signature": f"{config['beats']}/{config['beatType']}",
        "atlas-source-meter": config["meter"],
        "atlas-source-composer": config["composer"],
        "atlas-source-arranger": config["arranger"],
        "atlas-shape-encoding": "derived from retained written pitch steps and source-observed key; not direct per-event source engraving verification",
        "atlas-source-comparison": "partial direct source-image review; full event-by-event source agreement is not established",
        "atlas-pitch-rhythm-corrections": "none; retained OMR pitch/rhythm events are unchanged because unresolved mismatches cannot be safely repaired from the obscured raster",
        "atlas-lyrics": "source lyrics visible but not encoded because retained OMR has no directly aligned lyric underlay",
        "atlas-repeat-ending": "source repeat/ending treatment visible but not fully encoded because retained OMR semantics are incomplete",
        "atlas-provenance-policy": "immutable source image remains authoritative; this candidate is isolated review evidence only and cannot be promoted",
        "atlas-blocker": config["durationFinding"] + " " + config["watermarkFinding"],
    }
    for name, value in fields.items():
        put_field(identification, name, value)
    return noteheads_added, len(parts), before


def compare_events(raw: dict[str, list[tuple[str, str, str, str]]], draft: dict[str, list[tuple[str, str, str, str]]]) -> dict[str, Any]:
    comparison: dict[str, Any] = {}
    for part in sorted(set(raw) | set(draft)):
        a = raw.get(part, [])
        b = draft.get(part, [])
        opcodes = difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes()
        differences = sum((i2 - i1) + (j2 - j1) for tag, i1, i2, j1, j2 in opcodes if tag != "equal")
        comparison[part] = {
            "rawEvents": len(a),
            "sourceShapeDraftEvents": len(b),
            "sequenceDifferenceUnits": differences,
            "eventByEventAgreement": False,
            "verdict": "unresolved-source-event-mismatch" if differences else "not-proven-direct-source-match",
        }
    return comparison


def build_record(config: dict[str, Any]) -> dict[str, Any]:
    source_image = local(config["sourceImage"])
    raw = local(config["rawOmr"])
    normalized = local(config["normalizedOmr"])
    source_draft = local(config["sourceDraft"])
    output = OUTPUT_ROOT / config["queueId"].replace("/", "-") / config["candidateName"]
    output.parent.mkdir(parents=True, exist_ok=True)
    xml_name, root, members = read_xml(raw)
    noteheads_added, parts, raw_events = update_xml(root, config)
    members[xml_name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    raw_stats = stats(raw)
    draft_stats = stats(source_draft)
    candidate_stats = stats(output)
    normalized_stats = stats(normalized)
    receipt = {
        "queueId": config["queueId"],
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": config["queueId"].split("/", 1)[1],
        "title": config["title"],
        "status": "correction-needed-source-event-mismatch",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "directSourceShapeEvidence": False,
        "sourceAuthority": {
            "sourceImagePath": config["sourceImage"],
            "sourceImageUrl": config["sourceImageUrl"],
            "sourceImageSha256": sha256(source_image),
            "immutable": True,
            "directObservations": {
                "key": config["key"],
                "mode": config["mode"],
                "meter": config["meter"],
                "composer": config["composer"],
                "arranger": config["arranger"],
                "parts": parts,
                "measuresByPart": config["measuresByPart"],
                "fourGeometricNoteheadFormsVisible": True,
                "lyricsVisible": True,
                "repeatEndingTreatmentVisible": True,
                "watermarkIntersectsNotation": True,
            },
        },
        "inputOmr": {"path": config["rawOmr"], **raw_stats, "status": "retained-source-scan-omr-review-only"},
        "sourceShapeDraft": {"path": config["sourceDraft"], **draft_stats, "status": "derived-review-only"},
        "normalizedOmr": {"path": config["normalizedOmr"], **normalized_stats, "status": "review-only-comparison-witness"},
        "eventComparison": compare_events(raw_events, source_event_signature(read_xml(source_draft)[1])),
        "correction": {
            "candidatePath": output.relative_to(ROOT).as_posix(),
            "candidateSha256": sha256(output),
            "candidateStats": candidate_stats,
            "sourceObservedMetadataApplied": ["key", "mode", "time signature", "meter", "composer", "arranger"],
            "derivedFourShapeNoteheadsAdded": noteheads_added,
            "pitchEdits": 0,
            "rhythmEdits": 0,
            "partStructureEdits": 0,
            "lyricsAdded": 0,
            "repeatEndingEdits": 0,
            "eventStreamPreservedFromRawOmr": True,
        },
        "blockingFindings": [
            "The immutable source engraving visibly establishes the printed key, mode, meter, four parts, song topology, and four geometric notehead vocabulary; these observations were applied only as metadata and shape-derivation context.",
            config["durationFinding"],
            "The existing normalized source-shape draft is not a reliable correction witness: its event sequence differs from retained raw OMR, so it was compared but not merged into the candidate.",
            "The retained OMR has no aligned lyrics and incomplete repeat/ending semantics; none were fabricated.",
            config["watermarkFinding"],
            "The four-shape tags in this candidate remain derived from written pitch steps plus the source-observed key. No direct per-event visual shape comparison is claimed, so the candidate cannot be source-verified or promoted.",
        ],
        "nextAction": "human-event-by-event-transcription-required-before-promotion",
        "policy": "Keep raw OMR, normalized OMR, source-shape draft, and immutable source image unchanged. This candidate and receipt are isolated agent-04 review artifacts.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    return receipt


def main() -> int:
    receipts = [build_record(config) for config in TARGETS.values()]
    receipt_path = OUTPUT_ROOT / "agent-04-source-correction-receipt.json"
    receipt = {
        "kind": "agent-04-source-correction-receipt",
        "version": "1",
        "scope": [config["queueId"] for config in TARGETS.values()],
        "policy": "Only sh2025/140 and sh2025/161 were processed. No other queue ID, public ledger, UI file, immutable original, or prior correction artifact was written.",
        "summary": {
            "records": len(receipts),
            "blocked": sum(item["autonomousDecision"] == "blocked" for item in receipts),
            "safeToPromote": sum(item["safeToPromote"] is True for item in receipts),
            "directSourceShapeEvidence": sum(item["directSourceShapeEvidence"] is True for item in receipts),
            "pitchEdits": sum(item["correction"]["pitchEdits"] for item in receipts),
            "rhythmEdits": sum(item["correction"]["rhythmEdits"] for item in receipts),
            "partStructureEdits": sum(item["correction"]["partStructureEdits"] for item in receipts),
        },
        "records": receipts,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": receipt_path.relative_to(ROOT).as_posix(), **receipt["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
