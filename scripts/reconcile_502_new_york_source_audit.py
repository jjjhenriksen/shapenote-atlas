#!/usr/bin/env python3
"""Reconcile New York's retained shape draft into an autonomous block."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from reconcile_437_enoch_source_audit import retime_summary, score_stats


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/omr/502-new-york/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/502-new-york-5e712b883b.jpg"
RAW_OMR = ROOT / "work/omr/502-new-york/source.mxl"
WORKING_OMR = ROOT / "work/omr/cleaned-normalized-v2-502-new-york-5e712b883b/work__source-images__2025__502-new-york-5e712b883b.mxl"
PRIOR_DRAFT = ROOT / "work/omr/source-shape-review-drafts/2025/502-source-shape-review.mxl"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/502-new-york-source-correction.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/502-new-york-comparison.json"

COMPOSER_PDF = ROOT / "work/source-transcriptions/2025/clean-source-candidates/502-new-york-new-york-s-p-m-838251770a/source-candidate.pdf"
COMPOSER_MXL = ROOT / "work/omr/clean-source-candidates/502-new-york-new-york-s-p-m-573eee745f/source-candidate.mxl"
DEARBORN_PDF = ROOT / "work/source-transcriptions/2025/clean-source-candidates/502-new-york-dearborn-s-p-m-a1394a642e/source-candidate.pdf"
DEARBORN_MXL = ROOT / "work/omr/clean-source-candidates/502-new-york-dearborn-s-p-m-fca7794352/source-candidate.mxl"


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


def update_xml(xml_bytes: bytes, source_hash: str, working_hash: str) -> bytes:
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
        # The scan prints E minor: one sharp, with minor mode explicit in the source header.
        replace_child(key, "fifths", "1")
        replace_child(key, "mode", "minor", {"fifths"})
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
        "atlas-review-queue-id": "sh2025/502",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-key": "E minor",
        "atlas-source-mode": "minor",
        "atlas-source-time-signature": "4/4",
        "atlas-shape-encoding": "derived from retained OMR pitch steps and observed source key; not per-note visual verification",
        "atlas-provenance-policy": "autonomous block; immutable 2025 source remains authoritative; no OMR promotion",
        "atlas-source-image-sha256": source_hash,
        "atlas-source-omr-sha256": working_hash,
    }
    for name, value in fields.items():
        put_field(identification, name, value)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_output(source_hash: str, working_hash: str) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(PRIOR_DRAFT) as source_zip, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        xml_name = next(name for name in source_zip.namelist() if name.endswith(".xml") and not name.startswith("META-INF/"))
        updated = update_xml(source_zip.read(xml_name), source_hash, working_hash)
        for info in source_zip.infolist():
            target.writestr(info, updated if info.filename == xml_name else source_zip.read(info.filename))


def main() -> int:
    required = (SOURCE_IMAGE, RETAINED_IMAGE, RAW_OMR, WORKING_OMR, PRIOR_DRAFT, COMPOSER_PDF, COMPOSER_MXL, DEARBORN_PDF, DEARBORN_MXL)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    source_hash = sha256(SOURCE_IMAGE)
    retained_hash = sha256(RETAINED_IMAGE)
    raw_hash = sha256(RAW_OMR)
    working_hash = sha256(WORKING_OMR)
    write_output(source_hash, working_hash)
    draft_hash = sha256(OUTPUT)
    raw = retime_summary(score_stats(RAW_OMR), beats=4)
    working = retime_summary(score_stats(WORKING_OMR), beats=4)
    draft = retime_summary(score_stats(OUTPUT), beats=4)
    composer_pdf_hash = sha256(COMPOSER_PDF)
    composer_mxl_hash = sha256(COMPOSER_MXL)
    dearborn_pdf_hash = sha256(DEARBORN_PDF)
    dearborn_mxl_hash = sha256(DEARBORN_MXL)
    blocking = [
        "The immutable page visibly identifies NEW YORK. S.P.M., E minor, 4/4, Timothy Dwight (1801), Aldo Thomas Ceresa (2012), four vocal parts, and source-visible lyrics. A repeat with numbered first/second endings is visible, the page ends with a terminal double bar, and a diagonal DO NOT COPY watermark intersects the middle and lower systems.",
        "The strongest same-title witness is a public composer PDF and OMR derivative, not an authorized publisher-delivered 2025 MusicXML file; its printed attribution differs from the 2025 scan (Timothy Dwight 1800 and Aldous 2012 versus Timothy Dwight 1801 and Aldo Thomas Ceresa 2012). The candidate MusicXML is therefore a comparison witness only.",
        "The source-scan OMR exports 24 measures per part with 269 pitched events; normalized-v2 exports 25 measures per part with 273 pitched events; the same-title candidate exports 26 measures per part. These divergent structures do not establish note-for-note identity or complete repeat/ending topology. Normalized-v2 also has 11 empty exported measures and 77 of 100 part-measures fail the 4/4 duration target at divisions=6.",
        "The retained OMR and corrected derivative contain no lyrics or repeat/ending elements, and neither candidate MusicXML encodes four-shape noteheads. The 273 derivative shape tags are derived from OMR pitch steps plus the observed E-minor key, not independently verified against every printed notehead. The separate Dearborn witness is a title mismatch and was not used to fill New York notation.",
        "No authorized exact-edition structured New York witness was available. Alternate-edition or title-mismatch witnesses were retained separately and not used for promotion.",
    ]
    audit = {
        "queueId": "sh2025/502", "edition": "Sacred Harp, 2025 Edition", "songNo": "502", "title": "New York",
        "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=502", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/502-New-York/502.jpg",
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceImageSha256": source_hash, "immutable": True,
            "directObservations": {
                "header": "NEW YORK. S.P.M.", "composer": "Timothy Dwight, 1801", "arranger": "Aldo Thomas Ceresa, 2012", "key": "E minor", "mode": "minor", "timeSignature": "4/4", "meter": "Short Particular Meter (6,6,8,6,6,8)", "parts": 4,
                "sourceRawMeasuresFromAudiveris": 27, "sourceRawMeasuresBySystem": [10, 8, 9], "catalogMeasuresByPart": {"P1": 24, "P2": 24, "P3": 24, "P4": 24},
                "sourceLyricsVisible": True, "repeatBarsVisible": True, "numberedEndingsVisible": True, "terminalDoubleBarVisible": True, "watermarkIntersectsNotation": True,
            },
        },
        "retainedSourceImageDuplicate": {"path": str(RETAINED_IMAGE.relative_to(ROOT)), "sha256": retained_hash, "immutable": True, "byteEqualToRequestedSource": SOURCE_IMAGE.read_bytes() == RETAINED_IMAGE.read_bytes(), "geometryMatchesRequestedSource": True},
        "inputOmr": {"path": str(RAW_OMR.relative_to(ROOT)), "sha256": raw_hash, "status": "retained-source-scan-omr", "summary": raw},
        "sourceScanOmr": {"path": str(WORKING_OMR.relative_to(ROOT)), "sha256": working_hash, "selectedWorkingLayer": "normalized-v2", "status": "review-only-omr-input", "summary": working},
        "candidateWitness": {"available": True, "candidateRole": "same-title public composer PDF converted by OMR; alternate comparison witness, not authorized 2025 structured source", "candidatePageUrl": "https://www.sacredharptunes.com/author/aldous/new-york/", "candidatePdfPath": str(COMPOSER_PDF.relative_to(ROOT)), "candidatePdfSha256": composer_pdf_hash, "candidateMusicXmlPath": str(COMPOSER_MXL.relative_to(ROOT)), "candidateMusicXmlSha256": composer_mxl_hash, "candidateMusicXmlIsOmrDerivative": True, "printedAttributionDifference": "candidate Timothy Dwight 1800 and Aldous 2012; source Timothy Dwight 1801 and Aldo Thomas Ceresa 2012", "candidateMeasuresByPart": {"P1": 26, "P2": 26, "P3": 26, "P4": 26}},
        "alternateWitnesses": [{"role": "title-mismatch Dearborn witness; rejected for New York", "pdfPath": str(DEARBORN_PDF.relative_to(ROOT)), "pdfSha256": dearborn_pdf_hash, "musicXmlPath": str(DEARBORN_MXL.relative_to(ROOT)), "musicXmlSha256": dearborn_mxl_hash}],
        "correctedDraft": {"path": str(OUTPUT.relative_to(ROOT)), "sha256": draft_hash, "summary": draft, "eventStreamPreservedFromPriorReviewDraft": True, "status": "review-only-not-source-verified", "corrections": ["source-observed E-minor mode", "source-observed 4/4 meter", "explicit autonomous-block metadata", "preserved derived four-shape tags without claiming per-note verification", "lyrics and repeat/ending semantics intentionally omitted"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceScanSha256": source_hash, "retainedImagePath": str(RETAINED_IMAGE.relative_to(ROOT)), "retainedImageSha256": retained_hash, "rawOmrSha256": raw_hash, "workingOmrSha256": working_hash, "candidatePdfSha256": composer_pdf_hash, "candidateMusicXmlSha256": composer_mxl_hash, "method": "full-resolution visual inspection of immutable scan plus structural/event/duration audit of raw and normalized-v2 OMR and existing same-title/title-mismatch witnesses; alternate editions not used", "blockingFindings": blocking},
        "blockingFindings": blocking,
        "blockingReason": "Autonomous promotion is blocked by unauthorized/cross-attribution same-title witness evidence, the 24-versus-25-versus-26 measure topology discrepancy (with 27 raw Audiveris measures), 77-of-100 normalized-v2 4/4 duration failures, 11 empty exported measures, absent lyrics and source-confirmed per-note shapes, incomplete repeat/ending semantics, watermark-intersected notation, and lack of an authorized exact-edition structured witness. The corrected derivative remains review-only.",
        "autonomousDisposition": "OMR-derived and alternate witnesses are retained for audit, but no exact source-faithful transposable score is admitted.",
        "nextAction": "autonomous-promotion-blocked-by-cross-edition-and-incomplete-source-event-witness; retain-review-derivative-only",
        "policy": "Immutable 2025 source images remain authoritative. OMR and alternate witnesses are evidence only and cannot authorize promotion without direct event-level, rhythm, lyric, repeat, mode, meter, and shape proof.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "sourceImageSha256": source_hash, "retainedImageSha256": retained_hash, "rawOmrSha256": raw_hash, "workingOmrSha256": working_hash, "candidateMusicXmlSha256": composer_mxl_hash, "draftSha256": draft_hash, "workingDurationFailures": working["durationFailureCount"], "draftPitchedEvents": draft["pitchedEvents"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
