# P0 — Reconcile review and autonomous dispositions

## Goal

`/goal` Eliminate contradictory review semantics across the human review queue, source-comparison ledger, autonomous reconciliation, image-review queue, and transcription queue. Make each record's current disposition unambiguous and truthful.

## Current evidence

- `public/human-review-queue.json` contains 122 `reviewNow` records labeled `needs-human-review`.
- The canonical autonomous reconciliation reports `humanReviewRequired: 0` for its covered records.
- Existing queues, ledgers, and review-only artifacts intentionally use different provenance gates, but the user-facing semantics are currently easy to confuse.

## Work

- Join records by canonical edition/song identity, preserving duplicate artifact paths where they are intentionally distinct.
- Define the allowed state vocabulary and precedence: verified/promotable, source-observed, review-only, autonomously-blocked, rejected, and unavailable.
- Distinguish “human review is required” from “human review evidence exists but autonomous promotion is blocked.”
- Update the queue builder/validators and any generated explanatory fields so no record simultaneously claims zero human review and `needs-human-review` without context.

## Acceptance

- Every queue/ledger record joins to one canonical record and one explicit disposition.
- Contradictions are zero or explained by a documented state transition.
- No source-faithful blocked record is presented as completed; no review-only draft is presented as verified.
- Existing provenance gates and duplicate 81b artifacts remain unchanged.

## Ownership

Own queue/ledger state models, builders, and validators. Avoid editing notation, source images, or UI styling except for required status-field compatibility.
