# P1 — Build corpus-wide semantic fidelity verification

## Goal

`/goal` Create a corpus-wide comparison ledger proving, or precisely blocking, semantic fidelity for all 1,156 structured scores and their edition mappings. Compare notation semantics against the correct source without promoting unverified witnesses.

## Current evidence

- 1,156 structured score records exist, but the detailed comparison ledger covers only 180 records, all 2025.
- Current validators prove structure and consistency, not note-for-note source equivalence.

## Work

- Define a deterministic comparison representation for parts, measures, pitches, durations, rests, ties, repeats/endings, lyrics, key/mode, and source measure counts.
- Compare exact edition sources first; classify cross-edition witnesses separately.
- Emit per-record evidence, differences, source/candidate hashes, and final disposition.
- Handle intentional source transformations, such as documented closing-chord trimming, without hiding other differences.

## Acceptance

- All structured records have a ledger entry: verified, source-observed/review-only, blocked, or rejected.
- Every difference is classified as intentional, corrected, unresolved, or source mismatch.
- The ledger is reproducible and validates against corpus/queue joins.
- No candidate becomes authoritative merely because its title or broad measure count matches.

## Ownership

Own comparison normalization, diffing, and ledger generation. Do not change source files or UI components.

## Autonomous semantic recheck — 2026-08-30

`sh2025/366` Bremen and `sh2025/484b` Parwich were compared against their
immutable source pages and retained OMR. Source metadata, four-part layout,
and derived shape annotations were preserved, but event timing remains
incomplete: Bremen has 24 duration failures and Parwich has 25. Both remain
review-only, `autonomously-blocked`, and `safeToPromote: false`; no uncertain
lyrics, ties, repeats, endings, pitches, or rhythms were invented.

## Autonomous blocker-clearing batch — 2026-08-30

`sh2025/449` Lovely Social Band and `sh2025/520` Ata were re-audited against
their immutable retained source scans, raw OMR, normalized OMR where
available, and all locally available structured candidates. No exact
alternate witness was found.

- Lovely Social Band: source-visible F major, 6/8, four parts, 16 measures,
  three lyric verses, sectional repeat bars, and terminal double bars. The
  review derivative now records the source title/key/meter, normalizes
  terminal bars to `light-heavy`, preserves the 150-event OMR stream, and
  removes unverified per-note shape tags. Normalized OMR still has 62 of 64
  duration failures and unresolved repeat-bar measure mapping.
- Ata: source-visible B-flat major, 4/4, four parts, 13 source measures,
  three lyric verses, no repeat/ending marking, and terminal double bars.
  The review derivative now records the source title/key/meter and terminal
  bars while preserving the 110-event OMR stream. The retained OMR exports
  11 measures per part, has 6 empty measures, and 34 of 44 duration failures.
- Both remain `autonomously-blocked` and `safeToPromote: false`. Lyrics,
  ties, repeat positions, endings, and per-note shapes remain absent where
  event-level proof is unavailable; no alternate notation was borrowed.

Receipt: `work/agent-03-semantic/449-520-receipt.json`.
Focused regression: `tests/test_agent_03_449_520_source_corrections.py`.
Focused source-correction, semantic-parser, playback, and transposition checks
pass. Aggregate `validate_data.py` remains blocked by the unrelated existing
noncanonical disposition for `sh2025/118`; no other record was changed to
clear that failure.
