# P1 — Prove real browser playback

## Goal

`/goal` Verify that the dashboard actually produces the intended playback in a real browser, not merely a valid event schedule. Test major, minor, unknown-key, reference, draft, partial-part, and full-song cases, including transposition and stop behavior.

## Current evidence

- Earlier static validation covered 283,244 events and 1,283 playable assets; the current bundle is validated below at 289,392 events and 1,317 playable assets.
- Earlier interactive playback was manually proven only for one record, Devotion 50t; the current browser matrix is recorded below.

## Verification result

- Added the isolated [`public/audio-harness.html`](../../public/audio-harness.html) test page. It wraps `AudioContext` before loading the production app and reports the oscillator frequencies, start/stop calls, and wrapper errors without changing the dashboard UI or `src/main.jsx`.
- Browser matrix passed: source-verified major (1991 Samaria, Ab major), source-verified minor (2025 Evening Hymn, B minor), manually keyed unknown (Cooper 28t, entered C minor), reference witness (2025 Samaria), OMR draft (2025 Troubles Over, source-observed G minor), full-song playback, and Bass-deselected partial playback.
- Frequency proof passed in-browser: Ab→G first-note ratio `0.9438743126816935` (expected `2^(-1/12)`), B minor→C minor `1.059463094359295` (expected `2^(1/12)`), and G minor→C minor draft `1.3348398541700341` (expected `2^(5/12)`). Full Samaria scheduled 291 oscillators; Bass-deselected scheduled 220; Cooper 28t scheduled 100; Evening Hymn scheduled 169; Troubles Over scheduled 64.
- Manual stop and target-key cancellation passed: the Stop control disappears, every active oscillator receives a stop call, and target-key change emits `Playback stopped because the target key changed.` with no stale Stop control. Full-song automatic end also returned to Play with all scheduled draft oscillators stopped.
- A fresh clean-tab smoke run on Evening Hymn recorded 169 frequencies, 169 starts, 169 stops, and zero browser console errors or harness errors.
- Static checks passed: `npm run validate-playback` (`1317` assets, `289392` events, `277620` pitched events, `0` errors), `npm run validate-transposition` (`1317` assets, `0` OMR-detected, `201` unknown), and `npm run build`.

## Work

- Add a focused browser smoke/instrumentation path that observes scheduled oscillator frequencies or equivalent playback parameters.
- Test all selected parts, full-song duration/end handling, pause/stop, target-key changes, unknown-key entry, and reference/draft status.
- Verify that displayed source key/mode and actual pitch transformation agree for both major and minor.
- Record startup failures and browser console errors separately from data-validation failures.

## Acceptance

- Representative browser tests cover each playback state class and prove intended frequencies/intervals, not just button labels.
- Stop and target-key changes halt stale schedules reliably.
- No console errors or unhandled audio-context failures occur on the supported path.
- Static playback/transposition validators and production build pass.

## Ownership

Own playback test harnesses and narrowly scoped playback fixes. Do not rewrite notation or key-source evidence.
