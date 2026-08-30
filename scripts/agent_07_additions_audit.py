#!/usr/bin/env python3
"""Fail-closed audit for the Sacred Harp 2025 additions queue.

This audit is intentionally read-only with respect to ``public/``.  It writes
only an agent-07 evidence report under ``work/agent-07-additions/`` and keeps
alternate structured witnesses separate from exact SH25 source witnesses.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
WORK = ROOT / "work" / "agent-07-additions"
REPORT = WORK / "agent-07-additions-audit.json"

EDITION = "sh2025"
KNOWN_SUPERSEDED_ID = "sh2025/264b"
KNOWN_LEGACY_ID = "sh2025/414b"


def read_public(name: str) -> dict[str, Any]:
    return json.loads((PUBLIC / name).read_text(encoding="utf-8"))


def ident(song_no: Any) -> str:
    return f"{EDITION}/{str(song_no or '').strip().lower()}"


def record_id(value: Any) -> str:
    return str(value or "").strip().lower()


def ids(records: list[dict[str, Any]]) -> set[str]:
    return {record_id(row.get("queueId")) for row in records if record_id(row.get("queueId"))}


def audit(root: Path = ROOT) -> dict[str, Any]:
    # Keep the function injectable for small fixture tests while retaining the
    # authoritative public paths as the default.
    public = root / "public"
    corpus = json.loads((public / "corpus.json").read_text(encoding="utf-8"))
    additions = json.loads((public / "edition-2025-additions.json").read_text(encoding="utf-8"))
    transcription = json.loads((public / "transcription-queue.json").read_text(encoding="utf-8"))
    human = json.loads((public / "human-review-queue.json").read_text(encoding="utf-8"))
    image = json.loads((public / "image-review-queue.json").read_text(encoding="utf-8"))
    score_audit = json.loads((public / "shapenote-2025-score-audit.json").read_text(encoding="utf-8"))

    songs = [song for song in corpus.get("songs", []) if EDITION in song.get("books", [])]
    songs_by_id = {ident(song.get("songNo")): song for song in songs}
    addition_values = [record_id(value) for value in additions.get("records", [])]
    addition_ids = {ident(value) for value in addition_values}
    current_ids = set(songs_by_id)
    non_addition_ids = current_ids - addition_ids
    shared_revision_ids = {
        song_id for song_id, song in songs_by_id.items()
        if song_id in non_addition_ids and "sh1991" in song.get("books", [])
    }
    current_index_only_ids = non_addition_ids - shared_revision_ids

    queue_records = [
        row for row in transcription.get("records", []) if record_id(row.get("queueId")).startswith(f"{EDITION}/")
    ]
    queue_ids = ids(queue_records)
    human_rows = human.get("reviewNow", [])
    human_ids = ids(human_rows)
    image_records = image.get("records", [])
    image_ids = ids(image_records)

    score_audit_records = [
        row for row in score_audit.get("records", []) if record_id(row.get("queueId")).startswith(f"{EDITION}/")
    ]
    score_audit_by_id: dict[str, list[dict[str, Any]]] = {}
    for row in score_audit_records:
        score_audit_by_id.setdefault(record_id(row.get("queueId")), []).append(row)

    errors: list[str] = []
    blockers: list[str] = []

    if additions.get("edition") != EDITION:
        errors.append("additions register has the wrong edition")
    if additions.get("count") != len(addition_values) or len(addition_ids) != len(addition_values):
        errors.append("additions register count or identity uniqueness is stale")

    missing_additions = sorted(addition_ids - current_ids)
    if missing_additions:
        errors.append(f"additions absent from current corpus: {missing_additions}")

    status_mismatches = []
    for song_id, song in songs_by_id.items():
        expected = "added-in-2025" if song_id in addition_ids else "not-new-in-2025"
        actual = song.get("sourceCoverageByBook", {}).get(EDITION, {}).get("editionStatus")
        if actual != expected:
            status_mismatches.append({"id": song_id, "expected": expected, "actual": actual})
    if status_mismatches:
        errors.append(f"edition status mismatches: {status_mismatches}")

    coverage = {
        song_id: song.get("sourceCoverageByBook", {}).get(EDITION, {})
        for song_id, song in songs_by_id.items()
    }
    expected_nonstructured_queue = {
        song_id for song_id, row in coverage.items() if row.get("status") != "structured-score"
    }
    if queue_ids != expected_nonstructured_queue:
        errors.append(
            "transcription queue drift: "
            f"missing={sorted(expected_nonstructured_queue - queue_ids)}, "
            f"extra={sorted(queue_ids - expected_nonstructured_queue)}"
        )

    draft_ids = {
        song_id for song_id, song in songs_by_id.items() if song.get("draftScoreByBook", {}).get(EDITION)
    }
    if human_ids != draft_ids:
        errors.append(
            "human review draft coverage drift: "
            f"missing={sorted(draft_ids - human_ids)}, extra={sorted(human_ids - draft_ids)}"
        )

    expected_image = {
        song_id
        for song_id, song in songs_by_id.items()
        if not song.get("scoreByBook", {}).get(EDITION)
        and not song.get("referenceScoreByBook", {}).get(EDITION)
    }
    if image_ids != expected_image or len(image_ids) != len(image_records):
        errors.append(
            "image review coverage drift: "
            f"missing={sorted(expected_image - image_ids)}, extra={sorted(image_ids - expected_image)}"
        )

    exact_score_ids = {
        song_id for song_id, song in songs_by_id.items() if song.get("scoreByBook", {}).get(EDITION)
    }
    reference_ids = {
        song_id for song_id, song in songs_by_id.items() if song.get("referenceScoreByBook", {}).get(EDITION)
    }
    exact_transposable_ids = {
        song_id
        for song_id in exact_score_ids
        if songs_by_id[song_id]["scoreByBook"][EDITION].get("transposition", {}).get("available") is True
    }
    exact_manual_key_ids = sorted(exact_score_ids - exact_transposable_ids)
    addition_transposable_ids = exact_transposable_ids & addition_ids

    audit_verified_ids = {
        song_id
        for song_id, rows in score_audit_by_id.items()
        if any(row.get("comparisonStatus") == "verified-with-correction-needed" for row in rows)
    }
    audit_alternate_ids = {
        song_id
        for song_id, rows in score_audit_by_id.items()
        if any(row.get("comparisonStatus") == "external-source-blocked" for row in rows)
    }
    current_audit_ids = set(score_audit_by_id) & current_ids
    noncurrent_audit_ids = sorted(set(score_audit_by_id) - current_ids)
    if noncurrent_audit_ids:
        errors.append(f"source score audit has non-current identities: {noncurrent_audit_ids}")

    # The source audit is the stricter edition-identity witness. A row marked
    # external-source-blocked cannot remain in scoreByBook.sh2025: it is a
    # reference witness until an edition-matched source is acquired.
    misclassified_exact_ids = sorted(exact_score_ids & audit_alternate_ids)
    if misclassified_exact_ids:
        blockers.append(
            "alternate source-audit witnesses occupy exact scoreByBook.sh2025: "
            + ", ".join(misclassified_exact_ids)
        )

    direct_exact_ids = exact_score_ids & audit_verified_ids
    if direct_exact_ids != exact_score_ids - set(misclassified_exact_ids):
        blockers.append("exact score rows are not fully covered by the source-audit edition-identity ledger")

    addition_exact_ids = exact_score_ids & addition_ids
    addition_reference_only_ids = (reference_ids | set(misclassified_exact_ids)) & addition_ids
    addition_source_only_ids = sorted(
        addition_ids - direct_exact_ids - addition_reference_only_ids
    )
    addition_draft_ids = {
        song_id
        for song_id in addition_source_only_ids
        if songs_by_id[song_id].get("draftScoreByBook", {}).get(EDITION)
    }

    def reference_asset(song_id: str) -> dict[str, Any]:
        song = songs_by_id[song_id]
        return song.get("referenceScoreByBook", {}).get(EDITION) or song.get("scoreByBook", {}).get(EDITION) or {}

    addition_reference_transposable_ids = {
        song_id
        for song_id in addition_reference_only_ids
        if reference_asset(song_id).get("transposition", {}).get("available") is True
    }
    addition_reference_manual_key_ids = sorted(addition_reference_only_ids - addition_reference_transposable_ids)

    # A queue omission is expected for structured scores, but every
    # non-structured addition must be present. This distinguishes a deliberate
    # structured-score exclusion from a missing queue join.
    structured_exclusions = sorted(addition_ids - queue_ids)
    unexpected_queue_omissions = sorted(
        song_id for song_id in structured_exclusions if coverage[song_id].get("status") != "structured-score"
    )
    if unexpected_queue_omissions:
        errors.append(f"non-structured additions missing from transcription queue: {unexpected_queue_omissions}")

    strict_queue_required_ids = addition_reference_only_ids | set(addition_source_only_ids)
    strict_queue_missing_ids = sorted(strict_queue_required_ids - queue_ids)
    if strict_queue_missing_ids:
        errors.append(
            "strict source/reference semantics require queue rows for alternate witnesses: "
            f"{strict_queue_missing_ids}"
        )

    legacy_records = corpus.get("legacyEditionRecords", [])
    legacy_ids = sorted(ident(row.get("songNo")) for row in legacy_records if row.get("bookId") == EDITION)
    if KNOWN_LEGACY_ID not in legacy_ids:
        blockers.append(f"expected preserved legacy identifier is absent: {KNOWN_LEGACY_ID}")
    if KNOWN_SUPERSEDED_ID in current_ids or any(ident(row.get("songNo")) == KNOWN_SUPERSEDED_ID for row in legacy_records):
        errors.append(f"superseded identifier leaked into current or preserved legacy records: {KNOWN_SUPERSEDED_ID}")

    presence_patterns = Counter()
    addition_presence_patterns = Counter()
    for song_id, song in sorted(songs_by_id.items()):
        pattern = "".join(
            tag
            for tag, present in (
                ("E", bool(song.get("scoreByBook", {}).get(EDITION))),
                ("R", bool(song.get("referenceScoreByBook", {}).get(EDITION))),
                ("D", bool(song.get("draftScoreByBook", {}).get(EDITION))),
            )
            if present
        ) or "-"
        presence_patterns[pattern] += 1
        if song_id in addition_ids:
            addition_presence_patterns[pattern] += 1

    report = {
        "schemaVersion": 1,
        "status": "valid" if not errors and not blockers else "blocked",
        "edition": EDITION,
        "readOnlyPublicInputs": True,
        "policy": {
            "exactSource": "A source-audit verified-with-correction-needed SH25 witness with a scoreByBook asset; correction-needed remains unpromoted.",
            "referenceOnly": "An alternate-edition/source witness or referenceScoreByBook asset; it is never counted as an exact SH25 score.",
            "sourceOnly": "No exact SH25 score is admitted; source links, observations, and OMR drafts remain review evidence only.",
            "drafts": "draftScoreByBook is never completion or promotion evidence.",
            "queue": "Non-structured records must be queued; structured-score records are explicitly excluded with a disposition.",
        },
        "counts": {
            "current2025Records": len(current_ids),
            "additions": len(addition_ids),
            "currentNonAdditions": len(non_addition_ids),
            "sharedRevisionRecords": len(shared_revision_ids),
            "additionSharedRevisionRecords": len(addition_ids & {
                song_id for song_id, song in songs_by_id.items() if "sh1991" in song.get("books", [])
            }),
            "currentIndexOnlyRecords": len(current_index_only_ids),
            "legacyRecords": len(legacy_ids),
            "exactScoreRows": len(exact_score_ids),
            "exactTransposableScoreRows": len(exact_transposable_ids),
            "exactManualKeyRows": len(exact_manual_key_ids),
            "referenceRows": len(reference_ids),
            "transcriptionQueueRows": len(queue_ids),
            "additionQueueRows": len(addition_ids & queue_ids),
            "additionStructuredExclusions": len(structured_exclusions),
            "additionCoverageQueueUnexpectedOmissions": len(unexpected_queue_omissions),
            "additionStrictQueueRequired": len(strict_queue_required_ids),
            "additionStrictQueueMissing": len(strict_queue_missing_ids),
            "draftRows": len(draft_ids),
            "humanReviewRows": len(human_rows),
            "humanReviewUniqueRows": len(human_ids),
            "imageReviewRows": len(image_ids),
            "sourceAuditCatalogRows": len(score_audit_records),
            "sourceAuditCurrentUniqueRows": len(current_audit_ids),
            "sourceAuditNonCurrentRows": len(noncurrent_audit_ids),
            "sourceAuditVerifiedWithCorrectionNeeded": len(audit_verified_ids & current_ids),
            "sourceAuditExternalSourceBlocked": len(audit_alternate_ids & current_ids),
            "additionExactSourcePendingCorrection": len(direct_exact_ids & addition_ids),
            "additionExactSourceTransposable": len(direct_exact_ids & addition_transposable_ids),
            "additionExactSourceManualKey": len((direct_exact_ids & addition_ids) - addition_transposable_ids),
            "additionReferenceOnly": len(addition_reference_only_ids),
            "additionReferenceTransposable": len(addition_reference_transposable_ids),
            "additionReferenceManualKey": len(addition_reference_manual_key_ids),
            "additionSourceOnlyOrDraft": len(addition_source_only_ids),
            "additionDraftOnlyWithinSourceOnly": len(addition_draft_ids),
        },
        "ids": {
            "additionIds": sorted(addition_ids),
            "sharedRevisionIds": sorted(shared_revision_ids),
            "currentIndexOnlyIds": sorted(current_index_only_ids),
            "missingAdditionIds": missing_additions,
            "legacyIds": legacy_ids,
            "knownSupersededExcludedIds": [KNOWN_SUPERSEDED_ID],
            "exactScoreIds": sorted(exact_score_ids),
            "exactTransposableScoreIds": sorted(exact_transposable_ids),
            "exactManualKeyIds": exact_manual_key_ids,
            "exactSourceIds": sorted(direct_exact_ids),
            "additionExactSourceTransposableIds": sorted(direct_exact_ids & addition_transposable_ids),
            "additionExactSourceManualKeyIds": sorted((direct_exact_ids & addition_ids) - addition_transposable_ids),
            "alternateSourceMisclassifiedAsExactIds": misclassified_exact_ids,
            "referenceOnlyAdditionIds": sorted(addition_reference_only_ids),
            "referenceTransposableAdditionIds": sorted(addition_reference_transposable_ids),
            "referenceManualKeyAdditionIds": addition_reference_manual_key_ids,
            "sourceOnlyOrDraftAdditionIds": addition_source_only_ids,
            "sourceOnlyDraftAdditionIds": sorted(addition_draft_ids),
            "structuredScoreExcludedAdditionIds": structured_exclusions,
            "strictExactSourceExcludedAdditionIds": sorted(direct_exact_ids & addition_ids),
            "unexpectedQueueOmissionIds": unexpected_queue_omissions,
            "strictQueueMissingIds": strict_queue_missing_ids,
            "nonCurrentSourceAuditIds": noncurrent_audit_ids,
        },
        "patterns": {
            "currentPresence": dict(sorted(presence_patterns.items())),
            "additionPresence": dict(sorted(addition_presence_patterns.items())),
        },
        "legacyAndDeletionAudit": {
            "preservedLegacyRecords": legacy_ids,
            "currentDoesNotContainSuperseded264b": KNOWN_SUPERSEDED_ID not in current_ids,
            "current414bTitle": songs_by_id.get(KNOWN_LEGACY_ID, {}).get("titlesByBook", {}).get(EDITION),
            "preserved414bTitle": next(
                (row.get("title") for row in legacy_records if ident(row.get("songNo")) == KNOWN_LEGACY_ID),
                "",
            ),
        },
        "errors": errors,
        "blockers": blockers,
    }
    return report


def main() -> int:
    report = audit()
    WORK.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "counts": report["counts"], "blockers": report["blockers"]}, ensure_ascii=False, sort_keys=True))
    return 1 if report["errors"] or report["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
