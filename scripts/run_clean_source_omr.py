#!/usr/bin/env python3
"""Run Audiveris against clean public source-PDF candidates as review drafts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "work" / "source-transcriptions" / "2025" / "clean-source-candidates.json"
OUTPUT_ROOT = ROOT / "work" / "omr" / "clean-source-candidates"
RUN_INDEX = ROOT / "work" / "omr" / "clean-source-omr-run.json"
DEFAULT_AUDIVERIS = Path("/Volumes/Audiveris/Audiveris.app/Contents/MacOS/Audiveris")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "untitled"


def run_bounded(command: list[str], log_path: Path, timeout: int = 300) -> tuple[int, bool]:
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return process.wait(timeout=timeout), False
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            return 124, True


def page_count(path: Path) -> int:
    result = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=False)
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                break
    return 0


def candidate_suffix(item: dict[str, Any]) -> str:
    value = item.get("sha256") or item.get("pdfUrl") or item.get("candidatePageUrl") or item.get("songNo", "candidate")
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:10]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audiveris", type=Path, default=DEFAULT_AUDIVERIS)
    parser.add_argument("--record", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-pages", type=int, default=1, help="include candidates up to this many PDF pages")
    args = parser.parse_args()
    if not args.audiveris.exists():
        raise SystemExit(f"Audiveris executable not found: {args.audiveris}")

    payload = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    requested = {value.lower() for value in args.record}
    records = []
    for item in payload.get("records", []):
        if not item.get("localPdf") or item.get("status") != "candidate-source-needs-edition-comparison":
            continue
        if requested and str(item.get("songNo", "")).lower() not in requested:
            continue
        path = ROOT / (item.get("omrInputPdf") or item["localPdf"])
        if path.is_file() and 1 <= page_count(path) <= args.max_pages:
            records.append(item)
    records.sort(key=lambda item: (int(re.match(r"\d+", item.get("songNo", "0")).group()), item.get("songNo", "")))
    if args.limit:
        records = records[: args.limit]

    candidate_hashes = {item.get("sha256") for item in records if item.get("sha256")}
    prior = {}
    if RUN_INDEX.exists():
        try:
            prior = {
                item["candidateKey"]: item
                for item in json.loads(RUN_INDEX.read_text(encoding="utf-8")).get("records", [])
                if item.get("candidateKey", "").count("/") >= 2
                and item.get("candidatePdfSha256") in candidate_hashes
            }
        except (OSError, json.JSONDecodeError):
            prior = {}
    results: dict[str, dict[str, Any]] = dict(prior)
    for item in records:
        song_no = str(item.get("songNo", ""))
        suffix = candidate_suffix(item)
        candidate_key = item.get("candidateKey") or f"sh2025/{song_no}/{suffix}"
        output_dir = OUTPUT_ROOT / f"{slug(f'{song_no}-{item.get('title', '')}-{item.get('candidateTitle', '')}')}-{suffix}"
        output_dir.mkdir(parents=True, exist_ok=True)
        existing = next(output_dir.glob("*.mxl"), None)
        result: dict[str, Any] = {
            "candidateKey": candidate_key,
            "bookId": "sh2025",
            "songNo": song_no,
            "title": item.get("title", ""),
            "candidateTitle": item.get("candidateTitle", ""),
            "candidatePageUrl": item.get("candidatePageUrl", ""),
            "candidatePdfUrl": item.get("pdfUrl", ""),
            "candidatePdf": item.get("localPdf", ""),
            "candidatePdfSha256": item.get("sha256", ""),
            "omrInputPdf": item.get("omrInputPdf", item.get("localPdf", "")),
            "omrInputSha256": item.get("omrInputSha256", item.get("sha256", "")),
            "matchKind": item.get("matchKind", ""),
            "editionVerified": False,
            "reviewRequired": True,
            "outputDirectory": str(output_dir.relative_to(ROOT)),
            "status": "pending",
            "startedAt": datetime.now(timezone.utc).isoformat(),
        }
        if existing and prior.get(candidate_key, {}).get("candidatePdfSha256") == item.get("sha256"):
            result.update(prior[candidate_key])
            result["status"] = "draft-reused"
            results[candidate_key] = result
            print(f"draft-reused: {song_no} {item.get('title', '')}", flush=True)
            continue
        log_path = output_dir / "audiveris.log"
        command = [str(args.audiveris), "-batch", "-transcribe", "-export", "-output", str(output_dir), str(ROOT / (item.get("omrInputPdf") or item["localPdf"]))]
        exit_code, timed_out = run_bounded(command, log_path)
        artifacts = sorted(path for path in output_dir.glob("*.mxl") if path.is_file())
        result.update(
            {
                "exitCode": exit_code,
                "timedOutAfterExport": timed_out and bool(artifacts),
                "draftArtifacts": [str(path.relative_to(ROOT)) for path in artifacts],
                "log": str(log_path.relative_to(ROOT)),
                "status": "draft-created-after-timeout" if timed_out and artifacts else "draft-created" if artifacts else "failed",
                "finishedAt": datetime.now(timezone.utc).isoformat(),
            }
        )
        results[candidate_key] = result
        print(f"{result['status']}: {song_no} {item.get('title', '')}", flush=True)

    all_results = [results[key] for key in sorted(results)]
    RUN_INDEX.write_text(
        json.dumps(
            {
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "policy": "Clean public PDFs are alternate-source review aids only; OMR drafts are never promoted without comparison to the authorized Sacred Harp 2025 engraving.",
                "audiveris": str(args.audiveris),
                "requestedThisRun": len(records),
                "totalRecords": len(all_results),
                "created": sum(item.get("status", "").startswith("draft-created") for item in all_results),
                "reused": sum(item.get("status") == "draft-reused" for item in all_results),
                "failed": sum(item.get("status") == "failed" for item in all_results),
                "records": all_results,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(RUN_INDEX), "totalRecords": len(all_results), "created": sum(item.get("status", "").startswith("draft-created") for item in all_results), "failed": sum(item.get("status") == "failed" for item in all_results)}, indent=2))
    return 0 if not any(item.get("status") == "failed" for item in all_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
