#!/usr/bin/env python3
"""Run the existing Audiveris draft path against selected working images.

The deterministic ``normalized-v2`` layer is the default permitted input.
Other layers must be selected explicitly and unsafe AI-edited copies are
refused. Results are written beside the existing drafts under a versioned
``cleaned-v2-*`` folder, then recorded in a separate run ledger. They remain
draft work product and are deliberately not promoted into the corpus.
"""

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
MANIFEST = ROOT / "work" / "transcription-images" / "manifest.json"
SOURCE_IMAGE_MANIFEST = ROOT / "work" / "source-images" / "manifest.json"
OMR_ROOT = ROOT / "work" / "omr"
DEFAULT_AUDIVERIS = Path("/Volumes/Audiveris/Audiveris.app/Contents/MacOS/Audiveris")
LAYERS = {"normalized-v2", "suppressed-v2", "working-2025"}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "untitled"


def page_key(record: dict[str, Any]) -> str:
    path = Path(record["originalPath"])
    # source-transcriptions/2025/256-northampton.jpg -> 256-northampton
    return slug(path.stem)


def requested_record_matches(record: dict[str, Any], requested: str) -> bool:
    key = page_key(record)
    stem = Path(record["originalPath"]).stem
    return requested in {key, stem} or key.startswith(f"{requested}-")


def existing_review_draft(key: str) -> Path | None:
    """Find the canonical numbered review draft for a cleaned-input retry."""
    match = re.match(r"^(\d+[a-z]?)(?:-|$)", key)
    if not match:
        return None
    for candidate in sorted(OMR_ROOT.glob(f"{match.group(1)}-*/source.mxl")):
        if not candidate.parent.name.startswith("cleaned-"):
            return candidate
    return None


def canonical_source_paths() -> set[str]:
    """Return retained page paths, excluding stale duplicate downloads."""
    if not SOURCE_IMAGE_MANIFEST.exists():
        return set()
    try:
        payload = load(SOURCE_IMAGE_MANIFEST)
    except (OSError, json.JSONDecodeError):
        return set()
    return {
        str(item.get("localPath", ""))
        for item in payload.get("records", [])
        if item.get("localPath")
    }


def selected_records(payload: dict[str, Any], layer: str, requested: list[str]) -> list[dict[str, Any]]:
    retained_paths = canonical_source_paths()
    official = {
        item["originalPath"]: item
        for item in payload.get("records", [])
        if item.get("sourceKind") == "official-page-scan"
        and (not retained_paths or item.get("originalPath") in retained_paths)
    }
    if layer == "working-2025":
        candidates = []
        for item in payload.get("explicitWorkingImages", []):
            base = official.get(item.get("originalPath"))
            if base is None:
                continue
            selected = dict(base)
            selected["selectedWorkingPath"] = item["workingPath"]
            selected["selectedWorkingSha256"] = item["workingSha256"]
            selected["selectedWorkingLayer"] = layer
            selected["selectedWorkingStatus"] = item.get("status")
            selected["selectedWorkingOMRAllowed"] = item.get("omrAllowed", False)
            selected["selectedWorkingReviewReason"] = item.get("reviewReason", "")
            candidates.append(selected)
    else:
        candidates = []
        for item in official.values():
            selected = dict(item)
            selected["selectedWorkingLayer"] = layer
            selected["selectedWorkingPath"] = item["workingPath"] if layer == "normalized-v2" else item["suppressedWorkingPath"]
            selected["selectedWorkingSha256"] = item["workingSha256"] if layer == "normalized-v2" else item["suppressedWorkingSha256"]
            selected["selectedWorkingStatus"] = "deterministic"
            selected["selectedWorkingOMRAllowed"] = layer == "normalized-v2"
            selected["selectedWorkingReviewReason"] = "Suppressed layer can erase or obscure watermark-crossing ink." if layer == "suppressed-v2" else ""
            candidates.append(selected)
    candidates.sort(key=lambda item: item.get("originalPath", ""))
    if requested:
        candidates = [item for item in candidates if any(requested_record_matches(item, value) for value in requested)]
        if not candidates:
            raise SystemExit(f"No official 2025 record matched --record {', '.join(requested)}")
    if layer == "working-2025":
        unsafe = [item for item in candidates if not item.get("selectedWorkingOMRAllowed", False)]
        if unsafe:
            labels = ", ".join(page_key(item) for item in unsafe)
            raise SystemExit(f"OMR refused: working-2025 contains unsafe AI-edited notation ({labels}). Use normalized-v2 for draft OMR and retain working-2025 for visual review only.")
    return candidates


def run_audiveris(command: list[str], log_path: Path, timeout_seconds: int = 180) -> tuple[int, bool]:
    """Run one bounded job and kill any child process group on timeout."""
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            return process.wait(timeout=timeout_seconds), False
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audiveris", type=Path, default=DEFAULT_AUDIVERIS)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--layer", choices=sorted(LAYERS), default="normalized-v2", help="explicit working image layer; working-2025 is fail-closed for AI-edited copies")
    parser.add_argument("--record", action="append", default=[], help="restrict to a song number or source stem; may be repeated")
    args = parser.parse_args()
    run_index = OMR_ROOT / f"cleaned-{args.layer}-run.json"
    if not args.audiveris.exists():
        raise SystemExit(f"Audiveris executable not found: {args.audiveris}")
    payload = load(MANIFEST)
    records = selected_records(payload, args.layer, args.record)
    if args.limit:
        records = records[: args.limit]
    prior: dict[str, dict[str, Any]] = {}
    if run_index.exists():
        try:
            prior = {
                item["originalPath"]: item
                for item in load(run_index).get("records", [])
                if item.get("originalPath")
            }
        except (OSError, json.JSONDecodeError):
            prior = {}
    retained_paths = canonical_source_paths()
    if retained_paths and args.layer != "working-2025":
        prior = {path: item for path, item in prior.items() if path in retained_paths}

    results = dict(prior)
    for record in records:
        original_path = record["originalPath"]
        key = page_key(record)
        output_dir = OMR_ROOT / f"cleaned-{args.layer}-{key}"
        output_dir.mkdir(parents=True, exist_ok=True)
        result: dict[str, Any] = {
            "originalPath": original_path,
            "originalSha256": record["originalSha256"],
            "selectedWorkingLayer": record["selectedWorkingLayer"],
            "selectedWorkingPath": record["selectedWorkingPath"],
            "selectedWorkingSha256": record["selectedWorkingSha256"],
            "selectedWorkingStatus": record["selectedWorkingStatus"],
            "selectedWorkingOMRAllowed": record["selectedWorkingOMRAllowed"],
            "selectedWorkingReviewReason": record["selectedWorkingReviewReason"],
            "normalizedWorkingPath": record["workingPath"],
            "normalizedWorkingSha256": record["workingSha256"],
            "suppressedWorkingPath": record["suppressedWorkingPath"],
            "outputDirectory": str(output_dir.relative_to(ROOT)),
            "status": "pending",
            "reviewRequired": True,
            "watermarkAssessment": record["watermarkAssessment"],
            "startedAt": datetime.now(timezone.utc).isoformat(),
        }
        existing = prior.get(original_path)
        existing_mxl = list(output_dir.glob("*.mxl"))
        prior_layer = existing.get("selectedWorkingLayer", "normalized-v2") if existing else None
        prior_sha = existing.get("selectedWorkingSha256", existing.get("normalizedWorkingSha256")) if existing else None
        if existing and prior_layer == args.layer and prior_sha == record["selectedWorkingSha256"] and existing_mxl:
            result = dict(existing)
            # Upgrade older run-ledger rows in place with the explicit image
            # selection fields, without rerunning an unchanged draft job.
            result.update({
                "selectedWorkingLayer": record["selectedWorkingLayer"],
                "selectedWorkingPath": record["selectedWorkingPath"],
                "selectedWorkingSha256": record["selectedWorkingSha256"],
                "selectedWorkingStatus": record["selectedWorkingStatus"],
                "selectedWorkingOMRAllowed": record["selectedWorkingOMRAllowed"],
                "selectedWorkingReviewReason": record["selectedWorkingReviewReason"],
                "normalizedWorkingPath": record["workingPath"],
                "normalizedWorkingSha256": record["workingSha256"],
                "suppressedWorkingPath": record["suppressedWorkingPath"],
            })
            result["status"] = "draft-reused"
            results[original_path] = result
            continue
        log_path = output_dir / "audiveris.log"
        command = [
            str(args.audiveris),
            "-batch",
            "-transcribe",
            "-export",
            "-output",
            str(output_dir),
            str(ROOT / record["selectedWorkingPath"]),
        ]
        try:
            exit_code, timed_out = run_audiveris(command, log_path)
            artifacts = sorted(path for path in output_dir.glob("*.mxl") if path.is_file())
            result["exitCode"] = exit_code
            result["timedOutAfterExport"] = timed_out and bool(artifacts)
            result["draftArtifacts"] = [str(path.relative_to(ROOT)) for path in artifacts]
            result["log"] = str(log_path.relative_to(ROOT))
            result["status"] = "draft-created-after-timeout" if timed_out and artifacts else "draft-created" if artifacts else "failed"
            if not artifacts:
                # A cleaned-input retry is supplementary. Preserve an existing
                # canonical review draft when Audiveris itself fails, while
                # keeping the engine failure visible and non-promotable.
                fallback = existing_review_draft(key)
                if fallback is not None and fallback.is_file():
                    result["status"] = "failed-existing-draft"
                    result["fallbackDraft"] = str(fallback.relative_to(ROOT))
                    result["fallbackDraftSha256"] = sha256(fallback)
                    result["failureReason"] = "Audiveris failed on the selected cleaned image; an existing canonical review draft remains available."
        except (OSError, subprocess.SubprocessError) as exc:
            result["status"] = "failed"
            result["error"] = str(exc)
        result["finishedAt"] = datetime.now(timezone.utc).isoformat()
        results[original_path] = result
        print(f"{result['status']}: {original_path}", flush=True)

    all_results = [results[key] for key in sorted(results)]
    run_index.write_text(
        json.dumps(
            {
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "policy": "Audiveris output from selected working images is draft-only and requires source comparison; no corpus promotion is performed.",
                "selectedWorkingLayer": args.layer,
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
    print(f"Wrote {run_index} with {len(all_results)} records.")
    return 0 if not any(item.get("status") == "failed" for item in all_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
