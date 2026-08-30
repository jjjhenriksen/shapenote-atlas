#!/usr/bin/env python3
"""Run the Sacred Harp verification suite and emit a fail-closed receipt.

This orchestrator never edits source data. It may write receipts under
``work/verification`` (or a caller-provided output path) so a run is
auditable without changing the generated bundle.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
WORK = ROOT / "work" / "verification"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def git_context() -> dict[str, Any]:
    """Capture checkout identity without changing the worktree."""
    context: dict[str, Any] = {
        "root": str(ROOT),
        "head": "unknown",
        "dirty": None,
        "statusEntryCount": None,
    }
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        if head.returncode == 0 and head.stdout.strip():
            context["head"] = head.stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        if status.returncode == 0:
            entries = status.stdout.splitlines()
            context["dirty"] = bool(entries)
            context["statusEntryCount"] = len(entries)
    except (OSError, subprocess.TimeoutExpired):
        context["error"] = "git context unavailable"
    return context


def result(name: str, status: str, *, detail: str = "", **extra: Any) -> dict[str, Any]:
    item = {"name": name, "status": status, "detail": detail}
    item.update(extra)
    return item


def run_command(name: str, command: list[str], *, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return result(
            name,
            "failed",
            detail=f"timed out after {timeout}s",
            command=command,
            durationSeconds=round(time.monotonic() - started, 3),
            stdout=(exc.stdout or "")[-4000:],
            stderr=(exc.stderr or "")[-4000:],
        )
    except OSError as exc:
        return result(
            name,
            "failed",
            detail=f"could not start command: {exc}",
            command=command,
            durationSeconds=round(time.monotonic() - started, 3),
        )
    status = "passed" if completed.returncode == 0 else "failed"
    return result(
        name,
        status,
        detail=f"exit code {completed.returncode}",
        command=command,
        exitCode=completed.returncode,
        durationSeconds=round(time.monotonic() - started, 3),
        stdout=completed.stdout[-4000:],
        stderr=completed.stderr[-4000:],
    )


def check_generated_artifacts() -> dict[str, Any]:
    required = [
        "corpus.json",
        "source-coverage.json",
        "transcription-queue.json",
        "human-review-queue.json",
        "source-comparison-ledger.json",
    ]
    if (ROOT / "scripts" / "check_source_health.py").exists():
        required.append("source-health.json")
    missing = [name for name in required if not (PUBLIC / name).exists()]
    malformed: list[str] = []
    sizes: dict[str, int] = {}
    for name in required:
        path = PUBLIC / name
        if not path.exists():
            continue
        sizes[name] = path.stat().st_size
        try:
            load_json(path)
        except (OSError, json.JSONDecodeError):
            malformed.append(name)
    if missing or malformed:
        return result(
            "generated-artifacts",
            "failed",
            detail="required generated artifacts are missing or malformed",
            missing=missing,
            malformed=malformed,
            sizes=sizes,
        )
    return result("generated-artifacts", "passed", detail="required JSON artifacts load", sizes=sizes)


def check_stale_generated_data() -> dict[str, Any]:
    generated = PUBLIC / "corpus.json"
    generator = ROOT / "scripts" / "build_data.py"
    source_paths = [
        Path("/Users/jacquelinehenriksen/sh-corpus-scripts/dashboard/data.js"),
        Path("/Users/jacquelinehenriksen/sh-corpus-scripts/rag_web_metadata.csv"),
        Path("/Users/jacquelinehenriksen/sh-corpus-scripts/changed_across_editions.csv"),
    ]
    if not generated.exists():
        return result("stale-generated-data", "failed", detail="public/corpus.json is missing")
    existing = [path for path in source_paths if path.exists()]
    newer = [str(path) for path in existing if path.stat().st_mtime > generated.stat().st_mtime]
    if newer:
        return result(
            "stale-generated-data",
            "failed",
            detail="source inputs are newer than public/corpus.json",
            newerSources=newer,
        )
    return result(
        "stale-generated-data",
        "passed",
        detail="known corpus source inputs are not newer than generated corpus",
        generator=str(generator) if generator.exists() else None,
        checkedSourceInputs=[str(path) for path in existing],
    )


def check_unsafe_mode_defaults() -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    pattern = re.compile(r"\bmode\s*=.*\bor\s+[\"']major[\"']")
    for path in sorted((ROOT / "scripts").rglob("*.py")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, 1):
            if pattern.search(line):
                hits.append({"path": str(path.relative_to(ROOT)), "line": line_number, "text": line.strip()})
    if hits:
        return result(
            "unknown-mode-defaults",
            "failed",
            detail="missing MusicXML mode can still silently become major",
            matches=hits,
        )
    return result("unknown-mode-defaults", "passed", detail="no unsafe missing-mode major default found")


def walk_unsafe_promotions(value: Any, path: str = "$") -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if value.get("safeToPromote") is True:
            provenance = value.get("provenance") if isinstance(value.get("provenance"), dict) else {}
            context = " ".join(str(value.get(key, "")) for key in ("status", "kind", "label", "comparisonStatus"))
            if provenance.get("reviewRequired") is True or any(
                token in context.lower() for token in ("draft", "review", "omr", "imagegen", "candidate")
            ):
                found.append({"path": path, "context": context, "provenance": provenance})
        for key, child in value.items():
            found.extend(walk_unsafe_promotions(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(walk_unsafe_promotions(child, f"{path}[{index}]"))
    return found


def check_promotion_gate() -> dict[str, Any]:
    files = sorted(PUBLIC.rglob("*.json"))
    unsafe: list[dict[str, Any]] = []
    for path in files:
        try:
            unsafe.extend({"file": str(path.relative_to(ROOT)), **item} for item in walk_unsafe_promotions(load_json(path)))
        except (OSError, json.JSONDecodeError):
            continue
    if unsafe:
        return result(
            "promotion-gate",
            "failed",
            detail="review-only or candidate material is marked safeToPromote",
            unsafePromotions=unsafe[:100],
            unsafePromotionCount=len(unsafe),
        )
    return result("promotion-gate", "passed", detail="no unsafe promotion markers found")


def check_queue_contradictions() -> dict[str, Any]:
    queue_path = PUBLIC / "human-review-queue.json"
    reconciliation_path = PUBLIC / "sacred-harp-2025-autonomous-reconciliation.json"
    if not queue_path.exists() or not reconciliation_path.exists():
        return result("queue-contradictions", "failed", detail="canonical queue or reconciliation artifact is missing")
    queue = load_json(queue_path)
    reconciliation = load_json(reconciliation_path)
    queue_by_id: dict[str, set[str]] = {}
    review_required_by_id: dict[str, set[bool]] = {}
    invalid_review_now: list[dict[str, Any]] = []
    allowed_states = {
        "needs-human-review",
        "external-source-blocked",
        "autonomously-blocked",
        "verified-with-correction-needed",
        "rejected-source-mismatch",
        "alternate-key-witness-not-promoted",
        "review-only",
        "rejected",
    }
    for item in queue.get("reviewNow", []):
        queue_id = str(item.get("queueId", ""))
        disposition = item.get("disposition") if isinstance(item.get("disposition"), dict) else {}
        state = str(disposition.get("state") or item.get("autonomousDisposition") or item.get("status") or "")
        if queue_id:
            queue_by_id.setdefault(queue_id, set()).add(str(item.get("status", "")))
            review_required_by_id.setdefault(queue_id, set()).add(bool(item.get("humanReviewRequired")))
        if state not in allowed_states or item.get("safeToPromote") is not False:
            invalid_review_now.append(
                {
                    "queueId": queue_id,
                    "status": item.get("status"),
                    "dispositionState": state,
                    "safeToPromote": item.get("safeToPromote"),
                }
            )
    contradictions: list[dict[str, Any]] = []
    for item in reconciliation.get("records", []):
        queue_id = str(item.get("queueId", ""))
        statuses = queue_by_id.get(queue_id, set())
        review_required = review_required_by_id.get(queue_id, set())
        if item.get("humanReviewRequired") is False and True in review_required:
            contradictions.append(
                {
                    "queueId": queue_id,
                    "outcome": item.get("outcome"),
                    "humanReviewRequired": item.get("humanReviewRequired"),
                    "queueStatuses": sorted(statuses),
                    "queueHumanReviewRequired": sorted(review_required),
                }
            )
    if contradictions or invalid_review_now:
        return result(
            "queue-contradictions",
            "failed",
            detail="queue sections, statuses, and autonomous dispositions disagree",
            contradictionCount=len(contradictions),
            samples=contradictions[:20],
            invalidReviewNowCount=len(invalid_review_now),
            invalidReviewNowSamples=invalid_review_now[:20],
        )
    return result("queue-contradictions", "passed", detail="covered queue states agree")


def discover_optional_command(kind: str) -> list[str] | None:
    candidates = {
        "source-health": [
            ROOT / "scripts" / "verify_source_health.py",
            ROOT / "scripts" / "source_health.py",
            ROOT / "scripts" / "check_source_health.py",
        ],
        "browser-smoke": [
            ROOT / "scripts" / "verify_browser_smoke.py",
            ROOT / "scripts" / "browser_smoke.py",
            ROOT / "scripts" / "smoke_browser.py",
        ],
    }
    for path in candidates[kind]:
        if path.exists():
            return [sys.executable, str(path)]
    return None


def source_health_checks(args: argparse.Namespace) -> list[dict[str, Any]]:
    collector = ROOT / "scripts" / "check_source_health.py"
    validator = ROOT / "scripts" / "validate_source_health.py"
    if not collector.exists() or not validator.exists():
        return [
            result(
                "source-health",
                "not-available",
                detail="source-health worker scripts are not present in this checkout",
                required=not args.allow_missing_optional,
            )
        ]

    if args.no_write:
        checks = [
            result(
                "source-health-collection",
                "not-run",
                detail="skipped in --no-write mode; existing report will be validated",
                required=True,
            )
        ]
    else:
        if args.source_health_online and args.source_health_max_urls <= 0:
            return [
                result(
                    "source-health-collection",
                    "failed",
                    detail="online source-health mode requires --source-health-max-urls > 0",
                    required=True,
                    networkMode="online",
                    maxUrls=args.source_health_max_urls,
                )
            ]
        command = [sys.executable, str(collector)]
        if args.source_health_online:
            command.extend(
                [
                    "--max-urls",
                    str(args.source_health_max_urls),
                    "--timeout",
                    str(args.source_health_request_timeout),
                    "--workers",
                    str(args.source_health_workers),
                ]
            )
            mode = "online-bounded"
            detail = f"online source-health check capped at {args.source_health_max_urls} URLs"
        else:
            command.append("--offline")
            mode = "offline"
            detail = "offline source-health check; no network requests"
        checks = [run_command("source-health-collection", command, timeout=args.timeout)]
        checks[0]["networkMode"] = mode
        checks[0]["detail"] = detail if checks[0]["status"] == "passed" else checks[0]["detail"]

    validation = run_command("source-health-validation", [sys.executable, str(validator)], timeout=args.timeout)
    validation["networkMode"] = "offline-report-validation"
    checks.append(validation)
    return checks


def write_receipts(receipt: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Sacred Harp verification receipt",
        "",
        f"- Generated: `{receipt['generatedAt']}`",
        f"- Overall: **{receipt['overallStatus']}**",
        f"- Complete: **{str(receipt['complete']).lower()}**",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for item in receipt["checks"]:
        detail = str(item.get("detail", "")).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{item['name']}` | **{item['status']}** | {detail} |")
    lines.extend(["", "## Remaining blockers", ""])
    blockers = receipt.get("blockers", [])
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- None")
    lines.extend(["", "## Optional limitations", ""])
    limitations = receipt.get("limitations", [])
    if limitations:
        lines.extend(f"- {limitation}" for limitation in limitations)
    else:
        lines.append("- None")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=180, help="Timeout per subprocess check in seconds")
    parser.add_argument("--startup-timeout", type=float, default=12.0, help="Timeout for the owned local startup smoke test")
    parser.add_argument("--no-build", action="store_true", help="Do not run the production build")
    parser.add_argument("--allow-missing-optional", action="store_true", help="Do not fail solely because source-health/browser-smoke workers are absent")
    parser.add_argument("--source-health-online", action="store_true", help="Opt into remote source-health checks; requires a positive --source-health-max-urls")
    parser.add_argument("--source-health-max-urls", type=int, default=0, help="Hard cap for opt-in online source-health requests")
    parser.add_argument("--source-health-request-timeout", type=float, default=8.0, help="Per-request timeout for opt-in online source-health checks")
    parser.add_argument("--source-health-workers", type=int, default=4, help="Concurrent workers for opt-in online source-health checks")
    parser.add_argument("--no-write", action="store_true", help="Print the receipt without writing receipt files")
    parser.add_argument("--json-out", type=Path, default=WORK / "verification-receipt.json")
    parser.add_argument("--markdown-out", type=Path, default=WORK / "verification-receipt.md")
    args = parser.parse_args()

    checks: list[dict[str, Any]] = [
        check_generated_artifacts(),
        check_stale_generated_data(),
        check_unsafe_mode_defaults(),
        check_promotion_gate(),
        check_queue_contradictions(),
    ]
    commands = [
        ("data", [sys.executable, "scripts/validate_data.py"]),
        ("playback", [sys.executable, "scripts/validate_playback.py"]),
        ("transposition", [sys.executable, "scripts/validate_transposition.py"]),
        ("shape-review", [sys.executable, "scripts/validate_shape_review_drafts.py"]),
        ("source-shape-review", [sys.executable, "scripts/validate_source_shape_review_drafts.py"]),
        ("transcription-images", [sys.executable, "scripts/validate_transcription_images.py"]),
        ("image-review-queue", [sys.executable, "scripts/validate_image_review_queue.py"]),
        ("source-candidates", [sys.executable, "scripts/validate_source_candidates.py"]),
        ("omr-audit", [sys.executable, "scripts/audit_omr_drafts.py"]),
    ]
    for name, command in commands:
        checks.append(run_command(name, command, timeout=args.timeout))

    checks.extend(source_health_checks(args))

    for name in ("browser-smoke",):
        command = discover_optional_command(name)
        if command:
            checks.append(run_command(name, command, timeout=args.timeout))
        else:
            checks.append(
                result(
                    name,
                    "not-available",
                    detail="no worker-provided check exists in this checkout",
                    required=not args.allow_missing_optional,
                )
            )

    if args.no_build:
        checks.append(result("build", "not-run", detail="skipped by --no-build", required=True))
    else:
        checks.append(run_command("build", ["npm", "run", "build"], timeout=args.timeout))
    startup_script = ROOT / "scripts" / "verify_startup.py"
    if startup_script.exists():
        checks.append(
            run_command(
                "startup-smoke",
                [sys.executable, str(startup_script), "--timeout", str(args.startup_timeout)],
                timeout=args.timeout,
            )
        )
    else:
        checks.append(result("startup-smoke", "not-available", detail="startup smoke script is not present", required=True))

    blockers: list[str] = []
    limitations: list[str] = []
    for item in checks:
        if item["status"] in {"failed", "not-available", "not-run"}:
            message = f"{item['name']}: {item['detail']}"
            if item.get("required", True):
                blockers.append(message)
            else:
                limitations.append(message)
    receipt = {
        "schemaVersion": 1,
        "generatedAt": now_iso(),
        "projectRoot": str(ROOT),
        "python": sys.version.split()[0],
        "pid": os.getpid(),
        "git": git_context(),
        "overallStatus": "passed" if not blockers else "blocked",
        "complete": not blockers,
        "checks": checks,
        "blockers": blockers,
        "limitations": limitations,
        "policy": {
            "failClosed": True,
            "immutableSourcesPreserved": True,
            "unsafePromotionRejected": True,
            "missingModeNeverDefaultsToMajor": True,
            "sourceHealthDefault": "offline",
            "onlineSourceHealthRequiresPositiveBudget": True,
        },
    }
    if not args.no_write:
        write_receipts(receipt, args.json_out, args.markdown_out)
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
