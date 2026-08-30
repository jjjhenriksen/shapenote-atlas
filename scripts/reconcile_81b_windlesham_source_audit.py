#!/usr/bin/env python3
"""Reconcile both existing Windlesham comparison records without collapsing them."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from reconcile_433_springdale_source_audit import score_stats


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/source-images/2025/81b-windlesham-92b7e3d6fc.jpg"
OMR_SOURCE_IMAGE = ROOT / "work/omr/81b-windlesham/source.jpg"
RAW_OMR = ROOT / "work/omr/81b-windlesham/source.mxl"
NORMALIZED_OMR = ROOT / "work/omr/cleaned-normalized-v2-81b-windlesham-92b7e3d6fc/work__source-images__2025__81b-windlesham-92b7e3d6fc.mxl"
CANDIDATE_PDF = ROOT / "work/source-transcriptions/2025/clean-source-candidates/81b-windlesham/source-candidate.pdf"
CANDIDATE_OMR_A = ROOT / "work/omr/clean-source-candidates/81b-windlesham/source-candidate.mxl"
CANDIDATE_OMR_B = ROOT / "work/omr/clean-source-candidates/81b-windlesham-windlesham-l-m-8c2efdfd80/source-candidate.mxl"
IMAGEGEN_A = ROOT / "work/transcription-images/working/imagegen-batches/batch-a/81b-imagegen-v1.png"
IMAGEGEN_B = ROOT / "work/transcription-images/working/imagegen-pilot/81b-windlesham-imagegen-v1.png"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/81b-windlesham-source-correction.mxl"
AUDIT_A = ROOT / "work/source-transcriptions/2025/81b-windlesham-autonomous-comparison.json"
AUDIT_B = ROOT / "work/source-transcriptions/2025/81b-windlesham-comparison.json"


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


def duration_audit(summary: dict[str, object], beats: int = 3) -> dict[str, object]:
    divisions = summary.get("divisionsByPart", {})
    ends_by_part = summary.get("durationEndByPart", {})
    failures: dict[str, list[str]] = {}
    for part_id, ends in ends_by_part.items():  # type: ignore[union-attr]
        target = int(divisions[part_id]) * beats  # type: ignore[index]
        failures[part_id] = [f"m{index + 1}={end}" for index, end in enumerate(ends) if end != target]  # type: ignore[union-attr]
    summary.pop("durationFailuresAgainst4_4", None)
    summary["durationFailuresAgainst3_2"] = failures
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
        # The source prints A Major: three sharps.
        replace_child(key, "fifths", "3")
        replace_child(key, "mode", "major", {"fifths"})
        clock = first(attributes, "time")
        if clock is None:
            clock = ET.SubElement(attributes, "time")
        replace_child(clock, "beats", "3")
        replace_child(clock, "beat-type", "2", {"beats"})
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    fields = {
        "atlas-review-queue-id": "sh2025/81b",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-key": "A major",
        "atlas-source-mode": "major",
        "atlas-source-time-signature": "3/2",
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
    required = (SOURCE_IMAGE, OMR_SOURCE_IMAGE, RAW_OMR, NORMALIZED_OMR, CANDIDATE_PDF, CANDIDATE_OMR_A, CANDIDATE_OMR_B, IMAGEGEN_A, IMAGEGEN_B)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    source_hash = sha256(SOURCE_IMAGE)
    omr_source_hash = sha256(OMR_SOURCE_IMAGE)
    retained_same = SOURCE_IMAGE.read_bytes() == OMR_SOURCE_IMAGE.read_bytes()
    normalized_hash = sha256(NORMALIZED_OMR)
    raw_hash = sha256(RAW_OMR)
    candidate_pdf_hash = sha256(CANDIDATE_PDF)
    candidate_hash_a = sha256(CANDIDATE_OMR_A)
    candidate_hash_b = sha256(CANDIDATE_OMR_B)
    imagegen_hash_a = sha256(IMAGEGEN_A)
    imagegen_hash_b = sha256(IMAGEGEN_B)
    write_output(source_hash, raw_hash)
    draft_hash = sha256(OUTPUT)
    raw = duration_audit(score_stats(RAW_OMR), beats=3)
    normalized = brief(score_stats(NORMALIZED_OMR))
    candidate_a = brief(score_stats(CANDIDATE_OMR_A))
    candidate_b = brief(score_stats(CANDIDATE_OMR_B))
    draft = duration_audit(score_stats(OUTPUT), beats=3)
    blocking = [
        "The immutable 2025 page visibly identifies WINDLESHAM. L.M., A major, 3/2, Thomas Kelly (1804), Steven Brett (2016), four vocal parts, and source-visible lyrics. A repeat bar and terminal double bar are visible; the diagonal DO NOT COPY watermark crosses the central systems.",
        "The retained source-scan MXL exports 12 measures per part but contains only 54 pitched events, 5 rests, 15 empty measures, and 45 of 48 exported part-measures fail the source 3/2 duration target at divisions=2. The normalized-v2 retry is malformed as a one-part, 37-measure export. The source event and duration correspondence is therefore not proven complete.",
        "The same-title public composer PDF witness is a useful visual comparison, but both candidate MusicXML paths are OMR derivatives with only 37 pitched events, 2 rests, and 16 empty measures across four parts; neither encodes four-shape noteheads. Their structured event coverage cannot authorize a source-faithful playable or transposable score, and the source image's watermark intersects notation.",
        "The corrected derivative adds only source-observed A-major and 3/2 metadata while preserving the retained OMR event stream. Lyrics, repeats, endings, and per-note shapes are intentionally not fabricated. The two existing comparison records and both duplicate imagegen artifact paths remain distinct; generated pixels are review-only and were not used as notation evidence.",
        "No exact authorized 2025 structured MusicXML witness was found in the local cache or checked source index. Alternate/public composer witnesses remain separate from the 2025 authority.",
    ]
    imagegen = {
        "batchA": {"path": str(IMAGEGEN_A.relative_to(ROOT)), "sha256": imagegen_hash_a, "status": "rejected-for-notation-review-only"},
        "pilot": {"path": str(IMAGEGEN_B.relative_to(ROOT)), "sha256": imagegen_hash_b, "status": "rejected-for-notation-review-only"},
    }
    common = {
        "queueId": "sh2025/81b", "edition": "Sacred Harp, 2025 Edition", "songNo": "81b", "title": "Windlesham",
        "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=81b", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/001-099/081b-Windlesham/81b.jpg",
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceImageSha256": source_hash, "immutable": True,
            "directObservations": {
                "header": "WINDLESHAM. L.M.", "composer": "Thomas Kelly, 1804", "arranger": "Steven Brett, 2016", "key": "A major", "mode": "major", "timeSignature": "3/2", "meter": "Long Meter (8,8,8,8)", "parts": 4,
                "sourceRawMeasuresFromAudiveris": 12, "sourceRawMeasuresBySystem": [12], "exportedMeasuresByPart": {"P1": 12, "P2": 12, "P3": 12, "P4": 12},
                "sourceLyricsVisible": True, "repeatBarsVisible": True, "numberedEndingsVisible": False, "terminalDoubleBarVisible": True, "watermarkIntersectsNotation": True,
            },
        },
        "retainedSourceImageDuplicate": {"path": str(OMR_SOURCE_IMAGE.relative_to(ROOT)), "sha256": omr_source_hash, "immutable": True, "byteEqualToRequestedSource": retained_same, "geometryMatchesRequestedSource": True},
        "inputOmr": {"path": str(RAW_OMR.relative_to(ROOT)), "sha256": raw_hash, "status": "retained-source-scan-omr", "summary": raw},
        "sourceScanOmr": {"path": str(RAW_OMR.relative_to(ROOT)), "sha256": raw_hash, "selectedWorkingLayer": "raw-source-scan-omr", "status": "review-only-omr-input", "summary": raw},
        "normalizedScanOmr": {"path": str(NORMALIZED_OMR.relative_to(ROOT)), "sha256": normalized_hash, "selectedWorkingLayer": "normalized-v2", "status": "review-only-malformed-omr-retry", "summary": normalized},
        "imagegenArtifacts": imagegen,
        "correctedDraft": {"path": str(OUTPUT.relative_to(ROOT)), "sha256": draft_hash, "summary": draft, "eventStreamPreservedFromRetainedOmr": True, "status": "review-only-not-source-verified", "corrections": ["source-observed A-major key", "source-observed 3/2 meter", "explicit autonomous-block metadata", "lyrics/repeats/endings/shapes intentionally not fabricated"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceScanSha256": source_hash, "retainedOmrImagePath": str(OMR_SOURCE_IMAGE.relative_to(ROOT)), "retainedOmrImageSha256": omr_source_hash, "rawOmrSha256": raw_hash, "normalizedOmrSha256": normalized_hash, "candidatePdfSha256": candidate_pdf_hash, "candidateMusicXmlSha256": candidate_hash_a, "method": "full-resolution visual inspection of immutable 2025 scan plus structural/event/duration audit of raw and normalized source-scan OMR and separate same-title public PDF/OMR witnesses; generated imagegen pixels excluded from notation evidence", "blockingFindings": blocking},
        "blockingFindings": blocking,
        "blockingReason": "Autonomous promotion is blocked by the 45-of-48 retained-OMR 3/2 duration failures, 15 empty exported measures, malformed normalized-v2 retry, absent lyrics/repeat semantics/per-note shape encoding, watermark-intersected notation, incomplete alternate-witness event coverage, and lack of an authorized exact-edition structured witness. The corrected derivative remains review-only.",
        "autonomousDisposition": "The two existing Windlesham comparison records are reconciled in place; source OMR, alternate public witnesses, and generated imagegen aids remain evidence only, with no exact source-faithful transposable score admitted.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-unverified-structured-shapes; retain-both-comparison-records-and-duplicate-imagegen-artifacts; retain-review-derivative-only",
        "policy": "Immutable 2025 source images remain authoritative. OMR, alternate/public witnesses, and imagegen outputs cannot authorize promotion without direct event-level, rhythm, lyric, repeat, mode, meter, and shape proof.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    for path, candidate_path, candidate_hash in ((AUDIT_A, CANDIDATE_OMR_A, candidate_hash_a), (AUDIT_B, CANDIDATE_OMR_B, candidate_hash_b)):
        audit = dict(common)
        audit["recordIdentity"] = path.stem
        audit["candidateWitness"] = {"available": True, "candidateRole": "same-title public composer PDF and OMR derivative; not authorized exact 2025 structured source", "candidatePdfPath": str(CANDIDATE_PDF.relative_to(ROOT)), "candidatePdfSha256": candidate_pdf_hash, "candidateMusicXmlPath": str(candidate_path.relative_to(ROOT)), "candidateMusicXmlSha256": candidate_hash, "candidateMusicXmlIsOmrDerivative": True, "summary": candidate_a}
        audit["comparisonEvidence"] = dict(common["comparisonEvidence"])
        audit["comparisonEvidence"]["candidateMusicXmlSha256"] = candidate_hash
        audit["comparisonEvidence"]["candidateRecordPath"] = str(path.relative_to(ROOT))
        path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": common["queueId"], "status": common["comparisonStatus"], "sourceImageSha256": source_hash, "retainedOmrImageSha256": omr_source_hash, "rawOmrSha256": raw_hash, "candidateOmrSha256": candidate_hash_a, "draftSha256": draft_hash, "rawPitchedEvents": raw["pitchedEvents"], "draftPitchedEvents": draft["pitchedEvents"], "durationFailures": raw["durationFailureCount"], "recordsReconciled": 2}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
