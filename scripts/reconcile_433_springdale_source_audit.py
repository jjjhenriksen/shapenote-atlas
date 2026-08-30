#!/usr/bin/env python3
"""Reconcile the existing Springdale source-shape draft into an autonomous block.

This does not alter the immutable scan, the retained source OMR, or musical
events. It only records the bounded source/OMR evidence already inspected and
removes the stale generic human-review disposition from the comparison audit.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/omr/433-springdale/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/433-springdale-b32df5123d.jpg"
RAW_OMR = ROOT / "work/omr/433-springdale/source.mxl"
WORKING_OMR = ROOT / "work/omr/cleaned-normalized-v2-433-springdale-b32df5123d/work__source-images__2025__433-springdale-b32df5123d.mxl"
DRAFT = ROOT / "work/omr/source-shape-review-drafts/2025/433-source-shape-review.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/433-source-shape-autonomous-blocked-comparison.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def children(parent: ET.Element | None, wanted: str) -> list[ET.Element]:
    return [child for child in (parent if parent is not None else []) if tag(child) == wanted]


def first(parent: ET.Element | None, wanted: str) -> ET.Element | None:
    return next(iter(children(parent, wanted)), None)


def text(parent: ET.Element | None, wanted: str, default: str = "") -> str:
    child = first(parent, wanted)
    return (child.text or "").strip() if child is not None else default


def duration_end(measure: ET.Element) -> int:
    cursor = maximum = 0
    for item in measure:
        kind = tag(item)
        amount = int(text(item, "duration", "0") or "0")
        if kind == "backup":
            cursor -= amount
        elif kind == "forward":
            cursor += amount
        elif kind == "note":
            cursor += amount
            maximum = max(maximum, cursor)
    return maximum


def score_stats(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        xml_name = next(name for name in archive.namelist() if name.endswith(".xml") and not name.startswith("META-INF/"))
        root = ET.fromstring(archive.read(xml_name))
    parts = children(root, "part")
    measures_by_part: dict[str, int] = {}
    events_by_part: dict[str, int] = {}
    pitched_by_part: dict[str, int] = {}
    rests_by_part: dict[str, int] = {}
    empty_by_part: dict[str, int] = {}
    divisions_by_part: dict[str, int] = {}
    duration_end_by_part: dict[str, list[int]] = {}
    failures_by_part: dict[str, list[str]] = {}
    shape_count = lyric_count = repeat_count = barline_count = 0
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = children(part, "measure")
        measures_by_part[part_id] = len(measures)
        events_by_part[part_id] = sum(len(children(measure, "note")) for measure in measures)
        pitched_by_part[part_id] = sum(first(note, "pitch") is not None for measure in measures for note in children(measure, "note"))
        rests_by_part[part_id] = sum(first(note, "rest") is not None for measure in measures for note in children(measure, "note"))
        empty_by_part[part_id] = sum(not children(measure, "note") for measure in measures)
        attributes = first(measures[0], "attributes") if measures else None
        divisions = int(text(attributes, "divisions", "1") or "1")
        divisions_by_part[part_id] = divisions
        ends = [duration_end(measure) for measure in measures]
        duration_end_by_part[part_id] = ends
        failures_by_part[part_id] = [f"m{index + 1}={end}" for index, end in enumerate(ends) if end != divisions * 4]
        for measure in measures:
            for note in children(measure, "note"):
                if first(note, "pitch") is not None:
                    shape_count += len(children(note, "notehead"))
                lyric_count += len(children(note, "lyric"))
            for barline in children(measure, "barline"):
                barline_count += 1
                repeat_count += len(children(barline, "repeat")) + len(children(barline, "ending"))
    return {
        "parts": len(parts),
        "measuresByPart": measures_by_part,
        "eventsByPart": events_by_part,
        "pitchedEventsByPart": pitched_by_part,
        "restEventsByPart": rests_by_part,
        "emptyMeasuresByPart": empty_by_part,
        "pitchedEvents": sum(pitched_by_part.values()),
        "restEvents": sum(rests_by_part.values()),
        "emptyMeasures": sum(empty_by_part.values()),
        "divisionsByPart": divisions_by_part,
        "durationEndByPart": duration_end_by_part,
        "durationFailuresAgainst4_4": failures_by_part,
        "durationFailureCount": sum(len(items) for items in failures_by_part.values()),
        "shapeNoteheadsAdded": shape_count,
        "lyricsRetained": lyric_count,
        "barlines": barline_count,
        "repeatEndingElements": repeat_count,
    }


def main() -> int:
    raw = score_stats(RAW_OMR)
    working = score_stats(WORKING_OMR)
    draft = score_stats(DRAFT)
    image_hash = sha256(SOURCE_IMAGE)
    retained_hash = sha256(RETAINED_IMAGE)
    raw_hash = sha256(RAW_OMR)
    working_hash = sha256(WORKING_OMR)
    draft_hash = sha256(DRAFT)
    assert SOURCE_IMAGE.read_bytes() == RETAINED_IMAGE.read_bytes()
    blocking = [
        "The immutable page visibly identifies SPRINGDALE. L.M., F minor, 4/4, Isaac Watts (1719), Cory Winters (2019), four vocal parts, lyrics, first/second endings, and a terminal double bar; a diagonal DO NOT COPY watermark intersects the central systems.",
        "Audiveris reports 18 raw measures (10 in the first system and 8 in the second), while the retained source MXL and normalized-v2 working MXL export 16 measures per part. The normalized-v2 draft contains 152 pitched events across 4 parts and 41 of 64 exported measures fail the 4/4 duration target at divisions=2; 13 measures are empty in the raw export. This does not establish the complete source event stream or topology.",
        "The retained OMR and review derivative contain no lyrics or repeat/ending elements. The 152 four-shape noteheads in the derivative are derived from OMR pitch steps plus the observed F-minor key, not independently verified against each printed notehead. The raw OMR also omits an explicit time signature and mode.",
        "No authorized exact-edition structured witness was available. Alternate-edition records for song number 433 are distinct and were not used to fill notes, durations, lyrics, repeats, or shapes.",
    ]
    audit = {
        "queueId": "sh2025/433",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "433",
        "title": "Springdale",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=433",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/433-Springdale/433.jpg",
            "sourceImagePath": str(RETAINED_IMAGE.relative_to(ROOT)),
            "sourceImageSha256": image_hash,
            "immutable": True,
            "directObservations": {
                "header": "SPRINGDALE. L.M.",
                "composer": "Isaac Watts, 1719",
                "arranger": "Cory Winters, 2019",
                "key": "F minor",
                "mode": "minor",
                "timeSignature": "4/4",
                "meter": "Long Meter (8,8,8,8)",
                "parts": 4,
                "sourceRawMeasuresFromAudiveris": 18,
                "sourceRawMeasuresBySystem": [10, 8],
                "exportedMeasuresByPart": {"P1": 16, "P2": 16, "P3": 16, "P4": 16},
                "sourceLyricsVisible": True,
                "repeatBarsVisible": True,
                "numberedEndingsVisible": True,
                "terminalDoubleBarVisible": True,
                "watermarkIntersectsNotation": True,
            },
        },
        "retainedSourceImageDuplicate": {
            "path": str(RETAINED_IMAGE.relative_to(ROOT)),
            "sha256": retained_hash,
            "immutable": True,
            "byteEqualToRequestedSource": True,
        },
        "inputOmr": {
            "path": str(RAW_OMR.relative_to(ROOT)),
            "sha256": raw_hash,
            "status": "retained-source-scan-omr",
            "summary": raw,
        },
        "sourceScanOmr": {
            "path": str(WORKING_OMR.relative_to(ROOT)),
            "sha256": working_hash,
            "selectedWorkingLayer": "normalized-v2",
            "status": "review-only-omr-input",
            "summary": working,
        },
        "candidateWitness": {
            "available": False,
            "candidateRole": "No authorized exact-edition structured witness was available; alternate editions were not used.",
        },
        "correctedDraft": {
            "path": str(DRAFT.relative_to(ROOT)),
            "sha256": draft_hash,
            "summary": draft,
            "eventStreamPreservedFromWorkingOmr": True,
            "corrections": [
                "derived four-shape noteheads from retained OMR pitch steps and observed F-minor source key",
                "recorded source-observed F-minor mode and 4/4 meter in provenance",
                "retained no lyrics or uncertain repeat/ending semantics",
            ],
            "status": "review-only-not-source-verified",
        },
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)),
            "sourceScanSha256": image_hash,
            "retainedDuplicatePath": str(RETAINED_IMAGE.relative_to(ROOT)),
            "retainedDuplicateSha256": retained_hash,
            "rawOmrPath": str(RAW_OMR.relative_to(ROOT)),
            "rawOmrSha256": raw_hash,
            "method": "full-resolution visual inspection of the immutable scan plus structural audit of raw and normalized-v2 OMR; no alternate witness used to fill source events",
            "blockingFindings": blocking,
        },
        "blockingFindings": blocking,
        "blockingReason": "Autonomous promotion is blocked by the 18-versus-16 measure topology discrepancy, 41 duration failures in 64 normalized-v2 exported measures at divisions=2, 13 empty raw-OMR measures, absent lyrics and source-confirmed per-note shapes, incomplete repeat/ending semantics, watermark-intersected notation, and no authorized exact-edition structured witness. The existing shape-bearing derivative remains review-only.",
        "autonomousDisposition": "OMR-derived evidence is retained for audit, but no exact source-faithful transposable score is admitted.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-unresolved-topology; retain-review-derivative-only",
        "policy": "Immutable 2025 source images remain authoritative. OMR and derived shape tags are evidence only and cannot authorize promotion without direct event-level, rhythm, lyric, repeat, mode, meter, and shape proof.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "sourceImageSha256": image_hash, "rawOmrSha256": raw_hash, "workingOmrSha256": working_hash, "draftSha256": draft_hash, "raw": raw, "working": working, "draft": draft}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
