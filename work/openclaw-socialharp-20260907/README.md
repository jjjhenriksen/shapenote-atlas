# Social Harp: first five unresolved source identities

Reviewed 2026-09-07 against the retained Social Harp PDF. This is an additive page-identity supplement, not notation transcription or exact-edition semantic certification.

| Catalogue record | PDF leaf (1-based) | Printed page | Literal printed heading |
| --- | ---: | ---: | --- |
| 101 PARTING FRIENDS | 101 | 101 | PARTING FRIENDS.* |
| 103 MOSLEY | 103 | 103 | MOSLEY. |
| 104 SHOUT FOR JOY | 104 | 104 | SHOUT FOR JOY. |
| 105 THE SOUNDING TRUMPET | 105 | 105 | THE SOUNDING TRUMPET. |
| 107 MEMPHIS | 107 | 107 | MEMPHIS. |

All five headings and page numbers were read directly from full-page Poppler renders, not inferred from PDF offsets or catalogue titles. All five leaves contain notation. The asterisk on PARTING FRIENDS is a printed footnote marker; it is preserved in the literal heading, not inserted into the catalogue title. No notes, lyrics, mode, shapes, or repeat semantics are transcribed in this package.

## Result

The original map remains byte-for-byte unchanged: 67 mapped / 154 unresolved of 221 catalogue records. Applying this supplement yields **72 mapped / 149 unresolved**. This does not settle the historical 221-versus-222 inventory discrepancy and does not add a structured score or change public corpus data.

- [Supplement](socialharp-page-map-supplement-v1.json) identifies exact records, retained PDF hash, leaf numbers, printed headings, and evidence-render hashes.
- `renders/` contains the five visually reviewed full leaves, rendered at `-scale-to 1800`.
- `python3 work/openclaw-socialharp-20260907/verify.py` checks retained source/baseline/render hashes, unresolved-array selection, disjointness, and combined counts. This checks integrity, not a substitute for visual review.

Source: `work/luna-program-20260904/source_only/retained-sources/socialharp-1855-imslp-scan.pdf`, SHA-256 `562db348cf414b27c0c3e40da38cca0a8c39a11f2007abec370f9ddcae1bc331`.

Only this new package was written. No Git operations or canonical mutations were performed. Next bounded batch: select the next five unresolved records after these, leaving the original historical map intact.
