# P1 — Represent lyrics, repeats, and numbered endings faithfully

## Goal

Add source-faithful musical semantics that are currently absent from the
dashboard: lyrics/syllable attachment, repeat bars, and numbered endings.

## Current evidence

- Structured assets preserve pitch, rhythm, parts, clefs, accidentals, ties,
  voices, staffs, and encoded noteheads where available.
- The parser and renderer do not currently expose lyrics or repeat/ending
  playback semantics.
- The 1991/2025 reconciliation reports repeat/endings unavailable for all 448
  shared pairs and lyrics unavailable for many pairs.

## Work

- Audit source MusicXML and retained authorized scans for existing lyric,
  repeat, ending, and barline data before designing fields.
- Extend parsing, normalized comparison, and rendering only where the source
  encodes the information. Preserve omitted/obscured material as unavailable.
- Define playback behavior for repeats/endings explicitly; do not silently
  repeat or omit source material.
- Keep edition-specific semantics separate in 1991/2025 comparisons.

## Acceptance

- At least one source-backed fixture proves lyric alignment and repeat/ending
  parsing without fabricated content.
- Unsupported or unavailable semantics are visibly and honestly represented.
- Existing score timing, transposition, chord handling, and shape behavior
  remain unchanged.
- Relevant data, semantic-fidelity, playback, build, and browser checks pass.

## Ownership

Own parser semantic fields, score rendering, and semantic fixtures needed for
these features. Do not own or rewrite `public/source-comparison-ledger.json`
generation; coordinate with the semantic-fidelity worker instead.

## Agent-11 bounded handoff

Implemented an isolated source-semantic contract in
`scripts/agent_11_lyrics_repeats.py` and
`src/agent_11_score_semantics.js`, with fixtures and focused tests under
`tests/fixtures/agent-11-lyrics-repeats/` and
`tests/test_agent_11_lyrics_repeats.py`. The adapter is not connected to the
protected dashboard entry point; no shared public output or active
transcription was regenerated.

Verified from retained structured witness `work/445.mxl`: repeat barlines and
numbered endings are encoded and expand to an explicit measure sequence;
lyrics are unavailable in that MusicXML and remain unavailable. The fixture
also proves lyric-to-event attachment, editorial-marking extraction, and
linear fallback for absent or unpaired repeat data.

Blocked or unavailable: current dashboard UI integration is deferred because
`src/main.jsx` and `src/styles.css` are protected for this ownership boundary;
scan-visible lyrics are not promoted into structured playback without
event-level source encoding.
