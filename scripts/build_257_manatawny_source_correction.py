#!/usr/bin/env python3
"""Create a source-derived, fail-closed correction for Sacred Harp 257."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/omr/257-manatawny/257-manatawny.mxl"
SOURCE_IMAGE = ROOT / "work/source-transcriptions/2025/257-manatawny.jpg"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/257-manatawny-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/257-source-shape-autonomous-blocked-comparison.json"

# Four-shape spelling for E minor: E=la, F-sharp=mi, G=fa, A=sol,
# B=la, C=fa, D=sol. Accidentals remain untouched in MusicXML.
SHAPES = {"A": "sol", "B": "la", "C": "fa", "D": "sol", "E": "la", "F": "mi", "G": "fa"}


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


def text(parent: ET.Element | None, wanted: str, default: str = "") -> str:
    item = first(parent, wanted)
    return item.text.strip() if item is not None and item.text else default


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
                pitch_value = "rest" if first(note, "rest") is not None else "unknown"
                if pitch is not None:
                    pitch_value = ":".join([text(pitch, "step"), text(pitch, "alter", "0"), text(pitch, "octave")])
                events.append({"measure": measure.attrib.get("number", ""), "pitch": pitch_value, "duration": text(note, "duration"), "type": text(note, "type"), "voice": text(note, "voice")})
        result[part.attrib.get("id", "")] = events
    return result


def transform() -> tuple[bytes, dict[str, object], dict[str, list[dict[str, str]]]]:
    with zipfile.ZipFile(SOURCE) as archive:
        xml_name = next(item for item in archive.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        root = ET.fromstring(archive.read(xml_name))
    parts = children(root, "part")
    summary: dict[str, object] = {"parts": len(parts), "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "restEvents": 0, "shapeNoteheadsAdded": 0, "emptyMeasures": 0, "durationFailuresAgainst4_4": {}, "lyricsRetained": 0, "sourceBarlines": 0}
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = children(part, "measure")
        summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
        summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
        summary["emptyMeasures"] = int(summary["emptyMeasures"]) + sum(not children(measure, "note") for measure in measures)
        summary["sourceBarlines"] = int(summary["sourceBarlines"]) + sum(len(children(measure, "barline")) for measure in measures)
        summary["durationFailuresAgainst4_4"][part_id] = [f"m{measure.attrib.get('number')}={duration_end(measure)}" for measure in measures if duration_end(measure) != 16]  # type: ignore[index]
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
            ET.SubElement(key, "fifths").text = "1"
            ET.SubElement(key, "mode").text = "minor"
            time = first(attributes, "time")
            if time is None:
                time = ET.Element("time")
                attributes.insert(2, time)
            for old in children(time, "beats") + children(time, "beat-type"):
                time.remove(old)
            ET.SubElement(time, "beats").text = "4"
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
        "atlas-queue-id": "sh2025/257",
        "atlas-transcription-status": "autonomously-blocked",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-image": "work/source-transcriptions/2025/257-manatawny.jpg",
        "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
        "atlas-source-key": "E minor",
        "atlas-source-mode": "minor",
        "atlas-source-time-signature": "4/4",
        "atlas-source-meter": "Common Meter (8,6,8,6)",
        "atlas-source-title-and-credits": "MANATAWNY. C.M.; Isaac Watts, 1719; Rachel W. Hall, 2023",
        "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible E-minor key; not source-verified per event",
        "atlas-lyrics": "omitted; source lyrics are visible but retained OMR has no directly aligned lyric underlay",
        "atlas-provenance-policy": "immutable 2025 source image is authoritative; no authorized same-title structured candidate exists; this OMR derivative is evidence only",
        "atlas-blocker": "The immutable page visibly prints MANATAWNY. C.M., E minor, 4/4, four vocal parts, lyrics, two verse settings, first/second endings, and a terminal double bar. Audiveris reports 21 raw measures across two systems (12+9), while the retained OMR exports 19 measures per part with 7 empty measures, sparse events, no explicit time signature, no mode, no lyrics, and incomplete barline semantics. A diagonal DO NOT COPY watermark crosses lower-middle notation and lyrics. No notation was synthesized.",
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
        xml_name = next(item for item in archive.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        source_root = ET.fromstring(archive.read(xml_name))
    source_events = event_signature(source_root)
    blocking = [
        "The immutable page establishes E minor, 4/4, four parts, lyrics, first/second endings, and a terminal double bar, but the retained OMR has no directly aligned lyrics or complete repeat semantics.",
        "Audiveris reports 21 raw measures across two systems (12+9), while the exported MusicXML contains 19 measures per part; the source topology is not complete.",
        "The retained OMR contains 219 note elements, 217 pitched events, 2 rests, and 7 empty measures, with duration failures against 4/4 and no reliable source barline/event mapping.",
        "The watermark intersects lower-middle notation and lyrics; no hidden note, lyric, repeat, ending, or duration was inferred.",
        "No authorized same-title structured candidate is present; notation was not borrowed from another tune or edition.",
    ]
    audit = {
        "queueId": "sh2025/257", "edition": "Sacred Harp, 2025 Edition", "songNo": "257", "title": "Manatawny", "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {"sourcePageUrl": "https://fasola.org/indexes/2025/?p=257", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/257-Manatawny/257.jpg", "sourceImagePath": "work/source-transcriptions/2025/257-manatawny.jpg", "sourceImageSha256": source_image_hash, "immutable": True, "directObservations": {"header": "MANATAWNY. C.M.", "key": "E minor", "mode": "minor", "timeSignature": "4/4", "meter": "Common Meter (8,6,8,6)", "parts": 4, "audiverisRawMeasures": 21, "sourceMeasuresBySystem": [12, 9], "sourceLyricsVisible": True, "sourceRepeatEnding": "first/second endings and terminal double bar visible", "watermarkAffectedRegions": "lower-middle notation and lyric areas"}},
        "inputOmr": {"path": "work/omr/257-manatawny/257-manatawny.mxl", "sha256": source_hash, "status": "retained-source-scan-omr"},
        "priorReviewDraft": {"path": "work/omr/source-shape-review-drafts/2025/257-source-shape-review.mxl", "sha256": "ee992d6dafac70baf957ec8a6d9bd70c3a28c3f0a1dc521aa04541a66e6ce994", "status": "preserved-review-only-witness-not-used-as-authority"},
        "correctedDraft": {"path": "work/omr/autonomous-transcriptions/2025/257-manatawny-source-correction-v2.mxl", "sha256": draft_hash, "summary": summary, "eventStreamPreservedFromInput": True, "sourceEventSignature": source_events, "correctedEventSignature": corrected_events, "corrections": ["source E-minor key and explicit minor mode", "source 4/4 time signature", "four-shape noteheads added to every retained pitched event", "provenance and fail-closed status fields added", "lyrics, repeats, endings, missing events, and uncertain durations intentionally omitted"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": "work/source-transcriptions/2025/257-manatawny.jpg", "sourceScanSha256": source_image_hash, "method": "full-resolution direct source-image inspection plus XML event, duration, topology, and provenance audit; prior shape-review draft retained as distinct witness", "blockingFindings": blocking},
        "blockingReason": "Autonomous promotion is blocked because the retained OMR is two measures short of the source topology, sparse across seven empty measures, rhythmically unresolved, and lacks source-aligned lyrics/repeat semantics. The derivative preserves detected events and adds source metadata/shapes without inventing notation.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness; retain-corrected-draft-only",
        "policy": "Immutable 2025 source remains authoritative. OMR and derived shape tags are review work product only and cannot authorize promotion without direct event-level evidence.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/257", "status": audit["comparisonStatus"], "sourceImageSha256": source_image_hash, "inputOmrSha256": source_hash, "correctedDraftSha256": draft_hash, "summary": summary, "audit": str(AUDIT.relative_to(ROOT))}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
