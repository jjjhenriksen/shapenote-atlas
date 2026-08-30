#!/usr/bin/env python3
"""Create non-destructive, provenance-tracked working images for OMR.

The original page images are never modified. Each source image gets two
derived layers:

* ``normalized-v2`` is deterministic and intended as the conservative OMR
  input (grayscale, mild denoise/contrast/sharpening, complete frame retained).
* ``suppressed-v2`` is a high-contrast analysis aid that suppresses mid-tone
  scan/watermark pixels. It is never treated as authoritative notation.

The script also records the known model-edited samples separately. A model
may remove a watermark by regenerating pixels, so those samples are explicitly
uncertain and are not fed into corpus promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = ROOT / "work" / "transcription-images"
SOURCE_ROOTS = [
    ROOT / "work" / "source-transcriptions",
    ROOT / "work" / "source-images",
    ROOT / "work" / "omr",
    ROOT / "work" / "source-pdfs",
]
MANIFEST = WORK_ROOT / "manifest.json"
EXPLICIT_WORKING_ROOT = WORK_ROOT / "working" / "2025"
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"

# These are user-provided/model-edited watermark-removal working copies. Keep
# them in the ledger so a future OMR invocation can name the exact image, but
# fail closed because removing a watermark can regenerate or alter notation.
EXPLICIT_WORKING_SOURCES = {
    "254-warsaw-cleaned-v1.png": "work/source-transcriptions/2025/254-warsaw.jpg",
    "255-mechanicville-cleaned-v1.png": "work/source-transcriptions/2025/255-mechanicville.jpg",
    "256-northampton-cleaned-v1.png": "work/source-transcriptions/2025/256-northampton.jpg",
    "257-manatawny-cleaned-v1.png": "work/source-transcriptions/2025/257-manatawny.jpg",
    "258-inspiration-cleaned-v1.png": "work/source-transcriptions/2025/258-inspiration.jpg",
    "259-easton-cleaned-v1.png": "work/source-transcriptions/2025/259-easton.jpg",
    "414t-farewell-brethren-cleaned-v1.png": "work/source-transcriptions/2025/414t/414t.jpg",
    "484t-millbrook-cleaned-v1.png": "work/source-transcriptions/2025/484t/484t.jpg",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(path: Path) -> str:
    relative = path.relative_to(ROOT)
    value = "__".join(relative.with_suffix("").parts)
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")


def is_source_image(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}:
        return False
    excluded = {"review-renders", "crops", "iconset", "verified-iconset-2"}
    if any(part in excluded for part in path.parts):
        return False
    if "draft-preview" in path.stem:
        return False
    if path.name == "pickup.png":
        return False
    return any(path == root or root in path.parents for root in SOURCE_ROOTS)


def source_kind(path: Path) -> str:
    if "source-transcriptions" in path.parts or "source-images" in path.parts:
        return "official-page-scan"
    if "source-pdfs" in path.parts:
        return "rendered-source-pdf"
    if "omr" in path.parts and path.name == "source.jpg":
        return "omr-source-scan"
    return "source-page-image"


def watermark_note(path: Path) -> dict[str, Any]:
    if "source-transcriptions" in path.parts or "source-images" in path.parts:
        return {
            "status": "probable-watermark-overlap",
            "regions": ["central diagonal overlay; exact note intersections require page-by-page comparison"],
            "humanReviewRequired": True,
        }
    return {
        "status": "not-assessed",
        "regions": [],
        "humanReviewRequired": False,
    }


def artifact_kind(path: Path) -> str:
    if path.suffix.lower() == ".mxl":
        return "musicxml-draft"
    if path.suffix.lower() == ".omr":
        return "audiveris-project"
    if path.name.endswith(".audit.json"):
        return "transcription-audit"
    if path.suffix.lower() == ".json":
        return "omr-or-transcription-index"
    if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}:
        return "source-or-rendered-image"
    if path.suffix.lower() == ".html":
        return "source-transcription-page"
    if path.suffix.lower() == ".pdf":
        return "rendered-draft-or-source-pdf"
    if path.suffix.lower() == ".log":
        return "audiveris-log"
    return "transcription-artifact"


def artifact_inventory() -> list[dict[str, Any]]:
    roots = [ROOT / "work" / "omr", ROOT / "work" / "source-transcriptions"]
    records: list[dict[str, Any]] = []
    for base in roots:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if any(part in {"review-renders", "crops"} for part in path.parts):
                continue
            records.append({
                "path": str(path.relative_to(ROOT)),
                "kind": artifact_kind(path),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            })
    return records


def measure_skew_degrees(source: Path) -> float:
    """Estimate page rotation from the concentration of horizontal ink rows."""
    probe = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0:s=,", str(source)],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        width, height = (int(value) for value in probe.stdout.strip().split(",", 1))
    except (ValueError, TypeError):
        return 0.0
    scale = 4
    small_width = max(1, width // scale)
    small_height = max(1, height // scale)
    raw = subprocess.run(
        [
            FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-vf",
            f"format=gray,scale={small_width}:{small_height}:flags=area",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "pipe:1",
        ],
        capture_output=True,
        check=False,
    ).stdout
    if len(raw) < small_width * small_height:
        return 0.0
    dark_points = [
        (x, y)
        for y in range(4, small_height - 4)
        for x in range(2, small_width - 2)
        if raw[y * small_width + x] < 135
    ]
    if len(dark_points) < 100:
        return 0.0
    center_x = (small_width - 1) / 2
    center_y = (small_height - 1) / 2
    best_score = -1.0
    best_angle = 0.0
    for tenth in range(-20, 21):
        angle = tenth / 10.0
        radians = angle * 3.141592653589793 / 180.0
        sine = math.sin(radians)
        cosine = math.cos(radians)
        bins = [0] * (small_height + 12)
        for x, y in dark_points:
            rotated_y = -(x - center_x) * sine + (y - center_y) * cosine + center_y + 6
            index = int(round(rotated_y))
            if 0 <= index < len(bins):
                bins[index] += 1
        score = sum(count * count for count in bins)
        if score > best_score:
            best_score = score
            best_angle = angle
    return best_angle


def run_filter(source: Path, destination: Path, suppressed: bool, skew_degrees: float) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Keep the complete source frame. A prior v1 crop could clip title/footer
    # provenance text at the page edge; v2 retains it and leaves border noise
    # visible for human comparison. The suppressed layer intentionally removes
    # mid-tone pixels; it is an analysis aid, never a source replacement.
    filters = []
    if abs(skew_degrees) >= 0.2:
        filters.append(f"rotate={skew_degrees:.3f}*PI/180:fillcolor=white:ow=rotw(iw):oh=roth(ih)")
    filters.extend([
        "format=gray",
        "hqdn3d=1.2:1.2:6:6",
        "eq=contrast=1.18:brightness=0.01",
        "unsharp=3:3:0.35:3:3:0.0",
    ])
    if suppressed:
        # Keep dark ink black, push mid-tone overlay/noise almost to white,
        # and retain a little headroom for antialiased note edges. Any symbol
        # under the watermark remains uncertain and is flagged below.
        filters.append("lutyuv=y='if(lt(val,130),0,if(lt(val,225),245,255))'")
    command = [
        FFMPEG,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-vf",
        ",".join(filters),
        "-frames:v",
        "1",
        "-compression_level",
        "9",
        str(destination),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not destination.exists() or destination.stat().st_size < 1000:
        raise RuntimeError(f"ffmpeg failed for {source}: {completed.stderr.strip()}")


def ai_sample_map() -> dict[str, Path]:
    generated = Path.home() / ".codex" / "generated_images" / "01a046d0-8094-7112-b8e9-60a3d683c82f"
    return {
        "254-warsaw": generated / "exec-a291e872-3e2f-4009-8556-def328a7c424.png",
        "255-mechanicville": generated / "exec-47a8baa4-bc0f-43d2-ace3-6dd7ac63735e.png",
        "256-northampton": generated / "exec-e557e4a5-5007-4099-bacb-25b204529068.png",
        "257-manatawny": generated / "exec-2d4133da-ef4d-4be4-ae41-2fda29358fc1.png",
        "258-inspiration": generated / "exec-d56161c4-aa6a-43ed-b135-09b76101f327.png",
        "259-easton": generated / "exec-988ab418-3352-49e0-8b0a-b1d8b688a700.png",
        "414t": generated / "exec-1c50a89b-e996-43ac-8642-dcad75a9730a.png",
        "484t": generated / "exec-1f2abbe9-bbd6-4d47-b353-b0324fae51e1.png",
    }


def explicit_working_inventory(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Inventory the eight named 2025 working copies without treating them as source."""
    by_original = {item["originalPath"]: item for item in records}
    inventory: list[dict[str, Any]] = []
    for filename, original_path in EXPLICIT_WORKING_SOURCES.items():
        working = EXPLICIT_WORKING_ROOT / filename
        original = by_original.get(original_path)
        if not working.exists() or original is None:
            continue
        inventory.append({
            "workingPath": str(working.relative_to(ROOT)),
            "workingSha256": sha256(working),
            "workingBytes": working.stat().st_size,
            "originalPath": original_path,
            "originalSha256": original["originalSha256"],
            "sourceKind": original["sourceKind"],
            "layer": "working-2025",
            "status": "ai-edited-suspect",
            "omrAllowed": False,
            "humanReviewRequired": True,
            "reviewReason": "Watermark removal/resynthesis may have altered noteheads, beams, rests, text, or spacing; compare every symbol against the immutable original before any transcription.",
            "policy": "visual comparison only; do not use as automatic OMR or authoritative MusicXML input",
        })
    return inventory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="rebuild existing derived layers")
    args = parser.parse_args()

    if not Path(FFMPEG).exists() or not Path(FFPROBE).exists():
        raise SystemExit(f"ffmpeg not found: {FFMPEG}")
    paths = sorted({path for root in SOURCE_ROOTS if root.exists() for path in root.rglob("*") if is_source_image(path)})
    if not paths:
        raise SystemExit("no source images found")

    normalized_root = WORK_ROOT / "working" / "normalized-v2"
    suppressed_root = WORK_ROOT / "working" / "suppressed-v2"
    ai_root = WORK_ROOT / "working" / "ai-suppressed-v1"
    records: list[dict[str, Any]] = []

    for source in paths:
        name = safe_name(source)
        normalized = normalized_root / f"{name}.png"
        suppressed = suppressed_root / f"{name}.png"
        skew_degrees = measure_skew_degrees(source)
        if args.force or not normalized.exists():
            run_filter(source, normalized, suppressed=False, skew_degrees=skew_degrees)
        if args.force or not suppressed.exists():
            run_filter(source, suppressed, suppressed=True, skew_degrees=skew_degrees)
        record: dict[str, Any] = {
            "originalPath": str(source.relative_to(ROOT)),
            "originalSha256": sha256(source),
            "originalBytes": source.stat().st_size,
            "sourceKind": source_kind(source),
            "workingPath": str(normalized.relative_to(ROOT)),
            "workingSha256": sha256(normalized),
            "suppressedWorkingPath": str(suppressed.relative_to(ROOT)),
            "suppressedWorkingSha256": sha256(suppressed),
            "transformations": {
                "version": "v2",
                "grayscale": True,
                "denoise": "ffmpeg hqdn3d 1.2:1.2:6:6",
                "contrast": "ffmpeg eq contrast 1.18 brightness 0.01",
                "sharpen": "ffmpeg unsharp 3x3 amount 0.35",
                "crop": "none; complete source frame retained",
                "deskew": {
                    "measuredDegrees": skew_degrees,
                    "applied": abs(skew_degrees) >= 0.2,
                    "method": "horizontal-ink-row concentration; rotations below 0.2 degrees left unchanged",
                },
                "watermarkSuppression": "dark-ink/mid-tone threshold at luma 130/225 only in suppressed-working layer",
            },
            "watermarkAssessment": watermark_note(source),
            "omrPolicy": "normalized-v2 may be used for draft OMR only; never promote without source comparison",
        }
        records.append(record)

    ai_records: list[dict[str, Any]] = []
    for key, source in ai_sample_map().items():
        if not source.exists():
            continue
        destination = ai_root / f"{key}-ai-v1.png"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if args.force or not destination.exists():
            shutil.copy2(source, destination)
        ai_records.append({
            "sampleKey": key,
            "path": str(destination.relative_to(ROOT)),
            "sha256": sha256(destination),
            "sourcePath": str(source),
            "status": "ai-edited-suspect",
            "humanReviewRequired": True,
            "policy": "visual analysis only; do not use as authoritative notation or automatic MusicXML input",
        })

    explicit_working = explicit_working_inventory(records)
    artifacts = artifact_inventory()
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "version": "transcription-image-working-v2",
        "policy": "Original source images are immutable. Derived layers are analysis aids. Any watermark-overlap region remains human-review-required; no notation is inferred from pixels.",
        "sourceRoots": [str(root.relative_to(ROOT)) for root in SOURCE_ROOTS],
        "counts": {
            "sourceImages": len(records),
            "normalizedWorkingImages": len(records),
            "suppressedWorkingImages": len(records),
            "aiEditedSamples": len(ai_records),
            "watermarkReviewRequired": sum(item["watermarkAssessment"]["humanReviewRequired"] for item in records),
            "transcriptionAndOMRArtifacts": len(artifacts),
            "explicitWorkingImages": len(explicit_working),
            "unsafeExplicitWorkingImages": sum(not item["omrAllowed"] for item in explicit_working),
        },
        "records": records,
        "explicitWorkingImages": explicit_working,
        "transcriptionAndOMRArtifacts": artifacts,
        "aiEditedSamples": ai_records,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(records)} source images; wrote {MANIFEST}")
    print(json.dumps(payload["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
