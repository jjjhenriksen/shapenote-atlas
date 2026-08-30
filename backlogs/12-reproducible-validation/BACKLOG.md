# P2 — Make validation reproducible

## Goal

`/goal` Provide one documented, read-only verification entry point that validates the data bundle, provenance queues, playback, transposition, shapes, source health, browser smoke path, and production build from a clean export or packaged app.

## Current evidence

- `python3 scripts/verify_all.py` is the aggregate, read-only entry point. It emits a machine-readable JSON receipt and a human-readable Markdown receipt.
- The post-rewrite checkout is `580665e` before the refreshed receipt. Receipts belong under ignored `work/agent-10-verification/` so verification does not overwrite shared historical evidence.
- The aggregate is fail-closed for required checks. Browser smoke is an explicitly optional worker-discovered check: this checkout has no worker, so `--allow-missing-optional` records a limitation and still completes; without that flag, the absent worker is a blocker.

## Work

- [x] Use the existing deterministic aggregate order: generated-artifact and stale-input checks, fail-closed policy checks, focused validators, offline source-health collection/validation, optional browser smoke, production build, and required startup smoke.
- [x] Preserve useful stdout/stderr and exact command details in the JSON receipt; write receipts only to `work/agent-10-verification/` for this audit.
- [x] Verify generated output and the production static bundle without cleaning or mutating the checkout.
- [x] Document runtime boundaries: offline source-health is the default; bounded online source-health is opt-in; browser smoke requires a browser worker; retained local source evidence is required by the image/source validators; startup smoke uses the local preview server.
- [x] Add the agent-10 current-count reconciliation and a focused report-contract test so stale audit prose is detectable.

## Acceptance

- [x] One command produces a complete, machine-readable and human-readable receipt.
- [x] It fails closed on missing source data, stale generated data, unknown mode defaults, queue contradictions, or unsafe promotion.
- [x] The receipt includes exact counts, commit/worktree context, limitations, and remaining blockers.
- [x] Existing focused validators remain independently runnable.

## Agent-10 closeout — 2026-08-30

Run from the repository root:

```sh
python3 scripts/verify_all.py --allow-missing-optional \
  --json-out work/agent-10-verification/verification-receipt.json \
  --markdown-out work/agent-10-verification/verification-receipt.md
```

The fresh run passed all required checks at the post-rewrite `580665e` head. Browser smoke was recorded as `not-available` with `required: false`; startup smoke passed. The exact receipt is in `work/agent-10-verification/verification-receipt.json` and `work/agent-10-verification/verification-receipt.md`.

The current generated-report snapshot and stale-count reconciliation are recorded in `work/agent-10-verification/agent-10-current-audit-reconciliation.md`. The focused contract test is `tests/test_agent_10_reproducible_validation.py`.

## Ownership

Own orchestration/docs for verification. Do not conceal failures by weakening existing validators or mutating user-owned worktree state.
