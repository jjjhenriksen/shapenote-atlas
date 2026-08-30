#!/usr/bin/env python3
"""Build isolated, fail-closed source-verification candidates for two SH25 records."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "work/agent-04-shapes/blocker-clearing-561-562"

TARGETS = {
    "sh2025/561": {
        "songNo": "561",
        "title": "Cunningham",
        "sourceImage": "work/source-images/2025/561-cunningham-0c0d2be29e.jpg",
        "rawOmr": "work/omr/561-cunningham/source.mxl",
        "shapeDraft": "work/omr/source-shape-review-drafts/2025/561-source-shape-review.mxl",
        "shapeDraftJson": "work/omr/source-shape-review-drafts/2025/561-source-shape-review.json",
        "playableDraft": "public/draft-scores/0eb5199fcf22be6e6113eaf8.json",
        "expectedKey": "E minor",
        "mode": "minor",
        "fifths": "1",
        "timeSignature": "3/2",
        "beats": "3",
        "beatType": "2",
        "meter": "8s & 7s",
        "composer": "Thomas Hastings, 1824",
        "arranger": "Robert Stoddard, 2011",
        "sourceSystems": [6, 7],
        "sourceAudiverisMeasures": 13,
        "candidate": "561-cunningham-agent-04-source-candidate.mxl",
        "durationTarget": 3,
        "durationTargetUnits": 6,
        "watermark": "The diagonal DO NOT COPY watermark crosses the middle/lower systems and lyric region.",
    },
    "sh2025/562": {
        "songNo": "562",
        "title": "Mournful Joy",
        "sourceImage": "work/source-images/2025/562-mournful-joy-46f7ed1f29.jpg",
        "rawOmr": "work/omr/562-mournful-joy/source.mxl",
        "shapeDraft": "work/omr/source-shape-review-drafts/2025/562-source-shape-review.mxl",
        "shapeDraftJson": "work/omr/source-shape-review-drafts/2025/562-source-shape-review.json",
        "playableDraft": "public/draft-scores/39d7d31d8f617e2da2d73b54.json",
        "expectedKey": "E minor",
        "mode": "minor",
        "fifths": "1",
        "timeSignature": "4/4",
        "beats": "4",
        "beatType": "4",
        "meter": "Common Meter Double (8,6,8,6,8,6,8,6)",
        "composer": "John Newton, 1779",
        "arranger": "William Cleary, 2018",
        "sourceSystems": [10, 7, 9],
        "sourceAudiverisMeasures": 26,
        "candidate": "562-mournful-joy-agent-04-source-candidate.mxl",
        "durationTarget": 4,
        "durationTargetUnits": 8,
        "watermark": "The diagonal DO NOT COPY watermark crosses the central/lower systems and lyric region.",
    },
}

SHAPES = {"A": "sol", "B": "la", "C": "fa", "D": "sol", "E": "la", "F": "mi", "G": "fa"}
ALLOWED_SHAPES = {"fa", "sol", "la", "mi"}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def first(parent: ET.Element | None, name: str) -> ET.Element | None:
    if parent is None:
        return None
    return next((child for child in parent if local_name(child.tag) == name), None)


def children(parent: ET.Element | None, name: str) -> list[ET.Element]:
    if parent is None:
        return []
    return [child for child in parent if local_name(child.tag) == name]


def child_text(parent: ET.Element | None, name: str) -> str:
    child = first(parent, name)
    return (child.text or "").strip() if child is not None else ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_mxl(path: Path) -> tuple[bytes, str]:
    with zipfile.ZipFile(path) as archive:
        member = next(name for name in archive.namelist() if name.endswith(".xml") and not name.startswith("META-INF/"))
        return archive.read(member), member


def put_child(parent: ET.Element, name: str, value: str) -> None:
    existing = children(parent, name)
    item = existing[0] if existing else ET.SubElement(parent, name)
    item.text = value
    for duplicate in existing[1:]:
        parent.remove(duplicate)


def add_field(identification: ET.Element, name: str, value: str) -> None:
    miscellaneous = first(identification, "miscellaneous")
    if miscellaneous is None:
        miscellaneous = ET.SubElement(identification, "miscellaneous")
    matching = [item for item in children(miscellaneous, "miscellaneous-field") if item.attrib.get("name") == name]
    item = matching[0] if matching else ET.SubElement(miscellaneous, "miscellaneous-field", {"name": name})
    item.text = value
    for duplicate in matching[1:]:
        miscellaneous.remove(duplicate)


def event_signature(root: ET.Element) -> dict[str, list[tuple[str, str, str, str, str]]]:
    result: dict[str, list[tuple[str, str, str, str, str]]] = {}
    for part in children(root, "part"):
        events: list[tuple[str, str, str, str, str]] = []
        for measure in children(part, "measure"):
            number = measure.attrib.get("number", "")
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                events.append((number, child_text(pitch, "step"), child_text(pitch, "alter"), child_text(pitch, "octave"), child_text(note, "duration")))
        result[part.attrib.get("id", "")] = events
    return result


def duration_end(measure: ET.Element) -> int:
    cursor = 0
    maximum = 0
    for item in measure:
        name = local_name(item.tag)
        duration = int(float(child_text(item, "duration") or "0"))
        if name == "note":
            cursor += duration
            maximum = max(maximum, cursor)
        elif name == "backup":
            cursor -= duration
        elif name == "forward":
            cursor += duration
    return maximum


def xml_stats(root: ET.Element, duration_target_units: int) -> dict[str, object]:
    per_part: dict[str, object] = {}
    total_notes = 0
    total_pitched = 0
    total_noteheads = 0
    for part in children(root, "part"):
        divisions = 1.0
        measures = children(part, "measure")
        notes = 0
        pitched = 0
        noteheads = 0
        ends: dict[str, float] = {}
        for measure in measures:
            declared = child_text(first(measure, "attributes"), "divisions")
            if declared:
                divisions = float(declared)
            ends[measure.attrib.get("number", "")] = duration_end(measure)
            for note in children(measure, "note"):
                notes += 1
                if first(note, "pitch") is not None:
                    pitched += 1
                    head = first(note, "notehead")
                    if head is not None and (head.text or "").strip():
                        noteheads += 1
        failures = {number: end for number, end in ends.items() if end != duration_target_units}
        per_part[part.attrib.get("id", "")] = {
            "measures": len(measures),
            "notes": notes,
            "pitchedEvents": pitched,
            "noteheads": noteheads,
            "durationEnds": ends,
            "durationFailures": failures,
        }
        total_notes += notes
        total_pitched += pitched
        total_noteheads += noteheads
    return {"parts": len(children(root, "part")), "notes": total_notes, "pitchedEvents": total_pitched, "noteheads": total_noteheads, "byPart": per_part}


def playable_summary(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    declarations = data.get("musicXmlKeyDeclarations", [])
    return {
        "path": str(path.relative_to(ROOT)),
        "sourceUrl": data.get("sourceUrl"),
        "keySignature": data.get("keySignature"),
        "timeSignature": data.get("timeSignature"),
        "keyDeclarations": declarations,
        "keyEvidence": data.get("keyEvidence"),
        "transposition": data.get("transposition"),
        "sourceMeasureCounts": data.get("sourceMeasureCounts"),
        "parts": [{"name": part.get("name"), "events": len(part.get("events", []))} for part in data.get("parts", [])],
        "eventCount": sum(len(part.get("events", [])) for part in data.get("parts", [])),
    }


def update_candidate(xml_bytes: bytes, config: dict[str, object], source_hash: str, raw_hash: str, shape_hash: str, playable_path: str) -> tuple[bytes, dict[str, object]]:
    root = ET.fromstring(xml_bytes)
    raw_signature = event_signature(root)
    stats_before = xml_stats(root, int(config["durationTargetUnits"]))
    shape_count = 0
    for part in children(root, "part"):
        measure = next(iter(children(part, "measure")), None)
        if measure is None:
            continue
        attributes = first(measure, "attributes")
        if attributes is None:
            attributes = ET.Element("attributes")
            measure.insert(0, attributes)
        key = first(attributes, "key")
        if key is None:
            key = ET.SubElement(attributes, "key")
        put_child(key, "fifths", str(config["fifths"]))
        put_child(key, "mode", str(config["mode"]))
        clock = first(attributes, "time")
        if clock is None:
            clock = ET.SubElement(attributes, "time")
        put_child(clock, "beats", str(config["beats"]))
        put_child(clock, "beat-type", str(config["beatType"]))
        for measure in children(part, "measure"):
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                if pitch is None:
                    continue
                shape = SHAPES.get(child_text(pitch, "step").upper())
                if shape is None:
                    continue
                for old in children(note, "notehead"):
                    note.remove(old)
                notehead = ET.Element("notehead")
                notehead.text = shape
                stem_index = next((index for index, item in enumerate(note) if local_name(item.tag) == "stem"), len(note))
                note.insert(stem_index, notehead)
                shape_count += 1
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    fields = {
        "atlas-review-queue-id": str(config["queueId"]),
        "atlas-transcription-status": "autonomously-blocked-source-event-mismatch",
        "atlas-review-status": "agent-04-source-verification-needed",
        "atlas-safe-to-promote": "false",
        "atlas-source-key": str(config["expectedKey"]),
        "atlas-source-mode": str(config["mode"]),
        "atlas-source-time-signature": str(config["timeSignature"]),
        "atlas-source-meter": str(config["meter"]),
        "atlas-source-comparison": "global source metadata and four-shape vocabulary observed; no direct event-by-event alignment established",
        "atlas-shape-encoding": "derived from retained written pitch steps and source-observed E-minor key via relative G-major four-shape spelling; not per-event source verified",
        "atlas-playable-score": f"{playable_path}; playable draft retained, but key mode/time and event identity remain source-unverified",
        "atlas-source-image-sha256": source_hash,
        "atlas-source-omr-sha256": raw_hash,
        "atlas-source-shape-draft-sha256": shape_hash,
        "atlas-event-corrections": "none; raw pitch/rhythm/part event stream preserved because source alignment is unresolved",
        "atlas-lyrics-repeat-status": "source-visible lyrics/repeats/endings not reconstructed in candidate",
        "atlas-blocker": str(config["watermark"]),
    }
    for name, value in fields.items():
        add_field(identification, name, value)
    candidate_stats = xml_stats(root, int(config["durationTargetUnits"]))
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), {
        "rawEventSignature": raw_signature,
        "rawStats": stats_before,
        "candidateStats": candidate_stats,
        "derivedFourShapeNoteheads": shape_count,
        "pitchEdits": 0,
        "rhythmEdits": 0,
        "partStructureEdits": 0,
        "eventStreamPreserved": raw_signature == event_signature(root),
    }


def build_record(queue_id: str, config: dict[str, object]) -> dict[str, object]:
    config = {**config, "queueId": queue_id}
    source = ROOT / str(config["sourceImage"])
    raw = ROOT / str(config["rawOmr"])
    shape_draft = ROOT / str(config["shapeDraft"])
    shape_json = ROOT / str(config["shapeDraftJson"])
    playable = ROOT / str(config["playableDraft"])
    for path in (source, raw, shape_draft, shape_json, playable):
        if not path.is_file():
            raise FileNotFoundError(path)
    raw_xml, raw_member = read_mxl(raw)
    shape_xml, shape_member = read_mxl(shape_draft)
    raw_root = ET.fromstring(raw_xml)
    shape_root = ET.fromstring(shape_xml)
    source_hash = sha256(source)
    raw_hash = sha256(raw)
    shape_hash = sha256(shape_draft)
    candidate_xml, candidate_info = update_candidate(raw_xml, config, source_hash, raw_hash, shape_hash, str(config["playableDraft"]))
    output = OUTPUT_ROOT / str(config["candidate"])
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(raw) as source_zip, zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target_zip:
        for info in source_zip.infolist():
            target_zip.writestr(info, candidate_xml if info.filename == raw_member else source_zip.read(info.filename))
    raw_stats = candidate_info["rawStats"]
    shape_stats = xml_stats(shape_root, int(config["durationTargetUnits"]))
    candidate_stats = candidate_info["candidateStats"]
    shape_manifest = json.loads(shape_json.read_text(encoding="utf-8"))
    playable_stats = playable_summary(playable)
    expected_raw_events = sum(item["events"] for item in playable_stats["parts"])
    direct_shape_events = 0
    blocking = [
        f"The immutable page directly shows {config['expectedKey']} ({config['mode']}), {config['timeSignature']}, four vocal parts, lyrics, and the four geometric notehead vocabulary; these are source-observed global facts, not event-level verification.",
        f"Audiveris reports {config['sourceAudiverisMeasures']} source measures across systems {config['sourceSystems']}, while retained raw OMR exports {raw_stats['byPart']['P1']['measures']} measures per part; the existing source-shape draft exports {shape_stats['byPart']['P1']['measures']} XML measures per part. This topology disagreement prevents event-by-event promotion.",
        f"The retained raw OMR has {raw_stats['pitchedEvents']} pitched events and {sum(len(item['durationFailures']) for item in raw_stats['byPart'].values())} duration failures against the {config['timeSignature']} target; its source-shape draft has {shape_stats['pitchedEvents']} pitched events and {shape_stats['noteheads']} derived shape tags. These are not an aligned source witness.",
        f"The existing playable draft has {playable_stats['eventCount']} events in four parts and is usable as playback evidence, but its key evidence is {playable_stats['keyEvidence'].get('status') if isinstance(playable_stats['keyEvidence'], dict) else 'unavailable'}, its mode declarations are incomplete, and its time signature is blank; it is not source-verified.",
        "No direct per-event source-shape matches are admitted: the visible vocabulary proves only that four forms are used, while the draft tags are derived from OMR pitch steps. No pitch, rhythm, lyric, repeat, ending, or part change was guessed.",
        str(config["watermark"]),
    ]
    return {
        "queueId": queue_id,
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": config["songNo"],
        "title": config["title"],
        "status": "autonomously-blocked-source-event-mismatch",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "sourceObservedMetadata": {
            "key": config["expectedKey"], "mode": config["mode"], "timeSignature": config["timeSignature"], "meter": config["meter"],
            "composer": config["composer"], "arranger": config["arranger"], "parts": 4, "fourGeometricNoteheadFormsVisible": True,
            "lyricsVisible": True, "repeatEndingTreatmentVisible": True, "watermarkIntersectsNotation": True,
        },
        "verifiedEventData": {"pitchedEvents": 0, "shapes": 0, "pitchEdits": 0, "rhythmEdits": 0, "partStructureEdits": 0},
        "sourceAuthority": {"path": str(source.relative_to(ROOT)), "sha256": source_hash, "immutable": True},
        "rawOmr": {"path": str(raw.relative_to(ROOT)), "sha256": raw_hash, "xmlMember": raw_member, "stats": raw_stats, "status": "review-only"},
        "sourceShapeDraft": {"path": str(shape_draft.relative_to(ROOT)), "sha256": shape_hash, "xmlMember": shape_member, "stats": shape_stats, "manifest": shape_manifest, "status": "derived-review-only"},
        "playableDraft": playable_stats,
        "comparison": {
            "rawToSourceShapeDraftEventStreamsAligned": False,
            "rawToPlayableEventCountMatches": raw_stats["notes"] == expected_raw_events,
            "directPerEventSourceShapeMatches": direct_shape_events,
            "sourcePageGlobalMetadataObserved": True,
            "sourcePageGlobalMetadataAppliedToCandidate": True,
        },
        "candidate": {
            "path": str(output.relative_to(ROOT)), "sha256": sha256(output), "stats": candidate_stats,
            "sourceMetadataApplied": ["key", "mode", "time signature", "meter"],
            "derivedFourShapeNoteheads": candidate_info["derivedFourShapeNoteheads"],
            "pitchEdits": 0, "rhythmEdits": 0, "partStructureEdits": 0,
            "eventStreamPreserved": candidate_info["eventStreamPreserved"], "status": "review-only-not-source-verified",
        },
        "blockingFindings": blocking,
        "nextAction": "human-event-by-event-source-transcription-required-before-promotion",
        "policy": "Keep immutable source images, raw OMR, source-shape drafts, playable drafts, prior corrections, generated ledgers, and UI unchanged; this candidate is an isolated review artifact.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    records = [build_record(queue_id, config) for queue_id, config in TARGETS.items()]
    receipt = {
        "kind": "agent-04-source-verification-receipt",
        "version": "1",
        "scope": list(TARGETS),
        "summary": {
            "records": len(records), "blocked": sum(item["autonomousDecision"] == "blocked" for item in records),
            "safeToPromote": sum(item["safeToPromote"] for item in records), "directPerEventSourceShapeMatches": sum(item["comparison"]["directPerEventSourceShapeMatches"] for item in records),
            "verifiedPitchedEvents": sum(item["verifiedEventData"]["pitchedEvents"] for item in records), "pitchEdits": sum(item["candidate"]["pitchEdits"] for item in records),
            "rhythmEdits": sum(item["candidate"]["rhythmEdits"] for item in records), "partStructureEdits": sum(item["candidate"]["partStructureEdits"] for item in records),
        },
        "records": records,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    receipt_path = OUTPUT_ROOT / "agent-04-source-verification-receipt.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": str(receipt_path.relative_to(ROOT)), **receipt["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
