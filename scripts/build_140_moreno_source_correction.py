#!/usr/bin/env python3
"""Create a source-derived, fail-closed Moreno derivative."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/omr/140-moreno/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/140-moreno-1a2f916fe7.jpg"
SOURCE = ROOT / "work/omr/140-moreno/source.mxl"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/140-moreno-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/140-moreno-source-correction-v2-comparison.json"

# E minor uses the G-major relative scale for four-shape spelling.
SHAPES = {"A": "sol", "B": "la", "C": "fa", "D": "sol", "E": "la", "F": "mi", "G": "fa"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(parent: ET.Element | None, wanted: str) -> list[ET.Element]:
    return [child for child in parent if local_name(child.tag) == wanted] if parent is not None else []


def first(parent: ET.Element | None, wanted: str) -> ET.Element | None:
    return next(iter(children(parent, wanted)), None)


def text(parent: ET.Element | None, wanted: str, default: str = "") -> str:
    item = first(parent, wanted)
    return item.text.strip() if item is not None and item.text else default


def put_field(identification: ET.Element, key: str, value: str) -> None:
    miscellaneous = first(identification, "miscellaneous")
    if miscellaneous is None:
        miscellaneous = ET.SubElement(identification, "miscellaneous")
    for old in [item for item in children(miscellaneous, "miscellaneous-field") if item.attrib.get("name") == key]:
        miscellaneous.remove(old)
    ET.SubElement(miscellaneous, "miscellaneous-field", {"name": key}).text = value


def duration_end(measure: ET.Element) -> int:
    cursor = maximum = 0
    for item in measure:
        kind = local_name(item.tag)
        duration = first(item, "duration")
        units = int(duration.text) if duration is not None and duration.text and duration.text.isdigit() else 0
        if kind == "note":
            if first(item, "chord") is None:
                cursor += units
            maximum = max(maximum, cursor)
        elif kind == "backup":
            cursor -= units
        elif kind == "forward":
            cursor += units
    return maximum


def event_signature(root: ET.Element) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for part in children(root, "part"):
        rows: list[dict[str, str]] = []
        for measure in children(part, "measure"):
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                value = "rest" if first(note, "rest") is not None else "unknown"
                if pitch is not None:
                    value = ":".join([text(pitch, "step"), text(pitch, "alter", "0"), text(pitch, "octave")])
                rows.append({"measure": measure.attrib.get("number", ""), "pitch": value, "duration": text(note, "duration"), "type": text(note, "type"), "voice": text(note, "voice")})
        result[part.attrib.get("id", "")] = rows
    return result


def barline_signature(root: ET.Element) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for part in children(root, "part"):
        rows: list[dict[str, str]] = []
        for measure in children(part, "measure"):
            for bar in children(measure, "barline"):
                repeat = first(bar, "repeat")
                ending = first(bar, "ending")
                rows.append({"measure": measure.attrib.get("number", ""), "location": bar.attrib.get("location", ""), "style": text(bar, "bar-style"), "repeat": repeat.attrib.get("direction", "") if repeat is not None else "", "ending": ending.attrib.get("number", "") if ending is not None else ""})
        result[part.attrib.get("id", "")] = rows
    return result


def read_xml(path: Path) -> tuple[str, ET.Element]:
    with zipfile.ZipFile(path) as archive:
        xml_name = next(item for item in archive.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        return xml_name, ET.fromstring(archive.read(xml_name))


def transform() -> tuple[str, bytes, dict[str, object], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    xml_name, root = read_xml(SOURCE)
    source_events = event_signature(root)
    source_barlines = barline_signature(root)
    parts = children(root, "part")
    summary: dict[str, object] = {"parts": len(parts), "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "restEvents": 0, "shapeNoteheadsAdded": 0, "lyricsRetained": 0, "emptyMeasures": 0, "durationEndByPart": {}, "durationFailuresAgainst2_4": {}, "sourceBarlines": source_barlines}
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = children(part, "measure")
        summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
        summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
        summary["emptyMeasures"] = int(summary["emptyMeasures"]) + sum(not children(measure, "note") for measure in measures)
        ends = {measure.attrib.get("number", ""): duration_end(measure) for measure in measures}
        summary["durationEndByPart"][part_id] = ends  # type: ignore[index]
        summary["durationFailuresAgainst2_4"][part_id] = [f"m{number}={end}" for number, end in ends.items() if end != 4]  # type: ignore[index]
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
            clock = first(attributes, "time")
            if clock is None:
                clock = ET.Element("time")
                key_index = next((i for i, item in enumerate(attributes) if local_name(item.tag) == "key"), 1)
                attributes.insert(key_index + 1, clock)
            for old in children(clock, "beats") + children(clock, "beat-type"):
                clock.remove(old)
            ET.SubElement(clock, "beats").text = "2"
            ET.SubElement(clock, "beat-type").text = "4"
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                if pitch is None:
                    if first(note, "rest") is not None:
                        summary["restEvents"] = int(summary["restEvents"]) + 1
                    continue
                step = text(pitch, "step").upper()
                if step not in SHAPES:
                    continue
                for old in children(note, "notehead"):
                    note.remove(old)
                notehead = ET.Element("notehead")
                notehead.text = SHAPES[step]
                stem_index = next((i for i, item in enumerate(note) if local_name(item.tag) == "stem"), len(note))
                note.insert(stem_index, notehead)
                summary["pitchedEvents"] = int(summary["pitchedEvents"]) + 1
                summary["shapeNoteheadsAdded"] = int(summary["shapeNoteheadsAdded"]) + 1
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    fields = {
        "atlas-queue-id": "sh2025/140",
        "atlas-transcription-status": "autonomously-blocked",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-image": str(SOURCE_IMAGE.relative_to(ROOT)),
        "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
        "atlas-source-retained-image": str(RETAINED_IMAGE.relative_to(ROOT)),
        "atlas-source-retained-image-sha256": sha256(RETAINED_IMAGE),
        "atlas-source-key": "E minor",
        "atlas-source-mode": "minor",
        "atlas-source-time-signature": "2/4",
        "atlas-source-meter": "Long Meter with Hallelujah (L.M.H.)",
        "atlas-source-repeat-ending": "The source visibly has an internal repeat/ending layout and terminal repeat-bar treatment; the retained OMR records a backward repeat at measure 16 but does not encode the complete source semantics, so none was added.",
        "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible E-minor key; not source-verified per event",
        "atlas-lyrics": "omitted; source lyrics are visible but retained OMR has no directly aligned lyric underlay",
        "atlas-provenance-policy": "immutable 2025 scan is authoritative; alternate Moreno/Red Hook witness is not an exact source; this OMR derivative is evidence only",
        "atlas-blocker": "The immutable page visibly prints MORENO. L.M.H., E minor, 2/4, four vocal parts, source lyrics, repeated/ending barline treatment, and the 2025 copyright. The retained source OMR has 16 measures per part but incomplete durations in multiple parts, no mode, no lyrics, no shapes, and only a backward repeat at measure 16 without complete source repeat/ending semantics. No unsupported notation was synthesized.",
    }
    for key, value in fields.items():
        put_field(identification, key, value)
    corrected_events = event_signature(root)
    corrected_barlines = barline_signature(root)
    return xml_name, ET.tostring(root, encoding="utf-8", xml_declaration=True), summary, source_events, corrected_events, corrected_barlines


def main() -> int:
    source_hash = sha256(SOURCE)
    image_hash = sha256(SOURCE_IMAGE)
    retained_hash = sha256(RETAINED_IMAGE)
    xml_name, xml, summary, source_events, corrected_events, corrected_barlines = transform()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml if info.filename == xml_name else source.read(info.filename))
    draft_hash = sha256(OUTPUT)
    blocking = [
        "The immutable scan visibly prints MORENO. L.M.H., E minor, 2/4, Aldo Thomas Ceresa 2008, four vocal parts, lyrics, internal repeat/ending treatment, and a terminal repeat bar.",
        "The source-scan OMR preserves 16 measures per part and 132 note events, but duration auditing fails in multiple measures (P1 m11=5; P2 m1/m2/m6/m7/m8/m11/m15/m16=0 or partial; P3 m3 and m11=5; P4 m6/m15/m16=0 or partial), so event timing is not proven source-faithful.",
        "The retained source OMR has no mode, lyrics, or four-shape notehead tags and records only a backward repeat at measure 16; the complete source-visible repeat/ending semantics were not fabricated.",
        "The same-title public candidate is an alternate composite Moreno/Red Hook page: it has 33 measures per part, begins in 3/4, changes key at measure 19, and does not encode four-shape noteheads. It cannot establish the exact 2025 source.",
        "A diagonal DO NOT COPY watermark crosses the source middle notation and lyric region, so obscured content and lyric alignment were not invented.",
    ]
    audit = {
        "queueId": "sh2025/140", "edition": "Sacred Harp, 2025 Edition", "songNo": "140", "title": "Moreno", "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {"sourcePageUrl": "https://fasola.org/indexes/2025/?p=140", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/140-Moreno/140.jpg", "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceImageSha256": image_hash, "immutable": True, "directObservations": {"header": "MORENO. L.M.H.", "composer": "Smith's Divine Hymns, 1794", "arranger": "Aldo Thomas Ceresa, 2008", "key": "E minor", "mode": "minor", "timeSignature": "2/4", "meter": "Long Meter with Hallelujah (L.M.H.)", "parts": 4, "measuresByPart": {"P1": 16, "P2": 16, "P3": 16, "P4": 16}, "lyricsVisible": True, "repeatBarsVisible": True, "endingsVisible": True, "terminalDoubleBarVisible": True, "watermarkIntersectsNotation": True}, "retainedSourceImageDuplicate": {"path": str(RETAINED_IMAGE.relative_to(ROOT)), "sha256": retained_hash, "immutable": True, "status": "same-edition-retained-duplicate-byte-different"}},
        "inputOmr": {"path": str(SOURCE.relative_to(ROOT)), "sha256": source_hash, "status": "retained-source-scan-omr", "summary": summary},
        "candidateWitness": {"candidatePdfPath": "work/source-transcriptions/2025/clean-source-candidates/140-moreno-moreno-l-m-33863d1f4c/source-candidate.pdf", "candidatePdfSha256": "47ed65a0dabac843e0bd62f63733d5e083a1713c530f259e54b3a177ededf3d3", "candidateMusicXmlPath": "work/omr/clean-source-candidates/140-moreno-moreno-l-m-895d902f50/source-candidate.mxl", "candidateMusicXmlSha256": "8d6c6c8d40029df8b53f9741ae7b0cea7f3c4625b62a06353abcbe1c4d5a4286", "candidateMusicXmlIsOmrDerivative": True, "candidateRole": "alternate composite public witness; not an authorized exact 2025 structured source", "candidateVisibleTitles": ["MORENO. L.M.", "RED HOOK. 6, 6, 9."]},
        "correctedDraft": {"path": str(OUTPUT.relative_to(ROOT)), "sha256": draft_hash, "summary": summary, "eventStreamPreservedFromInput": True, "sourceEventSignature": source_events, "correctedEventSignature": corrected_events, "sourceBarlines": summary["sourceBarlines"], "correctedBarlines": corrected_barlines, "corrections": ["source E-minor key and explicit minor mode", "source 2/4 time signature", "four-shape noteheads derived for every retained pitched event", "source lyric/repeat/watermark visibility recorded in provenance", "lyrics and uncertain repeat/ending semantics intentionally omitted"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceScanSha256": image_hash, "retainedDuplicatePath": str(RETAINED_IMAGE.relative_to(ROOT)), "retainedDuplicateSha256": retained_hash, "method": "full-resolution visual inspection of requested immutable source scan plus retained source MXL and alternate candidate audit; no alternate witness used to fill source events", "blockingFindings": blocking},
        "blockingFindings": blocking,
        "blockingReason": "Autonomous promotion is blocked by incomplete source-OMR durations, absent lyrics and four-shape encoding, incomplete repeat/ending semantics, watermark-obscured source regions, and the alternate composite candidate's 16-versus-33-measure and 2/4-versus-3/4 mismatch. The corrected derivative remains review-only.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-alternate-composite-mismatch; retain-corrected-draft-only",
        "policy": "Immutable 2025 scan remains authoritative. Alternate-edition/composite candidates and OMR-derived shape tags are evidence only and cannot authorize corpus promotion.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"audit": str(AUDIT.relative_to(ROOT)), "record": audit["queueId"], "status": audit["comparisonStatus"], "sourceImageSha256": image_hash, "retainedImageSha256": retained_hash, "inputOmrSha256": source_hash, "correctedDraftSha256": draft_hash, "summary": summary}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
