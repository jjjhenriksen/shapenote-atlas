#!/usr/bin/env python3
"""Write an isolated receipt for the 449/520 source-correction batch."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "work/agent-03-semantic/449-520-receipt.json"

RECORDS = {
    "sh2025/449": {
        "audit": ROOT / "work/source-transcriptions/2025/449-source-shape-autonomous-blocked-comparison.json",
        "draft": ROOT / "work/omr/autonomous-transcriptions/2025/449-lovely-social-band-source-correction.mxl",
    },
    "sh2025/520": {
        "audit": ROOT / "work/source-transcriptions/2025/520-source-shape-autonomous-blocked-comparison.json",
        "draft": ROOT / "work/omr/autonomous-transcriptions/2025/520-ata-source-correction.mxl",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_receipt() -> dict[str, object]:
    records: list[dict[str, object]] = []
    for queue_id, paths in RECORDS.items():
        audit = json.loads(paths["audit"].read_text(encoding="utf-8"))
        source = audit["sourceAuthority"]
        draft = audit["correctedDraft"]
        records.append(
            {
                "queueId": queue_id,
                "status": audit["comparisonStatus"],
                "safeToPromote": audit["safeToPromote"],
                "sourceImagePath": source["sourceImagePath"],
                "sourceImageSha256": source["sourceImageSha256"],
                "inputOmrPath": audit["inputOmr"]["path"],
                "inputOmrSha256": audit["inputOmr"]["sha256"],
                "draftPath": draft["path"],
                "draftSha256": draft["sha256"],
                "blockingReason": audit["blockingReason"],
                "draftFileSha256Verified": sha256(paths["draft"]) == draft["sha256"],
                "auditFileSha256": sha256(paths["audit"]),
            }
        )
    return {
        "kind": "agent-03-449-520-source-correction-receipt",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "scope": sorted(RECORDS),
        "records": records,
        "allRecordsBlocked": all(item["status"] == "autonomously-blocked" for item in records),
        "sharedLedgersRewritten": False,
        "otherRecordsTouched": False,
        "uiTouched": False,
        "committed": False,
        "pushed": False,
        "validation": {
            "focusedSourceCorrectionTests": "passed",
            "semanticParserTests": "passed",
            "playbackValidation": "passed",
            "transpositionValidation": "passed",
            "gitDiffCheck": "passed",
            "aggregateDataValidation": "blocked-by-unrelated-sh2025/118-noncanonical-disposition",
        },
        "policy": "Immutable retained source images remain authoritative; OMR derivatives are review-only and no alternate witness fills unsupported notation.",
    }


def main() -> int:
    receipt = build_receipt()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": str(OUTPUT.relative_to(ROOT)), "scope": receipt["scope"], "allRecordsBlocked": receipt["allRecordsBlocked"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
