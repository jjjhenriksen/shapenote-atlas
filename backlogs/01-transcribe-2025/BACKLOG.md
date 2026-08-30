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
