#!/usr/bin/env python3
"""Create explicit autonomous decisions for source-shape drafts without a comparison.

Every current SH25 source-shape draft is useful audit work, but an OMR-derived
draft is not itself proof of the printed page.  For records that have no
comparison record yet, retain all paths and hashes and close the decision as a
fail-closed autonomous block.  Existing comparisons are never overwritten.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHAPE_MANIFEST = ROOT / "work/omr/source-shape-review-drafts/2025/manifest.json"
COMPARISON_ROOT = ROOT / "work/source-transcriptions/2025"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local(path: str) -> Path:
    return ROOT / path


def main() -> int:
    manifest = json.loads(SHAPE_MANIFEST.read_text(encoding="utf-8"))
    existing_ids = set()
    for path in COMPARISON_ROOT.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("queueId"):
            existing_ids.add(str(payload["queueId"]).lower())

    changed = []
    for item in manifest.get("records", []):
        queue_id = str(item.get("queueId", "")).lower()
        if not queue_id or queue_id in existing_ids:
            continue
        source = item.get("sourceAuthority", {})
        source_image = local(str(source.get("sourceImagePath", "")))
        source_omr = item.get("sourceScanOmr", {})
        review_draft = item.get("reviewDraft", {})
        omr_path = local(str(source_omr.get("path", "")))
        draft_path = local(str(review_draft.get("path", "")))
        if not source_image.is_file() or not omr_path.is_file() or not draft_path.is_file():
            raise SystemExit(f"{queue_id}: source image, OMR, or review draft is missing")
        source_hash = sha256(source_image)
        omr_hash = sha256(omr_path)
        draft_hash = sha256(draft_path)
        if source_hash != source.get("sourceImageSha256"):
            raise SystemExit(f"{queue_id}: immutable source checksum mismatch")
        if omr_hash != source_omr.get("sha256"):
            raise SystemExit(f"{queue_id}: source OMR checksum mismatch")
        if draft_hash != review_draft.get("sha256"):
            raise SystemExit(f"{queue_id}: review draft checksum mismatch")

        observed = source.get("observations", {})
        parts = observed.get("parts", {})
        key = observed.get("key", {})
        meter = observed.get("meter", {})
        findings = [
            "No exact-edition structured MusicXML witness is available for this record.",
            "The retained source-shape MusicXML is OMR-derived and its pitches, rhythms, rests, repeats, lyrics, and measure boundaries are not independently proven against every printed event.",
            "Its four-shape noteheads are deterministic hypotheses from OMR pitch steps and a review-only key observation, not direct per-note source evidence.",
        ]
        if key.get("reviewRequired") is True or key.get("status") != "observed-from-source-image-ocr":
            findings.append("The key/mode observation is not an independently validated structured declaration.")
        if meter.get("timeSignature"):
            findings.append("The source time signature is recorded as an observation but has not been proven against the full OMR event stream.")
        else:
            findings.append("The source time signature is not encoded in the available structured evidence.")
        findings.append("Autonomous promotion is therefore blocked; no missing event or lyric is being fabricated.")

        payload = {
            "queueId": queue_id,
            "edition": "Sacred Harp, 2025 Edition",
            "songNo": item.get("songNo", ""),
            "title": item.get("title", ""),
            "comparisonStatus": "autonomously-blocked",
            "autonomousDecision": "blocked",
            "safeToPromote": False,
            "humanReviewRequired": False,
            "sourceAuthority": {
                "sourcePageUrl": f"https://fasola.org/indexes/2025/?p={item.get('songNo', '')}",
                "sourceImageUrl": source.get("sourceImageUrl", ""),
                "sourceImagePath": source.get("sourceImagePath", ""),
                "sourceImageSha256": source_hash,
                "immutable": source.get("immutable") is True,
                "directObservations": {
                    "key": key.get("value", ""),
                    "mode": source.get("observedMode", ""),
                    "keyEvidenceStatus": key.get("status", ""),
                    "keyReviewRequired": key.get("reviewRequired") is True,
                    "meter": meter.get("value", ""),
                    "timeSignature": meter.get("timeSignature", ""),
                    "meterEvidenceStatus": meter.get("status", ""),
                    "parts": parts.get("count", 0),
                    "measuresByPart": parts.get("measuresByPart", {}),
                    "partsEvidenceStatus": parts.get("status", ""),
                    "fourShapeNoteheadsVisible": True,
                    "sourceLyricsVisible": True,
                },
            },
            "sourceScanOmr": {
                "path": source_omr.get("path", ""),
                "sha256": omr_hash,
                "selectedWorkingLayer": source_omr.get("selectedWorkingLayer", ""),
                "selectedWorkingPath": source_omr.get("selectedWorkingPath", ""),
                "status": "review-only-omr-input",
            },
            "reviewDraft": {
                "path": review_draft.get("path", ""),
                "sha256": draft_hash,
                "publicPath": review_draft.get("publicPath", ""),
                "pitchedEventsRetained": review_draft.get("pitchedEventsRetained", 0),
                "shapeNoteheadsAdded": review_draft.get("shapeNoteheadsAdded", 0),
                "sourceKey": review_draft.get("sourceKey", ""),
                "sourceMode": review_draft.get("sourceMode", ""),
                "sourceTimeSignature": review_draft.get("sourceTimeSignature", ""),
                "status": "review-only-not-source-verified",
            },
            "blockingFindings": findings,
            "autonomousDisposition": "Alternate/OMR-only evidence is retained for audit, but no exact source-faithful transposable score is admitted.",
            "nextAction": "autonomous-promotion-blocked-by-omr-only-evidence; retain-immutable-source-and-draft; requires-exact-authorized-2025-structured-source",
            "policy": "Immutable source images remain authoritative. OMR and derived shape tags are review work product only and cannot authorize promotion without direct event-level and shape evidence.",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        output = COMPARISON_ROOT / f"{item['songNo']}-source-shape-autonomous-blocked-comparison.json"
        if output.exists():
            raise SystemExit(f"refusing to overwrite existing output: {output}")
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        changed.append(queue_id)
    print(json.dumps({"created": len(changed), "queueIds": changed}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
