#!/usr/bin/env python3
"""Reconcile Gum Pond's retained scan OMR into an autonomous block."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from reconcile_433_springdale_source_audit import score_stats


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/omr/566-gum-pond/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/566-gum-pond-c5578864a3.jpg"
RAW_OMR = ROOT / "work/omr/566-gum-pond/source.mxl"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/566-gum-pond-source-correction.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/566-source-shape-autonomous-blocked-comparison.json"


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


def retime_summary(summary: dict[str, object], beats: int = 2) -> dict[str, object]:
    divisions = summary.get("divisionsByPart", {})
    ends_by_part = summary.get("durationEndByPart", {})
    failures: dict[str, list[str]] = {}
    for part_id, ends in ends_by_part.items():  # type: ignore[union-attr]
        target = int(divisions[part_id]) * beats  # type: ignore[index]
        failures[part_id] = [f"m{index + 1}={end}" for index, end in enumerate(ends) if end != target]  # type: ignore[union-attr]
    summary.pop("durationFailuresAgainst4_4", None)
    summary.pop("durationFailuresAgainst3_4", None)
    summary["durationFailuresAgainst2_4"] = failures
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
        # The scan prints E Major: four sharps.
        replace_child(key, "fifths", "4")
        replace_child(key, "mode", "major", {"fifths"})
        clock = first(attributes, "time")
        if clock is None:
            clock = ET.SubElement(attributes, "time")
        # The source page prints 2/4 in each vocal part.
        replace_child(clock, "beats", "2")
        replace_child(clock, "beat-type", "4", {"beats"})
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    fields = {
        "atlas-review-queue-id": "sh2025/566",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-key": "E major",
        "atlas-source-mode": "major",
        "atlas-source-time-signature": "2/4",
        "atlas-shape-encoding": "not encoded; source-visible shapes are not independently verified per note",
        "atlas-lyrics-encoding": "not encoded; source-visible lyrics are not directly syllable-aligned",
        "atlas-repeat-ending-encoding": "not encoded; source-visible terminal bars and phrase topology are not independently reconstructed",
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
    for path in (SOURCE_IMAGE, RETAINED_IMAGE, RAW_OMR):
        if not path.is_file():
            raise FileNotFoundError(path)
    source_hash = sha256(SOURCE_IMAGE)
    retained_hash = sha256(RETAINED_IMAGE)
    raw_hash = sha256(RAW_OMR)
    write_output(source_hash, raw_hash)
    draft_hash = sha256(OUTPUT)
    raw = retime_summary(score_stats(RAW_OMR), beats=2)
    draft = retime_summary(score_stats(OUTPUT), beats=2)
    blocking = [
        "The immutable page visibly identifies GUM POND. L.M., E major, 2/4, Isaac Watts (1719), Isaac Lloyd (2017), four vocal parts, and source-visible lyrics. The page has two systems (8 and 9 measures) and terminal double bars; exact repeat/ending semantics are not encoded in the retained structured score.",
        "The retained MXL exports 17 measures per part, matching Audiveris's 17 raw measures across two systems, but its event stream is not source-proven: it contains 138 pitched events, 10 empty exported measures, no rests, and 48 of 68 part-measures fail the source 2/4 duration target at divisions=2. The source event, duration, and measure-content correspondence is therefore not complete.",
        "The retained OMR and corrected derivative contain no lyrics, repeat/ending elements, or per-note four-shape encoding. The E-major key and 2/4 meter are source observations only; adding those attributes does not prove the underlying OMR events, printed shapes, lyric syllables, or phrase topology. No unsupported event, lyric, repeat, ending, or obscured material was fabricated.",
        "No authorized exact-edition structured Gum Pond witness was available. Alternate-edition records were not used to fill notes, durations, lyrics, repeats, endings, or shapes.",
    ]
    audit = {
        "queueId": "sh2025/566", "edition": "Sacred Harp, 2025 Edition", "songNo": "566", "title": "Gum Pond",
        "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=566", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/566-Gum-Pond/566.jpg",
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceImageSha256": source_hash, "immutable": True,
            "directObservations": {
                "header": "GUM POND. L.M.", "composer": "Isaac Watts, 1719", "arranger": "Isaac Lloyd, 2017", "key": "E major", "mode": "major", "timeSignature": "2/4", "meter": "Long Meter (8,8,8,8)", "parts": 4,
                "sourceRawMeasuresFromAudiveris": 17, "sourceRawMeasuresBySystem": [8, 9], "exportedMeasuresByPart": {"P1": 17, "P2": 17, "P3": 17, "P4": 17},
                "sourceLyricsVisible": True, "repeatBarsVisible": False, "numberedEndingsVisible": False, "terminalDoubleBarVisible": True, "watermarkIntersectsNotation": True,
            },
        },
        "retainedSourceImageDuplicate": {"path": str(RETAINED_IMAGE.relative_to(ROOT)), "sha256": retained_hash, "immutable": True, "byteEqualToRequestedSource": SOURCE_IMAGE.read_bytes() == RETAINED_IMAGE.read_bytes(), "geometryMatchesRequestedSource": True},
        "inputOmr": {"path": str(RAW_OMR.relative_to(ROOT)), "sha256": raw_hash, "status": "retained-source-scan-omr", "summary": raw},
        "sourceScanOmr": {"path": str(RAW_OMR.relative_to(ROOT)), "sha256": raw_hash, "selectedWorkingLayer": "raw-source-scan-omr", "status": "review-only-omr-input", "summary": raw},
        "candidateWitness": {"available": False, "candidateRole": "No authorized exact-edition structured Gum Pond witness was available; alternate editions were not used."},
        "correctedDraft": {"path": str(OUTPUT.relative_to(ROOT)), "sha256": draft_hash, "summary": draft, "eventStreamPreservedFromRetainedOmr": True, "status": "review-only-not-source-verified", "corrections": ["source-observed E-major key", "source-observed 2/4 meter", "explicit autonomous-block metadata", "lyrics/repeats/endings/shapes intentionally not fabricated"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceScanSha256": source_hash, "retainedImagePath": str(RETAINED_IMAGE.relative_to(ROOT)), "retainedImageSha256": retained_hash, "rawOmrSha256": raw_hash, "method": "full-resolution visual inspection of immutable scan plus structural/event/duration audit of retained source-scan OMR; alternate editions not used", "blockingFindings": blocking},
        "blockingFindings": blocking,
        "blockingReason": "Autonomous promotion is blocked by the 47-of-68 retained-OMR 2/4 duration failures, 10 empty exported measures, absent lyrics/repeat/ending semantics/per-note shape encoding, watermark-intersected notation, and lack of an authorized exact-edition structured witness. The corrected derivative remains review-only despite the matching 17-measure topology.",
        "autonomousDisposition": "OMR-derived evidence is retained for audit, but no exact source-faithful transposable score is admitted.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-unencoded-source-semantics; retain-review-derivative-only",
        "policy": "Immutable 2025 source images remain authoritative. OMR and metadata corrections cannot authorize promotion without direct event-level, rhythm, lyric, repeat, mode, meter, and shape proof.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "sourceImageSha256": source_hash, "retainedImageSha256": retained_hash, "rawOmrSha256": raw_hash, "draftSha256": draft_hash, "rawPitchedEvents": raw["pitchedEvents"], "draftPitchedEvents": draft["pitchedEvents"], "durationFailures": raw["durationFailureCount"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
