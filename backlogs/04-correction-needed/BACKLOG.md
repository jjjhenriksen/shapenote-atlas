# P1 — Finish the 13 correction-needed records

## Goal

`/goal` Resolve the 13 records whose event streams are source-aligned enough for correction but still lack encoded lyrics or other required fidelity details. Autonomously complete them where evidence supports it; otherwise record exact blockers and do not promote.

## Current evidence

- The comparison ledger has 13 `verified-with-correction-needed` records.
- Their main known gap is unencoded lyrics; none is currently promoted.

## Work

- Enumerate the exact 13 canonical IDs from the current ledger rather than assuming the count.
- Align lyrics to notes only when the source image/authorized source gives unambiguous syllable alignment.
- Check measure, repeat, ending, mode, shape, and part semantics while touching each record.
- Keep lyrics omitted when alignment would require guessing, and record that as a precise blocker rather than a generic review request.

## Acceptance

- Each record is either fully verified/promotable or autonomously blocked with a record-specific reason.
- No lyric, note, repeat, or shape is invented to satisfy the checklist.
- Updated records pass all focused validators, queue joins, and build checks.

## Ownership

Own only the 13 ledger records and their direct audit/correction artifacts. Do not rewrite global key policy or the UI.

## Agent-02 bounded outcome — 2026-08-30

- The current ledger was independently enumerated and contains exactly the 13 expected records: `41`, `50t`, `55`, `118`, `169`, `415`, `525`, `537`, `544`, `545`, `557`, `563`, and `575`.
- All 13 are autonomously blocked with `safeToPromote=false`; none was rejected because each has an exact manifest SH25 structured witness and a source-preserving correction derivative.
- The source scans visibly print lyrics and four-shape notation. The raw and corrected MusicXML each contain zero lyric elements, and no direct note-to-syllable alignment was established without inference. No lyrics, notes, repeats, endings, or shapes were fabricated.
- Independent event-signature comparison passed for all 13; corrected derivatives preserve candidate part/measure/pitched-event structure and carry complete allowed four-shape noteheads.
- Full evidence and checksums: `work/agent-02-corrections/correction-dispositions.json`. The agent-02 audit and focused tests pass; data, playback, transposition, key/mode, and shared-edition validators pass. Semantic-fidelity validation remains blocked by unrelated pre-existing checksum drift for `ch7/543 — Chase High Road`.

## Disposition-policy audit — 2026-08-30

The 13 correction-needed records are not wholly unusable: retained
comparison evidence establishes source-aligned notes/rhythms, parts, measure
topology, source key/mode, and corrected four-shape notation for linear
playback and transposition. Their remaining limitation is semantic: the
structured witnesses contain no direct lyric-to-note anchors. The disposition
policy now exposes `notationStatus: source-aligned-playable`,
`playbackStatus: source-order`, and `transpositionStatus: available` while
retaining `semanticLimitations: ["lyrics-not-encoded"]` and
`safeToPromote: false`. This keeps usable notation visible without fabricating
lyrics or authorizing corpus promotion. Regression coverage is in
`tests/test_review_dispositions.py` and
`tests/test_agent_02_corrections_audit.py`.

## Autonomous correction recheck — 2026-08-30

`sh2025/41` Evening Hymn, `sh2025/50t` Devotion, and `sh2025/55` Converse
were re-inspected against their retained SH25 source scans and exact
structured witnesses. All three preserve source-backed part/measure,
key/mode, event-signature, repeat/ending, and derived four-shape evidence.
None has a lyric-bearing structured witness, so none was promoted; each is
classified as `autonomously-blocked` specifically for missing direct
note-to-syllable alignment, not for an unresolved note-stream mismatch.
The bounded reports and receipt are under `work/agent-02-corrections/`.
