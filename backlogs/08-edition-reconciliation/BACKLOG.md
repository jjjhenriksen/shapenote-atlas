# P1 — Exhaustively reconcile shared 1991 and 2025 songs

## Goal

`/goal` Produce a complete, edition-separated semantic reconciliation for every song shared by Sacred Harp 1991 and Sacred Harp 2025. Explicitly classify title, key/mode, meter, lyrics, repeats/endings, parts, and notation differences; never substitute one edition's score for the other silently.

## Current evidence

- 448 shared 1991/2025 songs have edition-separated metadata.
- Mapping and source fields validate, but there is no full semantic diff proving which shared songs changed.
- Known cross-edition key conflicts already demonstrate why title/number matching is unsafe.

### Agent-06 audit (2026-08-30)

- `work/agent-06-editions/agent-06-edition-reconciliation.json` enumerates all 448 canonical shared pairs with edition-specific source URLs, manifest hashes, keys/key candidates, meters, time signatures, witness roles, and field dispositions. `safeToPromote` is `0`.
- The canonical pair set is complete and unique, but source-slot mapping remains incomplete: the change register contains 102 two-edition slots; 13 are covered by canonical shared records and 89 remain unmapped candidates. Of those 89, 12 have the same normalized title and 77 look like replacement/identity candidates. There is one unpaired change-register slot (`414b`) with two 2025 rows. Same-number records are never merged by the audit.
- The Golden Harp `274t` is explicitly retained as an unmapped same-title candidate: the 1991 and 2025 records have different retained text keys, and no explicit cross-edition alias authorizes pairing. The separate explicit Bishop renumbering remains `420` (1991) → `420b` (2025); 1991 metadata aliases remain `313` → `313b`, `445b` → `445`, and `503b` → `503`.
- Exact metadata key/mode comparison is unavailable for all 448 canonical pairs because no pair has both edition-specific `keySignature` values populated. There are 366 secondary 2025 key candidates; Samaria 26’s retained `F minor` candidate versus the exact 1991 `A-flat major` witness is kept as an unverified candidate, not promoted metadata.
- Title comparison has 28 raw differences and meter comparison has 156 raw differences; these remain source-field differences, not proof that all are substantive musical changes. Time signatures show 1 difference and 22 unavailable values.
- Lyric evidence is only text-key evidence: 179 pairs share a text key, 10 differ, and 259 lack edition-specific text keys. Verse-level lyrics and alignment are unavailable. Repeat bars, numbered endings, and volta semantics are unavailable for all 448 pairs.
- Witness coverage is edition-separated: 2 exact 2025 structured scores, 3 2025 review drafts, 444 2025 references sourced from 1991, and 446 pairs without an exact 2025 score. The two exact both-edition notation comparisons (`467 Lisbon`, `515 Rockbridge`) are changed; the remaining comparisons are alternate-witness-only or unavailable.

## Work

- Enumerate all shared pairs using canonical edition IDs and explicit aliases only.
- Compare metadata and structured witnesses field by field, then compare notation where both sources exist.
- Classify unchanged, editorially changed, key/mode changed, text/lyric changed, structural change, source mismatch, and unavailable.
- Ensure 2025 references do not inherit 1991 keys or notation without explicit witness classification.

### Agent-06 completion and remaining gaps

- [x] Enumerate and test the 448 canonical shared pairs without changing the public ledger or UI.
- [x] Preserve alternate witness roles and exact-vs-review-vs-unavailable score states.
- [x] Separate text-key observations from unavailable verse-level lyric evidence and block unavailable repeat/ending semantics.
- [x] Add regression coverage for Samaria 26 and Golden Harp 274t-style same-title conflicts.
- [ ] Resolve the 89 source-slot candidates only with authoritative edition IDs or explicit aliases; do not infer identity from number/title/text similarity.
- [ ] Obtain or verify edition-specific 2025 score witnesses for the 446 missing exact-score pairs before any notation, key/mode, lyric, or repeat conclusion is promoted.
- [ ] Normalize and source-audit the 156 meter differences to distinguish notation of the meter label from actual stanza/meter changes.
- [ ] Add edition-specific verse, repeat, ending, and shape structure evidence; current structured assets cannot support those comparisons.

## Acceptance

- Every shared pair has one reconciliation record and no unmapped/ambiguous pair is silently dropped.
- Edition-specific source URLs, hashes, and keys are preserved.
- Tests include Samaria 26 and The Golden Harp 274t-style conflicts.
- The dashboard can truthfully distinguish “same song” from “same edition notation.”

Agent-06 verification: `python3 scripts/agent_06_audit_edition_reconciliation.py && python3 -m unittest tests/test_agent_06_edition_reconciliation.py` passed (6 tests). Repository-wide validation and public artifact regeneration remain out of scope for this bounded pass; no public ledger or UI file was modified.

## Ownership

Own edition mapping and reconciliation artifacts. Do not promote alternate-edition scores or change the UI's visual language.

## Autonomous source reconciliation recheck — 2026-08-30

`sh2025/254` Warsaw and `sh2025/255` Mechanicville were rechecked against
their retained 2025 pages and available alternate witnesses. Warsaw remains
`external-source-blocked`: the same-text witness is Departure C.M.D. in 4/4
with different credits and layout. Mechanicville remains
`external-source-blocked`: the same-title witness is D minor with 22 measures
per part versus the retained E-minor 2025 page. Neither alternate can support
exact transposition or promotion. Receipt:
`work/agent-06-editions/agent-06-sh2025-254-255-receipt.json`.
