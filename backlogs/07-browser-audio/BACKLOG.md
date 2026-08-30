# P1 — Prove real browser playback

## Goal

`/goal` Verify that the dashboard actually produces the intended playback in a real browser, not merely a valid event schedule. Test major, minor, unknown-key, reference, draft, partial-part, and full-song cases, including transposition and stop behavior.

## Current evidence

- Earlier static validation covered 283,244 events and 1,283 playable assets; the current bundle is validated below at 292,984 events and 1,317 playable assets.
- Earlier interactive playback was manually proven only for one record, Devotion 50t; the current browser matrix is recorded below and is now bound to an aggregate verification receipt.

## Verification result

- Added the isolated [`public/audio-harness.html`](../../public/audio-harness.html) test page. It wraps `AudioContext` before loading the production app and reports the oscillator frequencies, start/stop calls, and wrapper errors without changing the dashboard UI or `src/main.jsx`.
- Browser matrix passed in a fresh local browser session: source-verified major (1991 Samaria, Ab major), source-verified minor (2025 Evening Hymn, B minor), manually keyed unknown (Cooper 28t, entered C minor), reference witness (2025 Samaria), OMR draft (2025 Troubles Over, source-observed G minor), full-song playback, Bass-deselected partial playback, target-key cancellation, and target reset on tune change.
- Current in-browser trace counts are data-linked: Samaria full song `295`, Samaria without Bass `223`, Cooper 28t `104`, Evening Hymn `173`, Troubles Over review playback `41`, and the 2025 Samaria reference witness `295`.
- Frequency proof passed in-browser: Ab→G first-note ratio `0.9438743126816935` (expected `2^(-1/12)`), B minor→C minor `1.059463094359295` (expected `2^(1/12)`), C minor→D minor `1.122462048309373` (expected `2^(2/12)`), and G minor→C minor draft `1.3348398541700341` (expected `2^(5/12)`).
- Manual stop and target-key cancellation passed: the Stop control disappears, every active oscillator receives a stop call, and target-key change emits `Playback stopped because the target key changed.` with no stale Stop control. Full-song automatic end returned to Play with all 41 scheduled draft oscillators stopped and the harness recorded 82 stop calls (scheduled stop plus cleanup stop).
- Aggregate proof is now reproducible through `scripts/verify_all.py`, which discovers `work/agent-05-browser/agent-05-browser-smoke.py`. The worker validates the current-head/hash-bound browser receipt, harness ordering, score-derived counts/frequencies, stop/reset state, target cancellation, automatic end, and replay-plan coverage; the worker passed with `6` data-linked playback cases and no errors.
- The browser session reported `AudioContext` available, zero harness errors, and zero console errors/warnings across the tested flows.
- Static checks passed: `npm run validate-playback` (`1317` assets, `292984` events, `281212` pitched events, `0` errors), `npm run validate-transposition` (`1317` assets, `0` OMR-detected, `170` unknown), and `npm run build`.

## Work

- Add a focused browser smoke/instrumentation path that observes scheduled oscillator frequencies or equivalent playback parameters.
- Test all selected parts, full-song duration/end handling, pause/stop, target-key changes, unknown-key entry, and reference/draft status.
- Verify that displayed source key/mode and actual pitch transformation agree for both major and minor.
- Record startup failures and browser console errors separately from data-validation failures.
- Keep the receipt fresh by replaying the isolated harness plan after any playback, harness, or representative score change; the aggregate worker intentionally fails closed on a missing or stale receipt.

## Acceptance

- Representative browser tests cover each playback state class and prove intended frequencies/intervals, not just button labels.
- Stop and target-key changes halt stale schedules reliably.
- No console errors or unhandled audio-context failures occur on the supported path.
- Static playback/transposition validators and production build pass.

## Ownership

Own playback test harnesses and narrowly scoped playback fixes. Do not rewrite notation or key-source evidence.
