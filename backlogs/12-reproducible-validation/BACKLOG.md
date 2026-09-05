# P2 — Make validation reproducible

## Goal

`/goal` Provide one documented, read-only verification entry point that validates the data bundle, provenance queues, playback, transposition, shapes, source health, browser smoke path, and production build from a clean export or packaged app.

## Current evidence

- `python3 scripts/verify_all.py` is the aggregate, read-only entry point. It emits a machine-readable JSON receipt and a human-readable Markdown receipt.
- `python3 scripts/verify_dependencies.py` is the read-only package/lock contract check. The current retained, build-proven set is Vite 7.3.6 with React and ReactDOM 19.2.8; an offline temporary-project `npm ci` restored 17 packages successfully.
- Aggregate subprocesses now run in their own process groups and are reaped on timeout. Public JSON inputs that look dataless are probed in a disposable child with a hard read bound and become explicit blockers when unavailable.
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

That historical receipt is not current integration proof. The 2026-09-04 runtime receipts are under `work/luna-program-20260904/runtime/startup-receipt.json` and `work/luna-program-20260904/runtime/verification-receipt.json`. The canonical build and startup checks pass; the aggregate remains fail-closed blocked by current data/playback/source-validator/browser-receipt issues recorded in the JSON and Markdown receipts.

The current generated-report snapshot and stale-count reconciliation are recorded in `work/agent-10-verification/agent-10-current-audit-reconciliation.md`. The focused contract test is `tests/test_agent_10_reproducible_validation.py`.

## Ownership

Own orchestration/docs for verification. Do not conceal failures by weakening existing validators or mutating user-owned worktree state.
