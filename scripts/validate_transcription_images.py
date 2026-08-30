#!/usr/bin/env python3
"""Validate the non-destructive image-preparation and cleaned-OMR ledgers."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "work" / "transcription-images" / "manifest.json"
CLEANED_RUNS = (
    ROOT / "work" / "omr" / "cleaned-v1-run.json",  # retain prior review runs
    ROOT / "work" / "omr" / "cleaned-normalized-v2-run.json",  # current normalized-v2 runs win
)
EXPECTED_EXPLICIT_WORKING = {
    "254-warsaw-cleaned-v1.png",
    "255-mechanicville-cleaned-v1.png",
    "256-northampton-cleaned-v1.png",
    "257-manatawny-cleaned-v1.png",
    "258-inspiration-cleaned-v1.png",
    "259-easton-cleaned-v1.png",
    "414t-farewell-brethren-cleaned-v1.png",
    "484t-millbrook-cleaned-v1.png",
}


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors: list[str] = []
    records = manifest.get("records", [])
    for item in records:
        label = item.get("originalPath", "unknown")
        paths = {
            "original": (ROOT / item["originalPath"], item["originalSha256"]),
            "working": (ROOT / item["workingPath"], item["workingSha256"]),
            "suppressed": (ROOT / item["suppressedWorkingPath"], item["suppressedWorkingSha256"]),
        }
        for kind, (path, expected) in paths.items():
            if not path.exists():
                errors.append(f"{label}: missing {kind} layer")
            elif digest(path) != expected:
                errors.append(f"{label}: {kind} hash drift")
    ai_samples = manifest.get("aiEditedSamples", [])
    for item in ai_samples:
        path = ROOT / item["path"]
        if not path.exists():
            errors.append(f"missing AI sample: {item.get('sampleKey', '')}")
        elif digest(path) != item.get("sha256"):
            errors.append(f"AI sample hash drift: {item.get('sampleKey', '')}")
        if item.get("status") != "ai-edited-suspect" or not item.get("humanReviewRequired"):
            errors.append(f"AI sample not fail-closed: {item.get('sampleKey', '')}")

    explicit = manifest.get("explicitWorkingImages", [])
    explicit_names = {Path(item.get("workingPath", "")).name for item in explicit}
    if explicit_names != EXPECTED_EXPLICIT_WORKING:
        errors.append(f"2025 explicit working inventory mismatch: {sorted(explicit_names)}")
    for item in explicit:
        label = item.get("workingPath", "unknown")
        original = ROOT / item["originalPath"]
        working = ROOT / item["workingPath"]
        if not original.exists() or digest(original) != item.get("originalSha256"):
            errors.append(f"{label}: original source hash drift or missing")
        if not working.exists() or digest(working) != item.get("workingSha256"):
            errors.append(f"{label}: working hash drift or missing")
        if item.get("status") != "ai-edited-suspect" or item.get("omrAllowed") is not False or not item.get("humanReviewRequired"):
            errors.append(f"{label}: unsafe AI working copy is not fail-closed")

    cleaned_by_source: dict[str, dict] = {}
    for cleaned_path in CLEANED_RUNS:
        if not cleaned_path.exists():
            continue
        cleaned = json.loads(cleaned_path.read_text(encoding="utf-8"))
        for item in cleaned.get("records", []):
            original_path = item.get("originalPath", "")
            if original_path:
                cleaned_by_source[original_path] = item
    cleaned_records = list(cleaned_by_source.values())
    for item in cleaned_records:
        if item.get("status") not in {"draft-created", "draft-created-after-timeout", "draft-reused", "failed-existing-draft"}:
            errors.append(f"cleaned OMR did not complete: {item.get('originalPath', '')}")
        for artifact in item.get("draftArtifacts", []):
            path = ROOT / artifact
            if not path.exists():
                errors.append(f"missing cleaned OMR artifact: {artifact}")
                continue
            try:
                with zipfile.ZipFile(path) as archive:
                    if archive.testzip() is not None:
                        errors.append(f"corrupt cleaned MXL: {artifact}")
            except zipfile.BadZipFile:
                errors.append(f"not a valid MXL archive: {artifact}")
        selected = item.get("selectedWorkingPath")
        if selected and not (ROOT / selected).exists():
            errors.append(f"missing selected working image: {selected}")
        if item.get("selectedWorkingLayer") == "working-2025":
            errors.append(f"unsafe working-2025 image reached cleaned OMR ledger: {item.get('originalPath', '')}")
        if item.get("status") == "failed-existing-draft":
            fallback = ROOT / item.get("fallbackDraft", "")
            if not fallback.is_file() or not zipfile.is_zipfile(fallback):
                errors.append(f"missing fallback draft for failed cleaned OMR: {item.get('originalPath', '')}")
            elif item.get("fallbackDraftSha256") and digest(fallback) != item["fallbackDraftSha256"]:
                errors.append(f"fallback draft hash drift: {item.get('originalPath', '')}")

    expected_watermark = sum(item.get("watermarkAssessment", {}).get("humanReviewRequired", False) for item in records)
    counts = manifest.get("counts", {})
    if counts.get("sourceImages") != len(records):
        errors.append("manifest source-image count mismatch")
    if counts.get("normalizedWorkingImages") != len(records) or counts.get("suppressedWorkingImages") != len(records):
        errors.append("manifest working-layer count mismatch")
    if counts.get("watermarkReviewRequired") != expected_watermark:
        errors.append("manifest watermark-review count mismatch")
    summary = {
        "sourceImages": len(records),
        "normalizedWorkingImages": sum((ROOT / item["workingPath"]).exists() for item in records),
        "suppressedWorkingImages": sum((ROOT / item["suppressedWorkingPath"]).exists() for item in records),
        "aiEditedSamples": len(ai_samples),
        "explicitWorkingImages": len(explicit),
        "unsafeExplicitWorkingImages": sum(item.get("omrAllowed") is False for item in explicit),
        "cleanedOMRRecords": len(cleaned_records),
        "cleanedOMRDrafts": sum(len(item.get("draftArtifacts", [])) for item in cleaned_records),
        "errors": errors,
    }
    print(json.dumps(summary, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
