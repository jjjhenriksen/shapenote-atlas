# P0 — Transcribe the 90 missing Sacred Harp 2025 scores

## Goal

`/goal` Deliver source-faithful, usable structured MusicXML for every one of the 90 current Sacred Harp 2025 records that lacks an exact verified score. Work autonomously: verify each record or mark it autonomously blocked/rejected with a precise reason. Do not leave a completed record as a vague human-review placeholder.

## Current evidence

- The canonical audit says 90 records remain autonomously blocked and 0 are verified/promoted.
- Retained source images and OMR/imagegen artifacts exist, but generated pixels are review-only and safe-to-promote is zero.
- Existing autonomous transcription scripts and per-record audits are under `scripts/` and `work/source-transcriptions/2025/`.

## Work

- Start from the current queue and deduplicate by canonical `sh2025/<songNo>`.
- Prefer an authorized exact-edition structured source. Otherwise use OMR only as a draft and correct it against the immutable 2025 page.
- Verify every part, measure count, pitch, duration, rests, ties, repeats/endings, source key/mode, and any claimed shapes. Do not fabricate obscured or absent material.
- Record exact source hashes, candidate hashes, corrections, and disposition per record.
- Promote only when the evidence meets the repository's source-faithful promotion policy; otherwise record `autonomously-blocked` or `rejected-source-mismatch` with the precise blocker.

## Acceptance

- Every one of the 90 records has an explicit final disposition; no generic `needs-human-review` escape hatch.
- Any promoted score passes data, playback, transposition, and provenance validation.
- Blocked records identify the exact missing/obscured/contradictory material and preserve the source link/image.
- Existing duplicate artifacts, manifests, and UI work remain intact.

## Ownership

May edit transcription scripts, per-record audit files, canonical transcription/reconciliation outputs, and generated data only through the established build path. Do not edit UI files or collapse duplicate artifact IDs.

## Autonomous disposition checkpoint — 2026-08-29

The 90 canonical records in `work/omr/source-shape-review-drafts/2025/manifest.json` now each have an explicit source-comparison disposition. The backlog has no unresolved or generic human-review records:

- **0 verified/promoted** — the zero-promotion gate remains intact.
- **82 autonomously blocked** — exact source-backed promotion is not established.
- **8 rejected for source mismatch** — the available witnesses are not the authorized 2025 settings.
- **0 remaining without a disposition.**

The 13 exact SH25 MusicXML candidates remain separately recorded as `verified-with-correction-needed` derivatives with preserved event streams, source modes, and shape tags; they are not in the authoritative corpus and are not counted as promotions. The complete evidence is regenerated in `public/source-comparison-ledger.json`, `public/human-review-queue.json`, and the per-record files under `work/source-transcriptions/2025/`.

## Bounded cross-book delivery batch — 2026-08-29

Claimed and completed `sh2025/263` Every Grace and `sh2025/367` Nassau. Both have retained immutable source pages and clean public candidate witnesses, but neither has an exact source-supported structured score: `263` has divergent/incomplete event grouping plus missing lyrics/repeat semantics, and `367` has unresolved source-OMR durations, a 1803/1804 witness discrepancy, and watermark-obscured intersections. Both are explicitly `external-source-blocked` with `safeToPromote=false`; no authoritative corpus count changed. Receipt: `work/source-transcriptions/2025/batches/2026-08-29-cross-book-263-367-disposition.json`.

## Bounded all-book exact-notation extension — 2026-08-30 (agent-01)

The exact-notation backlog now has a fail-closed cross-book inventory derived
from the current edition-specific coverage, transcription queue, and
structured-score manifest. It covers every queued source-reference record in
all 11 books, not only Sacred Harp 2025:

- 3,035 non-structured records are covered: 3,029 `source-reference` records
  and 6 existing `transcription-blocked` records.
- 3,033 are explicitly `autonomously-blocked` because the current manifests
  do not contain an exact structured witness or note-level comparison for
  every encoded note. Two records, `sh2025/115` and `sh2025/116`, are marked
  `protected-active-first-batch` and were not touched.
- No MusicXML was produced, promoted, or treated as exact. Source URLs and
  source-image references remain evidence leads only.
- Every record ID, source URL/host, manifest-evidence flags, and precise reason
  is retained in `work/agent-01-notation/all-book-notation-backlog.json`, with
  a human-readable summary in
  `work/agent-01-notation/all-book-notation-backlog.md`.

The report is intentionally outside `public/` and does not rewrite shared
ledgers. A record can leave this backlog only after an authorized exact-edition
source is retained and compared note-for-note, including rhythm, rests,
ties, repeats/endings, lyrics, and shape identity.

## Autonomous delivery recheck — 2026-08-30

Two additional retained SH25 records were re-inspected autonomously:

- `sh2025/258` Inspiration — source A major, 4/4, four parts; the retained
  derivative has 16 measures per part, 153 pitched events, empty/failed
  duration groups, omitted lyrics/repeats, and watermark-obscured notation.
- `sh2025/259` Easton — source F major, 4/4, four parts; the retained
  derivative has 18 rather than 20 source measures per part, 164 pitched
  events, empty/failed duration groups, omitted lyrics/repeats, and
  watermark-obscured notation.

Both remain `autonomously-blocked`, with `safeToPromote: false`; no new
MusicXML was claimed. The bounded receipt and per-record evidence are under
`work/agent-01-notation/` and preserve the protected 115/116 boundary.

The same recheck produced source-derived, review-only derivatives for
`sh2025/366` Bremen and `sh2025/484b` Parwich. Bremen has 24 duration
failures; Parwich has 25. Their source metadata and derived four-shape tags
are retained as evidence only, not promoted notation.

## Autonomous blocker-clearing batch — 2026-08-30 (agent-01)

The bounded batch for `sh2025/244` Plevna, `sh2025/257` Manatawny, and
`sh2025/265` Gwehelog was inspected against the immutable retained source
images and current OMR/correction witnesses. All three remain explicitly
`autonomously-blocked`; none produced or promoted usable MusicXML.

- `sh2025/244` Plevna — canonical image
  `work/source-images/2025/244-plevna-faef20b4bf.jpg` (SHA-256
  `f77b255e9a8f7652b588ff5535619c29791474e9935c6df1eaec0360f1e60d20`). The
  review derivative retains 4 parts and 18 measures per part, but has 232
  pitched events, 6 rests, 5 empty measures, 58 failed 4/4 duration groups,
  no lyrics, incomplete repeat/ending semantics, and no direct per-note shape
  proof. Its derivative source image has a different hash from the canonical
  retained image; no exact-edition structured candidate is authorized.
- `sh2025/257` Manatawny — canonical image
  `work/source-images/2025/257-manatawny-ba4cb969f4.jpg` (SHA-256
  `7b005c542898414b3bd45372e06589c2b42d2b3849e8dc93e6bb8139891d6057`). The
  source is a 21-measure 12+9 layout, while the review derivative has 19
  measures per part, 217 pitched events, 2 rests, 9 empty measures, 60 failed
  duration groups, no aligned lyrics, unresolved first/second-ending
  semantics, and a non-identical derivative source image.
- `sh2025/265` Gwehelog — canonical image
  `work/source-images/2025/265-gwehelog-fd0a910e8f.jpg` (SHA-256
  `f11f3d7c16a3e192a6a8fdfb016027013abc528ab4bec4c5e578994b08e43b6d`). The
  4-part, 11-measure outline has 78 pitched events, 3 rests, 7 empty
  measures, 44 failed 3/4 duration groups, no aligned lyrics, and no
  note-by-note shape proof; central watermark intersections and a
  non-identical derivative source image prevent exact verification.

Per-record evidence is preserved in `work/agent-01-notation/`; the bounded
receipt is `backlogs/01-transcribe-2025/agent-01-2026-08-30-244-257-265-receipt.json`.
Protected records `sh2025/115` and `sh2025/116`, public ledgers, and UI files
were not touched.
