# Atlas program continuation — 2026-09-07

Companion to the full [OpenClaw handoff](OPENCLAW_HANDOFF.md), not a replacement for its source rules or an all-book completion claim.

## Goal and delivery loop

Advance exact-source coverage across **all eleven books**, in small independently verified commits. Afton is one lane, not the project. Keep notation, lyric alignment, provenance, playback, discovery, and validation in scope. Existing structured mappings do not prove printed-edition fidelity.

One coordinator owns Git and integration. Workers own separate new record/version directories. For each batch: inspect current local handoffs and exact retained source; export a new candidate; verify actual XML and predecessor preservation; commit only the reviewed batch. Never stage the whole checkout. Publish useful human-correctable review drafts as soon as parsing, timing, provenance, and correction/download checks pass; do not wait for complete lyrics or every shape audit. Reserve exact-edition verified status for completed source review. The user explicitly prioritized early promotion with human correction on 2026-09-07. Application changes require focused runtime/browser checks; source-only review packages do not claim that proof.

## Current canonical scope

Recomputed from `public/source-coverage.json`, `public/transcription-queue.json`, and `public/human-review-queue.json` on 2026-09-07. The initial source-only cycle changed no canonical records. The next delivery publishes review drafts without increasing verified mapping counts.

| Book / edition | Appearances | Structured mappings | Missing mappings |
| --- | ---: | ---: | ---: |
| Sacred Harp 1991 | 554 | 552 | 2 |
| Sacred Harp 2025 | 590 | 13 | 577 |
| Cooper 2012 | 613 | 517 | 96 |
| Christian Harmony | 669 | 3 | 666 |
| Shenandoah Harmony | 468 | 0 | 468 |
| Southern Harmony | 335 | 70 | 265 |
| Kentucky Harmony | 133 | 0 | 133 |
| Social Harp | 221 | 0 | 221 |
| Minnesota Harmony | 87 | 0 | 87 |
| Sacred Harp Tunes | 427 | 0 | 427 |
| Trumpet | 105 | 0 | 105 |

**3,047 missing mappings + 13 SH2025 corrections = 3,060 outstanding records.** The shared-edition ledger's 448 SH2025 pairs without exact SH2025 scores remain reference-only; an alternate edition cannot close them.

## Committed milestones

| Batch | Commit | Proof | Remaining boundary |
| --- | --- | --- | --- |
| Afton v25 | `d6cdc49` | [Package](../work/openclaw-afton-20260907/README.md): eight lyric anchors; 251 pitches/noteheads preserved; Atlas parser accepts | P1 m8, P3 m12, melisma and full review remain unresolved; `safeToPromote=false` |
| Zion's Dove v21 | `70a805d` | [Package](../work/openclaw-zions-dove-20260907/README.md): seven notes, two corrected anchors, exact v17 prefix, 33 historical files unchanged | Later second-system content and shape audits remain incomplete; `safeToPromote=false` |

The current local existing-books handoff listed a v20 beyond the original overarching document's v17/v19 checkpoint. Direct scan review rejected v20's inherited `land`/`And` and second-note `The` appendix. V21 preserves v17 and supersedes that appendix without deleting any version. Inspect current lane files before resuming; document version numbers are not authority by themselves.

## Next bounded batches and dependencies

Lane root below: `work/luna-program-20260904/`.

1. **Trumpet page identity:** directly resolve or explicitly retain blockers for p116, p125, p139, p187, p20, p265, p42, p45, p47, p74 using `source_only/trumpet-page-map-20260904.json` and `source_only/retained-sources/trumpet-composite-vol-1-5.pdf`. Preserve 95 existing matches. Distinguish PDF leaf, printed page, and literal heading. No guessed title reconciliation or notation.
2. **Devotion:** resume exact P1 m15 `solemn` onset/span and voice-specific continuation from v10 using the scan and paths in the original handoff. Two worker follow-up attempts failed before execution with native hook relay timeouts; no new source review or artifacts were produced in this cycle.
3. **Social Harp:** resolve first five currently unmapped headings from `source_only/socialharp-page-map-20260904.json` against `retained-sources/socialharp-1855-imslp-scan.pdf`. Start with 101 PARTING FRIENDS and 103 MOSLEY; select the next three from the current unresolved array. Preserve the 221-versus-222 discrepancy until source evidence settles it.
4. **Zero-mapping book openings:** independently transcribe one complete opening measure across every printed voice from `source_only/retained-sources/kentucky-010-new-salem.pdf` and `shenandoah-010-something-new.jpg`. Record coordinates and actual XML parity; withhold unknown shapes, lyrics, and mode.
5. **SH2025/537 Portsmouth:** inspect one interior measure P1–P3 against `work/source-pdfs/official-sh25-scans/SH25-PORTSMOUTH.jpg`; preserve the v2 event stream and terminal anchors. No manufactured P4 lyric line. Inspect `sh2025/537-portsmouth-evidence-v2.json` and candidate before exporting v3.
6. **Existing-book fidelity:** establish whether `existing_books/assets/southern-harmony/sh-12.pdf` is an exact printed witness or derivative-only before any fidelity promotion. Separately recheck only the retained SH1991/322, /80b and Cooper/116 endpoints; dated 404 observations are not permanent impossibility.
7. **Continue active notation:** Afton P1 m8/P3 m12 and Zion after x502 remain explicit source-review tasks, not claims that the whole tunes are done.

Keep Sacred Harp Tunes and every other zero-mapping book visible in the table even when not assigned in the current batch. Do not replace the all-book objective with whichever scans happen to be easiest.

## Verification and infrastructure boundaries

- Both committed builders/verifiers reran successfully; parent additionally inspected Zion's retained scan.
- The broader reproducibility preflight ran 12 tests: 11 passed, one errored while reading existing `public/shapenote-2025-score-audit.json` with `Resource deadlock avoided`. No full-app verification claim.
- Git initially failed on an unreadable derived pack index and five tree objects. The index was regenerated from a readable pack; exact-hash tree bytes were recovered from a separate GitHub object copy. Original unreadable files were preserved; no reset, cleaning, or unrelated working-file replacement occurred.
- Unrelated untracked files, including iCloud duplicates, remain untouched. Do not clean them to make a status report appear clean.
- Command Center menu service remains absent; no service repair or operational dispatch was performed.
- Initial three commits were local. Draft publication and push status are recorded below. Historical predecessor files remain local-only dependencies; published review packages include their editable XML and source comparison assets.


## First usable draft publication

Afton v25 and Zion's Dove v21 are now attached to their live corpus records as published review drafts. Afton covers the full notation extent; Zion is explicitly partial. Both have playable pitch/rhythm data, editable MusicXML downloads, retained source comparison, evidence links, and a GitHub correction form with tune/version context. No issue is sent automatically. Mode stays unknown until the user supplies a key for transposition.

`scripts/review-publications.json` pins the releases; `scripts/review_publications.py` reapplies them after data regeneration. Missing local source files fall back to hash-checked tracked publication assets; changed source bytes are rejected. Verified mapping counts stay unchanged; the two drafts are available without waiting for complete source-semantic certification.

Validation: three publication tests passed, plus 19 playback/discovery/key tests and the Vite 7.3.6 production build in an isolated checkout with locked dependencies. Browser checks on desktop and 390px mobile passed for playback, pause/stop, manual-key transposition, byte-matched editable downloads, source/evidence HTTP links, correction context, and expandable known gaps. No browser errors or warnings in the final check. GitHub Issues is enabled; no correction was submitted during testing.

The existing full data validator remains unavailable in the isolated clone because `work/source-transcriptions/2025/clean-source-candidates.json` is a local-only dependency. This is focused draft-publication proof, not an all-application or all-book certification. The shared checkout's unreadable `index.html` was not replaced; isolated runtime proof used the same tracked base plus the exact changed files.

## Second delivery cycle — 2026-09-07

Completed three bounded handoff batches and a catalogue integration, with one Git owner:

| Result | Commit | Boundary |
| --- | --- | --- |
| All ten unresolved Trumpet leaves visually reviewed: seven notation identities, three prose pages; 95 earlier mappings preserved | `3636def` | Page identity, not notation transcription |
| Five Social Harp headings resolved: 101, 103, 104, 105, 107; additive mapping 67 → 72, unresolved 154 → 149 | `69b5839` | Original map and 221/222 discrepancy preserved; renders remain local |
| Thirteen SH2025 corrections published for practice and human correction | `6f7c40f` | Existing structured scores preserved; explicit Score version selector; no verified-edition promotion |
| Trumpet catalogue titles corrected and prose records visibly labeled; ten reviewed page links and identities integrated | `cc3f606` | Stable IDs, raw text, score mappings and coverage counts preserved |

SH2025 publications: 118 Heavenly Meeting v2, 50t Devotion v10, 55 Converse v2, 169 God's Helping Hand v1, 537 Portsmouth v2, 544 Youthful Blessings v1, 41 Evening Hymn v2, 415 Endless Praise v3, 525 Imandra v2, 545 Somers v3, 557 New Farewell v2, 563 Suffield v2, and 575 Lisbon v1. There are now **15 pinned human-correctable publications**, including Afton and Zion's Dove. Each new publication includes candidate MXL, original MXL, retained scan, evidence and limitations. Pitch-derived shapes remain review-only; New Farewell's missing lyrics and D.C./linear-witness boundary are explicit. Unknown keys are not filled from catalogue metadata.

The publisher now supports unchanged compressed MXL and verifies complete source part structure except the documented lyric/notehead/mode additions. All thirteen source note streams, durations, ties, repeats and endings were preserved. Suffield's unreadable raw file was checked against an exact-hash retained-bundle copy without replacing the original. New tests run using tracked publication assets without requiring local lane files.

### Current verification receipts

- Four publication tests passed in both source checkout and fresh isolated checkout: actual pitch streams, raw-part preservation, all download hashes, regeneration without local sources, idempotency, and reject-before-write behavior for hash changes and rehashed pitch corruption.
- One catalogue overlay test passed; independent full-corpus comparison confirmed exactly ten target records changed and all unrelated songs, IDs, score fields and count summaries remained unchanged.
- Both source identity package verifiers passed. These establish integrity and coverage, not a substitute for the recorded direct visual reviews.
- Locked Vite 7.3.6 production build and all 19 discovery/key/playback JS tests passed after the final UI changes in `/private/tmp/atlas-objectives-runtime-20260907`.
- Browser: all thirteen correction drafts selected, played and stopped; all 52 local download/evidence links returned success. Devotion pause/resume controls and stopping playback on version switch passed. The existing score stays selectable.
- Desktop and 390px mobile correction controls rendered and switched successfully; no browser errors or warnings were reported during publication checks. Horizontal overflow remains in the score rendering on mobile; the correction panel itself fits. Browser plugin absent; Playwright CLI used at `http://127.0.0.1:5187/`.
- Trumpet browser check confirms corrected JOSHUA discovery/detail title and stable old-ID deep link to PDF leaf 116. Prose records are retained as articles, not removed from historical inventories.
- Full evidence-dependent aggregate verification and public deployment were not claimed. Shared checkout filesystem errors persist; no services were repaired.

### Next bounded work (supersedes the completed first batches above)

1. Social Harp: select the next five unresolved headings after 101/103/104/105/107, incorporating the additive supplement rather than redoing it.
2. Kentucky Harmony and Shenandoah Harmony: first complete opening measure across every printed voice, then publish correctable partial drafts once event timing and source linkage pass.
3. Continue Afton P1 m8/P3 m12 and Zion after x502 as new versions; existing publications should remain available throughout.
4. Devotion/Portsmouth: remaining lyric work improves published drafts; it no longer blocks access to the current corrections.
5. Recheck the bounded SH1991/322, /80b, Cooper/116 source endpoints and Southern Harmony 12 witness fidelity when advancing those books.

The all-eleven-book mission remains open. Draft publication does not reduce the 3,047 missing exact mappings or certify the thirteen SH2025 correction records. The three Trumpet prose records remain in historical counts pending a separately defined inventory migration; they must not be described as three newly completed scores.
