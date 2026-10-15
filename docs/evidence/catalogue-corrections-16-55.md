# Source-backed catalogue corrections: #16 and #55

Reviewed 2026-10-14 against `fb184c4`.

## Source inspection

Both retained PDFs SHA-256 match `scripts/review-publications.json`.
`public/catalogue-source-corrections.json` records witness URLs, hashes, page
numbers, normalized top-left bounding boxes and observations. No Glimpse scan
is added to the publication: its policy remains external-link-only.

- New Salem, printed page 10, verse 1 first system: **O thou in whose presence my soul takes delight,**
- A Glimpse of Thee, title header: **L.M.D.**

The upstream dashboard data contains the legacy incipit and title. There is no
corresponding metadata CSV row for either exact book/record. A narrow final
builder overlay therefore corrects these two records without altering external
upstream data. Original catalogue values remain in `catalogueCorrection`.

## Reproduction

Run `python3 scripts/catalogue_source_corrections.py` to apply the overlay to a
retained bundle without reparsing musical sources. `scripts/build_data.py` calls
the same overlay after review publication. Run it twice: the second invocation
must produce no changes. Full data generation still requires the established
retained source inputs; this change does not bypass those prerequisites.

## Verification

- `npm run validate-data`: passes all 3,547 songs, 1,155 full-score assets,
  138 draft assets, 3,047 queue records, 90 image-review records and counters.
- `npm test`: 102 passed.
- `python3 -m unittest discover -s tests -p test_catalogue_source_corrections.py`: 2 passed.
- `python3 -m unittest discover -s tests -p test_review_publications.py`: 9 passed.
- `npm run build`: passed; existing large engraving-chunk warning remains.
- `ATLAS_BROWSER_CHANNEL=chrome npx playwright test tests/browser/catalogue-corrections.spec.js --workers=1`: 2 passed at 1440px and 390px. Search, result/detail text and historical deep link exercised; no page errors.
- Direct comparison against base: only the two intended corpus songs change;
  only Glimpse changes in coverage/queue. No MusicXML or score event bytes change.
- Local screenshots inspected in `/tmp/atlas-metadata-evidence/`.

Browser plugin unavailable; used repository Playwright with installed Chrome.
The fresh worktree initially lacked ignored retained inputs and dependencies.
Installed lockfile dependencies and linked retained local evidence; no validators
were weakened. Full data regeneration, native-window QA, deployment and score
source-fidelity certification are not claimed.

Stable song IDs and paths remain unchanged. New Salem lyric underlay remains
unavailable; Glimpse remains a four-measure partial draft.
