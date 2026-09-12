# Shape-Note Atlas guide

The Shape-Note Atlas is a source-faithful lookup and practice workspace for
shape-note and Sacred Harp repertory. It keeps the corpus searchable even when
a tune does not yet have structured notation, and it makes the boundary between
source evidence, practice material, and verified edition data visible.

This guide is the reader and maintainer entry point. It does not replace the
[OpenClaw handoff](OPENCLAW_HANDOFF.md), which contains the current continuation
state, retained-evidence requirements, and the all-eleven-book work plan.

## Start here

| Need | Use |
| --- | --- |
| Browse tunes and practice a score | Run the app and use the [reader workflow](#reader-workflow). |
| Understand what is and is not authoritative | Read [evidence states](#evidence-states). |
| Inspect current coverage and remaining work | Read [the program status](OPENCLAW_PROGRAM_STATUS.md), then inspect the generated ledgers in `public/`. |
| Refresh data | Follow [the data workflow](#data-workflow). |
| Change application code | Follow [the development workflow](#development-workflow) and run the focused checks before `verify-all`. |

## What the Atlas contains

The Atlas has three related layers:

1. **Corpus metadata** — tune numbers, titles, first lines, book membership,
   source links, edition relationships, and catalogue fields.
2. **Structured notation** — MusicXML-derived parts and timing, loaded lazily
   when the selected edition has an admitted score asset.
3. **Evidence and review work** — source scans, recordings, OMR drafts,
   comparison candidates, correction packages, and validation ledgers.

The application preserves a record when only the first or third layer exists.
It does not synthesize notation to make the catalogue look complete. A tune in
one edition is not silently substituted for the same title in another edition.

The corpus currently represents eleven books/editions:

- Sacred Harp 1991
- Sacred Harp 2025
- Cooper Book 2012
- The Christian Harmony
- The Shenandoah Harmony
- The Southern Harmony
- A Supplement to the Kentucky Harmony
- The Social Harp
- The Minnesota Harmony
- Sacred Harp Tunes
- The Trumpet

Coverage counts are generated data, not hand-maintained documentation. Read
the `generatedAt` value and `coverage` objects in `public/corpus.json` and
`public/source-coverage.json` when an exact current count matters.

## Reader workflow

### 1. Choose a book

Use the **Tune book** picker in the header. The book is part of the tune's
identity: the same title or first line can have different notation, lyrics, or
page numbers in another edition.

### 2. Find a tune

The Library, Practice, and Sources views share the same search results. Search
matches tune/page metadata, title, first line, and recorded source metadata.
The results can be narrowed by:

- notation availability;
- key and mode;
- available vocal part;
- transposability;
- title order or page order; and
- **New in 2025** when the Sacred Harp 2025 book is selected.

The tune link in the detail pane includes the selected book and tune query
parameters, so a specific record can be shared without relying on the current
search state.

### 3. Read the detail state before practicing

The detail pane identifies the selected book/page, first line, source links,
source health, and the status of any score or review material. Treat those
labels as part of the data model, not decorative UI:

| UI state | Meaning | Practice/transposition |
| --- | --- | --- |
| **Catalogued score** | A structured score is attached to the selected edition. | Available only when the asset has validated timing and key evidence. |
| **Alternate reference** | A structured witness exists for another edition or source. | May be usable for practice, but is never the selected edition's engraving. |
| **Review draft only** | A versioned transcription or OMR result is available for comparison. | May be playable/transposable when its review contract allows it; it is never authoritative. |
| **Source scan / source reference** | The source page, scan, or recording is linked without an admitted structured score. | No transposition from the source-only record. |
| **Transcription blocked** | The next safe action is source acquisition or resolution of a source blocker. | The isolated review material remains fail-closed. |
| **Metadata only / source mapping gap** | The catalogue record exists, but a usable source path has not been established. | No notation is inferred. |

An alternate witness or draft can be useful without closing the selected
edition's mapping gap. That distinction is intentional.

### 4. Practice a structured score

When a score is available:

1. Select the parts to hear. Part changes stop active playback so the schedule
   cannot continue with stale selections.
2. Choose **Written order** or **Follow encoded repeats** when repeat semantics
   are explicitly encoded and safe to apply. Unsupported D.C., segno, coda, or
   other navigation falls back to written order and is announced in the detail
   pane.
3. Set tempo between 40 and 220 BPM and choose one to eight practice loops.
   Loops are a deliberate practice setting; they are not evidence that the
   source contains another repeat.
4. Use **Play**, **Pause**, **Resume**, and **Stop** as needed. Playback also
   stops when the selected parts, score version, source key, or target key
   changes.

The reader schedules the complete selected score. The visual score is wrapped
into vertical four-measure systems for reading; that layout is not a four-bar
playback excerpt.

### 5. Transpose only with key evidence

Transposition is enabled only when a source key is available or explicitly
entered. The evidence label distinguishes source-verified, source-observed,
OMR-detected, and user-entered keys. A missing mode never silently becomes
major.

For an unknown-key score, choose the key printed in the linked source from the
**Source key** control. The entry is kept separate from catalogue metadata and
is remembered locally for that record. The target-key control then changes the
pitch by semitone while retaining the source mode.

If the key is not established, practice may still be possible, but target-key
transposition remains unavailable. That is a useful limitation, not a missing
default.

### 6. Interpret shapes and lyrics carefully

The shape legend represents four-shape solfège. A displayed shape can have one
of three evidence states:

- **Source** — the notehead/shape was encoded in the MusicXML witness.
- **Derived** — the shape was calculated from an established key and exact
  pitch spelling; it is not direct printed-glyph evidence.
- **Unavailable** — the source does not establish the shape or key, so the
  Atlas leaves it blank rather than guessing.

The linked shape-source PDF remains the visual authority for printed glyphs.
Lyrics, melismas, verses, repeats, endings, ties, slurs, and editorial markings
follow the same rule: encoded or directly evidenced values are preserved;
unknown values stay unknown.

### 7. Correct a published draft

Published review drafts include an expanded correction panel. Use it to:

1. download the editable MusicXML;
2. compare it with the untouched source page and evidence package;
3. preserve the original witness while making edits in a notation editor; and
4. open the pre-filled GitHub correction form if a correction should be
   proposed.

A published draft is a usable, human-correctable work product. Its
`safeToPromote` state remains false until the required edition-specific source
review is complete. Downloading or playing a draft does not promote it.

## Evidence states

The Atlas uses separate concepts that are easy to conflate:

### Source identity

Does a URL, scan, PDF leaf, or catalogue row identify the intended record? Page
identity work can resolve a title or printed page without establishing any
notation.

### Structured mapping

Is there a parseable MusicXML asset associated with the selected edition? This
supports rendering, timing checks, and—when key evidence permits—practice and
transposition. It is not a blanket claim that every lyric, shape, repeat, or
editorial detail has been visually audited against the printed page.

### Review disposition

Has a draft been compared enough to be useful, rejected for mismatch, or
blocked on unresolved evidence? Review material is retained with its source,
hashes, limitations, and version. It is not automatically promoted.

### Verified edition status

Has the exact selected edition's required notation and source semantics passed
the relevant review gates? This is the highest bar and is intentionally
independent from the existence of a matching title, an alternate witness, a
successful parser import, or a green application build.

The operational shorthand is:

> Source identity is not notation. Notation is not automatically edition
> certification. A passing build is not corpus completion.

## Data model and generated artifacts

### Canonical public bundle

`public/corpus.json` is the application index. Its top-level fields include:

- `books` — edition IDs and display labels;
- `songs` — merged corpus records;
- `coverage` — generated counts by book;
- `legacyEditionRecords` — retained historical records when an edition index
  changed; and
- `generatedAt` / `source` — provenance for the generated bundle.

Each song may carry edition-scoped values such as:

- `metadataByBook` — key, meter, source URLs, composer/lyricist, and edition
  evidence;
- `scoreByBook` — structured score previews for the selected edition;
- `referenceScoreByBook` — explicitly labeled alternate witnesses;
- `draftScoreByBook` — isolated or published review drafts; and
- `sourceCoverageByBook` — the edition-specific coverage state and next action.

Full score data is lazy-loaded from `public/scores/` or
`public/draft-scores/`; the index contains compact previews so the initial
catalogue stays small.

### Coverage and work queues

| Artifact | Purpose |
| --- | --- |
| `public/source-coverage.json` | One edition-scoped classification and next action per record. |
| `public/transcription-queue.json` | Every record without an exact structured score, including source links, priority, and blockers. |
| `public/human-review-queue.json` | Drafts, dispositions, review evidence, and correction/publication metadata. |
| `public/image-review-queue.json` | Immutable source images and non-authoritative working layers for image review. |
| `public/source-comparison-ledger.json` | Explicit source-versus-candidate comparisons; never an automatic promotion signal. |
| `public/shared-edition-reconciliation.json` | Relationships between edition records, including differences that require separate treatment. |
| `public/source-health.json` | Source-health observations and retention state; cached/offline evidence is labeled as such. |
| `public/shapenote-score-manifest.json` | Hash-checked mappings from the Shape Note Music Files index to local score inputs. |
| `public/edition-2025-additions.json` | Publisher's 2025 additions list; editorial status is not notation evidence. |

The `work/` tree contains retained scans, downloaded inputs, OMR outputs,
comparison packages, and verification receipts. Much of it is intentionally
ignored or local-only. A Git clone alone is not a complete source-dependent
validation environment.

## Data workflow

### Prerequisites

The browser bundle can be served from committed `public/` data, but data
regeneration requires the established local source checkout:

```text
/Users/jacquelinehenriksen/sh-corpus-scripts
```

The builder expects the dashboard corpus, metadata export, edition-change
register, and local MusicXML cache there. It refuses to build a partial corpus
when the required metadata sources are absent.

### Refresh and build

Run from the repository root:

```sh
npm ci --ignore-scripts --no-audit --no-fund
python3 scripts/verify_dependencies.py
python3 scripts/fetch_shapenote_scores.py       # only when refreshing score mappings
npm run prepare-data
```

`prepare-data` runs the corpus builder and candidate reconciliation. It writes
the generated index, coverage queue, lazy score assets, and publication
overlays. Source-retention, image, recording, and candidate commands are
separate because they have different inputs and evidence boundaries.

Do not run source-dependent generators blindly against missing or stale inputs.
Inspect the [OpenClaw handoff](OPENCLAW_HANDOFF.md) before restoring retained
evidence or resuming transcription work.

### Source and review commands

Use only the commands needed for the lane being advanced:

| Command | Result |
| --- | --- |
| `npm run index-source-images` | Refreshes confirmed 2025 source-image URLs. |
| `npm run retain-source-images` | Retains source images with URL and checksum provenance under ignored `work/`. |
| `npm run prepare-transcription-images` | Creates versioned review layers without changing immutable originals. |
| `npm run build-image-review-queue` | Publishes the current image-review queue. |
| `npm run run-cleaned-omr -- --record <id>` | Runs bounded OMR against the deterministic normalized review layer. |
| `npm run audit-omr` | Audits OMR outputs and review warnings. |
| `npm run build-review-queue` | Rebuilds the human-review index after draft changes. |
| `npm run build-source-comparison-ledger` | Rebuilds explicit source/candidate comparisons. |
| `npm run index-clean-source-candidates` | Finds/downloads comparison PDFs; candidates remain unverified. |
| `npm run validate-source-candidates` | Checks candidate PDF signatures, hashes, and fail-closed status. |
| `npm run build-shared-edition-reconciliation` | Rebuilds edition-pair relations. |
| `npm run validate-shared-edition-reconciliation` | Validates those relations against the current corpus fingerprint. |

Every correction or transcription must be versioned. Preserve the original
scan/MusicXML, evidence JSON, hashes, and superseded candidates. Do not make a
JSON-only correction when the downloadable MusicXML is the artifact users will
actually inspect.

## Development workflow

### Run the browser app

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run dev
```

Open the URL printed by Vite. The development server binds to `127.0.0.1`.
The separate `public/audio-harness.html` page instruments browser audio for
verification; it is not part of the reader UI.

For a static preview:

```sh
npm run build
npm run preview
```

### Run focused checks

After changing generated data, score parsing, playback, or discovery, run the
narrow checks that cover the changed layer:

```sh
python3 scripts/validate_data.py
python3 scripts/validate_playback.py
python3 scripts/validate_transposition.py
node --test tests/*.mjs
```

The JavaScript tests use Node's built-in test runner and are not currently
exposed as an `npm test` script. For browser behavior, follow
[`scripts/browser-smoke-test-plan.md`](../scripts/browser-smoke-test-plan.md),
capture a fresh receipt, and do not relabel an older receipt for a new commit.

### Aggregate verification

The fail-closed aggregate verifier checks generated artifacts, stale inputs,
promotion safety, queue consistency, data, playback, transposition, shape and
image review, source candidates, source health, browser smoke (when available),
production build, and startup:

```sh
npm run verify-all
```

Useful bounded options include:

```sh
npm run verify-all -- --no-build
npm run verify-all -- --no-write
npm run verify-all -- --skip-source-health-collection
npm run verify-all -- --allow-missing-optional
npm run verify-all -- --source-health-online --source-health-max-urls 25
```

Online source-health checks require an explicit positive URL cap. Offline mode
validates the existing report without claiming a fresh network sweep. The
verifier writes `work/verification/verification-receipt.json` and
`work/verification/verification-receipt.md` unless `--no-write` is used.

### Build the macOS wrapper

The SwiftUI wrapper bundles the built dashboard and serves its score assets from
a private local service:

```sh
bash script/build_and_run.sh
bash script/build_and_run.sh --verify
```

The output app is `outputs/The Shape-Note Atlas.app`. `--verify` checks the
static package/startup contract; it does not by itself prove native-window
interaction or public deployment.

## Contribution rules

Before editing:

1. Run `git status` and preserve unrelated changes.
2. Read the current handoff and any lane-specific evidence package.
3. Confirm that the source is the intended edition and that retained bytes
   match their recorded hashes.

When adding notation:

- compare the actual exported MusicXML, not only an evidence JSON file;
- preserve parts, event order, pitch, duration, clef, voice, staff, ties,
  repeats, endings, lyrics, and notehead geometry when the source establishes
  them;
- keep source notehead evidence separate from pitch-derived shape labels;
- leave missing lyrics, shapes, mode, repeats, and verse numbers unavailable;
- keep `safeToPromote: false` until the exact source-review gate is satisfied;
- publish a new candidate version instead of overwriting an earlier one; and
- stage only the reviewed batch.

When changing application behavior:

- keep alternate editions visibly labeled;
- stop and clean up playback when its source state changes;
- do not borrow a key from another edition to unlock transposition;
- add or update focused tests;
- run a fresh browser check for user-visible behavior; and
- report local tests, browser proof, build status, merge/push state, and
  deployment separately.

The project is intentionally a little suspicious of convenient certainty. That
is how a tune catalogue stays useful instead of becoming a very polished set
of guesses.

## Related documents

- [Project README](../README.md) — source policy and command inventory.
- [OpenClaw handoff](OPENCLAW_HANDOFF.md) — retained evidence, current lanes,
  and non-negotiable source rules.
- [Program status](OPENCLAW_PROGRAM_STATUS.md) — dated continuation notes and
  verification receipts.
- [Browser audio smoke plan](../scripts/browser-smoke-test-plan.md) — required
  runtime cases and receipt expectations.
