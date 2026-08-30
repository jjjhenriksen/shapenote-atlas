# P1 — Verify four-shape correctness

## Goal

`/goal` Establish source-faithful four-shape noteheads for every score that claims them. Presence of allowed tags is insufficient: compare each shape to the original engraving or an authoritative shape-preserving source, and keep derived shapes review-only when the comparison is not possible.

## Current evidence

- 2,589 shape noteheads in 19 review drafts pass XML/schema checks.
- Those checks prove only that tags exist and use `fa`, `sol`, `la`, or `mi`; safe promotions remain zero.

## Work

- Inventory every encoded shape across scores, references, drafts, and derived derivatives.
- Verify shape against source engraving, accounting for edition key/mode and pitch spelling.
- Detect accidental use of seven-shape `do/re/ti`, stale key metadata, or shape tags copied from a mismatched witness.
- Preserve a distinction between source-encoded, source-verified corrected, derived, and unavailable shapes.

## Acceptance

- Each shape-bearing record has per-event or clearly bounded evidence sufficient for its disposition.
- Derived shape tags never appear as source-verified without visual/authoritative evidence.
- Validator fixtures include major, minor, altered-key, and unknown-key cases.
- No generated image is promoted as notation evidence.

## Ownership

Own shape derivation, shape evidence, and shape validators. Do not alter pitch/rhythm events merely to make shapes fit.
