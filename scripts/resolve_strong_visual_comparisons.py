#!/usr/bin/env python3
"""Close source comparisons that cannot support autonomous promotion.

The comparison records already contain the source/candidate observations and
blocking findings.  This pass makes the decision explicit under the current
autonomous workflow: a visually promising alternate witness is blocked, not
left in an open-ended human-review state.  No source, score, or observation
is changed.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPARISON_ROOT = ROOT / "work/source-transcriptions/2025"


def main() -> int:
    changed = []
    for path in sorted(COMPARISON_ROOT.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        status = payload.get("comparisonStatus")
        if status not in {
            "strong-visual-match-not-promoted",
            "rejected-source-mismatch",
            "alternate-key-witness-not-promoted",
            "alternate-edition-witness-not-promoted",
        }:
            continue
        findings = payload.get("blockingFindings") or []
        if not findings:
            raise SystemExit(f"{path}: strong visual record has no blocking findings")
        queue_id = str(payload.get("queueId") or f"sh2025/{payload.get('songNo', '')}")
        if status == "strong-visual-match-not-promoted":
            payload["comparisonStatus"] = "autonomously-blocked"
            payload["autonomousDecision"] = "blocked"
        else:
            payload["autonomousDecision"] = "rejected" if status == "rejected-source-mismatch" else "blocked"
        payload["safeToPromote"] = False
        payload["humanReviewRequired"] = False
        payload["autonomousDisposition"] = (
            "Alternate or incomplete witness retained as evidence only; the record is "
            "blocked because the available evidence cannot prove exact 2025 notes, "
            "rhythms, lyrics, mode, and four-shape identity without unsupported reconstruction."
        )
        payload["blockingReason"] = (
            "Autonomous promotion is blocked for "
            f"{queue_id}: "
            + " ".join(findings)
            + " No authorized exact-edition structured source is available to resolve these findings."
        )
        payload["nextAction"] = (
            "autonomous-rejection-source-mismatch; retain-source-and-candidate-evidence; "
            "requires-authorized-exact-2025-musicxml"
            if status == "rejected-source-mismatch"
            else "autonomous-promotion-blocked-by-unproven-alternate-witness; "
            "retain-source-and-candidate-evidence; requires-authorized-exact-2025-musicxml"
        )
        payload["policy"] = (
            "Autonomous verify-or-block policy: visual similarity or an OMR derivative "
            "cannot authorize 2025 promotion without direct note/event, source-key/mode, "
            "meter, and four-shape evidence. This record is explicitly blocked and remains "
            "separate from any alternate-edition witness."
        )
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        changed.append(queue_id)
    print(json.dumps({"changed": len(changed), "queueIds": changed}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
