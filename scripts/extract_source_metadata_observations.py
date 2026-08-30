#!/usr/bin/env python3
"""Extract review-only metadata observations from immutable source pages.

The page image remains authoritative. OCR is used only to make visible header
metadata easier to review; it never changes a score, establishes edition
equivalence, or enables promotion. Raw OCR output and the source checksum are
retained beside each observation for an auditable human-review handoff.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "public" / "image-review-queue.json"
HUMAN_REVIEW_QUEUE = ROOT / "public" / "human-review-queue.json"
OUTPUT = ROOT / "public" / "source-metadata-observations.json"
OCR_ROOT = ROOT / "work" / "source-metadata" / "ocr" / "2025"
KEY_PATTERN = re.compile(r"\b([A-Ga-g](?:#|b)?)[\s-]*(Major|Minor)\b", re.IGNORECASE)


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "untitled"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_key(raw_key: str, mode: str) -> str:
    accidental = raw_key[1:] if len(raw_key) > 1 else ""
    pitch = raw_key[0].upper() + accidental
    return f"{pitch} {mode.lower()}"


def inspect_record(item: dict[str, Any], review_item: dict[str, Any], tesseract: str) -> dict[str, Any]:
    original = item.get("original", {})
    image_path = ROOT / str(original.get("path", ""))
    ocr_path = OCR_ROOT / f"{slug(item.get('songNo', item.get('queueId', 'record')))}-{slug(item.get('title', 'untitled'))}.txt"
    source_hash = sha256(image_path)
    completed = subprocess.run(
        [tesseract, str(image_path), "stdout", "--psm", "11"],
        capture_output=True,
        text=True,
        check=False,
    )
    ocr_text = completed.stdout
    ocr_path.write_text(ocr_text, encoding="utf-8")
    ocr_hash = sha256(ocr_path)
    header_text = " ".join(ocr_text.split())[:1000]
    match = KEY_PATTERN.search(header_text)
    if match:
        observed_key = normalize_key(match.group(1), match.group(2))
        key_observation = {
            "value": observed_key,
            "rawText": match.group(0),
            "status": "observed-from-source-image-ocr",
            "reviewRequired": True,
        }
    else:
        key_observation = {
            "value": "",
            "rawText": "",
            "status": "not-detected",
            "reviewRequired": True,
        }
    return {
        "queueId": item.get("queueId", ""),
        "edition": "sh2025",
        "songNo": item.get("songNo", ""),
        "title": item.get("title", ""),
        "source": {
            "imageUrl": item.get("sourceImageUrl", ""),
            "imagePath": original.get("path", ""),
            "imageSha256": source_hash,
            "immutable": original.get("immutable") is True,
        },
        "observations": {
            "key": key_observation,
            "meter": {
                "value": review_item.get("meter", ""),
                "timeSignature": review_item.get("timeSignature", ""),
                "status": "catalog-and-review-queue-metadata",
                "reviewRequired": True,
            },
            "parts": {
                "count": review_item.get("draftSummary", {}).get("parts", 0),
                "measuresByPart": review_item.get("draftSummary", {}).get("measuresByPart", {}),
                "status": "omr-draft-structure",
                "reviewRequired": True,
            },
        },
        "comparisonStatus": "not-compared",
        "safeToPromote": False,
        "humanReviewRequired": True,
        "ocr": {
            "engine": "tesseract",
            "rawTextPath": str(ocr_path.relative_to(ROOT)),
            "rawTextSha256": ocr_hash,
            "exitCode": completed.returncode,
            "headerText": header_text,
        },
    }


def main() -> int:
    tesseract = shutil.which("tesseract")
    if not tesseract:
        raise SystemExit("tesseract is required to extract source metadata observations")
    payload = json.loads(QUEUE.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    review_payload = json.loads(HUMAN_REVIEW_QUEUE.read_text(encoding="utf-8"))
    review_by_id = {item.get("queueId"): item for item in review_payload.get("reviewNow", [])}
    OCR_ROOT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        observations = list(
            pool.map(
                lambda item: inspect_record(item, review_by_id.get(item.get("queueId"), {}), tesseract),
                records,
            )
        )
    observations.sort(key=lambda item: item.get("queueId", ""))
    matched = sum(bool(item["observations"]["key"]["value"]) for item in observations)
    OUTPUT.write_text(
        json.dumps(
            {
                "version": 1,
                "generatedFrom": "public/image-review-queue.json",
                "policy": "OCR observations are review-only; the untouched source image remains authoritative and no observation is safe to promote.",
                "summary": {
                    "total": len(observations),
                    "keyObserved": matched,
                    "keyNotDetected": len(observations) - matched,
                    "safeToPromote": 0,
                },
                "records": observations,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT} with {len(observations)} source metadata observations ({matched} keys observed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
