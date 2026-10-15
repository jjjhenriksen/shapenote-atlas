# Trumpet prose classification — issue #56

## Evidence and exact identities

Classification follows the retained direct visual review, not title heuristics:
`work/openclaw-trumpet-20260907/trumpet-page-identity-review-v1.json`, applied through
`scripts/trumpet-catalogue-review.json`. The original review and source are unchanged.

| Stable catalogue ID | Reviewed heading | PDF leaf | Printed page |
| --- | --- | ---: | --- |
| `trumpet p139 — Three` | Three Amigos | 139 | vi |
| `trumpet p187 — By Thomas B` | Mr. Jeff Sheppard and a Brief Untrue History of the Rocking Chair Convention | 187 | iv |
| `trumpet p265 — Sacred b aLLs Town` | Old Paths: Nehemiah Shumway | 265 | iv |

On 2026-10-15 the published PDF was downloaded again from
<https://www.singthetrumpet.com/the-trumpet-composite-vol-1-5.pdf> to a temporary local
file. SHA-256 matched the retained review exactly:
`e96803eef77b5897ef1a43efb6ea08c88a842f11049e31bd490c050abec74f38`.
Text extraction from those three leaves independently exposed the recorded article
headings. This is reuse of the prior visual identity review, not new score fidelity
certification or a fresh full visual audit. No PDF or page images are redistributed.

## Count and migration contract

- Historical catalogue appearances stay at **105 Trumpet / 4,202 edition records**.
  All three articles remain in `corpus.songs` and the source-coverage ledger with
  their existing IDs, original OCR/text keys, paths, URLs and identity provenance.
- Only these three records gain edition-scoped `contentKind: prose`, coverage
  `status: non-notation`, and `nextAction: preserve-prose-reference`.
- Trumpet exposes **102 tune records and 3 prose records**. No new music is
  counted. Exact structured mappings remain **0 Trumpet / 1,155 total**.
- Non-notation records do not belong in the active notation transcription queue:
  it now contains **102 Trumpet / 3,044 total**, down from 105 / 3,047.
  The removed queue entries remain recoverable in Git history; canonical records
  and evidence have not been deleted. Edition-record joins remain complete.
- Source-reference coverage now counts 102 Trumpet / 3,038 total notation records.
  The ledger adds explicit totals: 3 prose / 4,199 notation appearances.
- The regeneration overlay runs after the canonical data build. Reapplying it is
  idempotent and refuses to classify a record that has an exact/reference/draft score
  as prose. No full source-data regeneration is claimed in this checkout.
- Compact reader catalogues preserve classification. All-record search and old
  `?book=trumpet&tune=<stable ID>` links still work. The prose filter shows three
  articles; the no-structured-notation filter shows 102 notation records. Article
  views do not request transcription and open the reviewed PDF leaf.

## Validation

- `python3 -m unittest discover -s tests -p test_trumpet_catalogue_review.py`:
  migration, safety, idempotence and all-corpus coverage/queue joins.
- `npm test`: discovery, compact/full reader parity and existing reader contracts.
- `npm run build`, `npm run validate-playback`, `npm run validate-transposition`.
- Parsed comparison against the parent: only the three named records change in
  corpus/coverage; only their three queue entries are removed. Every unrelated
  record is identical. All 1,334 existing score assets retain transposition state.
- Local production preview at `http://127.0.0.1:5186/`, Chrome/Playwright at
  1440×1000 and 390×1000: all three old deep links, article search, prose/notation
  filters, exact PDF-leaf links, no playback controls, no framework overlay or
  page errors. Remote PDF rendering was isolated from this reader test.

Full `validate-data` is not passing: after reconnecting existing local candidate
and image inputs without copying or publishing them, it stops at missing retained
immutable original `sh2025/254`. Clone-safe join checks above run independently.
The regenerated shared-edition report changes only its generation/checksum metadata;
all 448 shared-edition rows remain identical and its validator passes.

Final results: **104 Node tests, 17 Python tests (5 migration/join + 12 reproducibility),
and all 36 browser tests pass**. The full browser suite runs on its normal Vite dev
server because five harness tests import source modules; those five fail if the
whole suite is incorrectly run against preview. The dedicated article flow also
passes against the production preview. Browser plugin not available; the existing
Playwright setup used installed Chrome. Screenshots were inspected locally at both
viewport sizes and kept outside the repository.
No hosted release, native macOS-window QA, or deployment is claimed.
