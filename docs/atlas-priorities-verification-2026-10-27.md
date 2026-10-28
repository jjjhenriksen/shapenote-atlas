# Atlas follow-through and remaining release gates

## Completed engineering scope

- PR #529 (edition relationship navigation) was already merged at `9ecdc1bb`;
  continuation did not repeat the merge.
- Lossless versioned catalogue packing retains cross-edition discovery and lazy
  tune details. Malformed wire input fails closed and Retry restores the reader.
  See the matched production benchmark; gzip timing improvements are small.
- Read-only v1 publication planning reports proposed mapping changes, pins,
  predecessors, limitations and unresolved authorization without publishing.
  See [planner contract](publication-planning.md).
- Shared witness file actions distinguish local downloads from external links.
  Source/reference/draft labels describe the selected witness. Original files
  never incorporate display transposition. Unknown/non-file URLs are not guessed
  into downloads. Correction draft versions and limitations remain in their panel.
- Browser proof checks XML/MXL bytes, keyboard access, narrow-screen layout, and
  failed-download retry without loss of tune selection. Synthetic bytes are not
  musical source acceptance; externally hosted files remain external links.

## Explicit remaining gates

- Hosted `/atlas/reader-data/catalogue.json` returns HTTP 404 on 2026-10-27.
  The hosted application still refers to legacy `/corpus.json`; it is not proof
  of the new reader build. Deployment/release synchronization is unresolved.
- Local desktop Chrome and mobile-width Chrome are not native-app acceptance,
  mobile hardware results, Safari coverage, or comprehensive screen-reader QA.
- Existing notation/audio scheduling tests are not human confirmation of audible
  voice balance, repeat order, or disconnected native use.
- Human source fidelity, rights clearance and exact-scope publication authority
  remain required per candidate. No source image, notation, accepted mapping,
  research flag or publication permission was changed by this work.

## Producer dependency decision

No new Transcriber thread is necessary for these engineering increments:
existing versioned bundles and synthetic fixtures support the planner, and the
reader's retained witnesses support downloads. Correcting musical readings or
producing new accepted notation remains Transcriber/source-review work; the
planner explicitly refuses to turn those missing decisions into Atlas approval.
This is not a claim that transcription or source acceptance is complete.

## Verification receipts

- 140 JavaScript unit tests passed; 6 synthetic publication-plan tests passed,
  including subprocess exit status and unchanged input snapshot.
- Resumed development-mode browser run: 69 passed. Production-mode checks:
  17 unique tests passed across the initial run and a focused two-test rerun
  after fixing a test selector to use the existing accessible button name.
- `npm run build`, playback validator (1,334 assets), transposition validator
  (1,334 preserved), and `git diff --check` passed.
- Narrow-screen screenshot inspected at 390 px: file action fits, has visible
  keyboard focus and does not introduce horizontal overflow. This is bounded
  visual/accessibility evidence, not a complete WCAG or screen-reader audit.
