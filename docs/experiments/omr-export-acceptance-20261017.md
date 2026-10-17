# Export survival and full-song acceptance evidence

2026-10-17. Follow-up to [head topology](omr-head-topology-20261017.md),
PR #487. These are **read-only analyses of consumed artifacts**, not another
recognition experiment, a new recognizer, or a source-certified score.

## Main finding

**The ten topology recoveries have no engine/export path yet.** They exist in
the research proposal list, not as inserted Audiveris heads/chords/voice slots.
They cannot be credited as corrected exported notes. Nor are they ten exporter
deletions: no engine insertion occurred.

The current source-supported bottleneck is broader than head detection.
Direct inspection of Thy Strength's retained source and source-only enlarged
halves finds **17 written measures on each of four staves**. Its saved native
export contains **8 per part**. Merged and misinterpreted regions must be
accounted for, rather than comparing source and export by a silent index zip.
This new grid/header reading is provisional same-agent development evidence,
after exposure to the consumed topology study; not independent gold.

## Retained opening-head trace: Thy Strength

`scripts/omr_export_trace.py` verifies the retained protocol/census/inference
lock/report/recognition receipts and raw graph/export/log bytes. It follows the
**existing geometric pairs**, never matching by pitch or using source labels to
force export attribution. Every source head and unpaired candidate stays in
the accounting. Actual exported event fields are retained locally for witnesses;
there is no full source event inventory against which to score their accuracy.

| Opening population / stage | Native | Native + topology proposals |
| --- | ---: | ---: |
| Source heads | 32 | 32 |
| Geometrically matched proposals | 20 | 30 |
| Matched heads with native graph identity | 20 | 20 |
| Matched native heads with timed slots | 18 | 18 |
| Matched heads with unique export-presence witnesses | 18 | 18 |
| Matched proposals not integrated into the engine | 0 | 10 |
| Source heads not detected | 12 | 2 |
| Matched native heads without timed slots | 2 | 2 |

All three retained radii (0.35, 0.5, 0.75 interline) give these same counts.
The five unpaired native candidates remain in both populations. They are not
automatically source errors or extra exported notes.

### Explicit pickup handling, not a changed historical trace

The historical `sh1991_fa_survival.graph_rows` excludes **all special stacks**
from export witnesses, including pickups. Its unchanged recipe yields **15**
opening witnesses and **70** across the full image. The new analysis permits
`PICKUP` geometry only when the exact native measure label exists once in each
exported part. It uses an analysis copy, keeps mutual uniqueness/context/layout
requirements, and still excludes `CAUTIONARY` regions. The extension finds three
pickup witnesses: **18** in the observed opening and **73** across the image.
Legacy counts and each new pickup attribution remain explicit in the report.

This is better attribution, **not improved recognition**. The full graph has
136 head nodes, 88 with timed slots, and the export has 92 timed pitched notes.
Nineteen exported notes lack unique graph witnesses; fifteen timed graph heads
lack unique export witnesses. Neither population difference proves deletions.
Layout presence does not establish correct pitch, duration, voice or source bar.

## Whole-written-song evidence audit

`scripts/omr_acceptance_audit.py` binds a source image, observations, score and
optional reviewed measure map by SHA-256. It audits the complete declared source
grid, not just favorable opening measures. It cannot authorize promotion.

| Required evidence | Thy Strength raw | Penn raw | Penn existing repair |
| --- | --- | --- | --- |
| Written measure grid | **Fail: 17 vs 8 / part** | **Fail: 12 vs 9 / part** | Pass: 12 / part |
| Opening key/clef/meter | Fail | Fail | Pass |
| Explicit full-grid alignment | Blocked: no reviewed map | Reviewed development map, including orphans | Equal declared grids; not independent alignment proof |
| Complete source event agreement | Unavailable/blocked | **33/120** | **120/120** |
| Observed playback tie endpoints | Unavailable | **2/16** | **16/16** |
| Observed-absent dynamics/articulations/ornaments | Unavailable | 15 unsupported candidates | 0 unsupported candidates |
| Literal shape/fill, lyrics, slurs, repeats/endings | Unavailable | Unavailable | Unavailable |
| Other markings, later header changes, visual tie notation | Unavailable | Unavailable | Unavailable |
| Separate source-reader verification | Unavailable | Unavailable | Unavailable |
| Whole-song disposition | **Blocked** | **Blocked** | **Incomplete** |

Thy Strength's directly observed source has two sharps and a bass clef on the
fourth staff. The export has one sharp on the upper parts; its fourth part has
a C-clef on line 4 and no encoded key signature. These are source-observation
comparisons, not an automated cause diagnosis or a correction already applied.

Penn reuses the existing [consumed full-grid development evidence and repair](omr-accuracy-tracks-20261016.md).
No new corrections or independent musical accuracy are claimed. Its raw score
retains **208 missing-plus-extra complete-event error units** against those
observations; the existing repair has zero. A wrong substituted event can count
as both a missing and an extra unit. Agreement with repair inputs does not
complete the still-missing annotation or independent verification layers.

### Audit schema and fail-closed behavior

- `expectedMeasuresPerPart` and full `segments` use the existing source-repair
  schema. Pitch/rest, rational duration/onset, staff and voice are compared as
  complete-event multisets. Explicit orphan draft measures count as extra events.
- A structure-only observation may omit `segments` and supply `writtenGrid`
  ordered `edges` and per-part `staffBands`. This enables a full-grid/header
  diagnosis, **not** an event-accuracy claim. Source extents are checked in-frame.
- Optional `literalHeads`, `lyrics` and `slurs` cover every event in every
  source segment. `repeatsEndings` covers every source measure. Their elements
  use exact semantic trees: `tag`, `attributes`, `text`, `children`, as returned
  by `projection()`. They must be recorded from source, never copied out of the
  candidate as an answer key. A pitched head needs explicit observed shape and
  `filled=yes/no`; absent encoding or duration cannot establish literal fill.
- Missing/partial/null annotation evidence is not a passing empty inventory.
  Explicit empty lyric/slur/repeat inventories mean source-observed absence.
  Playback `tie` checks do not certify printed `tied` glyphs. Grace events block
  event completeness because the current source event schema cannot score them.
- No `independent=true` flag can substitute for a separate blinded source-reader
  adjudication receipt. That lane is not delivered by this audit. Unimplemented
  or unobserved requirements stay unavailable; `safeToPromote` remains false.

## Verification and reproduction

**19 new fixtures pass; 132 OMR + 105 SH1991 = 237 Python tests pass**, with
zero skips using the retained Pillow 11.3.0 / NumPy 2.0.2 environment. New tests
cover research-only additions, exact native identity, pair reuse, pickup versus
cautionary contexts, rational export timing, raw artifact drift, grid mismatch,
orphans, source coverage, unknown shapes, lyrics, grace events, ties, manifest
drift, immutable replay and in-place write rejection. Existing CI discovers the
new `test_omr_head_export_acceptance.py` without changing the workflow.

The final trace and all three audits replay byte-identically. All **10**
previously published topology evidence-file hashes still match. No historical
runner or recognizer was executed, and no source score/XML was changed.

Local evidence is under `work/model-pilot/export-acceptance-final-v1/`.
Source observations/manifests and source-only enlarged inspection cards are under
`work/model-pilot/export-acceptance-v1/`. Exploratory analysis outputs there are
retained, but final reports bind the final analysis code. Restricted scans,
coordinates, raw graphs/XML and per-note joins remain local/ignored. The
[companion JSON](omr-export-acceptance-20261017.json) publishes aggregates and
hashes only; a public clone cannot replay unavailable private/local inputs.

```sh
python3 -m unittest discover -s tests -p 'test_omr_*.py'
python3 -m unittest discover -s tests -p 'test_sh1991_*.py'
python3 scripts/omr_export_trace.py --study /retained/topology-transfer-469-v1 \
  --out /new-analysis/trace
python3 scripts/omr_acceptance_audit.py --manifest /local/song-manifest.json \
  --out /new-analysis/song-audit
```

The audit manifest contains `identity`, plus `source`, `score`, `observations`
and optionally `mapping` objects, each with `path` and `sha256`. Relative paths
resolve against the manifest. Existing report bytes cannot be overwritten with
changed inputs/code: choose a new output directory.

## Next work that moves toward usable scores

1. Diagnose/protect source-supported measure boundaries and opening headers on
   consumed development sources. Adding heads alone cannot restore a collapsed
   full-song grid; preserve genuine special measures rather than retaining every
   native bar indiscriminately.
2. Implement a separate, default-off engine integration for selective proposals,
   with stem/chord/rhythm/export accounting and complete-event regression gates.
   Do not credit an image-level recovery before it reaches an exported event.
3. Complete source-only literal head, lyric and marking observations, then build
   a genuinely separate blinded verification lane. Unresolved work stays with
   the agent, not Jacqueline.
4. Freeze a new recipe before inspecting the reserved Warsaw source. Thy Strength
   is consumed development data; these diagnostics are not a fresh transfer pass.

No engine integration, fresh recognition, training, source upload, reader edits,
corpus admission, deployment or merge. **Whole scores accepted: 0.
Safe to promote: false.**
