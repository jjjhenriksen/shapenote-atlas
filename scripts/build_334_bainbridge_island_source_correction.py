#!/usr/bin/env python3
"""Record a source-faithful, fail-closed Bainbridge Island comparison."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/omr/334-bainbridge-island/source.jpg"
SOURCE_OMR = ROOT / "work/omr/334-bainbridge-island/source.mxl"
DRAFT = ROOT / "work/omr/source-shape-review-drafts/2025/334-source-shape-review.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/334-source-shape-autonomous-blocked-comparison.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def read_root(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        name = next(name for name in archive.namelist() if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/"))
        return ET.fromstring(archive.read(name))


def duration_stats(measure: ET.Element) -> int:
    cursor = maximum = 0
    for item in measure:
        kind = local(item.tag)
        duration = next((child for child in item if local(child.tag) == "duration"), None)
        units = int(duration.text) if duration is not None and duration.text and duration.text.isdigit() else 0
        if kind == "note":
            if not any(local(child.tag) == "chord" for child in item):
                cursor += units
            maximum = max(maximum, cursor)
        elif kind == "backup":
            cursor -= units
        elif kind == "forward":
            cursor += units
    return maximum


def stats(path: Path) -> dict[str, object]:
    root = read_root(path)
    result: dict[str, object] = {"parts": 0, "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "restEvents": 0, "shapeNoteheads": 0, "lyrics": 0, "durationFailures": {}, "barlines": {}}
    parts = root.findall("./part")
    result["parts"] = len(parts)
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = part.findall("./measure")
        notes = [note for measure in measures for note in measure.findall("./note")]
        result["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
        result["eventsByPart"][part_id] = len(notes)  # type: ignore[index]
        result["pitchedEvents"] = int(result["pitchedEvents"]) + sum(note.find("./pitch") is not None for note in notes)
        result["restEvents"] = int(result["restEvents"]) + sum(note.find("./rest") is not None for note in notes)
        result["shapeNoteheads"] = int(result["shapeNoteheads"]) + sum(note.find("./notehead") is not None for note in notes)
        result["lyrics"] = int(result["lyrics"]) + sum(note.find("./lyric") is not None for note in notes)
        divisions = next((int(child.text) for child in measures[0].findall("./attributes/divisions") if child.text and child.text.isdigit()), 1) if measures else 1
        expected = divisions * 2
        result["durationFailures"][part_id] = [f"m{measure.attrib.get('number', '')}={duration_stats(measure)}" for measure in measures if duration_stats(measure) != expected]  # type: ignore[index]
        result["barlines"][part_id] = [  # type: ignore[index]
            {
                "measure": measure.attrib.get("number", ""),
                "location": bar.attrib.get("location", ""),
                "style": next((child.text or "" for child in bar if local(child.tag) == "bar-style"), ""),
                "repeat": next((child.attrib.get("direction", "") for child in bar if local(child.tag) == "repeat"), ""),
                "ending": next((child.attrib.get("number", "") for child in bar if local(child.tag) == "ending"), ""),
            }
            for measure in measures for bar in measure.findall("./barline")
        ]
    return result


def main() -> int:
    source_stats = stats(SOURCE_OMR)
    draft_stats = stats(DRAFT)
    image_hash = sha256(SOURCE_IMAGE)
    source_hash = sha256(SOURCE_OMR)
    draft_hash = sha256(DRAFT)
    source_measures = source_stats["measuresByPart"]
    draft_measures = draft_stats["measuresByPart"]
    audit = {
        "queueId": "sh2025/334",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "334",
        "title": "Bainbridge Island",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=334",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/334-Bainbridge-Island/334.jpg",
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)),
            "sourceImageSha256": image_hash,
            "retainedSourceImagePath": "work/source-images/2025/334-bainbridge-island-7796086775.jpg",
            "retainedSourceImageSha256": image_hash,
            "immutable": True,
            "directObservations": {
                "header": "BAINBRIDGE ISLAND. L.M.",
                "composer": "Joseph H. Gilmore, 1862, and Phillips's Singing Pilgrim, 1866",
                "arranger": "Kevin Laurance Barrans, 2013",
                "key": "A major",
                "mode": "major",
                "timeSignature": "2/4",
                "meter": "Long Meter (8,8,8,8)",
                "parts": 4,
                "sourceMeasureCount": 33,
                "measuresByPart": {"P1": 33, "P2": 33, "P3": 33, "P4": 33},
                "lyricsVisible": True,
                "repeatBarsVisible": True,
                "endingsVisible": True,
                "terminalDoubleBarVisible": True,
                "watermarkIntersectsNotation": True,
            },
        },
        "inputOmr": {"path": str(SOURCE_OMR.relative_to(ROOT)), "sha256": source_hash, "status": "retained-source-scan-omr", "stats": source_stats},
        "candidateWitness": {"status": "none-authorized", "sameTitleStructuredCandidate": False},
        "correctedDraft": {
            "path": str(DRAFT.relative_to(ROOT)),
            "sha256": draft_hash,
            "status": "review-only-not-source-verified",
            "stats": draft_stats,
            "sourceKey": "A major",
            "sourceMode": "major",
            "sourceTimeSignature": "2/4",
            "eventCountDeltaFromRetainedSourceOmr": {
                part: int(draft_stats["eventsByPart"].get(part, 0)) - int(source_stats["eventsByPart"].get(part, 0))  # type: ignore[union-attr]
                for part in sorted(set(source_stats["eventsByPart"]) | set(draft_stats["eventsByPart"]))  # type: ignore[union-attr]
            },
            "encodingBasis": "normalized-v2 source-scan OMR pitch steps plus observed A-major key; no event, lyric, repeat, or shape is source-verified",
        },
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)),
            "sourceScanSha256": image_hash,
            "method": "full-resolution visual inspection of the immutable page plus independent statistics of retained and normalized OMR derivatives; no alternate edition used",
            "measureTopology": {"sourceOmr": source_measures, "draft": draft_measures, "sourceVisible": {"P1": 33, "P2": 33, "P3": 33, "P4": 33}},
            "blockingFindings": [
                "The immutable page visibly prints A major, 2/4, four vocal parts, lyrics, repeat/ending markers, and a terminal double bar.",
                "The retained source OMR contains 272 events, while the normalized review draft retains 258; this event delta is not source proof and cannot be reconciled by inference.",
                "The OMR-derived draft has no lyrics, and its pitch, rhythm, rests, measure boundaries, repeats/endings, and per-note four-shape identities are not independently proven against the page.",
                "The diagonal DO NOT COPY watermark intersects central notation, so obscured content was not fabricated.",
                "No exact-edition authorized structured witness exists for this record.",
            ],
        },
        "blockingReason": "Autonomous promotion is blocked: the immutable scan is authoritative, but the available OMR derivatives disagree in event counts (272 versus 258) and do not establish source-exact pitches, rhythms, rests, lyrics, repeats/endings, or per-note shapes. The source page's watermark further obscures some notation. No missing material was synthesized.",
        "nextAction": "autonomous-promotion-blocked-by-event-count-delta-and-unverified-source-structure; retain-corrected-draft-only",
        "policy": "Immutable 2025 source remains authoritative. OMR and derived shape tags are audit work product only and cannot authorize promotion without direct event-level evidence.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": audit["queueId"], "status": audit["comparisonStatus"], "sourceImageSha256": image_hash, "sourceOmrSha256": source_hash, "draftSha256": draft_hash, "sourceEvents": source_stats["eventsByPart"], "draftEvents": draft_stats["eventsByPart"], "audit": str(AUDIT.relative_to(ROOT))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
