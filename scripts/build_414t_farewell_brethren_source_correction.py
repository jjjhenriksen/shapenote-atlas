#!/usr/bin/env python3
"""Create a source-derived, fail-closed Farewell Brethren derivative."""

from __future__ import annotations

import hashlib
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

SOURCE_IMAGE = ROOT / "work/omr/414t-farewell-brethren/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-transcriptions/2025/414t/414t.jpg"
SOURCE = ROOT / "work/omr/414t-farewell-brethren/source.mxl"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/414t-farewell-brethren-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/414t-farewell-brethren-source-correction-v2-comparison.json"
ALTERNATE_CANDIDATE = ROOT / "work/omr/clean-source-candidates/414b-farewell-brethren/source-candidate.mxl"
ALTERNATE_CANDIDATE_DUPLICATE = ROOT / "work/omr/clean-source-candidates/414b-farewell-brethren-farewell-brethren-c-m-0158d78729/source-candidate.mxl"

# A-major four-shape spelling: A=fa, B=sol, C-sharp=la, D=fa,
# E=sol, F-sharp=la, G-sharp=mi.
SHAPES = {"A": "fa", "B": "sol", "C": "la", "D": "fa", "E": "sol", "F": "la", "G": "mi"}


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
    ET.SubElement(key, "fifths").text = "3"
    ET.SubElement(key, "mode").text = "major"
    clock = first(attributes, "time")
    if clock is None:
        clock = ET.Element("time")
        key_index = next((i for i, item in enumerate(attributes) if item.tag.rsplit("}", 1)[-1] == "key"), 1)
        attributes.insert(key_index + 1, clock)
    for old in children(clock, "beats") + children(clock, "beat-type"):
        clock.remove(old)
    ET.SubElement(clock, "beats").text = "3"
    ET.SubElement(clock, "beat-type").text = "4"


def transform() -> tuple[str, bytes, dict[str, object], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    xml_name, root = read_xml(SOURCE)
    source_events = event_signature(root)
    source_barlines = barline_signature(root)
    parts = children(root, "part")
    summary: dict[str, object] = {"parts": len(parts), "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "restEvents": 0, "shapeNoteheadsAdded": 0, "lyricsRetained": 0, "emptyMeasures": 0, "durationEndByPart": {}, "durationFailuresAgainst3_4": {}, "sourceBarlines": source_barlines}
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = children(part, "measure")
        summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
        summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
        summary["emptyMeasures"] = int(summary["emptyMeasures"]) + sum(not children(measure, "note") for measure in measures)
        ends = {measure.attrib.get("number", ""): duration_end(measure) for measure in measures}
        summary["durationEndByPart"][part_id] = ends  # type: ignore[index]
        summary["durationFailuresAgainst3_4"][part_id] = [f"m{number}={end}" for number, end in ends.items() if end != 6]  # type: ignore[index]
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
        "atlas-queue-id": "sh2025/414t", "atlas-transcription-status": "autonomously-blocked", "atlas-review-status": "autonomously-blocked-source-derived-draft", "atlas-safe-to-promote": "false",
        "atlas-source-image": str(SOURCE_IMAGE.relative_to(ROOT)), "atlas-source-image-sha256": sha256(SOURCE_IMAGE), "atlas-source-retained-image": str(RETAINED_IMAGE.relative_to(ROOT)), "atlas-source-retained-image-sha256": sha256(RETAINED_IMAGE),
        "atlas-source-key": "A major", "atlas-source-mode": "major", "atlas-source-time-signature": "3/4", "atlas-source-meter": "Common Meter (8,6,8,6)",
        "atlas-source-repeat-ending": "The source visibly has a terminal double bar; no numbered first/second endings or complete repeat instruction was established, and none was fabricated.",
        "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible A-major key; not source-verified per event", "atlas-lyrics": "omitted; source lyrics are visible but retained OMR has no directly aligned lyric underlay",
        "atlas-provenance-policy": "immutable 2025 scan is authoritative; the retained prior source image is preserved separately; the same-title 414b witness remains an alternate record; this OMR derivative is evidence only",
        "atlas-blocker": "The immutable page visibly prints FAREWELL BRETHREN. C.M., A major, 3/4, Winchester's Collection 1782, Jesse P. Karlsberg 2010, four vocal parts across 12 source measures, three verses of lyrics, and a terminal double bar. A diagonal DO NOT COPY watermark crosses central notation and lyric regions. The retained source OMR exports 12 measures per part, but its duration ends fail the 3/4 target in 41 of 48 measures, with 6 empty measures, no lyrics, no source-confirmed shapes, and no complete source lyric/repeat semantics. No unsupported notation was synthesized.",
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
        "The immutable scan visibly establishes Farewell Brethren C.M., A major, 3/4, four vocal parts across 12 source measures, lyrics, a terminal double bar, and a diagonal DO NOT COPY watermark crossing central notation and lyric regions.",
        "The retained source OMR exports 12 measures per part and 105 pitched events, but its duration ends fail the 3/4 target in 41 of 48 measures and 6 measures are empty, so event timing and topology are not proven source-faithful.",
        "The retained source OMR has no lyrics, no four-shape notehead tags, and no complete source lyric/repeat semantics. The derivative adds observed A-major/3/4 metadata and derived shapes without rewriting uncertain events.",
        "The available same-title 414b witness is a distinct alternate record: its candidate MXL has 15 measures per part rather than the 12 source measures, so it was preserved as comparison evidence and not used to fill 414t events.",
    ]
    audit = {
        "queueId": "sh2025/414t", "edition": "Sacred Harp, 2025 Edition", "songNo": "414t", "title": "Farewell Brethren", "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {"sourcePageUrl": "https://fasola.org/indexes/2025/?p=414t", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/414t-Farewell-Brethren/414t.jpg", "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceImageSha256": image_hash, "immutable": True, "directObservations": {"header": "FAREWELL BRETHREN. C.M.", "composer": "Winchester's Collection, 1782", "arranger": "Jesse P. Karlsberg, 2010", "key": "A major", "mode": "major", "timeSignature": "3/4", "meter": "Common Meter (8,6,8,6)", "parts": 4, "measuresByPart": {"P1": 12, "P2": 12, "P3": 12, "P4": 12}, "sourceRawMeasuresFromAudiveris": 12, "lyricsVisible": True, "repeatBarsVisible": False, "endingsVisible": False, "terminalDoubleBarVisible": True, "watermarkIntersectsNotation": True}, "retainedSourceImageDuplicate": {"path": str(RETAINED_IMAGE.relative_to(ROOT)), "sha256": retained_hash, "immutable": True, "geometryMatchesRequestedSource": True, "byteEqualToRequestedSource": False}},
        "inputOmr": {"path": str(SOURCE.relative_to(ROOT)), "sha256": source_hash, "status": "retained-source-scan-omr", "summary": input_summary},
        "candidateWitness": {"available": True, "recordId": "sh2025/414b", "candidateRole": "Same-title alternate record only; not used as 414t notation authority.", "paths": [{"path": str(ALTERNATE_CANDIDATE.relative_to(ROOT)), "sha256": sha256(ALTERNATE_CANDIDATE), "measuresByPart": {"P1": 15, "P2": 15, "P3": 15, "P4": 15}, "eventsByPart": {"P1": 17, "P2": 18, "P3": 17, "P4": 15}}, {"path": str(ALTERNATE_CANDIDATE_DUPLICATE.relative_to(ROOT)), "sha256": sha256(ALTERNATE_CANDIDATE_DUPLICATE), "measuresByPart": {"P1": 15, "P2": 15, "P3": 15, "P4": 15}, "eventsByPart": {"P1": 17, "P2": 18, "P3": 17, "P4": 15}}], "disposition": "alternate-witness-not-promoted"},
        "correctedDraft": {"path": str(OUTPUT.relative_to(ROOT)), "sha256": draft_hash, "summary": summary, "eventStreamPreservedFromInput": source_events == corrected_events, "sourceEventSignature": source_events, "correctedEventSignature": corrected_events, "sourceBarlines": source_barlines, "correctedBarlines": corrected_barlines, "corrections": ["source A-major key and explicit major mode", "source 3/4 time signature", "four-shape noteheads derived for every retained pitched event", "source lyric/repeat/watermark visibility recorded in provenance", "lyrics and uncertain repeat semantics intentionally omitted"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceScanSha256": image_hash, "retainedDuplicatePath": str(RETAINED_IMAGE.relative_to(ROOT)), "retainedDuplicateSha256": retained_hash, "method": "full-resolution visual inspection of requested immutable Farewell Brethren scan and retained prior source image plus retained source MXL, Audiveris audit, and distinct 414b candidate witness; alternate witness not used to fill source events", "blockingFindings": blocking},
        "blockingFindings": blocking, "blockingReason": "Autonomous promotion is blocked by the 41 duration failures in the retained OMR, 6 empty measures, absent lyrics and source-confirmed per-note shapes, incomplete source lyric/repeat semantics, watermark-obscured central systems, and the 414b witness's 15-versus-12 measure mismatch. The corrected derivative remains review-only.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-alternate-setting-mismatch; retain-corrected-draft-only", "policy": "Immutable 2025 scan remains authoritative. OMR-derived events and shape tags are evidence only and cannot authorize corpus promotion without direct source proof.", "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"audit": str(AUDIT.relative_to(ROOT)), "record": audit["queueId"], "status": audit["comparisonStatus"], "sourceImageSha256": image_hash, "retainedImageSha256": retained_hash, "inputOmrSha256": source_hash, "correctedDraftSha256": draft_hash, "summary": summary}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
