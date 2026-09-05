# P2 — Prove clean startup and deployment

Status: runtime lane verified an isolated build/startup path on 2026-09-04; no hosted/public deployment was attempted.

## Goal

`/goal` Make the dashboard operationally reliable from a clean launch. Prove that the local service starts on an available port, loads the corpus and assets, and supports one score, playback, and transposition flow in the packaged deployment.

## Current evidence

- The production build passes.
- A prior “local service could not start” failure shows that build success is not sufficient operational proof.
- Agent-09 added a bounded startup receipt at `work/agent-09-startup/receipt.json`, a safe fresh-package builder, and focused regression tests. The new checks only stop processes they start and use ephemeral loopback ports.
- The fresh package passed a 3,040-file SHA-256 comparison against `dist/`, preview and packaged-static endpoint checks, occupied-port diagnostics, and a direct SwiftUI native launch. The native wrapper exposed its private service on `127.0.0.1:57395`; `/`, `corpus.json`, `source-coverage.json`, an exact score, and a review-draft asset all returned 200.
- Browser proof on a fresh production preview found no console warnings/errors. Exact score playback entered `Stop`, unknown-key transposition stayed disabled until a source key was entered, and the 2025 reference witness, review draft, and missing-notation/source-scan states rendered with their fail-closed labels.
- The packaging wrapper now changes to its own repository root, supports lane-isolated `ATLAS_*` output/public paths, bounds the build process group, and never kills by process name. `--verify` runs the bounded startup verifier.
- A retained Vite 7.3.6/React 19.2.8 dependency set built a minimal isolated package and served `/`, `corpus.json`, and `source-coverage.json` with 200 responses. The previously retained Vite 8.2.2/Rolldown set hung after transform on this host; it is not used as current runtime proof.

## Work

- [x] Add a clean-port launch smoke test with bounded startup/readiness diagnostics (`scripts/agent-09-startup-smoke.py`).
- [x] Test both development/local service and packaged app/static deployment paths.
- [x] Load the corpus, an exact score, an unknown-key record, a reference/draft record, and a missing-notation record.
- [x] Cover occupied ports, missing assets, and stale packaged output with fail-closed checks; root-path behavior is the supported deployment contract.

## Acceptance

- A fresh launch reaches a readiness signal without manual repair.
- Representative routes/assets load successfully and missing-source states remain truthful.
- Browser console and network checks are clean on the supported path.
- The test does not kill unrelated user processes or mutate unrelated configuration.

Verification command:

```sh
./script/agent-09-build-app.sh
python3 -m unittest tests/test_agent_09_startup.py
python3 scripts/agent-09-startup-smoke.py --package "$(find work/agent-09-startup -path '*/The Shape-Note Atlas.app' -type d | sort | tail -1)"
```

The native probe is bounded and reports an environment limitation instead of claiming success when a GUI session is unavailable. Browser proof covers the root path; a subpath deployment would require a separate Vite base-path build and is intentionally not claimed here. The 2026-09-04 receipt uses a two-file isolated public fixture, so it proves startup/package plumbing but not full corpus asset completeness.

## Ownership

Own launch scripts, smoke tests, and packaging diagnostics. Avoid changing source data or UI design unless required to fix a proven startup defect.
