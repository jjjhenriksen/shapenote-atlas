# P2 — Reconcile 2025 additions with score and review queues

## Goal

`/goal` Make the relationship between the publisher's 2025 additions list, corpus records, exact scores, references, drafts, and review-only items explicit and validator-enforced.

## Current evidence

- `edition-2025-additions.json` lists 113 additions, all mapped to corpus records.
- Exact, reference, and draft presence overlap; the current categories are difficult to interpret without precedence rules.

## Work

- Define whether each record is an addition, shared revision, or current-index record and preserve that distinction.
- Explain every overlap among exact score, alternate reference, OMR draft, image review, and transcription queue.
- Detect additions missing from the queue and non-additions incorrectly treated as new songs.
- Add invariant checks for counts, identity, and status precedence.

## Acceptance

- Every listed addition has one explicit corpus identity and queue disposition.
- Every overlap is either intentional and documented or fixed.
- Counts are reproducible from source files and validators fail on unexplained drift.

## Ownership

Own additions metadata, queue joins, and related validators. Do not alter notation assets or source images.
