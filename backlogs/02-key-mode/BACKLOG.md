# Completed — P0: Resolve major/minor and source-key authority

## Goal

Audit and correct major/minor and key metadata across every book without
inventing mode where the source does not encode it. Preserve the distinction
between source-verified, source-observed, OMR-detected, and unknown values.

## Delivered

- [x] Separate edition metadata, raw MusicXML declarations, source-page
  observations, OMR detections, and secondary/cross-edition candidates.
- [x] Changed both dashboard and enrichment-parser semantics so an absent
  MusicXML `<mode>` never defaults to major. Raw fifths remain in each score's
  `musicXmlKeyDeclarations` provenance.
- [x] Kept source labels such as `F-sharp minor` and `F♯ minor` convertible to
  MusicXML `fifths:mode` without discarding the human-readable label.
- [x] Downgraded 396 SH2025 keys copied from 1991 as secondary candidates;
  they remain available under `metadataByBook.sh2025.keyCandidate` but cannot
  drive transposition or claim 2025 source authority.
- [x] Preserved direct SH2025 source-audit keys, including explicit minor
  witnesses, and let a direct audit override a secondary candidate.
- [x] Preserved alternate-edition reference keys as alternate witnesses;
  they are never relabeled as exact-edition scores.
- [x] Added focused validator coverage for major, minor, missing-mode,
  unknown-key, secondary-candidate, and source-audit precedence cases.

## Verified state

The current generated corpus contains 3,547 songs and 1,317 unique structured
score assets:

| Book | Source-verified | Source-observed | Unknown | Secondary key candidates |
| --- | ---: | ---: | ---: | ---: |
| Sacred Harp 1991 | 484 | 0 | 68 | 0 |
| Sacred Harp 2025 | 56 | 82 | 37 | 396 |
| Cooper 2012 | 442 | 0 | 75 | 0 |
| Southern Harmony | 49 | 0 | 21 | 0 |
| Christian Harmony 7 | 3 | 0 | 0 | 0 |

The remaining 201 unknown structured assets have no source-encoded mode or
authorized edition-specific key evidence. They remain non-transposable rather
than being guessed. The 2025 reference reconciliation has 61 autonomous
blocks and 3 source-key observations retained as reference-only; the 1991
reconciliation has 68 autonomous blocks. Both report zero safe promotions.

The focused reconciliation also accounts for 20 source-verified 2025 assets
whose raw MusicXML declarations omit `<mode>`. Four source-audit drafts
(256 Northampton, 258 Inspiration, 322 Man's Redemption, and 366 Bremen)
preserve raw-fifths conflicts explicitly; no raw declaration is silently
rewritten or promoted as source authority.

## Autonomous blockers, not open data errors

- 68 SH1991 assets: exact structured witnesses and the checked Fasola pages do
  not encode a key/mode.
- 37 SH2025 assets: no authoritative mode/key is available for the selected
  witness after removing 1991 fallback authority.
- 75 Cooper and 21 Southern Harmony assets: pitch-bearing structured sources
  lack a usable source key/mode.
- SH2025 source images and alternate witnesses remain evidence-only where exact
  edition identity or complete notation has not been proven.

No value in these groups is inferred from pitch spelling, fifths alone,
filenames, another edition, or OMR output.

## Validation evidence

- `python3 scripts/validate_transposition.py` passes: 1,317 assets; 201
  unknown; 0 OMR-detected non-draft assets.
- `python3 scripts/validate_key_mode_reconciliation.py` passes: 201
  autonomously blocked, 20 resolved missing-mode assets, 4 preserved
  raw-fifths conflicts, and 0 safe promotions.
- `python3 scripts/validate_playback.py` passes: 1,317 playable assets,
  289,392 events, and 277,620 pitched events.
- `python3 scripts/validate_source_candidates.py` passes: 94 candidates and
  94 OMR records.
- `python3 scripts/validate_shape_review_drafts.py` passes: 19 records and
  zero safe promotions.
- `npm run build` passes.
- `python3 scripts/validate_data.py` passed immediately after the key rebuild;
  a later rerun is blocked by concurrent image-review changes for SH2025/115,
  outside this backlog's ownership. Those image/transcription files were not
  modified here.

## Ownership boundary

This backlog owns key parsing, key authority, key audits, and transposition
metadata only. UI files and unrelated transcription/image-review work remain
untouched.
