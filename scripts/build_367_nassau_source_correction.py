#!/usr/bin/env python3
"""Create a source-derived, fail-closed Nassau correction derivative."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/omr/367-nassau/source.mxl"
SOURCE_IMAGE = ROOT / "work/omr/367-nassau/source.jpg"
ALT_IMAGE = next(ROOT.glob("work/source-images/2025/367-nassau-*.jpg"))
CANDIDATE_PDF = ROOT / "work/source-transcriptions/2025/clean-source-candidates/367-nassau-nassau-c-m-d-94bcf18130/source-candidate.pdf"
CANDIDATE_MXL = ROOT / "work/omr/clean-source-candidates/367-nassau-nassau-c-m-d-3be1d43d29/source-candidate.mxl"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/367-nassau-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/367-nassau-source-correction-v2-comparison.json"

# Four-shape spellings for C major, the relative major of printed A minor.
SHAPES = {"A": "la", "B": "mi", "C": "fa", "D": "sol", "E": "la", "F": "fa", "G": "sol"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(parent: ET.Element | None, wanted: str) -> list[ET.Element]:
    return [child for child in parent if name(child.tag) == wanted] if parent is not None else []


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
        item_name = name(item.tag)
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


def events(root: ET.Element) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for part in children(root, "part"):
        rows: list[dict[str, str]] = []
        for measure in children(part, "measure"):
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                if pitch is None:
                    pitch_value = "rest" if first(note, "rest") is not None else "unknown"
                else:
                    pitch_value = ":".join([text(pitch, "step"), text(pitch, "alter", "0"), text(pitch, "octave")])
                rows.append({"measure": measure.attrib.get("number", ""), "pitch": pitch_value, "duration": text(note, "duration"), "type": text(note, "type"), "voice": text(note, "voice")})
        result[part.attrib.get("id", "")] = rows
    return result


def barlines(root: ET.Element) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for part in children(root, "part"):
        rows = []
        for measure in children(part, "measure"):
            for line in children(measure, "barline"):
                repeat = first(line, "repeat")
                ending = first(line, "ending")
                rows.append({"measure": measure.attrib.get("number", ""), "location": line.attrib.get("location", ""), "style": text(line, "bar-style"), "repeat": repeat.attrib.get("direction", "") if repeat is not None else "", "ending": ending.attrib.get("number", "") if ending is not None else ""})
        result[part.attrib.get("id", "")] = rows
    return result


def read_score(path: Path) -> tuple[ET.Element, dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    with zipfile.ZipFile(path) as archive:
        xml_name = next(item for item in archive.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        root = ET.fromstring(archive.read(xml_name))
    return root, events(root), barlines(root)


def transform() -> tuple[bytes, dict[str, object], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    with zipfile.ZipFile(SOURCE) as archive:
        xml_name = next(item for item in archive.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        root = ET.fromstring(archive.read(xml_name))
        source_events = events(root)
        source_barlines = barlines(root)
        parts = children(root, "part")
        summary: dict[str, object] = {"parts": len(parts), "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "shapeNoteheadsAdded": 0, "lyricsRetained": 0, "durationFailuresAgainst4_4": {}, "sourceBarlines": source_barlines}
        for part in parts:
            part_id = part.attrib.get("id", "")
            measures = children(part, "measure")
            summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
            summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
            summary["durationFailuresAgainst4_4"][part_id] = [  # type: ignore[index]
                f"m{measure.attrib.get('number')}={duration_end(measure)}"
                for measure in measures
                if duration_end(measure) != 12
            ]
            for measure_index, measure in enumerate(measures):
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
                ET.SubElement(key, "fifths").text = "0"
                ET.SubElement(key, "mode").text = "minor"
                clock = first(attributes, "time")
                if clock is None:
                    clock = ET.Element("time")
                    key_index = next((i for i, item in enumerate(attributes) if name(item.tag) == "key"), 1)
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
                    stem_index = next((i for i, item in enumerate(note) if name(item.tag) == "stem"), len(note))
                    note.insert(stem_index, notehead)
                    summary["pitchedEvents"] = int(summary["pitchedEvents"]) + 1
                    summary["shapeNoteheadsAdded"] = int(summary["shapeNoteheadsAdded"]) + 1
        identification = first(root, "identification")
        if identification is None:
            identification = ET.Element("identification")
            root.insert(0, identification)
        for key, value in {
            "atlas-queue-id": "sh2025/367",
            "atlas-transcription-status": "autonomously-blocked",
            "atlas-review-status": "autonomously-blocked-source-derived-draft",
            "atlas-safe-to-promote": "false",
            "atlas-source-image": "work/omr/367-nassau/source.jpg",
            "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
            "atlas-source-key": "A minor",
            "atlas-source-mode": "minor",
            "atlas-source-time-signature": "4/4",
            "atlas-source-meter": "Common Meter Double (8,6,8,6,8,6,8,6)",
            "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible A-minor key; not source-verified per event",
            "atlas-lyrics": "omitted; retained OMR contains no directly aligned lyric underlay",
            "atlas-provenance-policy": "immutable 2025 scan is authoritative; dated same-setting candidate and this OMR derivative are evidence only",
            "atlas-blocker": "The scan visibly contains 24 measures per part in two sections with repeat/ending markings; the delegation's 15-measure assertion conflicts with the direct scan and current source metadata. Retained OMR event grouping is incomplete and lyrics/repeats are not fully encoded.",
        }.items():
            put_field(identification, key, value)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), summary, source_events, source_barlines


def main() -> int:
    source_hash = sha256(SOURCE)
    source_image_hash = sha256(SOURCE_IMAGE)
    alt_image_hash = sha256(ALT_IMAGE)
    candidate_pdf_hash = sha256(CANDIDATE_PDF)
    candidate_mxl_hash = sha256(CANDIDATE_MXL)
    xml, summary, source_events, source_barlines = transform()
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml if info.filename == "source.xml" else source.read(info.filename))
    draft_hash = sha256(OUTPUT)
    with zipfile.ZipFile(OUTPUT) as archive:
        corrected_root = ET.fromstring(archive.read("source.xml"))
    corrected_events = events(corrected_root)
    corrected_barlines = barlines(corrected_root)
    candidate_root, candidate_events, candidate_barlines = read_score(CANDIDATE_MXL)
    blocking = [
        "The immutable scan visually shows NASSAU C.M.D., A minor, 4/4, four vocal parts, lyrics, two 12-measure sections, repeats, and alternate endings; direct scan structure is 24 measures per part, contradicting the delegated 15-measure count.",
        "The retained source OMR has 53/32/43/65 events in P1/P2/P3/P4 and blank measures including P2 m2,m4,m9,m11-m15, P3 m2,m4,m9,m11-m13, and P4 m16,m24 despite visible source notation.",
        "The retained OMR has duration failures against 4/4 at the exact per-part measures recorded in durationFailuresAgainst4_4; it does not encode the source repeat/ending structure as an authoritative witness.",
        "The source OMR has no reliable key/mode/time metadata, no lyrics, and no four-shape tags; the derivative adds source-level metadata and derived shapes without rewriting uncertain events.",
        "The same-setting candidate is dated 1803 while the 2025 scan prints 1804. Its MusicXML is an OMR derivative without shape tags and cannot establish exact 2025 edition identity.",
        "The watermark crosses the bass/closing systems, so obscured source intersections cannot be proven from the current raster alone.",
    ]
    audit = {
        "queueId": "sh2025/367", "edition": "Sacred Harp, 2025 Edition", "songNo": "367", "title": "Nassau", "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {"sourcePageUrl": "https://fasola.org/indexes/2025/?p=367", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/367-Nassau/367.jpg", "sourceImagePath": "work/omr/367-nassau/source.jpg", "sourceImageSha256": source_image_hash, "alternateRetainedPath": str(ALT_IMAGE.relative_to(ROOT)), "alternateRetainedSha256": alt_image_hash, "immutable": True, "directObservations": {"header": "NASSAU. C.M.D.", "key": "A minor", "mode": "minor", "timeSignature": "4/4", "meter": "Common Meter Double (8,6,8,6,8,6,8,6)", "parts": 4, "measuresByPart": {"P1": 24, "P2": 24, "P3": 24, "P4": 24}, "sections": 2, "repeatsAndEndingsVisible": True, "lyricsVisible": True, "watermarkAffectedRegions": "middle/lower and bass closing systems"}, "delegatedMeasureClaim": {"measuresByPart": 15, "status": "conflicts-with-direct-scan-and-existing-source-metadata"}},
        "inputOmr": {"path": "work/omr/367-nassau/source.mxl", "sha256": source_hash, "status": "retained-source-scan-omr"},
        "candidateWitness": {"candidatePageUrl": "https://www.sacredharptunes.com/author/lauren/nassau-2/", "candidatePdfPath": "work/source-transcriptions/2025/clean-source-candidates/367-nassau-nassau-c-m-d-94bcf18130/source-candidate.pdf", "candidatePdfSha256": candidate_pdf_hash, "candidateMusicXmlPath": "work/omr/clean-source-candidates/367-nassau-nassau-c-m-d-3be1d43d29/source-candidate.mxl", "candidateMusicXmlSha256": candidate_mxl_hash, "candidateMusicXmlIsOmrDerivative": True, "candidateEdition": "same-setting witness printed 1803; alternate/dated witness only", "candidateStructuredEvidence": {"parts": len(candidate_root.findall('./part')), "measuresByPart": {part.attrib.get('id', ''): len(part.findall('./measure')) for part in candidate_root.findall('./part')}, "eventsByPart": {part.attrib.get('id', ''): len(candidate_events.get(part.attrib.get('id', ''), [])) for part in candidate_root.findall('./part')}, "barlines": candidate_barlines, "shapeNoteheads": sum(1 for item in candidate_root.iter() if name(item.tag) == 'notehead'), "lyrics": sum(1 for item in candidate_root.iter() if name(item.tag) == 'lyric')}},
        "correctedDraft": {"path": "work/omr/autonomous-transcriptions/2025/367-nassau-source-correction-v2.mxl", "sha256": draft_hash, "summary": summary, "eventStreamPreservedFromInput": True, "sourceEventSignature": source_events, "correctedEventSignature": corrected_events, "sourceBarlines": source_barlines, "correctedBarlines": corrected_barlines, "corrections": ["source A-minor key and explicit minor mode", "source 4/4 time signature", "four-shape noteheads added to every retained pitched event", "provenance/fail-closed fields added", "lyrics intentionally omitted because direct alignment is unavailable"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": "work/omr/367-nassau/source.jpg", "sourceScanSha256": source_image_hash, "method": "full-resolution visual inspection of immutable scan plus XML event/duration/topology/barline audit; same-setting candidate retained distinctly", "blockingFindings": blocking},
        "blockingReason": "Autonomous promotion is blocked by the direct-scan/hand-off measure-count conflict, incomplete OMR events and durations, missing authoritative lyrics/repeats/shapes, the 1803/1804 witness discrepancy, and watermark-obscured intersections. The derivative preserves detected events and adds source metadata/shapes without fabricating notation.",
        "nextAction": "autonomous-promotion-blocked-by-conflicting-structure-and-incomplete-source-event-witness; retain-corrected-draft-only",
        "policy": "Immutable 2025 source remains authoritative. This corrected derivative and the dated candidate witness are not authoritative corpus assets.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/367", "status": audit["comparisonStatus"], "sourceImageSha256": source_image_hash, "alternateImageSha256": alt_image_hash, "inputOmrSha256": source_hash, "candidatePdfSha256": candidate_pdf_hash, "candidateMusicXmlSha256": candidate_mxl_hash, "correctedDraftSha256": draft_hash, "summary": summary, "audit": str(AUDIT.relative_to(ROOT))}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
