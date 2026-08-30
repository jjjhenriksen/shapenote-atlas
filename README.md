# The Shape-Note Atlas

A lightweight, source-faithful Sacred Harp lookup workspace. It keeps the existing corpus dashboard as the metadata source of truth, then adds complete MusicXML scores and browser playback only where an exact score mapping is available.

## Local source policy

- Corpus records come from `/Users/jacquelinehenriksen/sh-corpus-scripts/dashboard/data.js`.
- Score enrichment comes from `/Users/jacquelinehenriksen/sh-corpus-scripts/rag_web_metadata.csv`, the local `.cache/rag_metadata` MusicXML cache, and the checked-in `public/shapenote-score-manifest.json` produced from the authoritative [Shape Note Music Files index](https://shapenote.net/music.htm).
- Run `python3 scripts/fetch_shapenote_scores.py` when refreshing the public MusicXML mappings. Raw downloads stay under ignored `work/`; the manifest records each source URL and exact book/page or tune-title mapping.
- `scripts/build_data.py` refuses to build if the corpus metadata sources are missing.
- Records without an exact structured MusicXML mapping remain searchable and source-linked. Where a book publishes a PDF or page-image scan, the detail view presents that source notation and clearly disables transposition/playback for it. A parsed score from another edition may appear as a transposable reference witness, but it is labeled as such and never substituted for the selected edition. Local OMR drafts are exposed separately as playable/transposable review work product, never as verified notation. No notation is fabricated. When a structured witness has pitches but omits its key signature, the app offers an explicit source-key chooser; the user must select the key printed in the linked source before transposition is enabled, and that choice remains separate from source metadata.
- `public/source-coverage.json` is the generated edition-specific coverage ledger. Every book/page record is classified as `structured-score`, `source-reference`, `transcription-blocked`, `metadata-only`, or `mapping-gap`, with its next safe action and recorded source URLs.
- If the metadata export lacks a row but the canonical corpus record already has a source-page or PDF URL, the builder retains that link as a `source-reference` and queues it for structured transcription; only records with neither metadata nor a source URL remain `mapping-gap`.
- `public/transcription-queue.json` is the generated work queue for every non-structured edition record. It carries a stable edition/page key, priority, authoritative source URLs, key/meter metadata where known, 1991/2025 reconciliation context, and the next safe acquisition or transcription action. Its records are validated to exactly match the non-structured coverage ledger.
- Run `python3 scripts/index_2025_source_images.py` to refresh confirmed direct 2025 page-scan URLs. The generated `public/source-image-manifest.json` is used only to show authoritative scan evidence and to seed transcription work; it never promotes an image into a transposable score.
- Retained transcription audits under `work/source-transcriptions/` are folded into that ledger. A blocked witness remains visible as blocked until a clean authorized source is acquired; the dashboard never treats a watermarked or other-edition witness as a transposable score.
- Retained source-page recording URLs are indexed by `scripts/extract_source_recordings.py` and exposed as source playback for the six audited 2025 pages (254–259). The official 88-song 2025 debut-singing collection is indexed by `scripts/index_2025_debut_recordings.py` and merged into the same source-witness path. These recordings are explicitly labeled non-transposable until structured notation is verified.
- Audiveris first-pass outputs under `work/omr/` are draft material only. `scripts/audit_omr_drafts.py` records their checksums, part/measure counts, and review warnings; the build publishes isolated `public/draft-scores/` assets so drafts can be auditioned and transposed during human review without entering verified score coverage.
- `npm run retain-source-images` retains the current 2025 source scans that still need transcription under ignored `work/source-images/`, reusing the eight already-retained originals and recording URL/checksum provenance in `work/source-images/manifest.json`. `npm run prepare-transcription-images` then creates immutable-source, versioned `normalized-v2` and `suppressed-v2` layers under `work/transcription-images/working/` for every local source-page image. v2 retains the complete source frame; the suppressed layer is a visual aid only. The eight named 2025 `working/2025/*-cleaned-v1.png` copies remain inventoried as AI-edited, human-review-only images and are fail-closed for OMR. `npm run build-image-review-queue` produces `public/image-review-queue.json`; `npm run validate-image-review-queue` checks coverage, source hashes, working hashes, and fail-closed status. Audiveris outputs remain review-only and never replace the original scans or canonical draft queue.
- `python3 scripts/run_cleaned_omr.py --record <song-or-source-stem>` runs bounded draft OMR against the deterministic `normalized-v2` layer by default. Results are written to a separate `cleaned-v2` ledger and are joined into the human queue without becoming canonical notation; the suppressed-v2 and unsafe AI-edited layers remain explicitly non-authoritative.
- `public/human-review-queue.json` and `work/omr/human-review-queue.md` pair each local OMR draft with its source page/image, rendered draft, checksum, review checklist, and remaining 2025 backlog. Run `npm run build-review-queue` after changing drafts.
- `public/source-comparison-ledger.json` records explicit source-versus-candidate comparisons without authorizing promotion. Add auditable records under `work/source-transcriptions/2025/*-comparison.json`, then run `npm run build-source-comparison-ledger`; local witness checksums are verified and every record remains fail-closed.
- `public/image-review-queue.json` and `work/source-images/image-review-queue.md` track every current 2025 record that still lacks exact or reference structured notation, with immutable originals plus normalized-v2 and suppressed-v2 review layers. Run `npm run retain-source-images`, `npm run prepare-transcription-images`, and `npm run build-image-review-queue`; validate with `npm run validate-image-review-queue`. Working layers never become authoritative notation automatically.
- `npm run index-clean-source-candidates` checks the local crosswalk for public composer/source PDFs and downloads candidates under `work/source-transcriptions/2025/clean-source-candidates/`. These are clean comparison aids, not 2025-edition scores: each record remains explicitly unverified until it is compared note-for-note against the authorized 2025 engraving.
- The atlas carries those comparison leads onto each affected tune record and shows them in the draft/missing-score detail view as `Comparison sources`; the public PDF link is available for review, but the candidate remains excluded from verified score coverage until edition comparison is complete.
- `npm run validate-source-candidates` verifies each downloaded candidate's PDF signature, checksum, and fail-closed edition status.
- `npm run validate-playback` checks every bundled structured score for finite timing, valid pitches, and at least one schedulable event wherever the asset is marked playable.
- `npm run validate-playback` checks every bundled structured score for finite timing, valid pitches, and at least one schedulable event wherever the asset is marked playable.
- `npm run run-clean-source-omr` runs Audiveris on single-page clean candidates and records isolated review drafts in `work/omr/clean-source-candidates/`; multi-page PDFs are intentionally skipped by default, with `--max-pages 2` available for short candidates.
- `npm run extract-composite-candidates` extracts only unambiguous score pages from retained multi-page candidates for isolated review; the composite source and page number remain recorded.
- `npm run build-candidate-reconciliation` compares candidate OMR structure with the existing 2025 scan draft to prioritize human review. It is triage evidence only: every record remains `safeToPromote: false` until direct edition comparison is complete.
- `public/edition-2025-additions.json` records the publisher's 113-song 2025 additions list. The review queue uses it to separate new 2025 material from retained or revised records; it never treats editorial status as notation evidence.
- The 1991/2025 change register is represented as explicit edition-pair relations, including records that must remain separate because their page titles or text changed. Relation metadata includes each edition's source page and independent score availability. Shared records may expose an explicitly labeled transposable witness from the other edition for practice; it never becomes the selected edition's engraving.
- The current 2025 display set is reconciled to the authoritative 590-song Fasola index. The superseded local 414b export record remains under `legacyEditionRecords`; the hallucinated 264b record is discarded. Current 414b is Parting Friend, current 414t is Farewell Brethren, and current 484t is Millbrook. The current set has 14 exact 2025 MusicXML scores, 486 explicitly labeled transposable reference witnesses, and 121 records still awaiting verified structured notation. All 121 now have isolated OMR review assets: 98 include a source or detected draft key, while 23 expose a separate source-key chooser before transposition is enabled. Structured scores and review drafts with missing encoded keys are marked `manualKeyAllowed` in their asset metadata and use the same explicit chooser rather than an invented default. Of those 121, 89 are on the publisher's 113-song additions list and 32 are not new in 2025 but still need an edition-specific score; the corrected/additional records remain unverified until edition-specific structured scores are approved.
- MusicXML preserves the complete pitch/rhythm event streams and available parts, including duration type, dots, accidentals, clef, voice, staff, ties, and encoded notehead/shape fields when present. When a source score omits notehead names but records a major key, the UI derives the standard Sacred Harp four-shape sequence from exact pitch spelling and keeps the linked shape-source PDF as the authority; otherwise it leaves shapes unavailable rather than guessing.
- Shape-preserving source PDFs are linked from the matching [Shape Note Music Files](https://shapenote.net/music.htm) entries. That source also provides four-shape-aware `.mus` files, while the PDF is the visual reference for source comparison.
- The score view wraps the complete song into vertical four-measure systems; playback schedules the complete selected source, not a four-measure excerpt.
- For browser-level audio proof, run `npm run dev` and open `/audio-harness.html`. This isolated test page wraps `AudioContext` before loading the app and reports the actual oscillator frequencies and start/stop calls; it is instrumentation only and is not part of the dashboard UI.

## Current notation audit

The local corpus indexes 3,547 tune records across eleven books. The Sacred Harp 2025 display set contains 590 current edition records. Complete-score MusicXML is currently available where the local cache or public Shape Note Music Files source validates it: 950 song records backed by 1,156 lazy score assets across Sacred Harp 1991, Sacred Harp Cooper, Southern Harmony, Christian Harmony, and 14 exact 2025 mappings. A further 486 current 2025 records have explicitly labeled transposable reference witnesses from shared 1991 records or other sources; these remain separate from exact 2025 coverage. Every remaining edition record now has either a retained source-page/PDF reference or an explicit blocked status in the acquisition queue; the app does not substitute a different edition or synthesize missing notation.

## Run it

```sh
npm install
npm run prepare-data
npm run dev
```

For a deployment check:

```sh
npm run build
npm run preview
```

## Open it as a Mac app

The packaged app is in `outputs/The Shape-Note Atlas.app`. Double-click it in Finder to open the atlas in its own window. It bundles the production dashboard and starts a private local service for the score assets, so no separate browser tab or development server is required.

The Mac wrapper uses a SwiftUI window shell with a hidden title bar, so the dashboard header is the only visible app chrome while standard window controls remain available. The reader itself remains the same browser-compatible score surface, so the app and hosted dashboard share one source of truth.

## Reproducible verification

Run `npm run verify-all` from the project root for the aggregate fail-closed verification receipt. It checks generated-artifact integrity, stale source inputs, unsafe missing-mode defaults, promotion safety, queue contradictions, data, playback, transposition, shape-review, image, source-candidate, source-health, startup smoke, and production-build checks. It writes machine-readable and human-readable receipts to `work/verification/` and also prints the JSON receipt.

Source-health verification is offline by default: it reuses the existing report and checks retained local evidence without making network requests. Remote checking requires both `--source-health-online` and a positive hard cap, for example `--source-health-online --source-health-max-urls 25`; an unbounded online run is rejected. Use `--no-write` to validate the existing report without regenerating it. The command returns a nonzero result when a required check fails, when review-only material is marked safe to promote, when generated data is stale, or when a parser can silently turn missing MusicXML mode into major. `--allow-missing-optional` keeps an unavailable optional worker visible under receipt `limitations` while allowing `overallStatus: passed` and `complete: true` when every required check passes; without it, an unavailable optional worker is a required blocker.
The bundle also includes a generated macOS icon from `Assets/ShapeNoteAtlas.svg`, so Finder and the Dock use the same four-shape mark.

To rebuild the app after source changes:

```sh
./script/build_and_run.sh
```

The script rebuilds the dashboard, stages the native app bundle, and opens it. If macOS shows a first-launch security prompt, Control-click the app, choose **Open**, and confirm once.

The lookup index is served as `public/corpus.json`, separate from the small application JavaScript, and complete scores are served as lazy-loaded assets under `public/scores/`. Static hosting can cache the index and only fetch a full song when it is selected.
