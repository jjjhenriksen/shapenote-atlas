# P2 — Improve discovery, filtering, and navigation

## Goal

Make the 3,547-record atlas easier to navigate without changing its source
data or visual language.

## Current evidence

- Search covers tune/page/first-line/source metadata and the book selector
  covers all indexed books.
- Library, Practice, and Sources are the primary sections.
- Unfiltered results show the first 80 records; there are no dedicated filters
  for key/mode, transposability, source status, additions, or available parts.
- Selected state is persisted locally, but tunes do not have shareable URL
  deep links.

## Work

- Design a compact filter/sort model that works with the existing result list:
  key/mode, exact/reference/draft/source-only, new-in-2025, and available
  parts are the highest-value candidates.
- Add stable book/tune URL state or another copyable deep-link mechanism.
- Handle empty, loading, invalid-link, and no-match states clearly.
- Preserve keyboard navigation, focus visibility, 80-result performance, and
  responsive behavior.

## Acceptance

- Users can reach a known tune directly and understand the active filters.
- Filters do not relabel reference, draft, blocked, or source-only material.
- Existing search, book switching, selection persistence, and source links
  continue to work.
- Browser smoke, build, and accessibility-focused checks pass.

## Ownership

Own `src/main.jsx`, `src/styles.css`, and focused browser/UI tests only. Do not
edit corpus builders, score assets, key/mode data, or source-health reports.

## Implementation started — 2026-09-04

Added notation availability and new-in-2025 filters, title sorting, complete
80-row pagination, clear-filter/no-match states, and edition/tune URL links
with invalid-link recovery. Filters apply to all 11 books. The label
“Catalogued score” deliberately describes the existing score mapping, not
verified exact-edition fidelity: 12 SH2025 mappings still require provenance
correction in the data pipeline. Key/mode, transposability, and part filters
remain unfinished.

Verified in the browser: all 11 book totals; all 554 SH1991 records across
seven pages without duplicates; SH2025 filters; title sorting; search/empty
states; Rochester URL round-trip; invalid link; and 320px width without page
horizontal overflow. Four discovery tests pass against the actual corpus.
An isolated React 19/Vite 7 build passes; normal dependency/build and full
music validators remain blocked by cloud-placeholder files. No score data
or source authority was modified.
