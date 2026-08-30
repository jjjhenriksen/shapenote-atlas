# P1 — Exhaustively reconcile shared 1991 and 2025 songs

## Goal

`/goal` Produce a complete, edition-separated semantic reconciliation for every song shared by Sacred Harp 1991 and Sacred Harp 2025. Explicitly classify title, key/mode, meter, lyrics, repeats/endings, parts, and notation differences; never substitute one edition's score for the other silently.

## Current evidence

- 448 shared 1991/2025 songs have edition-separated metadata.
- Mapping and source fields validate, but there is no full semantic diff proving which shared songs changed.
- Known cross-edition key conflicts already demonstrate why title/number matching is unsafe.

## Work

- Enumerate all shared pairs using canonical edition IDs and explicit aliases only.
- Compare metadata and structured witnesses field by field, then compare notation where both sources exist.
- Classify unchanged, editorially changed, key/mode changed, text/lyric changed, structural change, source mismatch, and unavailable.
- Ensure 2025 references do not inherit 1991 keys or notation without explicit witness classification.

## Acceptance

- Every shared pair has one reconciliation record and no unmapped/ambiguous pair is silently dropped.
- Edition-specific source URLs, hashes, and keys are preserved.
- Tests include Samaria 26 and The Golden Harp 274t-style conflicts.
- The dashboard can truthfully distinguish “same song” from “same edition notation.”

## Ownership

Own edition mapping and reconciliation artifacts. Do not promote alternate-edition scores or change the UI's visual language.
