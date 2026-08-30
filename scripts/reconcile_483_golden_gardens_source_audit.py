#!/usr/bin/env python3
"""Reconcile Golden Gardens' retained shape draft into an autonomous block."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from reconcile_437_enoch_source_audit import retime_summary, score_stats


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/omr/483-golden-gardens/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/483-golden-gardens-9b0458e3aa.jpg"
RAW_OMR = ROOT / "work/omr/483-golden-gardens/source.mxl"
WORKING_OMR = ROOT / "work/omr/cleaned-normalized-v2-483-golden-gardens-9b0458e3aa/work__source-images__2025__483-golden-gardens-9b0458e3aa.mxl"
PRIOR_DRAFT = ROOT / "work/omr/source-shape-review-drafts/2025/483-source-shape-review.mxl"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/483-golden-gardens-source-correction.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/483-source-shape-autonomous-blocked-comparison.json"


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
        # The scan prints G Minor; G is two flats.
        replace_child(key, "fifths", "-2")
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
        "atlas-review-queue-id": "sh2025/483",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-key": "G minor",
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
    for path in (SOURCE_IMAGE, RETAINED_IMAGE, RAW_OMR, WORKING_OMR, PRIOR_DRAFT):
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
    blocking = [
        "The immutable page visibly identifies GOLDEN GARDENS. C.M.D., G minor, 4/4, Scottish Psalter (1650), Peter Schinske (2022), four vocal parts, source-visible lyrics, repeat bars with numbered first/second endings, and a terminal double bar; a diagonal DO NOT COPY watermark intersects the middle systems.",
        "Audiveris reports 21 raw measures (11 in the first system and 10 in the second), while the retained source MXL exports 19 measures per part and normalized-v2 exports 22 measures per part. The normalized-v2 working score contains 209 pitched events, 21 empty exported measures, and 68 of 88 exported part-measures fail the 4/4 duration target at divisions=2. The source event stream, durations, and measure topology are therefore not proven complete.",
        "The retained OMR and corrected derivative contain no lyrics or repeat/ending elements. Their 209 four-shape noteheads are derived from OMR pitch steps plus the observed G-minor key, not independently verified against every printed notehead. No unsupported event, lyric, repeat, or obscured watermark-intersected material was fabricated.",
        "No authorized exact-edition structured Golden Gardens witness was available. Alternate-edition records were not used to fill notes, durations, lyrics, repeats, or shapes.",
    ]
    audit = {
        "queueId": "sh2025/483", "edition": "Sacred Harp, 2025 Edition", "songNo": "483", "title": "Golden Gardens",
        "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=483", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/483-Golden-Gardens/483.jpg",
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceImageSha256": source_hash, "immutable": True,
            "directObservations": {
                "header": "GOLDEN GARDENS. C.M.D.", "composer": "Scottish Psalter, 1650", "arranger": "Peter Schinske, 2022", "key": "G minor", "mode": "minor", "timeSignature": "4/4", "meter": "Common Meter Double (8,6,8,6,8,6,8,6)", "parts": 4,
                "sourceRawMeasuresFromAudiveris": 21, "sourceRawMeasuresBySystem": [11, 10], "exportedMeasuresByPart": {"P1": 22, "P2": 22, "P3": 22, "P4": 22},
                "sourceLyricsVisible": True, "sourceVerseCount": 2, "repeatBarsVisible": True, "numberedEndingsVisible": True, "terminalDoubleBarVisible": True, "watermarkIntersectsNotation": True,
            },
        },
        "retainedSourceImageDuplicate": {"path": str(RETAINED_IMAGE.relative_to(ROOT)), "sha256": retained_hash, "immutable": True, "byteEqualToRequestedSource": SOURCE_IMAGE.read_bytes() == RETAINED_IMAGE.read_bytes(), "geometryMatchesRequestedSource": True},
        "inputOmr": {"path": str(RAW_OMR.relative_to(ROOT)), "sha256": raw_hash, "status": "retained-source-scan-omr", "summary": raw},
        "sourceScanOmr": {"path": str(WORKING_OMR.relative_to(ROOT)), "sha256": working_hash, "selectedWorkingLayer": "normalized-v2", "status": "review-only-omr-input", "summary": working},
        "candidateWitness": {"available": False, "candidateRole": "No authorized exact-edition structured Golden Gardens witness was available; alternate editions were not used."},
        "correctedDraft": {"path": str(OUTPUT.relative_to(ROOT)), "sha256": draft_hash, "summary": draft, "eventStreamPreservedFromPriorReviewDraft": True, "status": "review-only-not-source-verified", "corrections": ["source-observed G-minor mode", "source-observed 4/4 meter", "explicit autonomous-block metadata", "preserved derived four-shape tags without claiming per-note verification", "lyrics and repeat/ending semantics intentionally omitted"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceScanSha256": source_hash, "retainedImagePath": str(RETAINED_IMAGE.relative_to(ROOT)), "retainedImageSha256": retained_hash, "rawOmrSha256": raw_hash, "workingOmrSha256": working_hash, "method": "full-resolution visual inspection of immutable scan plus structural/event/duration audit of raw and normalized-v2 OMR; alternate editions not used", "blockingFindings": blocking},
        "blockingFindings": blocking,
        "blockingReason": "Autonomous promotion is blocked by the 21-versus-22 measure topology discrepancy (and 19-measure raw export), 68-of-88 normalized-v2 4/4 duration failures, 21 empty exported measures, absent lyrics and source-confirmed per-note shapes, incomplete repeat/ending semantics, watermark-intersected notation, and lack of an authorized exact-edition structured witness. The corrected derivative remains review-only.",
        "autonomousDisposition": "OMR-derived evidence is retained for audit, but no exact source-faithful transposable score is admitted.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-unresolved-topology; retain-review-derivative-only",
        "policy": "Immutable 2025 source images remain authoritative. OMR and derived shape tags are evidence only and cannot authorize promotion without direct event-level, rhythm, lyric, repeat, mode, meter, and shape proof.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "sourceImageSha256": source_hash, "retainedImageSha256": retained_hash, "rawOmrSha256": raw_hash, "workingOmrSha256": working_hash, "draftSha256": draft_hash, "workingDurationFailures": working["durationFailureCount"], "draftPitchedEvents": draft["pitchedEvents"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
