#!/usr/bin/env python3
"""Reconcile Service of the Lord's retained 2025 scan OMR into an autonomous block."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from reconcile_433_springdale_source_audit import score_stats


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/omr/80b-service-of-the-lord/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/80b-service-of-the-lord-ff01fb1209.jpg"
RAW_OMR = ROOT / "work/omr/80b-service-of-the-lord/source.mxl"
NORMALIZED_OMR = ROOT / "work/omr/cleaned-normalized-v2-80b-service-of-the-lord-ff01fb1209/work__source-images__2025__80b-service-of-the-lord-ff01fb1209.mxl"
COOPER_OMR = ROOT / "work/candidates/C-80b.mxl"
COOPER_PDF = ROOT / "work/source-transcriptions/2025/clean-source-candidates/80b-service-of-the-lord-cooper-reference/cooper-reference.pdf"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/80b-service-of-the-lord-source-correction.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/80b-service-of-the-lord-comparison.json"


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


def duration_audit(summary: dict[str, object], beats: int = 2) -> dict[str, object]:
    divisions = summary.get("divisionsByPart", {})
    ends_by_part = summary.get("durationEndByPart", {})
    failures: dict[str, list[str]] = {}
    for part_id, ends in ends_by_part.items():  # type: ignore[union-attr]
        target = int(divisions[part_id]) * beats  # type: ignore[index]
        failures[part_id] = [f"m{index + 1}={end}" for index, end in enumerate(ends) if end != target]  # type: ignore[union-attr]
    summary.pop("durationFailuresAgainst3_4", None)
    summary["durationFailuresAgainst2_4"] = failures
    summary["durationFailureCount"] = sum(len(items) for items in failures.values())
    return summary


def brief(summary: dict[str, object]) -> dict[str, object]:
    return {key: summary[key] for key in ("parts", "measuresByPart", "pitchedEvents", "restEvents", "emptyMeasures", "barlines", "repeatEndingElements")}


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
        # The 2025 scan prints F Major: one flat.
        replace_child(key, "fifths", "-1")
        replace_child(key, "mode", "major", {"fifths"})
        clock = first(attributes, "time")
        if clock is None:
            clock = ET.SubElement(attributes, "time")
        replace_child(clock, "beats", "2")
        replace_child(clock, "beat-type", "4", {"beats"})
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    fields = {
        "atlas-review-queue-id": "sh2025/80b",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-key": "F major",
        "atlas-source-mode": "major",
        "atlas-source-time-signature": "2/4",
        "atlas-shape-encoding": "not encoded; source-visible shapes are not independently verified per note",
        "atlas-lyrics-encoding": "not encoded; source-visible lyrics are not directly syllable-aligned",
        "atlas-repeat-ending-encoding": "not encoded; source-visible repeat structure is not independently reconstructed",
        "atlas-provenance-policy": "autonomous block; immutable 2025 source remains authoritative; no alternate-edition promotion",
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
    for path in (SOURCE_IMAGE, RETAINED_IMAGE, RAW_OMR, NORMALIZED_OMR, COOPER_OMR, COOPER_PDF):
        if not path.is_file():
            raise FileNotFoundError(path)
    source_hash = sha256(SOURCE_IMAGE)
    retained_hash = sha256(RETAINED_IMAGE)
    raw_hash = sha256(RAW_OMR)
    normalized_hash = sha256(NORMALIZED_OMR)
    cooper_hash = sha256(COOPER_OMR)
    cooper_pdf_hash = sha256(COOPER_PDF)
    write_output(source_hash, raw_hash)
    draft_hash = sha256(OUTPUT)
    raw = duration_audit(score_stats(RAW_OMR), beats=2)
    normalized = duration_audit(score_stats(NORMALIZED_OMR), beats=2)
    cooper = brief(score_stats(COOPER_OMR))
    draft = duration_audit(score_stats(OUTPUT), beats=2)
    blocking = [
        "The immutable 2025 page visibly identifies SERVICE OF THE LORD. L.M.H., F major, 2/4, The Baltimore Collection (1801), E. J. King (1844), Alto S. M. Denson (1911), four vocal parts, and source-visible lyrics. A repeat bar and terminal double bar are visible; the diagonal DO NOT COPY watermark intersects the middle systems.",
        "The retained source-scan MXL exports 13 measures per part and contains 98 pitched events, 11 empty measures, no rests, and 37 of 52 exported part-measures fail the source 2/4 duration target at divisions=2. The normalized-v2 retry exports 15 measures per part and remains structurally incomplete. The source event, duration, and repeat topology are therefore not proven complete.",
        "The only structured alternate witness is Cooper 2012, not an authorized 2025 MusicXML source. Its 18 measures per part, 152 pitched events, and 4 rests differ from the 2025 source-scan draft; it must remain a labeled alternate-edition reference and cannot fill the 2025 score.",
        "The retained OMR and corrected derivative contain no lyrics, repeat/ending elements, or per-note four-shape encoding. Adding the source-observed F-major key and 2/4 meter does not prove the underlying events, printed shapes, lyric syllables, or repeat topology. No unsupported event, lyric, repeat, ending, or watermark-obscured material was fabricated.",
    ]
    audit = {
        "queueId": "sh2025/80b", "edition": "Sacred Harp, 2025 Edition", "songNo": "80b", "title": "Service of the Lord",
        "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=80b", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/001-099/080b-Service-of-the-Lord/80b.jpg",
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceImageSha256": source_hash, "immutable": True,
            "directObservations": {
                "header": "SERVICE OF THE LORD. L.M.H.", "composer": "The Baltimore Collection, 1801; E. J. King, 1844", "arranger": "Alto S. M. Denson, 1911", "key": "F major", "mode": "major", "timeSignature": "2/4", "meter": "Long Meter with Hallelujah (8,8,8,8)", "parts": 4,
                "sourceRawMeasuresFromAudiveris": 13, "sourceRawMeasuresBySystem": [13], "exportedMeasuresByPart": {"P1": 13, "P2": 13, "P3": 13, "P4": 13},
                "sourceLyricsVisible": True, "repeatBarsVisible": True, "numberedEndingsVisible": False, "terminalDoubleBarVisible": True, "watermarkIntersectsNotation": True,
            },
        },
        "retainedSourceImageDuplicate": {"path": str(RETAINED_IMAGE.relative_to(ROOT)), "sha256": retained_hash, "immutable": True, "byteEqualToRequestedSource": SOURCE_IMAGE.read_bytes() == RETAINED_IMAGE.read_bytes(), "geometryMatchesRequestedSource": True},
        "inputOmr": {"path": str(RAW_OMR.relative_to(ROOT)), "sha256": raw_hash, "status": "retained-source-scan-omr", "summary": raw},
        "sourceScanOmr": {"path": str(RAW_OMR.relative_to(ROOT)), "sha256": raw_hash, "selectedWorkingLayer": "raw-source-scan-omr", "status": "review-only-omr-input", "summary": raw},
        "normalizedScanOmr": {"path": str(NORMALIZED_OMR.relative_to(ROOT)), "sha256": normalized_hash, "selectedWorkingLayer": "normalized-v2", "status": "review-only-omr-retry", "summary": normalized},
        "candidateWitness": {"available": True, "candidateEdition": "Sacred Harp Cooper 2012", "candidateRole": "alternate-edition reference only; not used for 2025 notation", "candidatePageUrl": "http://resources.texasfasola.org/index/poetry/080b.html", "candidateMusicXmlUrl": "https://shapenote.net/musicxml/C-80b.mxl", "candidatePdfPath": str(COOPER_PDF.relative_to(ROOT)), "candidatePdfSha256": cooper_pdf_hash, "candidateMusicXmlPath": str(COOPER_OMR.relative_to(ROOT)), "candidateMusicXmlSha256": cooper_hash, "candidateMusicXmlIsOmrDerivative": False, "summary": cooper},
        "correctedDraft": {"path": str(OUTPUT.relative_to(ROOT)), "sha256": draft_hash, "summary": draft, "eventStreamPreservedFromRetainedOmr": True, "status": "review-only-not-source-verified", "corrections": ["source-observed F-major key", "source-observed 2/4 meter", "explicit autonomous-block metadata", "lyrics/repeats/endings/shapes intentionally not fabricated"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceScanSha256": source_hash, "retainedImagePath": str(RETAINED_IMAGE.relative_to(ROOT)), "retainedImageSha256": retained_hash, "rawOmrSha256": raw_hash, "normalizedOmrSha256": normalized_hash, "candidateOmrSha256": cooper_hash, "candidatePdfSha256": cooper_pdf_hash, "method": "full-resolution visual inspection of immutable 2025 scan plus structural/event/duration audit of raw and normalized source-scan OMR and separate Cooper alternate-edition witness; alternate edition excluded from 2025 authority", "blockingFindings": blocking},
        "blockingFindings": blocking,
        "blockingReason": "Autonomous promotion is blocked by the 13-versus-15-versus-18 measure topology across the source OMR, normalized retry, and Cooper alternate witness, 37-of-52 retained-OMR 2/4 duration failures, 11 empty exported measures, absent lyrics/repeat semantics/per-note shape encoding, watermark-intersected notation, differing source-image hashes, and lack of an authorized exact-edition structured witness. The corrected derivative remains review-only and the Cooper 2012 witness remains edition-separated.",
        "autonomousDisposition": "The incomplete 2025 OMR and Cooper alternate witness are retained as evidence only; no exact source-faithful transposable score is admitted.",
        "nextAction": "autonomous-promotion-blocked-by-unproven-2025-event-and-edition-identity; retain-source-and-alternate-witness-evidence; retain-review-derivative-only",
        "policy": "Immutable 2025 source images remain authoritative. OMR and alternate-edition witnesses cannot authorize promotion without direct event-level, rhythm, lyric, repeat, mode, meter, and shape proof.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "sourceImageSha256": source_hash, "retainedImageSha256": retained_hash, "rawOmrSha256": raw_hash, "candidateOmrSha256": cooper_hash, "draftSha256": draft_hash, "rawPitchedEvents": raw["pitchedEvents"], "candidatePitchedEvents": cooper["pitchedEvents"], "draftPitchedEvents": draft["pitchedEvents"], "durationFailures": raw["durationFailureCount"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
