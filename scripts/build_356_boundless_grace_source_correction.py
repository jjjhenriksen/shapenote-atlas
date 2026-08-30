#!/usr/bin/env python3
"""Record a source-faithful, fail-closed Boundless Grace comparison."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/omr/356-boundless-grace/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/356-boundless-grace-e0113c52e2.jpg"
SOURCE_OMR = ROOT / "work/omr/356-boundless-grace/source.mxl"
NORMALIZED_OMR = ROOT / "work/omr/cleaned-normalized-v2-356-boundless-grace-e0113c52e2/work__source-images__2025__356-boundless-grace-e0113c52e2.mxl"
DRAFT_INPUT = ROOT / "work/omr/source-shape-review-drafts/2025/356-source-shape-review.mxl"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/356-boundless-grace-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/356-source-shape-autonomous-blocked-comparison.json"


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
    """Copy the normalized shape draft and add only source-supported metadata."""
    with zipfile.ZipFile(DRAFT_INPUT) as source:
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
                ET.SubElement(key, "fifths").text = "0"
                ET.SubElement(key, "mode").text = "minor"
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
    input_draft_stats = stats(DRAFT_INPUT)
    build_draft()
    draft_stats = stats(OUTPUT)
    source_image_hash = sha256(SOURCE_IMAGE)
    retained_image_hash = sha256(RETAINED_IMAGE)
    source_hash = sha256(SOURCE_OMR)
    normalized_hash = sha256(NORMALIZED_OMR)
    input_draft_hash = sha256(DRAFT_INPUT)
    draft_hash = sha256(OUTPUT)
    audit = {
        "queueId": "sh2025/356",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "356",
        "title": "Boundless Grace",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=356",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/356-Boundless-Grace/356.jpg",
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)),
            "sourceImageSha256": source_image_hash,
            "retainedSourceImagePath": str(RETAINED_IMAGE.relative_to(ROOT)),
            "retainedSourceImageSha256": retained_image_hash,
            "immutable": True,
            "directObservations": {
                "header": "BOUNDLESS GRACE. C.M.D.",
                "composer": "Ott(i)well Heginbotham, 1794",
                "arranger": "Micah John Walter, 2019",
                "key": "A minor",
                "mode": "minor",
                "timeSignature": "4/4",
                "meter": "Long Meter Double (8,8,8,8,8,8,8,8)",
                "parts": 4,
                "systems": 3,
                "sourceMeasureCount": 25,
                "measuresByPart": {"P1": 25, "P2": 25, "P3": 25, "P4": 25},
                "lyricsVisible": True,
                "repeatBarsVisible": True,
                "endingsVisible": True,
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
            "sourceKey": "A minor",
            "sourceMode": "minor",
            "sourceTimeSignature": "4/4",
            "inputReviewDraft": {"path": str(DRAFT_INPUT.relative_to(ROOT)), "sha256": input_draft_hash, "stats": input_draft_stats},
            "eventStreamPreservedFromNormalizedReviewDraft": True,
            "encodingBasis": "normalized-v2 source-scan OMR pitch steps plus observed A-minor key and 4/4 meter; no event, lyric, repeat, or shape is source-verified",
        },
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)),
            "sourceScanSha256": source_image_hash,
            "retainedImagePath": str(RETAINED_IMAGE.relative_to(ROOT)),
            "retainedImageSha256": retained_image_hash,
            "method": "full-resolution visual inspection of the immutable page plus independent statistics of raw, normalized, and shape-draft derivatives; no alternate edition used",
            "measureTopology": {"rawSourceOmr": source_stats["measuresByPart"], "normalizedOmr": normalized_stats["measuresByPart"], "draft": draft_stats["measuresByPart"], "sourceVisible": {"P1": 25, "P2": 25, "P3": 25, "P4": 25}},
            "eventCounts": {"rawSourceOmr": source_stats["eventsByPart"], "normalizedOmr": normalized_stats["eventsByPart"], "draft": draft_stats["eventsByPart"]},
            "blockingFindings": [
                "The immutable page visibly prints A minor, 4/4, four vocal parts, lyrics, sectional and numbered ending bars, and a terminal double bar.",
                "The retained raw source OMR has 25 measures per part and 223 events, while normalized-v2 has only 24 measures per part and 258 events; this topology/event divergence is not source proof and cannot be reconciled by inference.",
                "The OMR-derived draft has no lyrics, and its pitch, rhythm, rest, repeat/ending, measure, and per-note four-shape identities are not independently proven against the page.",
                "The diagonal DO NOT COPY watermark intersects the middle systems and lyrics, so obscured content was not fabricated.",
                "No exact-edition authorized structured witness exists for this record.",
            ],
        },
        "blockingReason": "Autonomous promotion is blocked: raw and normalized OMR disagree in measure topology and event coverage, and neither establishes source-exact pitches, rhythms, rests, lyrics, repeats/endings, or per-note shapes. The source scan also contains watermark-obscured notation. No missing material was synthesized.",
        "nextAction": "autonomous-promotion-blocked-by-omr-topology-and-event-delta-and-unverified-source-structure; retain-corrected-draft-only",
        "policy": "Immutable 2025 source remains authoritative. OMR and derived shape tags are audit work product only and cannot authorize promotion without direct event-level evidence.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": audit["queueId"], "status": audit["comparisonStatus"], "sourceImageSha256": source_image_hash, "retainedImageSha256": retained_image_hash, "sourceOmrSha256": source_hash, "normalizedOmrSha256": normalized_hash, "draftSha256": draft_hash, "sourceEvents": source_stats["eventsByPart"], "normalizedEvents": normalized_stats["eventsByPart"], "draftEvents": draft_stats["eventsByPart"], "audit": str(AUDIT.relative_to(ROOT))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
