#!/usr/bin/env python3
"""Reconcile Lovely Social Band's retained shape draft into an autonomous block."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from reconcile_437_enoch_source_audit import retime_summary, score_stats


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/source-images/2025/449-lovely-social-band-b2e12bf325.jpg"
OMR_IMAGE = ROOT / "work/omr/449-lovely-social-band/source.jpg"
RETAINED_IMAGE = SOURCE_IMAGE
RAW_OMR = ROOT / "work/omr/449-lovely-social-band/source.mxl"
WORKING_OMR = ROOT / "work/omr/cleaned-normalized-v2-449-lovely-social-band-b2e12bf325/work__source-images__2025__449-lovely-social-band-b2e12bf325.mxl"
PRIOR_DRAFT = ROOT / "work/omr/source-shape-review-drafts/2025/449-source-shape-review.mxl"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/449-lovely-social-band-source-correction.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/449-source-shape-autonomous-blocked-comparison.json"


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


def set_terminal_double_bar(part: ET.Element) -> None:
    measures = children(part, "measure")
    if not measures:
        return
    final = measures[-1]
    bars = [item for item in children(final, "barline") if item.attrib.get("location") == "right"]
    barline = bars[0] if bars else ET.SubElement(final, "barline", {"location": "right"})
    style = first(barline, "bar-style")
    if style is None:
        style = ET.SubElement(barline, "bar-style")
    style.text = "light-heavy"


def update_xml(xml_bytes: bytes) -> bytes:
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
        replace_child(key, "fifths", "-1")
        replace_child(key, "mode", "major", {"fifths"})
        clock = first(attributes, "time")
        if clock is None:
            clock = ET.SubElement(attributes, "time")
        replace_child(clock, "beats", "6")
        replace_child(clock, "beat-type", "8", {"beats"})
        set_terminal_double_bar(part)
    for note in root.iter():
        if clean(note.tag) == "note":
            for notehead in children(note, "notehead"):
                note.remove(notehead)
    work = first(root, "work")
    if work is None:
        work = ET.Element("work")
        root.insert(0, work)
    replace_child(work, "work-title", "Lovely Social Band")
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    fields = {
        "atlas-review-queue-id": "sh2025/449",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-transcription-status": "autonomously-blocked",
        "atlas-safe-to-promote": "false",
        "atlas-source-image": str(SOURCE_IMAGE.relative_to(ROOT)),
        "atlas-source-key": "F major",
        "atlas-source-mode": "major",
        "atlas-source-time-signature": "6/8",
        "atlas-shape-encoding": "not encoded; source-visible four-shape glyphs are not independently verified per event",
        "atlas-repeat-ending-encoding": "source-visible sectional repeat bars are recorded in the disposition, but their measure positions are not encoded because OMR barline alignment is unresolved; terminal double bars are encoded",
        "atlas-lyrics-encoding": "not encoded; source-visible verses are not directly syllable-aligned to retained events",
        "atlas-provenance-policy": "autonomous block; immutable 2025 source remains authoritative; no OMR promotion",
        "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
        "atlas-omr-image-sha256": sha256(OMR_IMAGE),
        "atlas-source-omr-sha256": sha256(WORKING_OMR),
    }
    for name, value in fields.items():
        put_field(identification, name, value)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_output() -> None:
    with zipfile.ZipFile(PRIOR_DRAFT) as source_zip, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        xml_name = next(name for name in source_zip.namelist() if name.endswith(".xml") and not name.startswith("META-INF/"))
        updated = update_xml(source_zip.read(xml_name))
        for info in source_zip.infolist():
            target.writestr(info, updated if info.filename == xml_name else source_zip.read(info.filename))


def main() -> int:
    write_output()
    raw = retime_summary(score_stats(RAW_OMR), beats=6)
    working = retime_summary(score_stats(WORKING_OMR), beats=6)
    draft = retime_summary(score_stats(OUTPUT), beats=6)
    image_hash = sha256(SOURCE_IMAGE)
    omr_image_hash = sha256(OMR_IMAGE)
    retained_hash = sha256(RETAINED_IMAGE)
    raw_hash = sha256(RAW_OMR)
    working_hash = sha256(WORKING_OMR)
    draft_hash = sha256(OUTPUT)
    blocking = [
        "The immutable page visibly identifies LOVELY SOCIAL BAND. L.M.D., F major, 6/8, John Poage Campbell (1806), Richard Mayers (2022), four vocal parts, three printed verses, lyrics, repeat bars, and a terminal double bar; a diagonal DO NOT COPY watermark intersects the middle systems.",
        "Audiveris reports 16 raw measures (7 in the first system and 9 in the second), matching the source page's 16-measure layout, but normalized-v2 exports no time signature and its 150-pitched-event working score fails the 6/8 duration target in 62 of 64 exported part-measures at divisions=2. The event durations are therefore not source-proven despite nominal measure-count agreement.",
        "The corrected derivative deliberately contains no notehead-shape tags, lyrics, or repeat/ending elements. The source visibly uses four-shape glyphs and sectional repeat bars, but the retained OMR does not provide independently verified per-event shapes, lyric alignment, or repeat measure positions. No unsupported event or semantic was fabricated.",
        "No authorized exact-edition structured witness was available. Alternate-edition records were not used to fill notes, durations, lyrics, repeats, or shapes.",
    ]
    audit = {
        "queueId": "sh2025/449", "edition": "Sacred Harp, 2025 Edition", "songNo": "449", "title": "Lovely Social Band",
        "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=449", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/449-Lovely-Social-Band/449.jpg",
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceImageSha256": image_hash, "immutable": True,
            "directObservations": {"header": "LOVELY SOCIAL BAND. L.M.D.", "composer": "John Poage Campbell, 1806", "arranger": "Richard Mayers, 2022", "key": "F major", "mode": "major", "timeSignature": "6/8", "meter": "Long Meter Double (8,8,8,8,8,8,8,8)", "parts": 4, "sourceRawMeasuresFromAudiveris": 16, "sourceRawMeasuresBySystem": [7, 9], "exportedMeasuresByPart": {"P1": 16, "P2": 16, "P3": 16, "P4": 16}, "sourceLyricsVisible": True, "numberedVersesVisible": True, "repeatBarsVisible": True, "repeatBarPositions": "visible but not safely mapped to retained OMR measure numbers", "terminalDoubleBarVisible": True, "watermarkIntersectsNotation": True},
        },
        "retainedSourceImageDuplicate": {"path": str(RETAINED_IMAGE.relative_to(ROOT)), "sha256": retained_hash, "immutable": True, "byteEqualToOmrImage": SOURCE_IMAGE.read_bytes() == OMR_IMAGE.read_bytes(), "geometryMatchesRequestedSource": True},
        "inputOmr": {"path": str(RAW_OMR.relative_to(ROOT)), "sha256": raw_hash, "status": "retained-source-scan-omr", "summary": raw},
        "sourceScanOmr": {"path": str(WORKING_OMR.relative_to(ROOT)), "sha256": working_hash, "selectedWorkingLayer": "normalized-v2", "status": "review-only-omr-input", "summary": working},
        "candidateWitness": {"available": False, "candidateRole": "No authorized exact-edition structured witness was available; alternate editions were not used."},
        "correctedDraft": {"path": str(OUTPUT.relative_to(ROOT)), "sha256": draft_hash, "summary": draft, "eventStreamPreservedFromPriorReviewDraft": True, "status": "review-only-not-source-verified", "corrections": ["source-observed F-major mode", "source-observed 6/8 meter", "source title added", "source-visible terminal double bars normalized to light-heavy", "unverified four-shape tags removed", "lyrics and repeat semantics intentionally omitted"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)), "sourceScanSha256": image_hash, "retainedImagePath": str(RETAINED_IMAGE.relative_to(ROOT)), "retainedImageSha256": retained_hash, "omrImagePath": str(OMR_IMAGE.relative_to(ROOT)), "omrImageSha256": omr_image_hash, "rawOmrSha256": raw_hash, "workingOmrSha256": working_hash, "method": "full-resolution visual inspection of immutable retained scan plus structural/event/duration audit of raw and normalized-v2 OMR; alternate editions not used", "blockingFindings": blocking},
        "blockingFindings": blocking,
        "blockingReason": "Autonomous promotion is blocked by the 62-of-64 normalized-v2 6/8 duration failures, absent event-aligned lyrics and per-note shape proof, unresolved mapping of visible sectional repeat bars to OMR measures, watermark-intersected notation, and lack of an authorized exact-edition structured witness. The corrected derivative remains review-only.",
        "autonomousDisposition": "OMR-derived evidence is retained for audit, but no exact source-faithful transposable score is admitted.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-unresolved-rhythm; retain-review-derivative-only",
        "policy": "Immutable 2025 source images remain authoritative. OMR and derived shape tags are evidence only and cannot authorize promotion without direct event-level, rhythm, lyric, repeat, mode, meter, and shape proof.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "imageSha256": image_hash, "retainedImageSha256": retained_hash, "rawOmrSha256": raw_hash, "workingOmrSha256": working_hash, "draftSha256": draft_hash, "workingDurationFailures": working["durationFailureCount"], "draftPitchedEvents": draft["pitchedEvents"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
