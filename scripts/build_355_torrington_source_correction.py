#!/usr/bin/env python3
"""Record a source-faithful, fail-closed Torrington comparison."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/omr/355-torrington/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/355-torrington-4c0cf9178f.jpg"
SOURCE_OMR = ROOT / "work/omr/355-torrington/source.mxl"
NORMALIZED_OMR = ROOT / "work/omr/cleaned-normalized-v2-355-torrington-4c0cf9178f/work__source-images__2025__355-torrington-4c0cf9178f.mxl"
DRAFT = ROOT / "work/omr/source-shape-review-drafts/2025/355-source-shape-review.mxl"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/355-torrington-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/355-source-shape-autonomous-blocked-comparison.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_root(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        name = next(name for name in archive.namelist() if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/"))
        return ET.fromstring(archive.read(name))


def stats(path: Path) -> dict[str, object]:
    root = read_root(path)
    result: dict[str, object] = {"parts": 0, "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "restEvents": 0, "shapeNoteheads": 0, "lyrics": 0}
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
    return result


def build_draft() -> None:
    """Copy the normalized review draft and add only source-supported metadata."""
    with zipfile.ZipFile(DRAFT) as source:
        xml_name = next(name for name in source.namelist() if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/"))
        root = ET.fromstring(source.read(xml_name))
        for part in root.findall("./part"):
            for measure in part.findall("./measure"):
                attributes = measure.find("./attributes")
                if attributes is None:
                    attributes = ET.Element("attributes")
                    measure.insert(0, attributes)
                key = attributes.find("./key")
                if key is None:
                    key = ET.Element("key")
                    attributes.insert(1, key)
                for old in list(key.findall("./fifths")) + list(key.findall("./mode")):
                    key.remove(old)
                ET.SubElement(key, "fifths").text = "2"
                ET.SubElement(key, "mode").text = "major"
                clock = attributes.find("./time")
                if clock is None:
                    clock = ET.Element("time")
                    key_index = next((i for i, item in enumerate(attributes) if item.tag.rsplit("}", 1)[-1] == "key"), 1)
                    attributes.insert(key_index + 1, clock)
                for old in list(clock.findall("./beats")) + list(clock.findall("./beat-type")):
                    clock.remove(old)
                ET.SubElement(clock, "beats").text = "4"
                ET.SubElement(clock, "beat-type").text = "4"
        xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for info in source.infolist():
                target.writestr(info, xml if info.filename == xml_name else source.read(info.filename))


def main() -> int:
    source_stats = stats(SOURCE_OMR)
    normalized_stats = stats(NORMALIZED_OMR)
    build_draft()
    draft_stats = stats(OUTPUT)
    source_image_hash = sha256(SOURCE_IMAGE)
    retained_image_hash = sha256(RETAINED_IMAGE)
    source_hash = sha256(SOURCE_OMR)
    normalized_hash = sha256(NORMALIZED_OMR)
    draft_input_hash = sha256(DRAFT)
    draft_hash = sha256(OUTPUT)
    audit = {
        "queueId": "sh2025/355",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "355",
        "title": "Torrington",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=355",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/355-Torrington/355.jpg",
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)),
            "sourceImageSha256": source_image_hash,
            "retainedSourceImagePath": str(RETAINED_IMAGE.relative_to(ROOT)),
            "retainedSourceImageSha256": retained_image_hash,
            "immutable": True,
            "directObservations": {
                "header": "TORRINGTON. S.M.",
                "composer": "Augustus Toplady, 1772",
                "arranger": "Keillor Mose, 2017",
                "key": "D major",
                "mode": "major",
                "timeSignature": "4/4",
                "meter": "Short Meter (6,6,8,6)",
                "parts": 4,
                "systems": 2,
                "sourceMeasureCount": 14,
                "measuresByPart": {"P1": 14, "P2": 14, "P3": 14, "P4": 14},
                "lyricsVisible": True,
                "repeatBarsVisible": True,
                "endingsVisible": False,
                "terminalDoubleBarVisible": True,
                "watermarkIntersectsNotation": True,
            },
        },
        "inputOmr": {"path": str(SOURCE_OMR.relative_to(ROOT)), "sha256": source_hash, "status": "retained-source-scan-omr", "stats": source_stats},
        "normalizedOmrWitness": {"path": str(NORMALIZED_OMR.relative_to(ROOT)), "sha256": normalized_hash, "status": "review-only-normalized-v2-omr", "stats": normalized_stats},
        "candidateWitness": {"status": "none-authorized", "sameTitleStructuredCandidate": False},
        "correctedDraft": {
            "path": str(OUTPUT.relative_to(ROOT)),
            "sha256": draft_hash,
            "status": "review-only-not-source-verified",
            "stats": draft_stats,
            "sourceKey": "D major",
            "sourceMode": "major",
            "sourceTimeSignature": "4/4",
            "eventCountDeltaFromRetainedSourceOmr": {
                part: int(draft_stats["eventsByPart"].get(part, 0)) - int(source_stats["eventsByPart"].get(part, 0))  # type: ignore[union-attr]
                for part in sorted(set(source_stats["eventsByPart"]) | set(draft_stats["eventsByPart"]))  # type: ignore[union-attr]
            },
            "inputReviewDraft": {"path": str(DRAFT.relative_to(ROOT)), "sha256": draft_input_hash},
            "eventStreamPreservedFromNormalizedReviewDraft": True,
            "encodingBasis": "normalized-v2 source-scan OMR pitch steps plus observed D-major key and 4/4 meter; no event, lyric, repeat, or shape is source-verified",
        },
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)),
            "sourceScanSha256": source_image_hash,
            "retainedImagePath": str(RETAINED_IMAGE.relative_to(ROOT)),
            "retainedImageSha256": retained_image_hash,
            "imageGeometry": "1312x984 for both retained source-image files; bytes differ, so hashes are preserved separately",
            "method": "full-resolution visual inspection of the immutable page plus independent statistics of raw and normalized OMR derivatives; no alternate edition used",
            "blockingFindings": [
                "The immutable page visibly prints D major, 4/4, four vocal parts, lyrics, a sectional repeat, and a terminal double bar.",
                "The retained source OMR contains 115 events (32/20/22/32 pitches plus rests), while the normalized review draft contains 103 events (93 pitches plus rests); this event delta is not source proof and cannot be reconciled by inference.",
                "The OMR-derived draft does not prove every source pitch, rhythm, rest, measure boundary, lyric, repeat/ending, or per-note four-shape identity.",
                "The diagonal DO NOT COPY watermark intersects the lower-middle notation and lyrics, so obscured content was not fabricated.",
                "No exact-edition authorized structured witness exists for this record.",
            ],
        },
        "blockingReason": "Autonomous promotion is blocked: raw and normalized OMR disagree in event coverage, and neither establishes source-exact pitches, rhythms, rests, lyrics, repeats/endings, or per-note shapes. The source scan also contains watermark-obscured notation. No missing material was synthesized.",
        "nextAction": "autonomous-promotion-blocked-by-omr-event-delta-and-unverified-source-structure; retain-corrected-draft-only",
        "policy": "Immutable 2025 source remains authoritative. OMR and derived shape tags are audit work product only and cannot authorize promotion without direct event-level evidence.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": audit["queueId"], "status": audit["comparisonStatus"], "sourceImageSha256": source_image_hash, "retainedImageSha256": retained_image_hash, "sourceOmrSha256": source_hash, "normalizedOmrSha256": normalized_hash, "draftSha256": draft_hash, "sourceEvents": source_stats["eventsByPart"], "normalizedEvents": normalized_stats["eventsByPart"], "draftEvents": draft_stats["eventsByPart"], "audit": str(AUDIT.relative_to(ROOT))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
