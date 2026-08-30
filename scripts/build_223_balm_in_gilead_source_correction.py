#!/usr/bin/env python3
"""Create a source-derived, fail-closed Balm in Gilead derivative."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/omr/223-balm-in-gilead/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/223-balm-in-gilead-df9724d780.jpg"
SOURCE = ROOT / "work/omr/223-balm-in-gilead/source.mxl"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/223-balm-in-gilead-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/223-balm-in-gilead-source-correction-v2-comparison.json"

# F minor uses the relative A-flat-major four-shape spelling:
# A-flat=fa, B-flat=sol, C=la, D-flat=fa, E-flat=sol, F=la, G=mi.
SHAPES = {"A": "fa", "B": "sol", "C": "la", "D": "fa", "E": "sol", "F": "la", "G": "mi"}


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
    summary: dict[str, object] = {"parts": len(parts), "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "restEvents": 0, "shapeNoteheadsAdded": 0, "lyricsRetained": 0, "emptyMeasures": 0, "durationEndByPart": {}, "durationFailuresAgainst4_4": {}, "sourceBarlines": source_barlines}
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = children(part, "measure")
        summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
        summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
        summary["emptyMeasures"] = int(summary["emptyMeasures"]) + sum(not children(measure, "note") for measure in measures)
        ends = {measure.attrib.get("number", ""): duration_end(measure) for measure in measures}
        summary["durationEndByPart"][part_id] = ends  # type: ignore[index]
        summary["durationFailuresAgainst4_4"][part_id] = [f"m{number}={end}" for number, end in ends.items() if end != 24]  # type: ignore[index]
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
            ET.SubElement(key, "fifths").text = "-4"
            ET.SubElement(key, "mode").text = "minor"
            clock = first(attributes, "time")
            if clock is None:
                clock = ET.Element("time")
                key_index = next((i for i, item in enumerate(attributes) if local_name(item.tag) == "key"), 1)
                attributes.insert(key_index + 1, clock)
            for old in children(clock, "beats") + children(clock, "beat-type"):
                clock.remove(old)
            ET.SubElement(clock, "beats").text = "4"
            ET.SubElement(clock, "beat-type").text = "4"
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
                stem_index = next((i for i, item in enumerate(note) if local_name(item.tag) == "stem"), len(note))
                note.insert(stem_index, notehead)
                summary["pitchedEvents"] = int(summary["pitchedEvents"]) + 1
                summary["shapeNoteheadsAdded"] = int(summary["shapeNoteheadsAdded"]) + 1
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    fields = {
        "atlas-queue-id": "sh2025/223",
        "atlas-transcription-status": "autonomously-blocked",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-image": str(SOURCE_IMAGE.relative_to(ROOT)),
        "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
        "atlas-source-retained-image": str(RETAINED_IMAGE.relative_to(ROOT)),
        "atlas-source-retained-image-sha256": sha256(RETAINED_IMAGE),
        "atlas-source-key": "F minor",
        "atlas-source-mode": "minor",
        "atlas-source-time-signature": "4/4",
        "atlas-source-meter": "7s & 6s.",
        "atlas-source-repeat-ending": "The source visibly has a repeated second section with numbered endings and a terminal double bar; the retained OMR does not encode complete repeat/ending semantics, so none was fabricated.",
        "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible F-minor key; not source-verified per event",
        "atlas-lyrics": "omitted; source lyrics are visible but retained OMR has no directly aligned lyric underlay",
        "atlas-provenance-policy": "immutable 2025 scan is authoritative; no authorized same-title structured witness was used; this OMR derivative is evidence only",
        "atlas-blocker": "The immutable page visibly prints BALM IN GILEAD. 7s & 6s., F minor, four vocal parts, lyrics, repeated second-section endings, and a terminal double bar. The retained source OMR exports 15 measures per part but Audiveris reports 17 raw measures, and the exported events fail 4/4 duration auditing across all parts. It has no lyrics, no source-confirmed shapes, and no complete repeat/ending semantics. No unsupported notation was synthesized.",
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
        "The immutable scan visibly establishes Balm in Gilead, 7s & 6s., F minor, 4/4, four vocal parts, lyrics, repeated second-section endings, and a terminal double bar.",
        "The retained source OMR exports 15 measures per part and 177 note events (176 pitched and 1 rest), but Audiveris reports 17 raw measures; its duration ends fail the 4/4 target across all four parts, so event timing and topology are not proven source-faithful.",
        "The retained source OMR has no lyrics, no four-shape notehead tags, and no complete source repeat/ending semantics. The derivative adds observed F-minor/4/4 metadata and derived shapes without rewriting uncertain events.",
        "No authorized same-title structured witness was available, so no alternate tune or edition was used to fill missing events, lyrics, rhythms, repeats, or shapes.",
    ]
    audit = {
        "queueId": "sh2025/223", "edition": "Sacred Harp, 2025 Edition", "songNo": "223", "title": "Balm in Gilead", "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {"sourcePageUrl": "https://fasola.org/indexes/2025/?p=223", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/223-Balm-in-Gilead/223.jpg", "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceImageSha256": image_hash, "immutable": True, "directObservations": {"header": "BALM IN GILEAD. 7s & 6s.", "credits": "V. 1, 3 Meta Heusser-Schweitzer, 1837; tr. Jane Borthwick, 1884; v. 2 Anna Laetitia Waring, 1850; Arr. Rebecca Wright, 2018", "key": "F minor", "mode": "minor", "timeSignature": "4/4", "meter": "7s & 6s.", "parts": 4, "measuresByPart": {"P1": 15, "P2": 15, "P3": 15, "P4": 15}, "lyricsVisible": True, "repeatBarsVisible": True, "endingsVisible": True, "terminalDoubleBarVisible": True, "watermarkIntersectsNotation": True}, "retainedSourceImageDuplicate": {"path": str(RETAINED_IMAGE.relative_to(ROOT)), "sha256": retained_hash, "immutable": True, "byteEqualToRequestedSource": True}},
        "inputOmr": {"path": str(SOURCE.relative_to(ROOT)), "sha256": source_hash, "status": "retained-source-scan-omr", "summary": input_summary},
        "candidateWitness": {"available": False, "candidateRole": "No authorized same-title structured witness was available; alternate editions were not used."},
        "correctedDraft": {"path": str(OUTPUT.relative_to(ROOT)), "sha256": draft_hash, "summary": summary, "eventStreamPreservedFromInput": source_events == corrected_events, "sourceEventSignature": source_events, "correctedEventSignature": corrected_events, "sourceBarlines": source_barlines, "correctedBarlines": corrected_barlines, "corrections": ["source F-minor key and explicit minor mode", "source 4/4 time signature", "four-shape noteheads derived for every retained pitched event", "source lyric/repeat/watermark visibility recorded in provenance", "lyrics and uncertain repeat/ending semantics intentionally omitted"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceScanSha256": image_hash, "retainedDuplicatePath": str(RETAINED_IMAGE.relative_to(ROOT)), "retainedDuplicateSha256": retained_hash, "method": "full-resolution visual inspection of immutable source scan plus retained source MXL and Audiveris audit; no alternate witness used to fill source events", "blockingFindings": blocking},
        "blockingFindings": blocking,
        "blockingReason": "Autonomous promotion is blocked by the 15-versus-17 measure topology discrepancy, pervasive duration failures against source 4/4, absent lyrics and source-confirmed per-note shapes, incomplete repeat/ending semantics, and lack of an authorized exact-edition structured witness. The corrected derivative remains review-only.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-unresolved-topology; retain-corrected-draft-only",
        "policy": "Immutable 2025 scan remains authoritative. OMR-derived events and shape tags are evidence only and cannot authorize corpus promotion without direct source proof.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"audit": str(AUDIT.relative_to(ROOT)), "record": audit["queueId"], "status": audit["comparisonStatus"], "sourceImageSha256": image_hash, "retainedImageSha256": retained_hash, "inputOmrSha256": source_hash, "correctedDraftSha256": draft_hash, "summary": summary}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
