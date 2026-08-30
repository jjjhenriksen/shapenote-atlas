#!/usr/bin/env python3
"""Materialize disposition fields without rebuilding corpus or notation data.

This narrow refresh is safe to run while broader corpus builders are owned by
another worker: it preserves every existing transcription-queue field and only
adds/replaces workflow metadata owned by the review-semantics backlog.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from review_dispositions import transcription_disposition


ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "public" / "transcription-queue.json"


def main() -> int:
    payload = json.loads(QUEUE.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    states: Counter[str] = Counter()
    for record in records:
        record["canonicalRecordId"] = record.get("queueId", "")
        disposition = transcription_disposition(record.get("status", ""), record.get("sourceUrls", []))
        record["disposition"] = disposition
        record["humanReviewRequired"] = False
        record["reviewAvailable"] = disposition["reviewAvailable"]
        record["safeToPromote"] = False
        states[disposition["state"]] += 1
    summary = payload.setdefault("summary", {})
    summary["dispositionCounts"] = dict(sorted(states.items()))
    summary["humanReviewRequired"] = sum(bool(item.get("humanReviewRequired")) for item in records)
    summary["reviewAvailable"] = sum(bool(item.get("reviewAvailable")) for item in records)
    summary["safeToPromote"] = 0
    QUEUE.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"records": len(records), **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
