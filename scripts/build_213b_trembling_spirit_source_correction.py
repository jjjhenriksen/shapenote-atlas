#!/usr/bin/env python3
"""Create a source-derived, fail-closed Trembling Spirit derivative."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/omr/213b-trembling-spirit/source.mxl"
SOURCE_IMAGE = next(ROOT.glob("work/source-images/2025/213b-trembling-spirit-*.jpg"))
CANDIDATE_PDF = ROOT / "work/source-transcriptions/2025/clean-source-candidates/213b-trembling-spirit-trembling-spirit-s-m-acfa6f3314/source-candidate.pdf"
CANDIDATE_MXL = ROOT / "work/omr/clean-source-candidates/213b-trembling-spirit-trembling-spirit-s-m-b238900b0b/source-candidate.mxl"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/213b-trembling-spirit-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/213b-trembling-spirit-source-correction-v2-comparison.json"

# Four-shape spellings for G major, the relative major of printed E minor.
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
    cursor = 0
    maximum = 0
    for item in measure:
        item_name = local_name(item.tag)
        duration = first(item, "duration")
        units = int(duration.text) if duration is not None and duration.text and duration.text.isdigit() else 0
        if item_name == "note":
            if first(item, "chord") is None:
                cursor += units
            maximum = max(maximum, cursor)
        elif item_name == "backup":
            cursor -= units
        elif item_name == "forward":
            cursor += units
    return maximum


def event_signature(root: ET.Element) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for part in children(root, "part"):
        rows: list[dict[str, str]] = []
        for measure in children(part, "measure"):
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                pitch_value = "rest" if first(note, "rest") is not None else "unknown"
                if pitch is not None:
                    pitch_value = ":".join([text(pitch, "step"), text(pitch, "alter", "0"), text(pitch, "octave")])
                rows.append({"measure": measure.attrib.get("number", ""), "pitch": pitch_value, "duration": text(note, "duration"), "type": text(note, "type"), "voice": text(note, "voice")})
        result[part.attrib.get("id", "")] = rows
    return result


def barline_signature(root: ET.Element) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for part in children(root, "part"):
        rows = []
        for measure in children(part, "measure"):
            for bar in children(measure, "barline"):
                repeat = first(bar, "repeat")
                ending = first(bar, "ending")
                rows.append({"measure": measure.attrib.get("number", ""), "location": bar.attrib.get("location", ""), "style": text(bar, "bar-style"), "repeat": repeat.attrib.get("direction", "") if repeat is not None else "", "ending": ending.attrib.get("number", "") if ending is not None else ""})
        result[part.attrib.get("id", "")] = rows
    return result


def read_score(path: Path) -> tuple[ET.Element, dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    with zipfile.ZipFile(path) as archive:
        xml_name = next(item for item in archive.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        root = ET.fromstring(archive.read(xml_name))
    return root, event_signature(root), barline_signature(root)


def transform() -> tuple[bytes, dict[str, object], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    with zipfile.ZipFile(SOURCE) as archive:
        xml_name = next(item for item in archive.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        root = ET.fromstring(archive.read(xml_name))
        source_events = event_signature(root)
        source_barlines = barline_signature(root)
        parts = children(root, "part")
        summary: dict[str, object] = {"parts": len(parts), "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "shapeNoteheadsAdded": 0, "lyricsRetained": 0, "durationFailuresAgainst4_4": {}, "sourceBarlines": source_barlines}
        for part in parts:
            part_id = part.attrib.get("id", "")
            measures = children(part, "measure")
            summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
            summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
            summary["durationFailuresAgainst4_4"][part_id] = [  # type: ignore[index]
                f"m{measure.attrib.get('number')}={duration_end(measure)}" for measure in measures if duration_end(measure) != 8
            ]
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
                ET.SubElement(clock, "beats").text = "4"
                ET.SubElement(clock, "beat-type").text = "4"
                for note in children(measure, "note"):
                    pitch = first(note, "pitch")
                    if pitch is None:
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
        for key, value in {
            "atlas-queue-id": "sh2025/213b",
            "atlas-transcription-status": "autonomously-blocked",
            "atlas-review-status": "autonomously-blocked-source-derived-draft",
            "atlas-safe-to-promote": "false",
            "atlas-source-image": str(SOURCE_IMAGE.relative_to(ROOT)),
            "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
            "atlas-source-key": "E minor",
            "atlas-source-mode": "minor",
            "atlas-source-time-signature": "4/4",
            "atlas-source-meter": "Short Meter (6,6,8,6)",
            "atlas-source-repeat-ending": "D.C. markings and repeat-style barlines are visible on the immutable page; retained OMR does not encode them as a verified structural witness",
            "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible E-minor key; not source-verified per event",
            "atlas-lyrics": "omitted; retained OMR contains no directly aligned lyric underlay",
            "atlas-provenance-policy": "immutable 2025 scan is authoritative; same-title candidate and this OMR derivative are evidence only",
            "atlas-blocker": "The page is source-complete, but retained OMR has blank measures and duration/event gaps, no lyrics or shape tags, and no verified D.C./repeat structure. The diagonal watermark crosses the middle system. No notation was synthesized.",
        }.items():
            put_field(identification, key, value)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), summary, source_events, source_barlines


def main() -> int:
    source_hash = sha256(SOURCE)
    image_hash = sha256(SOURCE_IMAGE)
    candidate_pdf_hash = sha256(CANDIDATE_PDF)
    candidate_mxl_hash = sha256(CANDIDATE_MXL)
    xml, summary, source_events, source_barlines = transform()
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml if info.filename == "source.xml" else source.read(info.filename))
    draft_hash = sha256(OUTPUT)
    with zipfile.ZipFile(OUTPUT) as archive:
        corrected_root = ET.fromstring(archive.read("source.xml"))
    corrected_events = event_signature(corrected_root)
    corrected_barlines = barline_signature(corrected_root)
    candidate_root, candidate_events, candidate_barlines = read_score(CANDIDATE_MXL)
    blocking = [
        "The immutable scan visibly prints TREMBLING SPIRIT S.M., E minor, 4/4, four vocal parts, visible lyrics, and D.C. markings/repeat-style barlines across an eight-measure setting.",
        "The retained source-scan OMR contains only 19/13/19/19 events in P1/P2/P3/P4 and blank source-visible measures, including P2 m1,m3,m4,m7, P3 m3,m4,m8, and P4 m2,m4; it is not a complete event witness.",
        "The retained source OMR has duration failures against 4/4 in the exact per-part measures recorded in durationFailuresAgainst4_4 and does not encode the visible D.C./repeat structure as authoritative playback data.",
        "The source OMR has no lyrics or four-shape noteheads and its one-sharp key lacks mode; the derivative adds E-minor metadata and derived shapes without rewriting uncertain events.",
        "The matching candidate has the same broad eight-measure setting but is an OMR-derived public witness without four-shape tags or encoded mode, and it is not an authorized 2025 engraving.",
        "The diagonal watermark crosses the middle system, so obscured source intersections cannot be proven from the current raster alone.",
    ]
    audit = {
        "queueId": "sh2025/213b", "edition": "Sacred Harp, 2025 Edition", "songNo": "213b", "title": "Trembling Spirit", "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {"sourcePageUrl": "https://fasola.org/indexes/2025/?p=213b", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/213b-Trembling-Spirit/213b.jpg", "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceImageSha256": image_hash, "immutable": True, "directObservations": {"header": "TREMBLING SPIRIT. S.M.", "key": "E minor", "mode": "minor", "timeSignature": "4/4", "meter": "Short Meter (6,6,8,6)", "parts": 4, "measuresByPart": {"P1": 8, "P2": 8, "P3": 8, "P4": 8}, "lyricsVisible": True, "dcMarkingsVisible": True, "watermarkAffectedRegions": "middle system"}},
        "inputOmr": {"path": "work/omr/213b-trembling-spirit/source.mxl", "sha256": source_hash, "status": "retained-source-scan-omr"},
        "candidateWitness": {"candidatePageUrl": "https://www.sacredharptunes.com/author/jesse/trembling-spirit/", "candidatePdfPath": "work/source-transcriptions/2025/clean-source-candidates/213b-trembling-spirit-trembling-spirit-s-m-acfa6f3314/source-candidate.pdf", "candidatePdfSha256": candidate_pdf_hash, "candidateMusicXmlPath": "work/omr/clean-source-candidates/213b-trembling-spirit-trembling-spirit-s-m-b238900b0b/source-candidate.mxl", "candidateMusicXmlSha256": candidate_mxl_hash, "candidateMusicXmlIsOmrDerivative": True, "candidateEdition": "same-title public witness; alternate engraving identity unproven", "candidateStructuredEvidence": {"parts": len(candidate_root.findall('./part')), "measuresByPart": {p.attrib.get('id', ''): len(p.findall('./measure')) for p in candidate_root.findall('./part')}, "eventsByPart": {p.attrib.get('id', ''): len(candidate_events.get(p.attrib.get('id', ''), [])) for p in candidate_root.findall('./part')}, "barlines": candidate_barlines, "shapeNoteheads": sum(1 for item in candidate_root.iter() if local_name(item.tag) == 'notehead'), "lyrics": sum(1 for item in candidate_root.iter() if local_name(item.tag) == 'lyric')}},
        "correctedDraft": {"path": "work/omr/autonomous-transcriptions/2025/213b-trembling-spirit-source-correction-v2.mxl", "sha256": draft_hash, "summary": summary, "eventStreamPreservedFromInput": True, "sourceEventSignature": source_events, "correctedEventSignature": corrected_events, "sourceBarlines": source_barlines, "correctedBarlines": corrected_barlines, "corrections": ["source E-minor key and explicit minor mode", "source 4/4 time signature", "four-shape noteheads added to every retained pitched event", "source D.C./repeat visibility recorded in provenance", "lyrics intentionally omitted because direct alignment is unavailable"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceScanSha256": image_hash, "method": "full-resolution visual inspection of immutable scan plus XML event/duration/topology/barline audit; same-title candidate retained distinctly", "blockingFindings": blocking},
        "blockingReason": "Autonomous promotion is blocked by incomplete source-scan OMR events and durations, missing lyrics/shapes/repeat structure, watermark-obscured intersections, and lack of an authorized exact-edition structured witness. The derivative preserves detected events and adds source metadata/shapes without fabrication.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness; retain-corrected-draft-only",
        "policy": "Immutable 2025 source remains authoritative. This corrected derivative and the public same-title witness are not authoritative corpus assets.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/213b", "status": audit["comparisonStatus"], "sourceImageSha256": image_hash, "inputOmrSha256": source_hash, "candidatePdfSha256": candidate_pdf_hash, "candidateMusicXmlSha256": candidate_mxl_hash, "correctedDraftSha256": draft_hash, "summary": summary, "audit": str(AUDIT.relative_to(ROOT))}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
