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

## Agent-04 audit — 2026-08-30

- Audited 120 records without changing public ledgers, UI, immutable source images, source OMR, existing drafts, or either `81b` comparison record. The isolated report is `work/agent-04-shapes/agent-04-shape-evidence-audit.json`.
- Disposition: 120 blocked, 0 rejected, 0 direct source-shape proofs, and `safeToPromote: 0`. The 19 older review drafts and 90 source-shape drafts each have complete structural four-shape tags, but those tags are derived review data rather than direct per-event engraving evidence.
- Render evidence: 110 of 111 scheduled MXLs rendered successfully in isolated PDFs. `sh2025/130` source-shape draft remains blocked because MuseScore returns code 40 without producing a PDF; its raw source OMR renders and its XML shape validator passes.
- Both duplicate `sh2025/81b` comparison records remain distinct and blocked. Their retained source image copy is byte-identical to the immutable source image; candidate MXLs render but contain zero direct notehead tags, so neither supplies source-faithful shape proof. Generated image artifacts remain excluded from notation evidence.
- Validators: `validate_shape_evidence.py` passed (`reviewErrors: 0`, `safeToPromote: 0`); `validate_shape_review_drafts.py` passed (19 records, 2,589 pitched events/noteheads); `validate_source_shape_review_drafts.py` passed (90 records, 14,115 pitched events/noteheads); `test_shape_evidence.py` passed when invoked with `PYTHONPATH=.`; the isolated agent-04 test passed (3 tests).

## Autonomous source-correction recheck — 2026-08-30

`sh2025/140` Moreno and `sh2025/161` Southminster received isolated
source-correction candidates. Both remain blocked: `safeToPromote: false`,
with zero pitch/rhythm/part edits and zero direct per-event source-shape
proof. Candidates render successfully and preserve the raw event streams;
the exact blockers are duration/topology mismatches and watermark-obscured
source regions. Receipt: `work/agent-04-shapes/agent-04-source-correction-receipt.json`.

## Autonomous blocker-clearing batch — 2026-08-30

- Audited only `sh2025/561` Cunningham and `sh2025/562` Mournful Joy against
  their immutable SH25 page images, retained raw OMR, existing source-shape
  drafts, and playable draft witnesses. The pages directly establish E minor,
  the printed meters, four vocal parts, lyrics/repeat treatment, and the four
  geometric notehead vocabulary. They do not establish event-level alignment.
- Both records remain blocked. The existing playable drafts are usable for
  playback but are not source-verified: their key evidence is source-observed,
  mode declarations are incomplete, and time signatures are blank. Existing
  shape tags remain derived OMR hypotheses rather than direct per-note proof.
- Isolated candidates add only source-observed key/mode/time metadata and
  derived four-shape tags while preserving raw pitch/rhythm/part events;
  `safeToPromote: 0`, direct per-event shape matches `0`, verified event data
  `0`, and pitch/rhythm/part edits `0`. The exact evidence gaps are recorded
  per record, including source/OMR topology and duration disagreement and
  watermark-intersected notation. No imagegen output or generated ledger was
  used as notation authority.
- Receipt: `work/agent-04-shapes/blocker-clearing-561-562/agent-04-source-verification-receipt.json`.
  Builder: `scripts/agent-04_source_verification_561_562.py`. Read-only
  integrity test: `tests/test_agent-04_source_verification_561_562.py`.
