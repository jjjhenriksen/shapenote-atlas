# P1 — Build a real Practice workflow

## Goal

Turn the current Practice tab from a filtered library list into a focused,
usable practice surface without changing source notation or provenance.

## Current evidence

- Part selection, full-song playback, stop behavior, and target-key
  transposition exist and pass static/browser checks.
- Practice currently reuses the library result list and detail view.
- There is no tempo control, pause/resume, loop range, playback cursor, or
  phrase-level practice state.

## Work

- Inspect the current audio scheduler and UI before editing.
- Add the highest-value minimal workflow: tempo, pause/resume, loop or repeat,
  and a clear current-playback indicator if the existing architecture supports
  them without timing drift.
- Keep selected parts, target key, source mode, and full-song semantics
  correct. Stop/cancel must clear all scheduled nodes and stale UI state.
- Provide intentional loading, empty, unsupported, and audio-error states.
- Keep controls keyboard-accessible and usable at narrow widths.

## Acceptance

- Practice is distinguishable from Library in visible behavior, not merely a
  nav label.
- A user can start, pause/resume, stop, and repeat a bounded practice unit or
  the full song without duplicate schedules.
- Static playback/transposition validation and a real browser smoke pass.
- No score, key, shape, source, or promotion metadata is changed.

## Ownership

Own `src/main.jsx`, `src/styles.css`, and browser practice tests/harness
changes only. Do not edit score builders, ledgers, source images, or
transcription outputs.
