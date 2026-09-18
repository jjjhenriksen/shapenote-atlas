# Shape-Note Atlas: active backlog

Updated **2026-09-18**, following the audit of implementation commit
`3fbfeeffe0d36423525d1910b2ea0e2e29b26c27`.

This is the authoritative dispatch list for new Atlas work. It supersedes the
unfinished-work lists in older handoffs and the dated packets under `backlogs/`.
The [program status](docs/OPENCLAW_PROGRAM_STATUS.md#2026-09-18-current-state-audit)
explains prior work; the [source handoff](docs/OPENCLAW_HANDOFF.md) retains the
source and preservation rules. Neither a green build nor a published practice
draft means the eleven-book project is finished.

## Start here

1. Inspect the current branch, changes, recent commits, and publication manifest.
   Confirm whether another contributor already completed the selected item.
2. Select one unchecked item below. Record the item ID, owner/session, exact
   records and files, starting commit, and intended next version before editing.
   Items are unassigned unless an owner is recorded; listing them here does not
   start background execution or authorize duplicate workers.
3. Read its retained source and latest candidate. Verify the pinned hashes.
   A clone contains published assets, but not every retained scan or lane input.
   Missing evidence is a specific prerequisite to restore, never a reason to
   invent content or skip the source check.
4. Complete a bounded batch, validate the actual exported bytes, and preserve
   all issued predecessors. Record a precise next step for anything unfinished.
5. Commit only the reviewed task files, push to `origin/main` without force,
   verify the remote head, and update this backlog with evidence. Public site
   deployment, source redistribution, and sending a correction are separate
   actions; a repository push does not prove them.

**Default next task: ATLAS-01**, the source-backed New Salem first-line repair.
After it, prioritize useful extensions to existing partial scores (ATLAS-02 and
ATLAS-03), then the lyric/shape lanes and new notation batches. Recheck the runtime
only as required by an actual change; do not repeatedly rerun completed audits.

## Current baseline and completed work

| Measure | Verified baseline |
| --- | ---: |
| Distinct songs | 3,547 |
| Book appearances | 4,202 |
| Structured score mappings | 1,155 |
| Missing score mappings | 3,047 |
| Additional SH2025 correction records | 13 |
| Pinned human-correctable publications | 18 |
| Validated review draft assets | 138 |
| Known retained-source prerequisite paths present | 1,546 / 1,546 |
| Required aggregate checks passed at the implementation commit above | 20 / 20 |

The 3,047 missing mappings and 13 correction records represent **3,060
outstanding records**, not 3,060 independently diagnosed blockers. Existing
structured mappings still require their own printed-edition fidelity review.

Do not redispatch these as missing initial implementations:

- [x] Social Harp source-page identities: **221 mapped / 0 unresolved** for the
  existing catalogue, through [supplement 19](work/openclaw-socialharp-nineteenth-20260911/README.md).
  This completes page identity, not transcription or the 221/222 inventory question.
- [x] Afton v27 is published: 251 pitched notes and 158 lyric anchors. The P3 m12
  `dis` onset correction is already in v26 and preserved in v27.
- [x] A Glimpse of Thee v1 is published: four complete measures in all four voices,
  60 pitched notes, and directly observed notehead shapes.
- [x] New Salem and Something New v3 contain their full written notation extents.
  Do not restart their opening-measure transcriptions.
- [x] Encoded-repeat playback, pause/resume, cancellation, and bounded practice
  loops exist. New Salem schedules 167 notes in written order and 334 following
  its encoded repeat. Its obsolete limitation was corrected in `3fbfeef`.
- [x] The local macOS package builds and passes package/static-preview startup.
- [x] Fresh browser audio and desktop/mobile checks passed at `3fbfeef`.
  Native-window interaction and live deployment are still unverified.

Receipts, screenshots, and the full audit are committed under
[docs/handoff/review-20260918](docs/handoff/review-20260918/README.md).
They remain evidence for their recorded implementation commit. Later docs-only
commits must not relabel those receipts as newly executed runtime tests.

## Work items

### ATLAS-01 — P1 — Repair New Salem's garbled first line

**Status:** open. **Record:** `kentucky 10 — New-Salem`.

**Problem:** both the search result and tune detail currently show
`fort in will in on in` as the first line. This is an extraction fragment, not an
acceptable verified lyric incipit.

**Inputs:** retained `work/luna-program-20260904/source_only/retained-sources/kentucky-010-new-salem.pdf`;
[New Salem v3 source evidence](work/openclaw-openings-v3-20260907/kentucky-new-salem-evidence-v3.json);
`public/corpus.json`; `scripts/build_data.py`. Trace the current value through
`/Users/jacquelinehenriksen/sh-corpus-scripts/dashboard/data.js` and
`rag_web_metadata.csv` before choosing the smallest durable correction point.

- [ ] Read the exact printed lyric opening and record source page, coordinates,
  hash, and transcription. Do not substitute a remembered lyric or another edition.
- [ ] Repair the authoritative upstream value or add a documented, source-backed
  generator override; an edit only to generated `public/corpus.json` is insufficient.
- [ ] Retain the raw extraction/provenance and stable record ID. Do not claim that
  fixing a catalogue first line completes note-level lyric underlay.
- [ ] Regenerate only with complete verified inputs, or use the established scoped
  overlay approach. Prove unrelated records and musical data remain unchanged.
- [ ] Verify search by the corrected first line and the displayed result/detail
  text on desktop and mobile. Run data/discovery checks and relevant aggregate checks.

**Done when:** the source-backed incipit survives regeneration and matches in
search and detail views. If the scan cannot establish it, show an honest unavailable
state and record the exact missing evidence; do not mark lyric transcription complete.

### ATLAS-02 — P1 — Extend A Glimpse of Thee beyond measure 4

**Status:** open; retained source exists. **Book:** Sacred Harp Tunes.

**Start:** [published v1 package](work/openclaw-sacredharptunes-glimpse-20260911/README.md)
and the `sacredharptunes-glimpse` entry in
[scripts/review-publications.json](scripts/review-publications.json).

- [ ] Inspect printed measure 5 onward in all four voices and choose one complete,
  bounded next segment. State the exact ending measure of the batch.
- [ ] Export a new MusicXML/evidence version with the four-measure v1 prefix
  unchanged, except separately justified source corrections.
- [ ] Verify every added pitch, duration, onset, clef, accidental and literal
  notehead against source coordinates; validate complete bar totals in every voice.
- [ ] Keep unreviewed stanza underlay, later repeats/endings and mode unavailable.
  Do not insert silence or a final barline at the excerpt boundary.
- [ ] Publish an editable partial review draft after timing, parser, source-link,
  download and correction checks pass; keep `safeToPromote=false`.

**Done for each batch:** the new segment is playable/downloadable with a precise
remaining extent and preserved predecessor. **Whole item remains open** until the
remaining printed music and required semantics are reviewed.

**Publication boundary:** the retained 2009 PDF and all source renders stay local.
Preserve `publicationPolicy: external-link-only`; comparison links to the original
PDF. Do not copy that source into Git or the public asset bundle.

### ATLAS-03 — P1 — Extend Zion's Dove after the current x502 boundary

**Status:** open. **Record:** Christian Harmony / 10.

**Start:** [v21 package](work/openclaw-zions-dove-20260907/README.md), pinned in the
publication manifest; retained scan at
`work/luna-program-20260904/existing_books/assets/christian-harmony/batch-01/scans/10-zions-dove.jpg`.

- [ ] Identify the next printed bar after x502 using the coordinate system in
  the existing evidence. Read each voice independently.
- [ ] Export a new version with the full v21 prefix preserved and no duplicated
  events or overlapping onsets. Source-check the exact added lyric anchors.
- [ ] Distinguish distinct-pitch slurs from ties. Leave unreviewed shapes and
  later navigation unavailable; do not revive rejected `land` / `And` alignment.
- [ ] Compare exported XML to evidence and predecessor, run parser/timing checks,
  and verify the updated partial publication's playback and editable download.

**Done for each batch:** complete added bars in every printed voice, with exact
remaining extent recorded. The whole tune is not complete merely because the
current partial score plays.

### ATLAS-04 — P1 — Complete Afton v27's remaining underlay

**Status:** open. **Start:** [v27 evidence and inventory](work/openclaw-afton-v27-20260911/README.md).

- [ ] Resolve P1 m8 `ripened harvest` onset/span from the scan.
- [ ] Resolve P2 m4's printed, unhyphenated `wonder,` without manufacturing a
  syllable division just to populate two notes.
- [ ] Resolve P3 m4 `see thy`, including the uncertain `see` onset at n3/n4.
- [ ] Audit P2 second-system alignment, inherited syllabic labels, and remaining
  multi-note spans; identify each residual gap by part/measure/note.
- [ ] Export each accepted change in a new version. Preserve all 251 pitches,
  explicit notehead geometry/fill, durations, rests and established anchors unless
  a separate source observation justifies a correction.

**Done when:** the per-event gap inventory is resolved or explicitly source-unavailable,
with actual XML parity. Do not add an unprinted bass lyric line, invent mode,
redispatch the fixed P3 m12 `dis`, or call empty staves missing music.

### ATLAS-05 — P1 — Improve SH2025 Devotion and Portsmouth lyrics

**Status:** open. These corrections are already available for practice.

**Start:** publication-manifest entries `sh2025-50t-devotion` **v10** and
`sh2025-537-portsmouth` **v2**; source/evidence paths in those entries and the
[source handoff](docs/OPENCLAW_HANDOFF.md#devotion--sh202550t).

- [ ] Devotion: establish P1 m15 `solemn` onset/span and voice-specific P2–P4
  continuation. Preserve 72 established lyric anchors and the source event stream.
- [ ] Devotion: inspect m16 first-ending underlay separately; retain established
  m17 `sound.` anchors without copying them into another ending.
- [ ] Portsmouth: directly inspect one complete interior measure across P1–P3;
  preserve v2 timing, terminal anchors, repeats and endings. Do not manufacture P4 lyrics.
- [ ] Export new candidate/evidence versions and compare actual lyrics, pitch,
  timing, ties and navigation with both source and predecessor.

**Done for each batch:** supported anchors improve the available publication and
remaining ambiguities are explicit. The thirteen correction records stay review-only
until their full exact-source review gates are satisfied.

### ATLAS-06 — P1 — Add New Salem / Something New lyric and shape evidence

**Status:** open; full written-notation v3 drafts and source pages already exist.
**Start:** [v3 package](work/openclaw-openings-v3-20260907/README.md).

- [ ] Select a bounded, complete passage per tune. Observe printed syllable
  placement separately for each voice and notehead shape/fill separately from pitch.
- [ ] Encode only observed lyric anchors, shapes, slurs and extenders in a new
  candidate/evidence version, preserving the established pitch/rhythm stream.
- [ ] Review explicit printed key labels separately from catalogue metadata;
  change mode/key authority only with documented exact-source evidence.
- [ ] Preserve New Salem's final backward repeat and Something New's lack of an
  encoded repeat. Do not mistake duration dots for repeat dots.
- [ ] Validate XML/source parity, updated downloads, transposition boundaries and
  both written-order and supported repeat playback where affected.

**Done when:** each targeted passage has exported source evidence and a residual
inventory. Full-song lyric/shape certification requires all printed passages,
not just a successful opening sample.

### ATLAS-07 — P1 — First useful Social Harp notation draft

**Status:** open; existing catalogue page identities are complete.
**Start:** [supplement 19 and its predecessor chain](work/openclaw-socialharp-nineteenth-20260911/README.md).

- [ ] Choose and name one mapped notation record and its exact PDF leaf/printed
  page/region. Check that another task has not already started its transcription.
- [ ] Transcribe at least one complete source-supported segment across every
  printed voice; keep continuation headings and adjacent tunes separate.
- [ ] Create a versioned, importable MusicXML draft and event-level source evidence.
  Leave unobserved lyrics, mode, shapes and navigation unavailable.
- [ ] Verify timing and exported bytes, then publish a clearly partial or complete
  practice draft through the manifest when the publication gates pass.

**Done for the first batch:** one usable, correctly labeled draft with exact source
linkage. All 221 missing structured mappings remain subject to their own admission
and fidelity criteria; neither page identity nor draft publication closes them.

**Boundary:** preserve the existing local-only source-PDF/render rules. Do not
restart page-mapping batches 8–19 or assume the 221/222 discrepancy is settled.

### ATLAS-08 — P1 — First useful Trumpet notation draft

**Status:** open. Ten formerly ambiguous leaf identities were already reviewed.

- [ ] Choose one retained notation page and confirm its literal heading, PDF leaf
  and printed page using the current Trumpet identity evidence/catalogue overlay.
- [ ] Exclude the three identified prose records from this notation selection;
  preserve their catalogue records pending the separate inventory migration.
- [ ] Produce a complete bounded segment across all printed voices, source-linked
  evidence, a new MusicXML version and an honestly limited practice publication.
- [ ] Verify actual XML timing, pitches and supported semantics, downloads and playback.

**Done for the first batch:** one source-backed usable notation draft, without
claiming all 105 historical appearances are tunes or exact mappings are complete.

### ATLAS-09 — P2 — Obtain missing exact witnesses

**Status:** open; source availability must be established per record.

- [ ] Southern Harmony / 12: obtain an identifiable printed-edition page and
  retain edition identity, origin, retrieval date and SHA-256. The already-classified
  modern derivative engraving is not sufficient printed-edition evidence.
- [ ] SH1991 / 322 and / 80b, Cooper2012 / 116: recheck only the exact dated
  endpoints when advancing these records; capture status, redirects and retained bytes.
- [ ] If an endpoint is still unavailable, record the precise failed URL, date,
  intended edition and next required source. Do not borrow another edition.
- [ ] Once obtained, compare the witness to the record and any candidate before
  changing source availability or mapping status.

**Done per record:** either an exact usable witness with verified identity, or a
current, record-specific blocker. A dated 404 is not proof of permanent impossibility.

### ATLAS-10 — P2 — Reconcile catalogue inventory and meter discrepancies

**Status:** open. Keep each correction independently reviewable.

- [ ] Social Harp: reconcile all 221 current records with the historical 222 count
  using the printed index/contents and reviewed page map. Identify the exact missing,
  duplicated or differently counted item; do not invent a 222nd record.
- [ ] A Glimpse of Thee: compare printed `L.M.D.` with catalogue `L.M.` and trace the
  upstream metadata source. Make a source-backed, regeneration-safe metadata correction
  while preserving stable IDs and the existing four-measure score.
- [ ] Trumpet: define the classification/count migration for the three prose records.
  Preserve provenance, stable references and deep links; update joins/coverage deliberately.

**Done per discrepancy:** documented source resolution, reproducible metadata handling,
consistent counts and unaffected unrelated records. Inventory cleanup is never
reported as newly completed notation.

### ATLAS-11 — P2 — Verify native macOS window behavior

**Status:** not yet verified. Build and package/static-preview startup already pass.

- [ ] Build the current implementation with `bash script/build_and_run.sh --verify`.
- [ ] Launch that exact bundle and inspect the native window, not only its embedded
  web assets served in a separate browser.
- [ ] Exercise tune lookup, source links, score selection, playback, pause/resume,
  stopping, reopening the app and offline retained assets where supported.
- [ ] Capture window evidence, relevant runtime errors and the exact tested commit.

**Done when:** actual native-window interactions pass with a reproducible receipt.
Do not label the existing package/static-preview check as native UI proof.

### ATLAS-12 — P2 — Verify the live hosted Atlas separately

**Status:** live deployment unverified by the September 18 local audit.

- [ ] Inspect the currently hosted Atlas and docs; identify the deployed revision
  or compare served assets with the intended implementation.
- [ ] Check direct tune links, docs navigation, score downloads, source-link policy,
  caching and primary practice controls at the actual hosted URL.
- [ ] Record deployed revision/equivalent asset hashes, observation time and failures.
  Fix deployment configuration only within the authorized release workflow.

**Done when:** the live site is verified against the intended release. A push to
`origin/main`, local build, or localhost screenshot is insufficient.

### ATLAS-13 — Ongoing — Advance all eleven books without losing coverage scope

**Status:** open. Recompute from tracked corpus/queues whenever canonical records change.

| Book / edition | Appearances | Structured mappings | Missing mappings | Concrete continuation |
| --- | ---: | ---: | ---: | --- |
| Sacred Harp 1991 | 554 | 552 | 2 | ATLAS-09; exact witnesses for 322 / 80b |
| Sacred Harp 2025 | 590 | 13 | 577 | ATLAS-05; remaining source-backed queue, plus 13 correction records |
| Cooper 2012 | 613 | 517 | 96 | ATLAS-09 for 116, then exact-source queue records |
| Christian Harmony | 669 | 3 | 666 | ATLAS-03; extend Zion's Dove, then retained-source batches |
| Shenandoah Harmony | 468 | 0 | 468 | ATLAS-06; improve Something New and select further retained witnesses |
| Southern Harmony | 335 | 70 | 265 | ATLAS-09; exact printed page-12 witness and remaining queue |
| A Supplement to the Kentucky Harmony | 133 | 0 | 133 | ATLAS-01 / ATLAS-06; New Salem metadata and source semantics |
| Social Harp | 221 | 0 | 221 | ATLAS-07 / ATLAS-10; notation and inventory, not repeated page mapping |
| Minnesota Harmony | 87 | 0 | 87 | ATLAS-04; Afton v27 underlay and remaining source-backed drafts |
| Sacred Harp Tunes | 427 | 0 | 427 | ATLAS-02; Glimpse m5 onward, then further exact witnesses |
| Trumpet | 105 | 0 | 105 | ATLAS-08 / ATLAS-10; notation and prose classification |
| **Total** | **4,202** | **1,155** | **3,047** | **All eleven books remain in scope** |

**Done for each record:** exact-source acquisition/transcription, all supported
semantics reviewed, provenance and source/candidate hashes retained, and the
applicable admission gate met. A draft may be useful and published earlier, but
it must not silently acquire verified-edition status. Unsupported fields remain
explicitly unavailable. Keep a record-specific blocker when evidence is absent.

## Required verification and publication gates

For notation changes, inspect the actual exported MusicXML/MXL and compare
part/measure/note counts, pitches, durations, cumulative onsets, voice/staff,
clefs, key evidence, lyrics, notehead shape/fill, ties/slurs, repeats/endings and
source/candidate hashes. Tests that repeat a new table do not prove source fidelity.

For metadata changes, prove the exact edited records and fields, preserve stable
IDs and unrelated scores, test regeneration, and refresh dependent ledger
fingerprints only after checking their underlying comparisons remain valid.

For practice publication, verify parsing/timing, honest completeness labels,
source/evidence links, byte-matched editable downloads, correction context and
browser playback. Keep `safeToPromote=false` until full source-review gates are met.
Preserve `external-link-only` entries and all other source-distribution boundaries.

Run the relevant existing focused checks before broader validation:

```sh
python3 scripts/verify_dependencies.py
python3 scripts/validate_data.py
python3 tests/test_review_publications.py
node --test tests/test_practice.mjs tests/test_key_resolution.mjs tests/test_discovery.mjs tests/test_notehead_evidence.mjs
```

For changed application/data releases, build the package, capture a fresh browser
receipt using [the replay plan](scripts/browser-smoke-test-plan.md), then run:

```sh
bash script/build_and_run.sh --verify
python3 scripts/verify_all.py \
  --skip-source-health-collection \
  --browser-receipt /absolute/path/to/fresh-browser-receipt.json
```

The browser checker ties evidence to a commit and asset hashes. The saved
September 18 receipt must not be relabeled to satisfy a later head. Source-health
validation here is offline; make any new network probe bounded and report its
actual date. Pure documentation updates need link/count/whitespace checks,
not a fabricated fresh runtime receipt.

## Completion record required for every item

Record the item ID and owner/session; previous and new versions; source hashes;
changed records/files; actual exported-byte checks; focused test results; browser,
native and live-site proof separately; commit and verified remote head; and the
next exact unresolved source location or prerequisite. Update the relevant checkbox
only for work actually completed. Keep this backlog and the publication manifest
consistent so another task does not repeat finished work.
