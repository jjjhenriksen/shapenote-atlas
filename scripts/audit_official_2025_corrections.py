#!/usr/bin/env python3
"""Reconcile the bounded audit state for the 13 official SH25 corrections.

These records already have direct source comparisons and corrected derivatives.
This pass does not promote them: it makes the existing autonomous blocker
explicit and preserves the source-comparison/corpus separation.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "sh2025/41": ("41-official-scan-correction-comparison.json", "Evening Hymn"),
    "sh2025/50t": ("50t-devotion-autonomous-comparison.json", "Devotion"),
    "sh2025/55": ("55-converse-autonomous-comparison.json", "Converse"),
    "sh2025/118": ("118-official-scan-correction-comparison.json", "Heavenly Meeting"),
    "sh2025/169": ("169-official-scan-correction-comparison.json", "God’s Helping Hand"),
    "sh2025/415": ("415-endless-praise-autonomous-comparison.json", "Endless Praise"),
    "sh2025/525": ("525-official-scan-correction-comparison.json", "Imandra"),
    "sh2025/537": ("537-official-scan-correction-comparison.json", "Portsmouth"),
    "sh2025/544": ("544-official-scan-correction-comparison.json", "Youthful Blessings"),
    "sh2025/545": ("545-official-scan-correction-comparison.json", "Somers"),
    "sh2025/557": ("557-official-scan-correction-comparison.json", "New Farewell"),
    "sh2025/563": ("563-official-scan-correction-comparison.json", "Suffield"),
    "sh2025/575": ("575-official-scan-correction-comparison.json", "Lisbon"),
}


def main() -> int:
    changed = []
    for queue_id, (filename, title) in TARGETS.items():
        path = ROOT / "work/source-transcriptions/2025" / filename
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("queueId") != queue_id:
            raise SystemExit(f"{filename}: queueId mismatch")
        draft = payload.get("correctedDraft") or {}
        summary = draft.get("summary") or {}
        if payload.get("safeToPromote") is not False or payload.get("humanReviewRequired") is not False:
            raise SystemExit(f"{queue_id}: promotion/handoff gate is not already fail-closed")
        if summary.get("lyricsEncoded") is not False:
            raise SystemExit(f"{queue_id}: expected lyricsEncoded=false")
        payload["autonomousDecision"] = "blocked"
        payload["blockingReason"] = (
            f"Autonomous promotion of {title} is blocked: the direct source comparison preserves the audited "
            f"event stream and structural counts ({summary.get('parts')} parts, {summary.get('pitchedEvents')} pitched events) "
            "and the corrected derivative has complete four-shape tags, but lyrics are intentionally unencoded because "
            "direct syllable alignment is not established. The authoritative source and corrected derivative remain "
            "separate; no notes or lyrics are fabricated and no human handoff is required."
        )
        payload["nextAction"] = "autonomous-promotion-blocked-by-unencoded-lyrics; retain-corrected-derivative; no-corpus-promotion"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        changed.append(queue_id)
    print(json.dumps({"records": len(changed), "changed": changed, "promoted": [], "safeToPromote": 0}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
