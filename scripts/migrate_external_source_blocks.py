#!/usr/bin/env python3
"""Convert exhausted source-audit blockers to explicit external-source blocks.

This migration never changes notation or source witnesses. It only replaces the
ambiguous internal ``autonomously-blocked`` label on existing 2025 comparison
records with an explicit external-source disposition while preserving every
existing reason, path, and checksum field.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPARISON_ROOT = ROOT / "work" / "source-transcriptions" / "2025"
RECEIPT = COMPARISON_ROOT / "batches" / "2026-08-29-external-source-block-migration.json"


def migrate_reason(value: str) -> str:
    text = str(value or "")
    if text.startswith("Autonomous promotion is blocked"):
        return "External-source block" + text[len("Autonomous promotion is blocked") :]
    if text.startswith("Blocked autonomously"):
        return "External-source block" + text[len("Blocked autonomously") :]
    return text or "External-source block: no authorized exact structured witness is available."


def migrate_next_action(value: str) -> str:
    text = str(value or "")
    text = text.replace("autonomous-promotion-blocked", "external-source-blocked")
    text = text.replace("requires-authorized-exact-2025-musicxml", "requires-authorized-exact-2025-structured-source")
    return text or "external-source-blocked; retain-immutable-source-and-evidence"


def main() -> int:
    changed_files: list[str] = []
    changed_ids: set[str] = set()
    for path in sorted(COMPARISON_ROOT.glob("*-comparison.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not str(payload.get("queueId", "")).startswith("sh2025/"):
            continue
        if payload.get("comparisonStatus") != "autonomously-blocked":
            continue
        queue_id = str(payload["queueId"])
        original_reason = payload.get("blockingReason") or payload.get("reason") or payload.get("nextAction") or ""
        payload["originalComparisonStatus"] = "autonomously-blocked"
        payload["comparisonStatus"] = "external-source-blocked"
        payload["autonomousDecision"] = "external-source-blocked"
        payload["blockingReason"] = migrate_reason(original_reason)
        payload["nextAction"] = migrate_next_action(payload.get("nextAction", ""))
        payload["autonomousDisposition"] = (
            "External-source blocked; exact 2025 structured evidence is unavailable or obscured, "
            "so the retained draft is not promoted."
        )
        payload["externalSourceBlock"] = {
            "state": "external-source-blocked",
            "safeToPromote": False,
            "humanReviewRequired": False,
            "sourceEvidenceRetained": True,
            "reason": payload["blockingReason"],
        }
        if isinstance(payload.get("disposition"), dict):
            disposition = payload["disposition"]
            disposition["state"] = "external-source-blocked"
            disposition["role"] = "source-comparison-external-block"
            disposition["autonomousDecision"] = "external-source-blocked"
            disposition["reason"] = payload["blockingReason"]
            disposition["humanReviewRequired"] = False
            disposition["reviewAvailable"] = True
            disposition["safeToPromote"] = False
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        changed_files.append(str(path.relative_to(ROOT)))
        changed_ids.add(queue_id)

    receipt = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "policy": "Exhausted unresolved source comparisons use external-source-blocked; source-mismatch-rejected remains reserved for explicit mismatches. No notation or source witness is changed or promoted.",
        "changedComparisonFiles": len(changed_files),
        "changedRecordIds": sorted(changed_ids),
        "changedRecordCount": len(changed_ids),
        "files": changed_files,
        "safeToPromote": 0,
        "verified": 0,
        "promoted": 0,
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("changedComparisonFiles", "changedRecordCount", "safeToPromote", "verified", "promoted")}, sort_keys=True))
    print("changedRecordIds=" + ",".join(receipt["changedRecordIds"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
