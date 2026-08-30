#!/usr/bin/env python3
"""Create a source-derived, fail-closed correction for Sacred Harp 445.

The retained Audiveris export is evidence only.  This script preserves its
detected events, adds facts visible on the immutable 2025 scan, and records
why autonomous promotion is blocked.  It never synthesizes omitted notes,
lyrics, repeats, or durations.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/omr/445-passing-away/source.mxl"
SOURCE_IMAGE = ROOT / "work/omr/445-passing-away/source.jpg"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/445-passing-away-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/445-passing-away-source-correction-v2-comparison.json"

# Four-shape spelling for the C-major source key.  This annotates only pitches
# already detected by OMR; it is not evidence that the OMR event is correct.
SHAPES = {"C": "fa", "D": "sol", "E": "la", "F": "mi", "G": "fa", "A": "sol", "B": "la"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(parent: ET.Element | None, name: str) -> list[ET.Element]:
    return [child for child in parent if tag_name(child.tag) == name] if parent is not None else []


def first(parent: ET.Element | None, name: str) -> ET.Element | None:
    return next(iter(children(parent, name)), None)


def field(identification: ET.Element, name: str, value: str) -> None:
    miscellaneous = first(identification, "miscellaneous")
    if miscellaneous is None:
        miscellaneous = ET.SubElement(identification, "miscellaneous")
    for old in [item for item in children(miscellaneous, "miscellaneous-field") if item.attrib.get("name") == name]:
        miscellaneous.remove(old)
    ET.SubElement(miscellaneous, "miscellaneous-field", {"name": name}).text = value


def duration_end(measure: ET.Element) -> int:
    cursor = 0
    maximum = 0
    for item in measure:
        name = tag_name(item.tag)
        duration = first(item, "duration")
        units = int(duration.text) if duration is not None and duration.text and duration.text.lstrip("-").isdigit() else 0
        if name == "note":
            if first(item, "chord") is None:
                cursor += units
            maximum = max(maximum, cursor)
        elif name == "backup":
            cursor -= units
        elif name == "forward":
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
                    pitch_value = ":".join(
                        [
                            (first(pitch, "step").text or "") if first(pitch, "step") is not None else "",
                            (first(pitch, "alter").text or "0") if first(pitch, "alter") is not None else "0",
                            (first(pitch, "octave").text or "") if first(pitch, "octave") is not None else "",
                        ]
                    )
                duration = first(note, "duration")
                note_type = first(note, "type")
                voice = first(note, "voice")
                events.append(
                    {
                        "measure": measure.attrib.get("number", ""),
                        "pitch": pitch_value,
                        "duration": duration.text if duration is not None and duration.text else "",
                        "type": note_type.text if note_type is not None and note_type.text else "",
                        "voice": voice.text if voice is not None and voice.text else "",
                    }
                )
        result[part.attrib.get("id", "")] = events
    return result


def transform() -> tuple[bytes, dict[str, object], dict[str, list[dict[str, str]]]]:
    with zipfile.ZipFile(SOURCE) as archive:
        xml_name = next(name for name in archive.namelist() if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/"))
        root = ET.fromstring(archive.read(xml_name))
        parts = children(root, "part")
        summary: dict[str, object] = {
            "parts": len(parts),
            "measuresByPart": {},
            "eventsByPart": {},
            "pitchedEvents": 0,
            "restEvents": 0,
            "shapeNoteheadsAdded": 0,
            "emptyMeasures": 0,
            "durationFailuresAgainst4_4": {},
            "lyricsRetained": 0,
            "sourceBarlines": 0,
        }
        for part in parts:
            part_id = part.attrib.get("id", "")
            measures = children(part, "measure")
            summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
            summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
            summary["emptyMeasures"] = int(summary["emptyMeasures"]) + sum(not children(measure, "note") for measure in measures)
            summary["sourceBarlines"] = int(summary["sourceBarlines"]) + sum(len(children(measure, "barline")) for measure in measures)
            summary["durationFailuresAgainst4_4"][part_id] = [  # type: ignore[index]
                f"m{measure.attrib.get('number')}={duration_end(measure)}"
                for measure in measures
                if duration_end(measure) != 8
            ]
            for measure in measures:
                attributes = first(measure, "attributes")
                if attributes is None:
                    attributes = ET.Element("attributes")
                    measure.insert(0, attributes)
                divisions = first(attributes, "divisions")
                if divisions is None:
                    divisions = ET.Element("divisions")
                    attributes.insert(0, divisions)
                key = first(attributes, "key")
                if key is None:
                    key = ET.Element("key")
                    attributes.insert(1, key)
                for old in children(key, "fifths") + children(key, "mode"):
                    key.remove(old)
                ET.SubElement(key, "fifths").text = "0"
                ET.SubElement(key, "mode").text = "major"
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
                    stem_index = next((index for index, item in enumerate(note) if tag_name(item.tag) == "stem"), len(note))
                    note.insert(stem_index, notehead)
                    summary["pitchedEvents"] = int(summary["pitchedEvents"]) + 1
                    summary["shapeNoteheadsAdded"] = int(summary["shapeNoteheadsAdded"]) + 1

        identification = first(root, "identification")
        if identification is None:
            identification = ET.Element("identification")
            root.insert(0, identification)
        provenance = {
            "atlas-queue-id": "sh2025/445",
            "atlas-transcription-status": "autonomously-blocked",
            "atlas-review-status": "autonomously-blocked-source-derived-draft",
            "atlas-safe-to-promote": "false",
            "atlas-source-image": "work/omr/445-passing-away/source.jpg",
            "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
            "atlas-source-key": "C major",
            "atlas-source-mode": "major",
            "atlas-source-time-signature": "4/4",
            "atlas-source-meter": "Common Meter (8,6,8,6)",
            "atlas-source-title-and-credits": "PASSING AWAY. C.M.; Charles Wesley, 1763; John A. Watson, 1872; Alto William Walker, 1873",
            "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible C-major key; not source-verified per event",
            "atlas-lyrics": "omitted; source lyrics are visible but retained OMR has no directly aligned lyric underlay",
            "atlas-provenance-policy": "immutable 2025 scan is authoritative; no same-title structured candidate is authorized; this OMR derivative is evidence only",
            "atlas-blocker": "The immutable page visibly prints PASSING AWAY. C.M., C major, 4/4, four vocal parts, three lyric verses, repeat endings 1/2, and a terminal double bar. The retained OMR exports 12 measures per part with sparse events, empty measures, no mode, no time signature, no lyrics, no barlines, and malformed durations against 4/4. A diagonal DO NOT COPY watermark intersects the middle systems. No notation was synthesized.",
        }
        for name, value in provenance.items():
            field(identification, name, value)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), summary, event_signature(root)


def main() -> int:
    source_hash = sha256(SOURCE)
    source_image_hash = sha256(SOURCE_IMAGE)
    xml, summary, corrected_events = transform()
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml if info.filename == "source.xml" else source.read(info.filename))
    draft_hash = sha256(OUTPUT)
    with zipfile.ZipFile(SOURCE) as archive:
        source_root = ET.fromstring(archive.read("source.xml"))
    source_events = event_signature(source_root)
    blocking = [
        "The immutable scan visibly establishes C major, 4/4, four parts, three lyric verses, first/second endings, and a terminal double bar, but the retained OMR has no corresponding metadata or lyric underlay.",
        "Audiveris reports 13 raw measures in one four-part system, while the exported MusicXML contains 12 measures per part; the topology is therefore not source-complete.",
        "The retained OMR contains 156 note elements total (145 pitched and 11 rests), 12 empty measures, divisions of 2, no barlines, and duration failures against the source 4/4 target of 8 divisions; several notes/rests are structurally malformed.",
        "The source watermark intersects the middle systems and lyric areas; no hidden note, lyric, repeat, or ending was inferred.",
        "No authorized exact-edition structured candidate is present for this record; alternate-edition notation was not borrowed.",
    ]
    audit = {
        "queueId": "sh2025/445",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "445",
        "title": "Passing Away",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=445",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/445-Passing-Away/445.jpg",
            "sourceImagePath": "work/omr/445-passing-away/source.jpg",
            "sourceImageSha256": source_image_hash,
            "immutable": True,
            "directObservations": {
                "header": "PASSING AWAY. C.M.",
                "key": "C major",
                "mode": "major",
                "timeSignature": "4/4",
                "meter": "Common Meter (8,6,8,6)",
                "parts": 4,
                "audiverisRawMeasures": 13,
                "sourceLyricsVisible": True,
                "sourceRepeatEnding": "first/second endings and terminal double bar visible",
                "watermarkAffectedRegions": "middle systems and lyric areas",
            },
        },
        "inputOmr": {"path": "work/omr/445-passing-away/source.mxl", "sha256": source_hash, "status": "retained-source-scan-omr"},
        "correctedDraft": {
            "path": "work/omr/autonomous-transcriptions/2025/445-passing-away-source-correction-v2.mxl",
            "sha256": draft_hash,
            "summary": summary,
            "eventStreamPreservedFromInput": True,
            "sourceEventSignature": source_events,
            "correctedEventSignature": corrected_events,
            "corrections": [
                "source C-major key and explicit major mode",
                "source 4/4 time signature",
                "four-shape noteheads added to every retained pitched event",
                "provenance and fail-closed status fields added",
                "lyrics, repeats, endings, and missing notation intentionally omitted",
            ],
        },
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "sourceScanPath": "work/omr/445-passing-away/source.jpg",
            "sourceScanSha256": source_image_hash,
            "method": "full-resolution visual inspection of immutable scan plus XML event, duration, topology, and provenance audit",
            "blockingFindings": blocking,
        },
        "blockingReason": "Autonomous promotion is blocked because the retained OMR is structurally incomplete and rhythmically inconsistent with the source-visible 4/4 page, differs in raw/exported measure topology, omits lyrics and repeat/ending semantics, and has watermark-intersected source regions. The derivative preserves detected events and adds source metadata/shapes without inventing notation.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness; retain-corrected-draft-only",
        "policy": "Immutable 2025 source remains authoritative. This corrected derivative is not an authoritative corpus asset.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/445", "status": audit["comparisonStatus"], "sourceImageSha256": source_image_hash, "inputOmrSha256": source_hash, "correctedDraftSha256": draft_hash, "summary": summary, "audit": str(AUDIT.relative_to(ROOT))}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
