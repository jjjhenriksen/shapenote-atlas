#!/usr/bin/env python3
"""Validate image provenance, layer identity, and fail-closed review status."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from review_dispositions import image_review_disposition


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public" / "corpus.json"
QUEUE = ROOT / "public" / "image-review-queue.json"


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def main() -> int:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    expected = {
        f"sh2025/{song.get('songNo', '').lower()}"
        for song in corpus.get("songs", [])
        if "sh2025" in song.get("books", [])
        and not song.get("scoreByBook", {}).get("sh2025")
        and not song.get("referenceScoreByBook", {}).get("sh2025")
    }
    records = queue.get("records", [])
    errors: list[str] = []
    actual = {item.get("queueId") for item in records}
    if actual != expected or len(actual) != len(records):
        errors.append(f"queue coverage mismatch: expected {len(expected)}, got {len(records)}")
    if queue.get("summary", {}).get("total") != len(records):
        errors.append("summary total is stale")
    if queue.get("summary", {}).get("humanReviewRequired") != len(records):
        errors.append("summary human-review-required count is stale")
    if queue.get("summary", {}).get("reviewAvailable") != len(records):
        errors.append("summary review-available count is stale")
    if queue.get("summary", {}).get("dispositionCounts") != {"review-only": len(records)}:
        errors.append("summary disposition counts are stale")
    for item in records:
        label = item.get("queueId", "unknown")
        if item.get("canonicalRecordId") != label:
            errors.append(f"{label}: canonical record identity is missing or mismatched")
        if item.get("humanReviewRequired") is not True or item.get("reviewAvailable") is not True or item.get("safeToPromote") is not False:
            errors.append(f"{label}: queue is not fail-closed")
        if item.get("disposition") != image_review_disposition():
            errors.append(f"{label}: image disposition is not the required source-comparison state")
        original = item.get("original", {})
        path = ROOT / original.get("path", "")
        if not original.get("immutable") or not path.is_file():
            errors.append(f"{label}: immutable original missing")
        elif original.get("sha256") != digest(path):
            errors.append(f"{label}: original checksum drift")
        normalized = item.get("workingLayers", {}).get("normalized-v2", {})
        suppressed = item.get("workingLayers", {}).get("suppressed-v2", {})
        for layer_name, layer in (("normalized-v2", normalized), ("suppressed-v2", suppressed)):
            layer_path = ROOT / layer.get("path", "")
            if not layer.get("path") or not layer_path.is_file():
                errors.append(f"{label}: {layer_name} missing")
            elif layer.get("sha256") != digest(layer_path):
                errors.append(f"{label}: {layer_name} checksum drift")
        if normalized.get("omrAllowed") is not True or suppressed.get("omrAllowed") is not False:
            errors.append(f"{label}: working-layer policy drift")
        if original.get("path", "").startswith("work/transcription-images/"):
            errors.append(f"{label}: original was placed under a derived working-image path")
    summary = {
        "records": len(records),
        "readyForHumanReview": sum(item.get("status") == "ready-for-human-review" for item in records),
        "errors": errors,
    }
    print(json.dumps(summary, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
