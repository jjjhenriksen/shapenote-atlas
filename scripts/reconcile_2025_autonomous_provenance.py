#!/usr/bin/env python3
"""Reconcile the current SH25 missing-score population with autonomous outcomes.

This is intentionally a companion artifact, not a rewrite of the historical
autonomous-transcriptions/2025/manifest.json. That manifest records the scope
of its original 16-record run; this report joins the current corpus population
to the already-produced ledger, queue, and per-record audit evidence.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from review_dispositions import aggregate_comparison_disposition, comparison_disposition


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public/corpus.json"
LEDGER = ROOT / "public/source-comparison-ledger.json"
QUEUE = ROOT / "public/human-review-queue.json"
HISTORICAL_MANIFEST = ROOT / "work/omr/autonomous-transcriptions/2025/manifest.json"
AUDIT_ROOT = ROOT / "work/source-transcriptions/2025"
OUTPUT = ROOT / "public/sacred-harp-2025-autonomous-reconciliation.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def current_missing(corpus: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for song in corpus.get("songs", []):
        if "sh2025" not in song.get("books", []):
            continue
        if song.get("scoreByBook", {}).get("sh2025"):
            continue
        if song.get("referenceScoreByBook", {}).get("sh2025"):
            continue
        song_no = str(song.get("songNo", "")).lower()
        result.append(
            {
                "queueId": f"sh2025/{song_no}",
                "songNo": song_no,
                "title": song.get("titlesByBook", {}).get("sh2025", song.get("title", "")),
            }
        )
    return sorted(result, key=lambda item: (int("".join(c for c in item["songNo"] if c.isdigit()) or 0), item["songNo"]))


def audit_ids(path: Path, payload: dict[str, Any]) -> list[str]:
    ids = []
    for key in ("queueId", "record", "songNo"):
        value = payload.get(key)
        if value:
            text = str(value).lower()
            ids.append(text if text.startswith("sh2025/") else f"sh2025/{text}")
    for key in ("sourceAuthority", "sourceMetadata"):
        nested = payload.get(key)
        if isinstance(nested, dict) and nested.get("queueId"):
            ids.append(str(nested["queueId"]).lower())
    return unique(ids)


def reasons(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("blockingReason", "nextAction"):
        if isinstance(row.get(key), str):
            values.append(row[key])
    observations = row.get("visualObservations")
    if isinstance(observations, dict) and isinstance(observations.get("blocker"), str):
        values.append(observations["blocker"])
    evidence = row.get("comparisonEvidence")
    if isinstance(evidence, dict):
        findings = evidence.get("blockingFindings", [])
        if isinstance(findings, list):
            values.extend(str(item) for item in findings if item)
    disposition = row.get("promotionDisposition")
    if isinstance(disposition, dict):
        for key in ("reason", "blockingReason", "nextAction"):
            if isinstance(disposition.get(key), str):
                values.append(disposition[key])
    return unique(values) or [
        "No direct source-verified exact structured notation is recorded; authoritative promotion remains blocked."
    ]


def aggregate_disposition(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Collapse duplicate evidence rows without collapsing their provenance."""
    return aggregate_comparison_disposition(rows)


def main() -> int:
    corpus = load(CORPUS)
    ledger = load(LEDGER)
    queue = load(QUEUE)
    historical_manifest = load(HISTORICAL_MANIFEST)

    source_paths = [LEDGER, QUEUE, HISTORICAL_MANIFEST]
    ledger_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ledger.get("records", []):
        queue_id = str(row.get("queueId", "")).lower()
        if queue_id.startswith("sh2025/"):
            ledger_by_id[queue_id].append(row)

    queue_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for section in ("reviewNow", "autonomouslyVerified", "correctionNeeded", "remaining2025Backlog"):
        for row in queue.get(section, []):
            queue_id = str(row.get("queueId", "")).lower()
            if queue_id:
                queue_by_id[queue_id].append({"section": section, "row": row})

    audits_by_id: dict[str, list[str]] = defaultdict(list)
    for path in sorted(AUDIT_ROOT.glob("*.json")):
        payload = load(path)
        for queue_id in audit_ids(path, payload):
            audits_by_id[queue_id].append(rel(path))

    historical_ids = {
        str(row.get("queueId", "")).lower()
        for row in historical_manifest.get("records", [])
        if row.get("queueId")
    }
    records = []
    for current in current_missing(corpus):
        queue_id = current["queueId"]
        rows = ledger_by_id.get(queue_id, [])
        disposition = aggregate_disposition(rows)
        decisions = unique([str(row.get("autonomousDecision", "")) for row in rows])
        statuses = unique([str(row.get("comparisonStatus", "")) for row in rows])
        safe = any(row.get("safeToPromote") is True for row in rows)
        verified = any(row.get("autonomousDecision") == "verified" and row.get("humanReviewRequired") is False for row in rows)
        if verified and safe:
            outcome = "autonomously-verified"
        elif disposition["state"] == "rejected":
            outcome = "source-mismatch-rejected"
        elif disposition["state"] == "external-source-blocked":
            outcome = "externally-blocked"
        else:
            outcome = "autonomously-blocked"
        evidence = []
        for row in rows:
            evidence.append(
                {
                    "auditFile": row.get("auditFile", ""),
                    "comparisonStatus": row.get("comparisonStatus", ""),
                    "autonomousDecision": row.get("autonomousDecision", ""),
                    "safeToPromote": row.get("safeToPromote", False),
                    "humanReviewRequired": row.get("humanReviewRequired", None),
                    "disposition": comparison_disposition(row),
                    "reasons": reasons(row),
                }
            )
        records.append(
            {
                **current,
                "outcome": outcome,
                "canonicalRecordId": queue_id,
                "disposition": disposition,
                "safeToPromote": safe,
                "humanReviewRequired": disposition["humanReviewRequired"],
                "reviewAvailable": disposition["reviewAvailable"],
                "historicalManifestRecord": queue_id in historical_ids,
                "ledgerRecordCount": len(rows),
                "ledgerStatuses": statuses,
                "ledgerAutonomousDecisions": decisions,
                "queueSections": unique([item["section"] for item in queue_by_id.get(queue_id, [])]),
                "queueStatus": unique([item["row"].get("status", "") for item in queue_by_id.get(queue_id, [])]),
                "perRecordAuditFiles": unique(audits_by_id.get(queue_id, [])),
                "evidence": evidence,
            }
        )

    outcome_counts = Counter(item["outcome"] for item in records)
    missing_disposition = [item["queueId"] for item in records if not item["ledgerRecordCount"] or not item["perRecordAuditFiles"]]
    payload = {
        "generatedAt": corpus.get("generatedAt"),
        "kind": "sacred-harp-2025-autonomous-provenance-reconciliation",
        "version": 1,
        "authority": {
            "population": "current public/corpus.json songs in sh2025 with neither scoreByBook.sh2025 nor referenceScoreByBook.sh2025",
            "outcomeAuthority": "public/source-comparison-ledger.json plus traceable per-record audits",
            "historicalManifestPolicy": "The original autonomous manifest remains unchanged as a historical 16-record batch; this companion reconciles the current corpus population without rewriting its provenance.",
            "queueDisplayNote": "reviewNow is an optional evidence-review surface. humanReviewRequired is the authoritative required-action gate; external-source-blocked, autonomously-blocked, and rejected records are not human-transcription handoffs.",
        },
        "inputs": [
            {"path": rel(path), "sha256": sha256(path)}
            for path in source_paths
        ],
        "summary": {
            "current2025MissingStructuredScore": len(records),
            "autonomousOutcomes": dict(sorted(outcome_counts.items())),
            "safeToPromote": sum(item["safeToPromote"] for item in records),
            "humanReviewRequired": sum(item["humanReviewRequired"] for item in records),
            "reviewAvailable": sum(item["reviewAvailable"] for item in records),
            "dispositionCounts": dict(sorted(Counter(item["disposition"]["state"] for item in records).items())),
            "recordsWithLedgerEvidence": sum(bool(item["ledgerRecordCount"]) for item in records),
            "recordsWithPerRecordAuditEvidence": sum(bool(item["perRecordAuditFiles"]) for item in records),
            "recordsStillWithoutAutonomousDisposition": len(missing_disposition),
            "recordsOnlyInHistoricalManifest": len(historical_ids - {item["queueId"] for item in records}),
            "historicalManifestRecords": len(historical_manifest.get("records", [])),
            "currentLedgerRowsForPopulation": sum(item["ledgerRecordCount"] for item in records),
        },
        "records": records,
        "recordsStillWithoutAutonomousDisposition": missing_disposition,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {rel(OUTPUT)}: {len(records)} current records, {dict(sorted(outcome_counts.items()))}, missing dispositions={len(missing_disposition)}")
    print(f"Input hashes: {', '.join(f'{rel(path)}={sha256(path)}' for path in source_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
