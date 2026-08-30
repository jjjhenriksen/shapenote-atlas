#!/usr/bin/env python3
"""Build a source-image-only human review queue for the current 2025 backlog."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from review_dispositions import image_review_disposition


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "work" / "source-images" / "manifest.json"
WORKING_MANIFEST = ROOT / "work" / "transcription-images" / "manifest.json"
OUTPUT_JSON = ROOT / "public" / "image-review-queue.json"
OUTPUT_MD = ROOT / "work" / "source-images" / "image-review-queue.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def review_checklist() -> list[str]:
    return [
        "Compare the untouched original and normalized-v2 image at full-page scale.",
        "Confirm that only border/scan cleanup changed; no musical symbol, lyric, title, or page mark was reconstructed.",
        "Inspect every watermark or obstruction crossing notation directly against the original.",
        "Use suppressed-v2 only as a visual aid; treat any erased or weakened ink as uncertain.",
        "Record a human comparison decision before using any image to support transcription.",
    ]


def main() -> int:
    source = load(SOURCE_MANIFEST)
    working = load(WORKING_MANIFEST)
    working_by_original = {item.get("originalPath"): item for item in working.get("records", [])}
    entries = []
    disposition = image_review_disposition()
    for item in source.get("records", []):
        original_path = item.get("localPath", "")
        layers = working_by_original.get(original_path, {})
        ready = item.get("status") == "ready" and bool(original_path) and bool(layers.get("workingPath")) and bool(layers.get("suppressedWorkingPath"))
        entries.append({
            "queueId": item.get("queueId", ""),
            "canonicalRecordId": item.get("queueId", ""),
            "edition": "Sacred Harp 2025",
            "songNo": item.get("songNo", ""),
            "title": item.get("title", ""),
            "status": "ready-for-human-review" if ready else item.get("status", "image-prep-pending"),
            "humanReviewRequired": True,
            "reviewAvailable": True,
            "safeToPromote": False,
            "disposition": disposition,
            "sourceImageUrl": item.get("sourceImageUrl", ""),
            "sourceIndexKey": item.get("sourceIndexKey", ""),
            "original": {
                "path": original_path,
                "sha256": item.get("sha256", ""),
                "bytes": item.get("bytes", 0),
                "immutable": item.get("immutable") is True,
                "acquisition": item.get("acquisition", ""),
            },
            "workingLayers": {
                "normalized-v2": {
                    "label": "NORMALIZED V2 — conservative legibility aid; full frame retained",
                    "path": layers.get("workingPath", ""),
                    "sha256": layers.get("workingSha256", ""),
                    "omrAllowed": True,
                },
                "suppressed-v2": {
                    "label": "SUPPRESSED V2 — visual analysis aid only",
                    "path": layers.get("suppressedWorkingPath", ""),
                    "sha256": layers.get("suppressedWorkingSha256", ""),
                    "omrAllowed": False,
                },
            },
            "watermarkAssessment": layers.get("watermarkAssessment", {"status": "not-assessed", "humanReviewRequired": True}),
            "transformations": layers.get("transformations", {}),
            "reviewChecklist": review_checklist(),
            "policy": "Original remains the source of truth; working layers are reversible review aids and no image is source-faithful until explicitly compared with the original.",
        })
    entries.sort(key=lambda item: item.get("queueId", ""))
    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "version": "image-review-queue-v1",
        "policy": "Image preparation is separate from notation promotion. These records are review-only and explicitly require human comparison against the immutable original before image evidence can support transcription.",
        "summary": {
            "total": len(entries),
            "readyForHumanReview": sum(item["status"] == "ready-for-human-review" for item in entries),
            "pendingOrBlocked": sum(item["status"] != "ready-for-human-review" for item in entries),
            "originalsImmutable": sum(item["original"]["immutable"] for item in entries),
            "safeToPromote": 0,
            "humanReviewRequired": sum(bool(item["humanReviewRequired"]) for item in entries),
            "reviewAvailable": sum(bool(item["reviewAvailable"]) for item in entries),
            "dispositionCounts": {"review-only": len(entries)},
        },
        "records": entries,
    }
    OUTPUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Sacred Harp image preparation review queue",
        "",
        "This queue covers current Sacred Harp 2025 records that still lack an exact or reference structured score. Originals are immutable; derived images are labeled review aids only. No image is source-faithful until a human compares it with the original.",
        "",
        f"Records: **{len(entries)}** · ready for human review: **{output['summary']['readyForHumanReview']}** · pending/blocked: **{output['summary']['pendingOrBlocked']}**",
        "",
        "| Record | Status | Original | Normalized-v2 | Suppressed-v2 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in entries:
        layers = item["workingLayers"]
        lines.append(f"| {item['songNo']} {item['title']} | `{item['status']}` | `{item['original']['path'] or 'not retained'}` | `{layers['normalized-v2']['path'] or 'not prepared'}` | `{layers['suppressed-v2']['path'] or 'not prepared'}` |")
    lines.extend(["", "## Review rule", "", *[f"- [ ] {check}" for check in review_checklist()], ""])
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT_JSON), **output["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
