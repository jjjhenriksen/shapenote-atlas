#!/usr/bin/env python3
"""Run Audiveris on confirmed 2025 source scans as drafts only.

This command never edits the corpus or promotes a draft. It downloads only
confirmed source-image URLs into the local work area, runs Audiveris, retains a
per-record log, and leaves the resulting MXL files for human comparison.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public" / "corpus.json"
SOURCE_IMAGES = ROOT / "public" / "source-image-manifest.json"
OMR_ROOT = ROOT / "work" / "omr"
RUN_INDEX = OMR_ROOT / "2025-batch-run.json"
DEFAULT_AUDIVERIS = Path("/Volumes/Audiveris/Audiveris.app/Contents/MacOS/Audiveris")


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "untitled"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def missing_2025_records(corpus: dict[str, Any], images: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for song in corpus.get("songs", []):
        if "sh2025" not in song.get("books", []):
            continue
        if song.get("scoreByBook", {}).get("sh2025") or song.get("referenceScoreByBook", {}).get("sh2025"):
            continue
        song_no = song.get("songNo", "").lower()
        image = images.get(f"sh2025/{song_no}", {})
        if not image.get("sourceImageUrl"):
            continue
        records.append({"song": song, "image": image})
    return sorted(records, key=lambda item: (int(re.match(r"\d+", item["song"].get("songNo", "0")).group()), item["song"].get("songNo", "")))


def has_draft(song_no: str) -> bool:
    return any(
        path.is_file() and path.suffix.lower() == ".mxl"
        for path in OMR_ROOT.glob(f"{song_no.lower()}-*/*.mxl")
    )


def fetch_image(url: str, path: Path) -> None:
    if path.exists() and path.stat().st_size > 1000:
        return
    request = urllib.request.Request(url, headers={"User-Agent": "Shape-Note-Atlas/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
    if len(data) < 1000:
        raise ValueError(f"source image was unexpectedly small ({len(data)} bytes)")
    path.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="process at most N records; zero means all")
    parser.add_argument("--audiveris", type=Path, default=Path(__import__("os").environ.get("AUDIVERIS_BIN", str(DEFAULT_AUDIVERIS))))
    args = parser.parse_args()
    if not args.audiveris.exists():
        raise SystemExit(f"Audiveris executable not found: {args.audiveris}")

    corpus = load(CORPUS)
    images = load(SOURCE_IMAGES).get("records", {})
    candidates = [item for item in missing_2025_records(corpus, images) if not has_draft(item["song"].get("songNo", ""))]
    if args.limit:
        candidates = candidates[: args.limit]
    OMR_ROOT.mkdir(parents=True, exist_ok=True)
    prior_results: dict[str, dict[str, Any]] = {}
    if RUN_INDEX.exists():
        try:
            prior_results = {
                item.get("queueId", ""): item
                for item in load(RUN_INDEX).get("records", [])
                if item.get("queueId")
            }
        except (OSError, json.JSONDecodeError):
            prior_results = {}
    results: dict[str, dict[str, Any]] = dict(prior_results)
    # A failed full transcribe can still leave a usable partial .omr book.
    # Reconcile exports recovered from that book before deciding what remains
    # failed; this keeps the cumulative run ledger truthful without promoting
    # anything into the corpus.
    for result in results.values():
        if result.get("status") != "failed":
            continue
        output_directory = result.get("outputDirectory", "")
        recovered_mxl = ROOT / output_directory / "source.mxl"
        if recovered_mxl.is_file():
            result["status"] = "draft-created"
            result["draftArtifact"] = str(recovered_mxl.relative_to(ROOT))
            result["recoveryMethod"] = "exported-from-partial-omr-book"
            result["recoveredAt"] = datetime.now(timezone.utc).isoformat()
    for item in candidates:
        song = item["song"]
        song_no = song.get("songNo", "")
        title = song.get("titlesByBook", {}).get("sh2025", song.get("title", ""))
        record_dir = OMR_ROOT / f"{song_no.lower()}-{slug(title)}"
        image_path = record_dir / "source.jpg"
        log_path = record_dir / "audiveris.log"
        record_dir.mkdir(parents=True, exist_ok=True)
        result: dict[str, Any] = {
            "queueId": f"sh2025/{song_no}",
            "songNo": song_no,
            "title": title,
            "sourceImageUrl": item["image"].get("sourceImageUrl", ""),
            "sourceImage": str(image_path.relative_to(ROOT)),
            "outputDirectory": str(record_dir.relative_to(ROOT)),
            "status": "pending",
            "startedAt": datetime.now(timezone.utc).isoformat(),
        }
        try:
            fetch_image(result["sourceImageUrl"], image_path)
            command = [
                str(args.audiveris),
                "-batch",
                "-transcribe",
                "-export",
                "-output",
                str(record_dir),
                str(image_path),
            ]
            with log_path.open("w", encoding="utf-8") as log:
                completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=300, check=False)
            result["exitCode"] = completed.returncode
            mxl = record_dir / "source.mxl"
            omr = record_dir / "source.omr"
            result["draftArtifact"] = str(mxl.relative_to(ROOT)) if mxl.exists() else ""
            result["omrArtifact"] = str(omr.relative_to(ROOT)) if omr.exists() else ""
            result["log"] = str(log_path.relative_to(ROOT))
            result["status"] = "draft-created" if mxl.exists() else "failed"
        except (OSError, urllib.error.URLError, ValueError, subprocess.SubprocessError) as exc:
            result["status"] = "failed"
            result["error"] = str(exc)
        result["finishedAt"] = datetime.now(timezone.utc).isoformat()
        results[result["queueId"]] = result
        print(f"{result['status']}: {song_no} {title}", flush=True)

    all_results = [results[key] for key in sorted(results)]

    RUN_INDEX.write_text(
        json.dumps(
            {
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "policy": "Drafts only; no output is promoted without human source comparison.",
                "audiveris": str(args.audiveris),
                "requestedThisRun": len(candidates),
                "totalRecords": len(all_results),
                "created": sum(result["status"] == "draft-created" for result in all_results),
                "failed": sum(result["status"] == "failed" for result in all_results),
                "records": all_results,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {RUN_INDEX} with {len(all_results)} cumulative attempted records.")
    return 0 if not any(result["status"] == "failed" for result in all_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
