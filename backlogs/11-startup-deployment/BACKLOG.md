# P2 — Prove clean startup and deployment

## Goal

`/goal` Make the dashboard operationally reliable from a clean launch. Prove that the local service starts on an available port, loads the corpus and assets, and supports one score, playback, and transposition flow in the packaged deployment.

## Current evidence

- The production build passes.
- A prior “local service could not start” failure shows that build success is not sufficient operational proof.

## Work

- Add a clean-port launch smoke test with bounded startup/readiness diagnostics.
- Test both development/local service and packaged app/static deployment paths.
- Load the corpus, an exact score, an unknown-key record, a reference/draft record, and a missing-notation record.
- Include startup failure causes such as occupied ports, missing assets, bad base paths, and stale generated output.

## Acceptance

- A fresh launch reaches a readiness signal without manual repair.
- Representative routes/assets load successfully and missing-source states remain truthful.
- Browser console and network checks are clean on the supported path.
- The test does not kill unrelated user processes or mutate unrelated configuration.

## Ownership

Own launch scripts, smoke tests, and packaging diagnostics. Avoid changing source data or UI design unless required to fix a proven startup defect.
