#!/usr/bin/env python3
"""Create a source-derived, fail-closed Hall derivative."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from build_409_exeter_source_correction import (
    ROOT,
    barline_signature,
    children,
    duration_end,
    event_signature,
    first,
    put_field,
    read_xml,
    sha256,
    text,
)

SOURCE_IMAGE = ROOT / "work/omr/423b-hall/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/423b-hall-69342fc4a3.jpg"
SOURCE = ROOT / "work/omr/423b-hall/source.mxl"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/423b-hall-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/423b-hall-source-correction-v2-comparison.json"

# E-minor four-shape spelling uses the relative G-major scale:
# G=fa, A=sol, B=la, C=fa, D=sol, E=la, F-sharp=mi.
SHAPES = {"A": "sol", "B": "la", "C": "fa", "D": "sol", "E": "la", "F": "mi", "G": "fa"}


def ensure_source_attributes(measure: ET.Element) -> None:
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
    clock = first(attributes, "time")
    if clock is None:
        clock = ET.Element("time")
        key_index = next((i for i, item in enumerate(attributes) if item.tag.rsplit("}", 1)[-1] == "key"), 1)
        attributes.insert(key_index + 1, clock)
    for old in children(clock, "beats") + children(clock, "beat-type"):
        clock.remove(old)
    ET.SubElement(clock, "beats").text = "4"
    ET.SubElement(clock, "beat-type").text = "4"


def transform() -> tuple[str, bytes, dict[str, object], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    xml_name, root = read_xml(SOURCE)
    source_events = event_signature(root)
    source_barlines = barline_signature(root)
    parts = children(root, "part")
    summary: dict[str, object] = {"parts": len(parts), "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "restEvents": 0, "shapeNoteheadsAdded": 0, "lyricsRetained": 0, "emptyMeasures": 0, "durationEndByPart": {}, "durationFailuresAgainst4_4": {}, "sourceBarlines": source_barlines}
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = children(part, "measure")
        summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
        summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
        summary["emptyMeasures"] = int(summary["emptyMeasures"]) + sum(not children(measure, "note") for measure in measures)
        ends = {measure.attrib.get("number", ""): duration_end(measure) for measure in measures}
        summary["durationEndByPart"][part_id] = ends  # type: ignore[index]
        summary["durationFailuresAgainst4_4"][part_id] = [f"m{number}={end}" for number, end in ends.items() if end != 8]  # type: ignore[index]
        for measure in measures:
            ensure_source_attributes(measure)
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                if pitch is None:
                    if first(note, "rest") is not None:
                        summary["restEvents"] = int(summary["restEvents"]) + 1
                    continue
                shape = SHAPES.get(text(pitch, "step").upper())
                if shape is None:
                    continue
                for old in children(note, "notehead"):
                    note.remove(old)
                notehead = ET.Element("notehead")
                notehead.text = shape
                stem_index = next((i for i, item in enumerate(note) if item.tag.rsplit("}", 1)[-1] == "stem"), len(note))
                note.insert(stem_index, notehead)
                summary["pitchedEvents"] = int(summary["pitchedEvents"]) + 1
                summary["shapeNoteheadsAdded"] = int(summary["shapeNoteheadsAdded"]) + 1
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    fields = {
        "atlas-queue-id": "sh2025/423b", "atlas-transcription-status": "autonomously-blocked", "atlas-review-status": "autonomously-blocked-source-derived-draft", "atlas-safe-to-promote": "false",
        "atlas-source-image": str(SOURCE_IMAGE.relative_to(ROOT)), "atlas-source-image-sha256": sha256(SOURCE_IMAGE), "atlas-source-retained-image": str(RETAINED_IMAGE.relative_to(ROOT)), "atlas-source-retained-image-sha256": sha256(RETAINED_IMAGE),
        "atlas-source-key": "E minor", "atlas-source-mode": "minor", "atlas-source-time-signature": "4/4", "atlas-source-meter": "Short Meter (6,6,8,6)",
        "atlas-source-repeat-ending": "The source visibly has numbered first/second endings and a terminal double bar; the retained OMR does not encode complete repeat/ending semantics, so none was fabricated.",
        "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible E-minor key using the relative G-major scale; not source-verified per event", "atlas-lyrics": "omitted; source lyrics are visible but retained OMR has no directly aligned lyric underlay",
        "atlas-provenance-policy": "immutable 2025 scan is authoritative; the retained source-image duplicate is preserved separately; no alternate witness was used; this OMR derivative is evidence only",
        "atlas-blocker": "The immutable page visibly prints HALL. S.M., E minor, 4/4, John Leland 1790, Leah Velleman 2019, four vocal parts across 11 source measures, lyrics, numbered first/second endings, a terminal double bar, and a diagonal DO NOT COPY watermark crossing central notation and lyrics. The retained source OMR exports 9 measures per part and 126 events (124 pitched and 2 rests), with 8 empty measures and duration ends failing the 4/4 target in 32 of 36 exported measures; its Audiveris log also records a key-export exception. It has no lyrics, no source-confirmed shapes, and no complete repeat/ending semantics. No unsupported notation was synthesized.",
    }
    for key, value in fields.items():
        put_field(identification, key, value)
    return xml_name, ET.tostring(root, encoding="utf-8", xml_declaration=True), summary, source_events, event_signature(root), barline_signature(root)


def main() -> int:
    source_hash, image_hash, retained_hash = sha256(SOURCE), sha256(SOURCE_IMAGE), sha256(RETAINED_IMAGE)
    xml_name, xml, summary, source_events, corrected_events, corrected_barlines = transform()
    source_barlines = summary["sourceBarlines"]
    input_summary = dict(summary)
    input_summary["shapeNoteheadsAdded"] = 0
    input_summary["lyricsRetained"] = 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml if info.filename == xml_name else source.read(info.filename))
    draft_hash = sha256(OUTPUT)
    blocking = [
        "The immutable scan visibly establishes Hall S.M., E minor, 4/4, four vocal parts across 11 source measures, lyrics, numbered first/second endings, a terminal double bar, and a diagonal DO NOT COPY watermark crossing central notation and lyrics.",
        "The retained source OMR exports 9 measures per part and 126 events (124 pitched and 2 rests), while the source page has 11 measures per part; 32 of 36 exported measures fail the 4/4 duration audit and 8 measures are empty, so event timing and topology are not proven source-faithful.",
        "The retained source OMR has no lyrics, no four-shape notehead tags, and no complete source repeat/ending semantics; its Audiveris log records a key-export exception. The derivative adds observed E-minor/4/4 metadata and relative-G-major derived shapes without rewriting uncertain events.",
        "No authorized same-title structured witness was available, so no alternate tune or edition was used to fill missing events, lyrics, rhythms, repeats, or shapes.",
    ]
    audit = {
        "queueId": "sh2025/423b", "edition": "Sacred Harp, 2025 Edition", "songNo": "423b", "title": "Hall", "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {"sourcePageUrl": "https://fasola.org/indexes/2025/?p=423b", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/423b-Hall/423b.jpg", "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceImageSha256": image_hash, "immutable": True, "directObservations": {"header": "HALL. S.M.", "composer": "John Leland, 1790", "arranger": "Leah Velleman, 2019", "key": "E minor", "mode": "minor", "timeSignature": "4/4", "meter": "Short Meter (6,6,8,6)", "parts": 4, "measuresByPart": {"P1": 11, "P2": 11, "P3": 11, "P4": 11}, "sourceRawMeasuresFromAudiveris": 11, "lyricsVisible": True, "repeatBarsVisible": True, "endingsVisible": True, "terminalDoubleBarVisible": True, "watermarkIntersectsNotation": True}, "retainedSourceImageDuplicate": {"path": str(RETAINED_IMAGE.relative_to(ROOT)), "sha256": retained_hash, "immutable": True, "geometryMatchesRequestedSource": True, "byteEqualToRequestedSource": True}},
        "inputOmr": {"path": str(SOURCE.relative_to(ROOT)), "sha256": source_hash, "status": "retained-source-scan-omr", "summary": input_summary},
        "candidateWitness": {"available": False, "candidateRole": "No authorized same-title structured witness was available; alternate editions were not used."},
        "correctedDraft": {"path": str(OUTPUT.relative_to(ROOT)), "sha256": draft_hash, "summary": summary, "eventStreamPreservedFromInput": source_events == corrected_events, "sourceEventSignature": source_events, "correctedEventSignature": corrected_events, "sourceBarlines": source_barlines, "correctedBarlines": corrected_barlines, "corrections": ["source E-minor key and explicit minor mode", "source 4/4 time signature", "four-shape noteheads derived for every retained pitched event using the relative G-major scale", "source lyric/repeat/watermark visibility recorded in provenance", "lyrics and uncertain repeat/ending semantics intentionally omitted"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceScanSha256": image_hash, "retainedDuplicatePath": str(RETAINED_IMAGE.relative_to(ROOT)), "retainedDuplicateSha256": retained_hash, "method": "full-resolution visual inspection of requested immutable Hall scan and retained byte-identical image plus retained source MXL and Audiveris audit; no alternate witness used to fill source events", "blockingFindings": blocking},
        "blockingFindings": blocking, "blockingReason": "Autonomous promotion is blocked by the missing four source measures, 32 duration failures in the nine-measure-per-part export, 8 empty measures, the Audiveris key-export exception, absent lyrics and source-confirmed per-note shapes, incomplete repeat/ending semantics, watermark-obscured central systems, and lack of an authorized exact-edition structured witness. The corrected derivative remains review-only.",
        "nextAction": "autonomous-promotion-blocked-by-missing-source-measures-and-incomplete-event-witness; retain-corrected-draft-only", "policy": "Immutable 2025 scan remains authoritative. OMR-derived events and shape tags are evidence only and cannot authorize corpus promotion without direct source proof.", "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"audit": str(AUDIT.relative_to(ROOT)), "record": audit["queueId"], "status": audit["comparisonStatus"], "sourceImageSha256": image_hash, "retainedImageSha256": retained_hash, "inputOmrSha256": source_hash, "correctedDraftSha256": draft_hash, "summary": summary}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
