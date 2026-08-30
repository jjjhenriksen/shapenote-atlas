# P2 — Make validation reproducible

## Goal

`/goal` Provide one documented, read-only verification entry point that validates the data bundle, provenance queues, playback, transposition, shapes, source health, browser smoke path, and production build from a clean export or packaged app.

## Current evidence

- Validators are separate scripts and the checkout is heavily dirty/untracked.
- Individual checks pass, but there is no single reproducible command proving the complete state.

## Work

- Define a deterministic validation order and dependency/runtime requirements.
- Add a read-only aggregate command that reports pass/fail per subsystem and preserves useful logs.
- Verify against generated output and, where possible, a clean temporary export or packaged app without cleaning the user's checkout.
- Document which checks require network, a browser, retained source files, or optional tools.

## Acceptance

- One command produces a complete, machine-readable and human-readable receipt.
- It fails closed on missing source data, stale generated data, unknown mode defaults, queue contradictions, or unsafe promotion.
- The receipt includes exact counts, commit/worktree context, and remaining blockers.
- Existing focused validators remain independently runnable.

## Ownership

Own orchestration/docs for verification. Do not conceal failures by weakening existing validators or mutating user-owned worktree state.
