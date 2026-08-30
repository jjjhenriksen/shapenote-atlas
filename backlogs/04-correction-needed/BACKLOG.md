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
