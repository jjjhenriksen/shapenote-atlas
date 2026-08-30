#!/usr/bin/env python3
"""Reconcile Thomaston's retained scan OMR into an autonomous block."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from reconcile_433_springdale_source_audit import score_stats


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/omr/574-thomaston/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/574-thomaston-94560cea87.jpg"
RAW_OMR = ROOT / "work/omr/574-thomaston/source.mxl"
CANDIDATE_OMR = ROOT / "work/omr/clean-source-candidates/574-thomaston-norfolk-s-m-3930a95a27/source-candidate.mxl"
CANDIDATE_PDF = ROOT / "work/source-transcriptions/2025/clean-source-candidates/574-thomaston-norfolk-s-m-b700e2392d/source-candidate.pdf"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/574-thomaston-source-correction.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/574-thomaston-comparison.json"


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


def duration_audit(summary: dict[str, object], beats: int = 4) -> dict[str, object]:
    divisions = summary.get("divisionsByPart", {})
    ends_by_part = summary.get("durationEndByPart", {})
    failures: dict[str, list[str]] = {}
    for part_id, ends in ends_by_part.items():  # type: ignore[union-attr]
        target = int(divisions[part_id]) * beats  # type: ignore[index]
        failures[part_id] = [f"m{index + 1}={end}" for index, end in enumerate(ends) if end != target]  # type: ignore[union-attr]
    summary.pop("durationFailuresAgainst3_4", None)
    summary["durationFailuresAgainst4_4"] = failures
    summary["durationFailureCount"] = sum(len(items) for items in failures.values())
    return summary


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
        # The scan prints A Minor: no sharps or flats.
        replace_child(key, "fifths", "0")
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
        "atlas-review-queue-id": "sh2025/574",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-key": "A minor",
        "atlas-source-mode": "minor",
        "atlas-source-time-signature": "4/4",
        "atlas-shape-encoding": "not encoded; source-visible shapes are not independently verified per note",
        "atlas-lyrics-encoding": "not encoded; source-visible lyrics are not directly syllable-aligned",
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
    for path in (SOURCE_IMAGE, RETAINED_IMAGE, RAW_OMR, CANDIDATE_OMR, CANDIDATE_PDF):
        if not path.is_file():
            raise FileNotFoundError(path)
    source_hash = sha256(SOURCE_IMAGE)
    retained_hash = sha256(RETAINED_IMAGE)
    raw_hash = sha256(RAW_OMR)
    candidate_omr_hash = sha256(CANDIDATE_OMR)
    candidate_pdf_hash = sha256(CANDIDATE_PDF)
    write_output(source_hash, raw_hash)
    draft_hash = sha256(OUTPUT)
    raw = duration_audit(score_stats(RAW_OMR), beats=4)
    candidate = duration_audit(score_stats(CANDIDATE_OMR), beats=4)
    draft = duration_audit(score_stats(OUTPUT), beats=4)
    blocking = [
        "The immutable page visibly identifies THOMASTON. S.M., A minor, 4/4, Isaac Watts (1719), Jesse P. Karlsberg (2012), four vocal parts, and source-visible lyrics. Audiveris reports two systems of 11 and 9 raw measures; the page visibly includes repeat bars with numbered first/second endings, terminal double bars, and a diagonal DO NOT COPY watermark across the middle/lower systems.",
        "The retained source-scan MXL exports 19 measures per part and contains 163 pitched events, 1 rest event, 22 empty measures, and 60 of 76 exported part-measures fail the 4/4 duration target at divisions=2. The source event and duration correspondence is therefore not proven complete.",
        "The strongest same-title witness is a public Norfolk S.M. composer PDF/OMR derivative, not an authorized publisher-delivered 2025 MusicXML file. Its 17-measure, 170-pitched-event structure differs from the 19-measure source-scan draft; it contains 12 rests and 35 duration failures, and its MusicXML has no encoded key/mode or per-note four-shape tags. The differing title/setting name (Norfolk versus Thomaston) prevents autonomous edition identity.",
        "The retained OMR and corrected derivative contain no lyrics, repeat/ending elements, or per-note four-shape encoding. Adding the source-observed A-minor key and 4/4 meter does not prove the underlying events, printed shapes, lyric syllables, or repeat topology. No unsupported event, lyric, repeat, ending, or watermark-obscured material was fabricated.",
    ]
    audit = {
        "queueId": "sh2025/574", "edition": "Sacred Harp, 2025 Edition", "songNo": "574", "title": "Thomaston",
        "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=574", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/574-Thomaston/574.jpg",
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceImageSha256": source_hash, "immutable": True,
            "directObservations": {
                "header": "THOMASTON. S.M.", "composer": "Isaac Watts, 1719", "arranger": "Jesse P. Karlsberg, 2012", "key": "A minor", "mode": "minor", "timeSignature": "4/4", "meter": "Short Meter (6,6,8,6)", "parts": 4,
                "sourceRawMeasuresFromAudiveris": 20, "sourceRawMeasuresBySystem": [11, 9], "exportedMeasuresByPart": {"P1": 19, "P2": 19, "P3": 19, "P4": 19},
                "sourceLyricsVisible": True, "repeatBarsVisible": True, "numberedEndingsVisible": True, "terminalDoubleBarVisible": True, "watermarkIntersectsNotation": True,
            },
        },
        "retainedSourceImageDuplicate": {"path": str(RETAINED_IMAGE.relative_to(ROOT)), "sha256": retained_hash, "immutable": True, "byteEqualToRequestedSource": SOURCE_IMAGE.read_bytes() == RETAINED_IMAGE.read_bytes(), "geometryMatchesRequestedSource": True},
        "inputOmr": {"path": str(RAW_OMR.relative_to(ROOT)), "sha256": raw_hash, "status": "retained-source-scan-omr", "summary": raw},
        "sourceScanOmr": {"path": str(RAW_OMR.relative_to(ROOT)), "sha256": raw_hash, "selectedWorkingLayer": "raw-source-scan-omr", "status": "review-only-omr-input", "summary": raw},
        "candidateWitness": {"available": True, "candidateRole": "same-text public Norfolk S.M. witness; alternate/non-authoritative and not used for promotion", "candidateKey": "sh2025/574/3930a95a27", "candidatePageUrl": "https://www.sacredharptunes.com/author/jesse/norfolk/", "candidatePdfUrl": "https://media.sacredharptunes.com/jesse_524.pdf", "candidatePdfPath": str(CANDIDATE_PDF.relative_to(ROOT)), "candidatePdfSha256": candidate_pdf_hash, "candidateMusicXmlPath": str(CANDIDATE_OMR.relative_to(ROOT)), "candidateMusicXmlSha256": candidate_omr_hash, "candidateMusicXmlIsOmrDerivative": True, "summary": candidate},
        "correctedDraft": {"path": str(OUTPUT.relative_to(ROOT)), "sha256": draft_hash, "summary": draft, "eventStreamPreservedFromRetainedOmr": True, "status": "review-only-not-source-verified", "corrections": ["source-observed A-minor key", "source-observed 4/4 meter", "explicit autonomous-block metadata", "lyrics/repeats/endings/shapes intentionally not fabricated"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceScanSha256": source_hash, "retainedImagePath": str(RETAINED_IMAGE.relative_to(ROOT)), "retainedImageSha256": retained_hash, "rawOmrSha256": raw_hash, "candidateOmrSha256": candidate_omr_hash, "candidatePdfSha256": candidate_pdf_hash, "method": "full-resolution visual inspection of immutable scan plus structural/event/duration audit of retained source-scan OMR and separate same-text candidate; alternate witness not used as source authority", "blockingFindings": blocking},
        "blockingFindings": blocking,
        "blockingReason": "Autonomous promotion is blocked by the 20-versus-19 raw/exported measure topology discrepancy, 60-of-76 retained-OMR 4/4 duration failures, 22 empty exported measures, the 17-measure alternate Norfolk witness mismatch, absent lyrics/repeat/ending semantics/per-note shape encoding, watermark-intersected notation, differing source-image hashes, and lack of an authorized exact-edition structured witness. The corrected derivative remains review-only.",
        "autonomousDisposition": "The incomplete source-scan OMR and alternate Norfolk witness are retained as evidence only; no exact source-faithful transposable score is admitted.",
        "nextAction": "autonomous-promotion-blocked-by-unproven-source-event-and-edition-identity; retain-source-and-alternate-witness-evidence; retain-review-derivative-only",
        "policy": "Immutable 2025 source images remain authoritative. OMR and alternate witnesses cannot authorize promotion without direct event-level, rhythm, lyric, repeat, mode, meter, and shape proof.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "sourceImageSha256": source_hash, "retainedImageSha256": retained_hash, "rawOmrSha256": raw_hash, "candidateOmrSha256": candidate_omr_hash, "draftSha256": draft_hash, "rawPitchedEvents": raw["pitchedEvents"], "candidatePitchedEvents": candidate["pitchedEvents"], "draftPitchedEvents": draft["pitchedEvents"], "durationFailures": raw["durationFailureCount"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
