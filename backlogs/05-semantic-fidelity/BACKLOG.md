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
