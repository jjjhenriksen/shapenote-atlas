#!/usr/bin/env python3
"""Audit the Sacred Harp 2025 additions register and all related queues.

This is deliberately an identity/precedence audit, not a notation validator.
It explains which surfaces coexist for each 2025 record and fails closed on
unmapped additions, queue drift, unsafe review items, or unexplained duplicate
artifacts. It never edits notation or source-image assets.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
REPORT = PUBLIC / "2025-additions-queue-audit.json"
ALLOWED_REVIEW_STATUSES = {
    "needs-human-review",
    "autonomously-blocked",
    "external-source-blocked",
    "verified-with-correction-needed",
    "rejected-source-mismatch",
    "alternate-key-witness-not-promoted",
    # Canonical workflow states materialized by review_dispositions.py.
    "review-only",
    "rejected",
}


def read_json(name: str) -> dict[str, Any]:
    return json.loads((PUBLIC / name).read_text(encoding="utf-8"))


def queue_id(song_no: Any) -> str:
    return f"sh2025/{str(song_no or '').strip().lower()}"


def records_by_id(records: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = str(record.get("queueId", "")).strip().lower()
        if key:
            grouped[key].append(record)
    missing = [str(index) for index, record in enumerate(records) if not str(record.get("queueId", "")).strip()]
    return grouped, missing


def presence(song: dict[str, Any]) -> dict[str, Any]:
    coverage = song.get("sourceCoverageByBook", {}).get("sh2025", {})
    exact = bool(song.get("scoreByBook", {}).get("sh2025"))
    reference = bool(song.get("referenceScoreByBook", {}).get("sh2025"))
    draft = bool(song.get("draftScoreByBook", {}).get("sh2025"))
    observation = bool(coverage.get("sourceMetadataObservation"))
    candidates = bool(coverage.get("cleanSourceCandidates"))
    if exact:
        primary = "exact-structured-score"
    elif reference:
        primary = "alternate-reference-score"
    elif draft:
        primary = "review-only-draft"
    elif observation:
        primary = "source-observation-only"
    elif candidates:
        primary = "source-candidate-only"
    else:
        primary = coverage.get("status", "unclassified") or "unclassified"
    auxiliary = []
    if exact and draft:
        auxiliary.append("review-only-draft")
    if reference and draft:
        auxiliary.append("review-only-draft")
    if observation and primary != "source-observation-only":
        auxiliary.append("source-observation")
    if candidates and primary != "source-candidate-only":
        auxiliary.append("source-candidate")
    return {
        "primary": primary,
        "auxiliary": auxiliary,
        "exact": exact,
        "reference": reference,
        "draft": draft,
        "sourceObservation": observation,
        "sourceCandidates": candidates,
        "sourceCandidateCount": len(coverage.get("cleanSourceCandidates", [])),
        "coverageStatus": coverage.get("status", ""),
    }


def audit() -> tuple[dict[str, Any], list[str]]:
    corpus = read_json("corpus.json")
    additions = read_json("edition-2025-additions.json")
    transcription_queue = read_json("transcription-queue.json")
    human_review = read_json("human-review-queue.json")
    image_review = read_json("image-review-queue.json")
    ledger = read_json("source-comparison-ledger.json")

    errors: list[str] = []
    songs = [song for song in corpus.get("songs", []) if "sh2025" in song.get("books", [])]
    songs_by_id: dict[str, dict[str, Any]] = {}
    duplicate_song_ids: list[str] = []
    for song in songs:
        identifier = queue_id(song.get("songNo"))
        if identifier in songs_by_id:
            duplicate_song_ids.append(identifier)
        songs_by_id[identifier] = song
    if duplicate_song_ids:
        errors.append(f"2025 corpus has duplicate identities: {sorted(set(duplicate_song_ids))}")

    addition_values = [str(value).strip().lower() for value in additions.get("records", [])]
    addition_ids = {f"sh2025/{value}" for value in addition_values}
    if additions.get("edition") != "sh2025":
        errors.append("additions register has the wrong edition")
    if additions.get("count") != len(addition_values) or len(addition_ids) != len(addition_values):
        errors.append("additions register count or identity uniqueness is stale")
    missing_additions = sorted(addition_ids - set(songs_by_id))
    if missing_additions:
        errors.append(f"additions are absent from the 2025 corpus: {missing_additions}")

    addition_status_counts = Counter()
    for identifier, song in songs_by_id.items():
        is_addition = identifier in addition_ids
        coverage = song.get("sourceCoverageByBook", {}).get("sh2025", {})
        expected_status = "added-in-2025" if is_addition else "not-new-in-2025"
        actual_status = coverage.get("editionStatus")
        addition_status_counts[actual_status or "missing"] += 1
        if actual_status != expected_status:
            errors.append(f"{identifier}: editionStatus={actual_status!r}, expected {expected_status!r}")
        if not coverage.get("editionEvidenceUrl"):
            errors.append(f"{identifier}: missing edition evidence URL")

    queue_records = [
        record
        for record in transcription_queue.get("records", [])
        if str(record.get("queueId", "")).lower().startswith("sh2025/")
    ]
    queue_by_id, queue_missing_ids = records_by_id(queue_records)
    if queue_missing_ids:
        errors.append(f"2025 transcription queue has records without queueId: {queue_missing_ids}")
    duplicate_queue_ids = sorted(identifier for identifier, rows in queue_by_id.items() if len(rows) > 1)
    if duplicate_queue_ids:
        errors.append(f"2025 transcription queue has duplicate identities: {duplicate_queue_ids}")
    expected_queue_ids = {
        identifier
        for identifier, song in songs_by_id.items()
        if song.get("sourceCoverageByBook", {}).get("sh2025", {}).get("status") != "structured-score"
    }
    actual_queue_ids = set(queue_by_id)
    if actual_queue_ids != expected_queue_ids:
        errors.append(
            "2025 transcription queue coverage drift: "
            f"missing={sorted(expected_queue_ids - actual_queue_ids)}, "
            f"extra={sorted(actual_queue_ids - expected_queue_ids)}"
        )
    for identifier in sorted(expected_queue_ids):
        record = queue_by_id[identifier][0]
        song = songs_by_id.get(identifier, {})
        coverage = song.get("sourceCoverageByBook", {}).get("sh2025", {})
        if record.get("status") != coverage.get("status"):
            errors.append(f"{identifier}: queue status does not match corpus coverage status")
        if record.get("editionStatus") != coverage.get("editionStatus"):
            errors.append(f"{identifier}: queue edition status does not match corpus")
    structured_queue_ids = set(songs_by_id) - expected_queue_ids
    if structured_queue_ids & actual_queue_ids:
        errors.append("structured-score records leaked into the transcription queue")

    human_records = human_review.get("reviewNow", [])
    human_by_id, human_missing_ids = records_by_id(human_records)
    if human_missing_ids:
        errors.append(f"human review queue has records without queueId: {human_missing_ids}")
    human_ids = set(human_by_id)
    draft_ids = {
        identifier
        for identifier, song in songs_by_id.items()
        if song.get("draftScoreByBook", {}).get("sh2025")
    }
    if human_ids != draft_ids:
        errors.append(
            "human review queue does not exactly cover 2025 drafts: "
            f"missing={sorted(draft_ids - human_ids)}, extra={sorted(human_ids - draft_ids)}"
        )
    duplicate_human_explanations: dict[str, list[str]] = {}
    for identifier, rows in human_by_id.items():
        if identifier not in songs_by_id:
            errors.append(f"human review queue identity is absent from corpus: {identifier}")
        artifacts = [str(row.get("draftArtifact", "")) for row in rows]
        if len(rows) > 1:
            if len(set(artifacts)) != len(artifacts) or not all(artifacts):
                errors.append(f"human review duplicate is unexplained: {identifier}")
            else:
                duplicate_human_explanations[identifier] = artifacts
        for row in rows:
            if row.get("status") not in ALLOWED_REVIEW_STATUSES or row.get("safeToPromote") is not False:
                errors.append(f"human review item has an invalid or unsafe disposition: {identifier}")
            song = songs_by_id.get(identifier, {})
            expected_status = song.get("sourceCoverageByBook", {}).get("sh2025", {}).get("editionStatus")
            if row.get("editionStatus") != expected_status:
                errors.append(f"human review edition status drift: {identifier}")

    image_records = image_review.get("records", [])
    image_by_id, image_missing_ids = records_by_id(image_records)
    expected_image_ids = {
        identifier
        for identifier, song in songs_by_id.items()
        if not song.get("scoreByBook", {}).get("sh2025")
        and not song.get("referenceScoreByBook", {}).get("sh2025")
    }
    if image_missing_ids or set(image_by_id) != expected_image_ids or any(len(rows) != 1 for rows in image_by_id.values()):
        errors.append(
            "image review queue coverage drift: "
            f"missing={sorted(expected_image_ids - set(image_by_id))}, "
            f"extra={sorted(set(image_by_id) - expected_image_ids)}"
        )

    ledger_records = [
        record
        for record in ledger.get("records", [])
        if str(record.get("queueId", "")).lower().startswith("sh2025/")
    ]
    ledger_by_id, ledger_missing_ids = records_by_id(ledger_records)
    if ledger_missing_ids:
        errors.append(f"source comparison ledger has records without queueId: {ledger_missing_ids}")
    duplicate_ledger_explanations: dict[str, list[str]] = {}
    for identifier, rows in ledger_by_id.items():
        if identifier not in songs_by_id:
            errors.append(f"source comparison identity is absent from corpus: {identifier}")
        audit_files = [str(row.get("auditFile", "")) for row in rows]
        if len(rows) > 1:
            if len(set(audit_files)) != len(audit_files) or not all(audit_files):
                errors.append(f"source comparison duplicate is unexplained: {identifier}")
            else:
                duplicate_ledger_explanations[identifier] = audit_files
        for row in rows:
            if row.get("safeToPromote") is not False:
                errors.append(f"source comparison is not fail-closed: {identifier}")

    pattern_counts: Counter[str] = Counter()
    addition_pattern_counts: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    for identifier, song in sorted(songs_by_id.items()):
        state = presence(song)
        tags = "".join(
            tag
            for tag, enabled in (
                ("E", state["exact"]),
                ("R", state["reference"]),
                ("D", state["draft"]),
                ("I", state["sourceObservation"]),
                ("C", state["sourceCandidates"]),
            )
            if enabled
        ) or "-"
        pattern_counts[tags] += 1
        if identifier in addition_ids:
            addition_pattern_counts[tags] += 1
        state_counts[state["primary"]] += 1

    summary = {
        "corpus2025Records": len(songs_by_id),
        "additions": len(addition_ids),
        "transcriptionQueueRecords": len(queue_records),
        "structuredScoreRecordsExcludedFromTranscriptionQueue": len(structured_queue_ids),
        "draftRecords": len(draft_ids),
        "humanReviewRows": len(human_records),
        "humanReviewUniqueRecords": len(human_ids),
        "imageReviewRecords": len(image_records),
        "sourceComparisonRows": len(ledger_records),
        "sourceComparisonUniqueRecords": len(ledger_by_id),
        "errors": len(errors),
    }
    report = {
        "generatedAt": corpus.get("generatedAt", ""),
        "status": "valid" if not errors else "invalid",
        "edition": "sh2025",
        "sourceOfTruth": {
            "additions": "public/edition-2025-additions.json",
            "corpus": "public/corpus.json",
            "transcriptionQueue": "public/transcription-queue.json",
            "humanReviewQueue": "public/human-review-queue.json",
            "imageReviewQueue": "public/image-review-queue.json",
            "sourceComparisonLedger": "public/source-comparison-ledger.json",
        },
        "precedenceRules": [
            "exact-structured-score is the primary surface when scoreByBook.sh2025 exists",
            "alternate-reference-score is primary only when an exact 2025 score is absent",
            "review-only-draft is primary only when exact and reference scores are absent",
            "source observations and clean candidates are auxiliary evidence, never authoritative notation",
            "transcription queue includes every 2025 record whose coverage status is not structured-score",
            "human review uniquely covers every 2025 draft; duplicate rows require distinct draft artifacts",
            "source-comparison ledger duplicates require distinct audit files and never authorize promotion",
        ],
        "summary": summary,
        "counts": {
            "editionStatus": dict(sorted(addition_status_counts.items())),
            "primarySurface": dict(sorted(state_counts.items())),
            "presencePatterns": dict(sorted(pattern_counts.items())),
            "additionPresencePatterns": dict(sorted(addition_pattern_counts.items())),
        },
        "overlaps": {
            "humanReviewDuplicateArtifacts": duplicate_human_explanations,
            "sourceComparisonDuplicateAuditFiles": duplicate_ledger_explanations,
        },
        "errors": errors,
    }
    return report, errors


def main() -> int:
    report, errors = audit()
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
