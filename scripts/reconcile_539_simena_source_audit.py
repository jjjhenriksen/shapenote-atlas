#!/usr/bin/env python3
"""Reconcile Simena's retained scan OMR into an autonomous block."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from reconcile_437_enoch_source_audit import retime_summary, score_stats


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/omr/539-simena/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/539-simena-fd54c55dab.jpg"
RAW_OMR = ROOT / "work/omr/539-simena/source.mxl"
CANDIDATE_PDF = ROOT / "work/source-transcriptions/2025/clean-source-candidates/539-simena-simena-f209d45efd/source-candidate.pdf"
CANDIDATE_OMR = ROOT / "work/omr/clean-source-candidates/539-simena-simena-fddb73d604/page-303.mxl"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/539-simena-source-correction.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/539-source-shape-autonomous-blocked-comparison.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(parent: ET.Element | None, wanted: str) -> list[ET.Element]:
    return [child for child in (parent if parent is not None else []) if clean(child.tag) == wanted]


def first(parent: ET.Element | None, wanted: str) -> ET.Element | None:
    return next(iter(children(parent, wanted)), None)


def replace_child(parent: ET.Element, wanted: str, value: str, after: set[str] | None = None) -> ET.Element:
    matches = children(parent, wanted)
    if matches:
        result = matches[0]
        result.text = value
        for duplicate in matches[1:]:
            parent.remove(duplicate)
        return result
    result = ET.Element(wanted)
    result.text = value
    if after:
        indexes = [index for index, item in enumerate(parent) if clean(item.tag) in after]
        parent.insert(max(indexes) + 1 if indexes else len(parent), result)
    else:
        parent.append(result)
    return result


def put_field(identification: ET.Element, name: str, value: str) -> None:
    miscellaneous = first(identification, "miscellaneous")
    if miscellaneous is None:
        miscellaneous = ET.SubElement(identification, "miscellaneous")
    fields = [item for item in children(miscellaneous, "miscellaneous-field") if item.attrib.get("name") == name]
    field = fields[0] if fields else ET.SubElement(miscellaneous, "miscellaneous-field", {"name": name})
    field.text = value
    for duplicate in fields[1:]:
        miscellaneous.remove(duplicate)


def update_xml(xml_bytes: bytes, source_hash: str, raw_hash: str) -> bytes:
    root = ET.fromstring(xml_bytes)
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
        # The scan prints F Major: one flat.
        replace_child(key, "fifths", "-1")
        replace_child(key, "mode", "major", {"fifths"})
        clock = first(attributes, "time")
        if clock is None:
            clock = ET.SubElement(attributes, "time")
        replace_child(clock, "beats", "4")
        replace_child(clock, "beat-type", "4", {"beats"})
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    fields = {
        "atlas-review-queue-id": "sh2025/539",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-key": "F major",
        "atlas-source-mode": "major",
        "atlas-source-time-signature": "4/4",
        "atlas-shape-encoding": "not encoded; source-visible shapes are not independently verified per note",
        "atlas-lyrics-encoding": "not encoded; two source-visible stanzas are not directly syllable-aligned",
        "atlas-repeat-ending-encoding": "not encoded; source-visible repeats and numbered endings are not independently reconstructed",
        "atlas-provenance-policy": "autonomous block; immutable 2025 source remains authoritative; no OMR promotion",
        "atlas-source-image-sha256": source_hash,
        "atlas-source-omr-sha256": raw_hash,
    }
    for name, value in fields.items():
        put_field(identification, name, value)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_output(source_hash: str, raw_hash: str) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(RAW_OMR) as source_zip, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        xml_name = next(name for name in source_zip.namelist() if name.endswith(".xml") and not name.startswith("META-INF/"))
        updated = update_xml(source_zip.read(xml_name), source_hash, raw_hash)
        for info in source_zip.infolist():
            target.writestr(info, updated if info.filename == xml_name else source_zip.read(info.filename))


def main() -> int:
    for path in (SOURCE_IMAGE, RETAINED_IMAGE, RAW_OMR, CANDIDATE_PDF, CANDIDATE_OMR):
        if not path.is_file():
            raise FileNotFoundError(path)
    source_hash = sha256(SOURCE_IMAGE)
    retained_hash = sha256(RETAINED_IMAGE)
    raw_hash = sha256(RAW_OMR)
    candidate_pdf_hash = sha256(CANDIDATE_PDF)
    candidate_omr_hash = sha256(CANDIDATE_OMR)
    write_output(source_hash, raw_hash)
    draft_hash = sha256(OUTPUT)
    raw = retime_summary(score_stats(RAW_OMR), beats=4)
    draft = retime_summary(score_stats(OUTPUT), beats=4)
    candidate = retime_summary(score_stats(CANDIDATE_OMR), beats=4)
    blocking = [
        "The immutable page visibly identifies SIMENA. S.P.M., F major, 4/4, Isaac Watts (1719), Myles Louis Dakan (2014), four vocal parts, and two source-visible lyric stanzas. Repeat bars with numbered first/second endings and a terminal double bar are visible; a diagonal DO NOT COPY watermark intersects the middle/lower systems.",
        "Audiveris reports 21 raw measures across two systems (12 and 9), while the retained source-scan MXL exports 20 measures per part. The retained score contains 166 pitched events, 18 empty exported measures, and 68 of 80 exported part-measures fail the 4/4 duration target at divisions=2. The source event stream, durations, and measure topology are therefore not proven complete.",
        "The same-titled public composite-page candidate has 18 measures per part, 126 pitched events, 7 empty measures, and 55 duration failures, so it is not a structured match to the source-scan witness. Its MusicXML has no four-shape notehead tags and is an OMR derivative of a non-authoritative public page. The retained OMR and corrected derivative contain no lyrics, repeat/ending elements, or per-note four-shape encoding. No unsupported event, lyric, repeat, ending, or watermark-obscured material was fabricated.",
        "No authorized exact-edition structured Simena witness was available. The public composite PDF and its OMR are retained as distinct alternate witnesses and were not used to fill notes, durations, lyrics, repeats, endings, or shapes.",
    ]
    audit = {
        "queueId": "sh2025/539", "edition": "Sacred Harp, 2025 Edition", "songNo": "539", "title": "Simena",
        "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=539", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/539-Simena/539.jpg",
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceImageSha256": source_hash, "immutable": True,
            "directObservations": {
                "header": "SIMENA. S.P.M.", "composer": "Isaac Watts, 1719", "arranger": "Myles Louis Dakan, 2014", "key": "F major", "mode": "major", "timeSignature": "4/4", "meter": "Short Particular Meter (6,6,8,6)", "parts": 4,
                "sourceRawMeasuresFromAudiveris": 21, "sourceRawMeasuresBySystem": [12, 9], "exportedMeasuresByPart": {"P1": 20, "P2": 20, "P3": 20, "P4": 20},
                "sourceLyricsVisible": True, "sourceStanzaCount": 2, "repeatBarsVisible": True, "numberedEndingsVisible": True, "terminalDoubleBarVisible": True, "watermarkIntersectsNotation": True,
            },
        },
        "retainedSourceImageDuplicate": {"path": str(RETAINED_IMAGE.relative_to(ROOT)), "sha256": retained_hash, "immutable": True, "byteEqualToRequestedSource": SOURCE_IMAGE.read_bytes() == RETAINED_IMAGE.read_bytes(), "geometryMatchesRequestedSource": True},
        "inputOmr": {"path": str(RAW_OMR.relative_to(ROOT)), "sha256": raw_hash, "status": "retained-source-scan-omr", "summary": raw},
        "sourceScanOmr": {"path": str(RAW_OMR.relative_to(ROOT)), "sha256": raw_hash, "selectedWorkingLayer": "raw-source-scan-omr", "status": "review-only-omr-input", "summary": raw},
        "candidateWitness": {"available": True, "candidatePdfPath": str(CANDIDATE_PDF.relative_to(ROOT)), "candidatePdfSha256": candidate_pdf_hash, "candidateMusicXmlPath": str(CANDIDATE_OMR.relative_to(ROOT)), "candidateMusicXmlSha256": candidate_omr_hash, "candidateMusicXmlIsOmrDerivative": True, "candidateRole": "same-titled public composite-page witness; alternate evidence only", "summary": candidate},
        "correctedDraft": {"path": str(OUTPUT.relative_to(ROOT)), "sha256": draft_hash, "summary": draft, "eventStreamPreservedFromRetainedOmr": True, "status": "review-only-not-source-verified", "corrections": ["source-observed F-major key", "source-observed 4/4 meter", "explicit autonomous-block metadata", "lyrics/repeats/endings/shapes intentionally not fabricated"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceScanSha256": source_hash, "retainedImagePath": str(RETAINED_IMAGE.relative_to(ROOT)), "retainedImageSha256": retained_hash, "rawOmrSha256": raw_hash, "candidatePdfSha256": candidate_pdf_hash, "candidateOmrSha256": candidate_omr_hash, "method": "full-resolution visual inspection of immutable scan plus structural/event/duration audit of retained source-scan OMR and alternate candidate witness; alternate witness not used for source reconstruction", "blockingFindings": blocking},
        "blockingFindings": blocking,
        "blockingReason": "Autonomous promotion is blocked by the 21-versus-20 source-OMR measure topology discrepancy, 68-of-80 retained-OMR 4/4 duration failures, 18 empty exported measures, divergent 18-measure alternate witness, absent lyrics/repeat/ending semantics/per-note shape encoding, watermark-intersected notation, and lack of an authorized exact-edition structured witness. The corrected derivative remains review-only.",
        "autonomousDisposition": "OMR-derived evidence is retained for audit, but no exact source-faithful transposable score is admitted.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-unencoded-source-semantics; retain-review-derivative-only",
        "policy": "Immutable 2025 source images remain authoritative. OMR and alternate witnesses cannot authorize promotion without direct event-level, rhythm, lyric, repeat, mode, meter, and shape proof.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "sourceImageSha256": source_hash, "retainedImageSha256": retained_hash, "rawOmrSha256": raw_hash, "candidateOmrSha256": candidate_omr_hash, "draftSha256": draft_hash, "rawPitchedEvents": raw["pitchedEvents"], "candidatePitchedEvents": candidate["pitchedEvents"], "draftPitchedEvents": draft["pitchedEvents"], "durationFailures": raw["durationFailureCount"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
