#!/usr/bin/env python3
"""Create a source-derived, fail-closed correction for Sacred Harp 565b."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/omr/565b-hebron/source.mxl"
SOURCE_IMAGE = ROOT / "work/omr/565b-hebron/source.jpg"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/565b-hebron-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/565b-hebron-source-correction-v2-comparison.json"

# Four-shape spelling for the source-visible A-major key. This annotates only
# OMR-retained pitches and is not note-level source proof.
SHAPES = {"A": "fa", "B": "sol", "C": "la", "D": "mi", "E": "fa", "F": "sol", "G": "la"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(parent: ET.Element | None, wanted: str) -> list[ET.Element]:
    return [item for item in parent if name(item.tag) == wanted] if parent is not None else []


def first(parent: ET.Element | None, wanted: str) -> ET.Element | None:
    return next(iter(children(parent, wanted)), None)


def field(identification: ET.Element, key: str, value: str) -> None:
    misc = first(identification, "miscellaneous")
    if misc is None:
        misc = ET.SubElement(identification, "miscellaneous")
    for old in [item for item in children(misc, "miscellaneous-field") if item.attrib.get("name") == key]:
        misc.remove(old)
    ET.SubElement(misc, "miscellaneous-field", {"name": key}).text = value


def duration_end(measure: ET.Element) -> int:
    cursor = maximum = 0
    for item in measure:
        duration = first(item, "duration")
        units = int(duration.text) if duration is not None and duration.text and duration.text.lstrip("-").isdigit() else 0
        if name(item.tag) == "note":
            if first(item, "chord") is None:
                cursor += units
            maximum = max(maximum, cursor)
        elif name(item.tag) == "backup":
            cursor -= units
        elif name(item.tag) == "forward":
            cursor += units
    return maximum


def event_signature(root: ET.Element) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for part in children(root, "part"):
        events: list[dict[str, str]] = []
        for measure in children(part, "measure"):
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                if pitch is None:
                    pitch_value = "rest" if first(note, "rest") is not None else "unknown"
                else:
                    pitch_value = ":".join([(first(pitch, "step").text or "") if first(pitch, "step") is not None else "", (first(pitch, "alter").text or "0") if first(pitch, "alter") is not None else "0", (first(pitch, "octave").text or "") if first(pitch, "octave") is not None else ""])
                duration = first(note, "duration")
                note_type = first(note, "type")
                voice = first(note, "voice")
                events.append({"measure": measure.attrib.get("number", ""), "pitch": pitch_value, "duration": duration.text if duration is not None and duration.text else "", "type": note_type.text if note_type is not None and note_type.text else "", "voice": voice.text if voice is not None and voice.text else ""})
        result[part.attrib.get("id", "")] = events
    return result


def transform() -> tuple[bytes, dict[str, object], dict[str, list[dict[str, str]]]]:
    with zipfile.ZipFile(SOURCE) as archive:
        xml_name = next(item for item in archive.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        root = ET.fromstring(archive.read(xml_name))
    parts = children(root, "part")
    summary: dict[str, object] = {"parts": len(parts), "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "restEvents": 0, "shapeNoteheadsAdded": 0, "emptyMeasures": 0, "durationFailuresAgainst3_4": {}, "lyricsRetained": 0, "sourceBarlines": 0}
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = children(part, "measure")
        summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
        summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
        summary["emptyMeasures"] = int(summary["emptyMeasures"]) + sum(not children(measure, "note") for measure in measures)
        summary["sourceBarlines"] = int(summary["sourceBarlines"]) + sum(len(children(measure, "barline")) for measure in measures)
        summary["durationFailuresAgainst3_4"][part_id] = [f"m{measure.attrib.get('number')}={duration_end(measure)}" for measure in measures if duration_end(measure) != 6]  # type: ignore[index]
        for measure in measures:
            attributes = first(measure, "attributes")
            if attributes is None:
                attributes = ET.Element("attributes")
                measure.insert(0, attributes)
            key = first(attributes, "key")
            if key is None:
                key = ET.Element("key")
                attributes.insert(1, key)
            for old in children(key, "fifths") + children(key, "mode"):
                key.remove(old)
            ET.SubElement(key, "fifths").text = "3"
            ET.SubElement(key, "mode").text = "major"
            time = first(attributes, "time")
            if time is None:
                time = ET.Element("time")
                attributes.insert(2, time)
            for old in children(time, "beats") + children(time, "beat-type"):
                time.remove(old)
            ET.SubElement(time, "beats").text = "3"
            ET.SubElement(time, "beat-type").text = "4"
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                if pitch is None:
                    if first(note, "rest") is not None:
                        summary["restEvents"] = int(summary["restEvents"]) + 1
                    continue
                step = first(pitch, "step")
                if step is None or not step.text or step.text.strip().upper() not in SHAPES:
                    continue
                for old in children(note, "notehead"):
                    note.remove(old)
                notehead = ET.Element("notehead")
                notehead.text = SHAPES[step.text.strip().upper()]
                stem_index = next((index for index, item in enumerate(note) if name(item.tag) == "stem"), len(note))
                note.insert(stem_index, notehead)
                summary["pitchedEvents"] = int(summary["pitchedEvents"]) + 1
                summary["shapeNoteheadsAdded"] = int(summary["shapeNoteheadsAdded"]) + 1
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    provenance = {
        "atlas-queue-id": "sh2025/565b",
        "atlas-transcription-status": "autonomously-blocked",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-image": "work/omr/565b-hebron/source.jpg",
        "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
        "atlas-source-catalog-title": "Hebron",
        "atlas-source-printed-title": "The Hill of Zion",
        "atlas-source-key": "A major",
        "atlas-source-mode": "major",
        "atlas-source-time-signature": "3/4",
        "atlas-source-meter": "Short Meter (6,6,8,6)",
        "atlas-source-title-and-credits": "THE HILL OF ZION. S.M.; Isaac Watts, 1707; B. F. White, 1859; Alto S. M. Denson, 1911",
        "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible A-major key; not source-verified per event",
        "atlas-lyrics": "omitted; source lyrics are visible but retained OMR has no directly aligned lyric underlay",
        "atlas-provenance-policy": "immutable 2025 scan is authoritative; printed-title/catalog-title discrepancy is preserved; no alternate-edition notation is borrowed",
        "atlas-blocker": "The immutable page prints THE HILL OF ZION. S.M., A major, 3/4, four vocal parts, two lyric verses, and a terminal double bar, while the queue/catalog title is Hebron. The retained OMR exports 10 measures per part, with 11 empty measures across parts, sparse events, rhythm failures, no explicit source mode, no lyrics, and incomplete barline semantics. A diagonal DO NOT COPY watermark crosses the middle parts. No notation was synthesized.",
    }
    for key, value in provenance.items():
        field(identification, key, value)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), summary, event_signature(root)


def main() -> int:
    source_hash = sha256(SOURCE)
    source_image_hash = sha256(SOURCE_IMAGE)
    xml, summary, corrected_events = transform()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml if info.filename == "source.xml" else source.read(info.filename))
    draft_hash = sha256(OUTPUT)
    with zipfile.ZipFile(SOURCE) as archive:
        source_root = ET.fromstring(archive.read("source.xml"))
    source_events = event_signature(source_root)
    blocking = [
        "The immutable page prints THE HILL OF ZION. S.M. while the queue record is Hebron; source identity is not silently reconciled.",
        "The source establishes A major, 3/4, four parts, two lyric verses, and a terminal double bar, but the retained OMR has no explicit source mode, no aligned lyrics, and incomplete barline semantics.",
        "Audiveris reports 10 raw measures and the OMR exports 10 per part, but 11 source-visible measures are empty across the four parts and the retained event stream has rhythm failures against 3/4.",
        "The source watermark intersects middle notation and lyric areas; no hidden note, lyric, repeat, ending, or duration was inferred.",
        "No authorized exact-edition structured candidate is present; alternate-edition notation was not borrowed.",
    ]
    audit = {
        "queueId": "sh2025/565b", "edition": "Sacred Harp, 2025 Edition", "songNo": "565b", "title": "Hebron", "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {"sourcePageUrl": "https://fasola.org/indexes/2025/?p=565b", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/565b-The-Hill-of-Zion/565b.jpg", "sourceImagePath": "work/omr/565b-hebron/source.jpg", "sourceImageSha256": source_image_hash, "immutable": True, "directObservations": {"printedTitle": "The Hill of Zion", "catalogTitle": "Hebron", "key": "A major", "mode": "major", "timeSignature": "3/4", "meter": "Short Meter (6,6,8,6)", "parts": 4, "measuresByPart": {"P1": 10, "P2": 10, "P3": 10, "P4": 10}, "sourceLyricsVisible": True, "sourceRepeatEnding": "terminal double bar visible", "watermarkAffectedRegions": "middle notation and lyric areas"}},
        "inputOmr": {"path": "work/omr/565b-hebron/source.mxl", "sha256": source_hash, "status": "retained-source-scan-omr"},
        "correctedDraft": {"path": "work/omr/autonomous-transcriptions/2025/565b-hebron-source-correction-v2.mxl", "sha256": draft_hash, "summary": summary, "eventStreamPreservedFromInput": True, "sourceEventSignature": source_events, "correctedEventSignature": corrected_events, "corrections": ["source A-major key and explicit major mode", "source 3/4 time signature", "four-shape noteheads added to every retained pitched event", "printed-title/catalog-title discrepancy recorded", "provenance and fail-closed status fields added", "lyrics, repeats, endings, and missing notation intentionally omitted"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": "work/omr/565b-hebron/source.jpg", "sourceScanSha256": source_image_hash, "method": "full-resolution visual inspection of immutable scan plus XML event, duration, topology, and provenance audit", "blockingFindings": blocking},
        "blockingReason": "Autonomous promotion is blocked because the printed source title conflicts with the queue title, the retained event stream is sparse with 11 empty measures and rhythm failures, and lyrics/barline semantics are not directly aligned. The derivative preserves detected events and adds source metadata/shapes without inventing notation.",
        "nextAction": "autonomous-promotion-blocked-by-source-identity-and-incomplete-event-witness; retain-corrected-draft-only",
        "policy": "Immutable 2025 source remains authoritative. This corrected derivative is not an authoritative corpus asset.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/565b", "status": audit["comparisonStatus"], "sourceImageSha256": source_image_hash, "inputOmrSha256": source_hash, "correctedDraftSha256": draft_hash, "summary": summary, "audit": str(AUDIT.relative_to(ROOT))}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
