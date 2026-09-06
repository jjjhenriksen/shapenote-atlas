# Shape-Note Atlas: OpenClaw handoff

Prepared 2026-09-06 for Jacqueline. This is a continuation brief, not a completion claim. Read this document before editing or assigning work.

## Mission and current checkpoint

Continue implementation across **all eleven books and editions**, including source-backed notation, lyric alignment, provenance, playback, discovery, and validation. Implement what the actual retained source supports; document each remaining gap by record and exact requirement. Do not redefine success as a passing build or a few completed pieces.

Repository: https://github.com/jjjhenriksen/shapenote-atlas

Last verified implementation commit: `bdd6c49e5208aa9bb9c09f4a9872e6917cdefed2`, pushed to `main`. Eleven implementation commits were pushed during the preceding work. This documentation commit comes after that checkpoint; do not describe a later code revision as tested merely because this one passed.

At that implementation commit, an isolated checkout with restored retained evidence passed **20 required checks**, including data, playback, transposition, source/image validation, shared-edition reconciliation, browser checks, production build, and startup. The tracked tree stayed clean. Actual local versions were React/React DOM 19.2.8 and Vite 7.3.6. Source-health collection was intentionally skipped; the existing committed report was validated unchanged. No fresh network sweep is implied.

See [the copied aggregate receipt](handoff/verified-bdd6c49.json). Receipt paths describe the historical verification machine, not portable dependencies.

## First actions

1. Establish checkout and ownership. Run `git status`, read available repository instructions, inspect recent commits, and check whether anyone is actively editing the same files. The earlier Codex lanes were interrupted; do not assume they are still working or start duplicate workers without checking.
2. Read the generated corpus, queues, and provenance ledgers listed below. Keep canonical data separate from isolated candidates.
3. On Jacqueline's Mac, locate the retained evidence bundle and lane handoffs. On another machine, obtain those separately before attempting source-dependent validation or transcription. A Git clone alone does not contain them.
4. Install the locked local dependencies and run preflight. Never accept an ancestor/global Vite installation as project proof.
5. Resume one bounded source correction below. Inspect the scan and the actual exported XML; write a new version, validate it, and record the precise remaining gap.
6. Commit small, verified changes and push to main as Jacqueline requested. Coordinate a single Git owner if using multiple agents. Never force-push or stage unrelated concurrent changes.

## Checkout and local-only evidence

Established checkout on Jacqueline's Mac:

```text
/Users/jacquelinehenriksen/Documents/Codex/2026-08-27/sacred-harp-dashboard
```

The similarly named August 30 folder and generated September 4 task folders are not reliable substitutes. Some were empty. Do not copy the repository into an empty task folder to mask a wrong working directory.

Local lane root, relative to the established checkout:

```text
work/luna-program-20260904/
  COORDINATION.md
  THREADS.json
  data/retained-source-dependency-manifest.json
  data/evidence-bundles/retained-source-evidence-v4/
  sh2025/{STATUS.md,handoff.json}
  existing_books/{STATUS.md,handoff.json}
  source_only/{STATUS.md,handoff.json}
```

**These work files, retained scans, and many lane scripts/tests are ignored or untracked. This handoff does not upload them.** Version 4 of the evidence bundle restores dependencies for the verified application checkpoint; it is not a complete backup of the later transcription lanes. Transfer the lane directories and their referenced scripts/tests separately if moving machines, preserving all historical versions and hashes. Inspect each handoff's paths before declaring the transfer complete.

Evidence bundle v4 contains 2,602 files / 216,415,855 bytes. The dependency manifest covers 4,038 records, including 1,436 tracked dependencies supplied by Git.

- Source manifest SHA-256: `9e043665bd7c0413f2fe2eb818f4cfe51b8ebb8b862ee4915f2bc080c6b034d8`
- Bundle manifest SHA-256: `304c6a2f9490ae45c9c6545111f97cd4bfb2c1005875ce2f4d023dba59e29758`
- Verified committed source-health SHA-256: `f05744ff54eb5a665c1eb9078326f0c4a0652a84396afff1f581fa82cc21c365`

Use `scripts/local_evidence_bundle.py verify --bundle PATH` to verify the bundle. To restore, run the utility **from the existing source checkout**, targeting a separate checkout:

```sh
python3 scripts/local_evidence_bundle.py restore \
  --bundle work/luna-program-20260904/data/evidence-bundles/retained-source-evidence-v4 \
  --destination /absolute/path/to/separate-checkout
```

The utility restores missing files only and rejects conflicting bytes, symlink paths, traversal, and restoration into its own source checkout. Use a physical path: macOS `/tmp` is a symlink; `/private/tmp` or an actual Documents directory avoids that problem. Do not manually overwrite a conflicting file to get a green check.

Some generators also consume `/Users/jacquelinehenriksen/sh-corpus-scripts`. Run `scripts/report_fresh_checkout_prerequisites.py` and inspect the dependency manifest before regeneration. Do not run `prepare-data` blindly against missing upstream inputs.

## Verification and development

From the intended checkout:

```sh
npm ci --ignore-scripts --no-audit --no-fund
python3 scripts/verify_dependencies.py
python3 tests/test_agent_10_reproducible_validation.py
npm run build
```

Python 3.9.6 was used in the verified run. The macOS native wrapper needs the local Swift/Xcode command-line tools; inspect `script/build_and_run.sh` and `scripts/verify_startup.py` for current requirements. Use `npm run dev` for local browser work.

Full verification, after restoring source evidence and obtaining a fresh browser receipt for the tested commit:

```sh
python3 scripts/verify_all.py \
  --skip-source-health-collection \
  --browser-receipt /absolute/path/to/current-browser-receipt.json
```

Consult `scripts/browser-smoke-test-plan.md` and `scripts/verify_browser_smoke.py`. Re-run real browser interactions; never relabel an older receipt. Required coverage includes major/minor/unknown-key transposition, alternate-edition reference warnings, playable draft behavior, partial voice playback, automatic ending, and SH2025/497b source-key handling. Unknown source key must remain unavailable until entered explicitly.

Historical browser receipt: `work/luna-program-20260905/ui/agent-11-browser-receipt-bdd6c49-497b-v6-20260905.json`. Historical isolated verification directory: `/Users/jacquelinehenriksen/Documents/Codex/2026-09-04/atlas-luna-runtime/work/atlas-runtime-bdd-blzfF7/checkout`.

A previous receipt claimed success while `npm run build` used home-level Vite 8.2.1. That receipt was rejected. The current checker validates installed versions and the local Vite executable target, not just package-lock contents. Build output must agree with the lockfile.

## Corpus-wide unfinished scope

Verified checkpoint: 3,547 distinct songs, 4,202 book appearances, 1,155 catalogued structured score mappings, 1,317 unique referenced assets, 121 review drafts, 3,047 missing-score queue rows, and 90 image-review rows. A structured mapping is not proof of printed-edition fidelity. One invalid-duration draft remains quarantined; 1,316 assets are playable.

| Book / edition | Appearances | Structured mappings | Missing mappings |
|---|---:|---:|---:|
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

The outstanding inventory is 3,060 rows: 3,047 missing-score rows plus 13 SH2025 correction records. This is not a count of fully investigated blockers. Recompute from current files when canonical data changes.

Authoritative tracked files:

- `public/corpus.json`, `public/source-coverage.json`
- `public/transcription-queue.json`, `public/human-review-queue.json`, `public/image-review-queue.json`
- `public/semantic-fidelity-ledger.json`, `public/source-comparison-ledger.json`
- `public/shared-edition-reconciliation.json`, `public/source-health.json`
- `public/scores/`, `public/draft-scores/` as referenced by the corpus

The coordinator's local report is `/Users/jacquelinehenriksen/Documents/Codex/2026-09-04/look/outputs/atlas-unfinished-notation-records.json`; it is not included here. The tracked queues are available without that report.

The original 7,590 URL / 3,857 cache-missing claim was a historical exact-string, deduplicated HTTP(S) count under `corpus.songs`: 3,733 URLs intersected the old cache. Current corpus inventory is 7,600 URLs; the broader health inventory contains 7,619. These scopes differ. Retaining local source bytes does not establish fresh remote network health.

## Resume the source lanes

All candidates below remain isolated and **not safe to promote**. Re-read current handoffs and verify hashes; version numbers alone do not prove correctness.

### Afton — Minnesota Harmony

Latest reviewed candidate: `source_only/manual-transcription/afton-full-song-candidate-v24.musicxml` and `.json`, under the lane root above. Source: `source_only/retained-sources/mnharmony-afton.pdf`; render: `source_only/rendered-pages/mnharmony-afton.png`.

V24 serializes 251 pitched notes and 251 directly audited noteheads with explicit fill state. Root verified glyph/fill parity by part, measure, and note index and confirmed the other XML semantics were unchanged. The retained source is one page ending at a final barline; do not invent an unseen later-page blocker.

Next: enumerate exact remaining printed lyric-to-note gaps, then inspect measure 8 across P1–P3 and P3 measure 12's `dis-` / following `play,` boundary. Distinguish an unprinted bass lyric line from a missing transcription. Keep mode/tonal interpretation unknown where not explicitly established. The last worker turn was interrupted during this lyric inventory; no later completion is assumed.

Prior errors to avoid: guessed second-system notes, displaced syllables, and sidecar corrections never exported to XML. V22 P1 m12's last two glyph labels were reversed; current sequence is triangle, square, round, square, square, round. Preserve superseded versions.

### Devotion — SH2025/50t

Latest local candidate: `sh2025/50t-devotion-correction-v10.mxl`; corresponding evidence and interior-opening audit v10 are in the same directory. V10 contains 72 lyric anchors: the 68 supported v8 anchors plus P1 `Da` at m13 n1, `vid's` at m13 n4, `harp` at m14 n1, and `of` at m14 n4. Source notes, durations, ties, 8 repeats, and 4 endings are preserved. V9's open-ended lyric-extension markers were removed; `solemn` remains withheld.

- V10 candidate SHA-256: `e3d30c6fe426c6f985052a342de54ec3040140fe92ce76cceacfbbaa5fccb0cb`
- V10 evidence SHA-256: `66f42407a04c705621627ed1585d6749eeae7c9ca09d038f84627b6f808c5db7`
- Exact raw MXL: `work/shapenote-musicxml/25051a87a2fddb2c322ec07f.mxl`
- Scan: `work/source-pdfs/official-sh25-scans/isolated-audit/SH25-DEVOTION.jpg`

Next: directly establish P1 m15 `solemn` onset/span and the voice-specific P2–P4 continuation. Do not manufacture hyphenation for an unhyphenated printed word. M16 first-ending underlay remains unavailable; retain established m17 `sound.` anchors without copying them into another ending. Printed pickup before x≈113 is raw m1, not the following bar. P3 `tune` spans m11 n1–n2; `be` and `found,` are n3/n4. Never copy measure alignment across voices.

The other SH2025 isolated records are 118, 55, 169, 537, 544, 41, 415, 525, 545, 557, 563, 575. Follow `sh2025/handoff.json`. In particular: 415/545 current v3 preserve restored v2/v1; 544 has two verse lyrics on each retained terminal note, not inferred ending branches; 557 retains a D.C./linear-MXL navigation boundary; derived four-shape tags are review-only, not direct printed-glyph evidence.

### Zion's Dove — Christian Harmony / 10

Latest exported candidate is `existing_books/ch7-10-first-system-candidate-v17.musicxml` and `.json`. It contains the first system plus two second-system measures. Root verified exact v14 prefix preservation, seven added events per part, cumulative onsets 44/46/47/48/49/50/51, corrected split syllables, and omission of unaudited noteheads.

`existing_books/ch7-10-second-system-slur-evidence-v19.json` is **provisional evidence only**, not an exported v19 score. Next implement the x≈438–502 bar after direct scan review: upper voices appear to have two half notes; bass has one whole note. Preliminary pitches are Treble Eb5→Bb4, Alto Ab4→G4, Tenor C5→Eb5, Bass Eb3. These are inspection guidance, not permission to bypass the scan.

The v19 evidence's `lyricsObserved` is not accepted underlay: it lists tenor `land` / `And`, while this location must be checked directly against the printed phrase ending `be;`. Re-read the exact glyphs and word coordinates before serialization. Distinct-pitch curves are slurs, not ties.

Source: `existing_books/assets/christian-harmony/batch-01/scans/10-zions-dove.jpg`, SHA-256 `eba3f9387bf9b2ba9b83bee3e8c6f7abb33f37acb38ddf3f726423175af78584`.

Earlier bugs included overlapping JSON onsets, duplicated appended events, impossible coordinate tables, lost opening lyrics, and JSON-only fixes. Compare actual XML, event counts, and prior prefixes rather than writing tests that merely repeat a new constant table.

### Other books

Christian Harmony 1, 10, 100, 101, 102 have retained scans and canonical image provenance, not newly promoted notation. Existing structured witnesses include CH 543, 546b, 549b and Southern 12; their exact printed fidelity remains a separate review requirement.

SH1991/322 and /80b and all 96 missing Cooper mappings had source-access gaps in prior probes. Cooper116 has retained metadata but its structured witness returned 404. Treat these as dated observations, not eternal impossibility. Recheck a bounded exact source when useful; do not substitute another edition. For source-only books, retained PDFs/scans support manual work even when OMR software is unavailable.

## Non-negotiable evidence and delivery rules

- A matching title, tune, key, alternate edition, or visual resemblance is not exact-edition proof.
- Never infer missing lyrics, notation, mode, shapes, repeat topology, or lyric verse numbers to make an import pass. Preserve unknown values and explicit source boundaries.
- Observe notehead shape separately from staff-position pitch. Pitch-derived shape tags must stay review-only.
- Preserve immutable scans/MXL and every issued candidate/evidence version. Fix a released candidate in a new version; do not overwrite old bytes and silently reuse a version label.
- Preserve raw event streams unless a source-backed correction explicitly justifies changing them. Distinguish verses, numbered endings, repeats, ties, slurs, and lyric melismas.
- Compare actual exported MusicXML with the evidence: note count, pitches, durations, onsets, lyrics, noteheads, repeat/ending topology, and hashes. Passing tests that mirror incorrect JSON do not establish fidelity.
- Keep `safeToPromote=false` until all required exact-source semantics and review gates are satisfied. Do not alter canonical public data merely because an isolated candidate imports.
- Preserve unrelated changes and iCloud duplicate files (many names end in ` 2`). Avoid broad `git add`, reset, clean, or automatic source regeneration. One coordinator owns staging and pushing.
- Report implemented changes, tests, committed/pushed state, and remaining source gaps separately. Keep the all-book scope visible.

## Suggested initial instruction for the OpenClaw agent

Read `docs/OPENCLAW_HANDOFF.md`, establish the current checkout and retained-evidence availability, and report any differences from the verified bdd6c49 checkpoint. Continue one of the bounded source tasks with direct scan evidence and a versioned, importable correction. Validate actual XML against the source and preserved prior versions. Commit and push verified scoped changes to main while protecting concurrent work. Continue across the outstanding books; do not claim the corpus is finished because the application checks pass.
