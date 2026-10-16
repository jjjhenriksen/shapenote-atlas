# Whole-grid repair and the first SH2025 cross-edition test

2026-10-16. Jacqueline authorized work on rhythm/structure, full-song
image-grounded correction, targeted shape/fill training, and regression-aware
evaluation; then suggested an SH2025 song as the new test.

**Result:** the source-driven repair capability is substantially broader, but
the symbol prototype did **not** establish reliable cross-edition improvement.
The first frozen SH2025 whole-grid adapter **failed**. Its subsequent extension
is disclosed development on the consumed test, not a rebranded held-out pass.
No recognizer upgrade, corpus promotion, merge, human correction task, or
source-score publication is implied.

## Work on all four tracks

| Track | Concrete implementation | Evidence / remaining boundary |
| --- | --- | --- |
| Rhythm and structure | `omr_score_audit.py`: rational onsets, per-voice extent, backup/forward/chords, symbol-vs-duration conflicts, orphan/unclosed ties, part-grid disagreement, unavailable meter | Diagnoses contradictions; never fabricates a rest from a short bar. Pickups/repeat boundaries are review signals, not automatic errors. |
| Image-grounded correction | `omr_source_repair.py`: full declared source grid, source image hash and in-frame crop per segment, explicit source/draft measure map, exact-note reuse, audited event replacement, explicitly absent marking removal | All four voices across complete written songs, not just openings. Still requires agent-produced source observations and alignment; not an autonomous image-to-gold verifier. |
| Shape/fill training | `sh1991_symbol_classifier.py`: concrete local fitted 1-nearest-neighbor model, fixed normalized crop recipe, source labels plus reviewed non-heads, page-blocked diagnostics | 229 provisional examples on three consumed training pages. Model stays shadow-only: 26/48 SH2025 joint shape/fill matches is inadequate evidence for deployment. |
| Fixes versus regressions | Full-grid multiset event comparison, distinct errors removed/introduced, unsupported marking counts, explicit orphan events in denominator, independent second parser, offline full-score render | Source observations used to repair are also used to score consistency. Independent source accuracy is **unavailable**, not 100%. |

## Development on the consumed SH1991 page

Before reading the complete draft event lists, freeze a source-only reading of
**Heavenly Land (303)**: all 17 written measures on each of four staves,
**68 staff-measures / 128 pitch/rest/duration events**. The earlier fresh-song
opening study already consumed this song; it is development data here.

Draft part measure counts are **16 / 14 / 16 / 16**, not 17 each. A reviewed,
hash-bound map accounts for all draft measures and explicitly inserts missing
source boundaries/material. No silent index-wise zip after a missing measure.

| Source-consistency measurement | Before | After |
| --- | ---: | ---: |
| Complete pitch/duration/onset/staff/voice event matches | 83/128 | 128/128 |
| Missing + extra complete-event error units | 85 | 0 |
| Source-unsupported dynamics/articulation/ornament candidates in observed scope | 29 | 0 |

Errors introduced against these observations: **0**. This is not independent
accuracy. Changed/inserted notes encode only known source event fields. Exact
matching note nodes retain candidate lyrics/shapes/notations; replaced fields
are retained in the local audit, not guessed onto a different note.

## The SH2025 test: Penn (501t)

### Selection and source exposure

Freeze SHA256-ranked selection using seed `atlas-sh2025-accuracy-v1` from
SH2025 additions with confirmed source images, excluding dedicated correction
script names and review-publication pages. Deduplicating catalogue aliases by
the edition/source-manifest ID leaves **22** eligible records; the selected song
is **Penn**, unchanged by that pre-source inventory correction.

All locally available eligible SH2025 additions already have generic OMR
artifacts. Therefore this is a **new cross-edition evaluation for this run**,
not never-processed novelty. Metadata/OCR also exist. Earlier Penn draft or
reference XML was not opened as an answer key in this run. No claim about model
pretraining, other agents' exposure, or Jacqueline's familiarity is made.

Read the raw watermarked 2025 scan and freeze, before new inference/output:

- All **48 staff-measures / 120 events** and **8 source tie pairs**.
- Literal shape/fill and manually localized centers for all **48 noteheads in
  the first four measures across four staves**. No shape inferred from pitch/key.
- Source-only geometry corrections remain versioned: the m5/m6 crop boundary
  is x642, not x601; eight rough m3 note centers were refined with an original-x
  ruler. No event or shape/fill labels changed; no model predictions viewed.

These are single-agent provisional observations, not independent gold. Source
watermark pixels were not removed, regenerated or uploaded.

### Frozen test outcome — FAILURE retained

Freeze the implementation at commit `0e76706`, recognizer/library identity,
settings, template-point bytes, model, source observations, selection and runner
hashes before the single new full-page recognition. The local export succeeds
in about seven seconds; no retries or page replacement.

- The fitted symbol model matches **26/48** joint literal shape/fill labels
  (**54.2%**). Shape alone: 30/48; fill alone: 41/48, counting predicted
  non-heads as failures. There are no SH2025 negative examples, so no
  false-positive rate or detector-recall claim.
- Page-blocked training diagnostics were **176/229** (**76.9%**), versus
  18/229 for per-fold majority-label prediction. Those three original training
  pages are not fresh validation, and some classes are absent from a fold's
  training pages. The cross-edition drop is not a causal font/watermark study.
- The raw score has **9 measures in each part versus 12 in the source**, an
  extra leading measure, and merged bars. The frozen adapter cannot represent
  the orphan measure without an invalid source mapping. Its whole-song repair
  outcome is **blocked/failed**, not a passing score or a smaller denominator.

The fixed nearest-neighbor recipe was not retuned, refitted on Penn, or
installed in Audiveris. Reject this prototype as evidence of a reliable
recognizer improvement; keep the concrete model and negative result.

### Subsequent development rescue — NOT a fresh-test result

Penn is now consumed. Extend the adapter to support explicitly inventoried
orphan draft measures, retain their XML, and count their extra events. Restore
opening key/clef/meter only from additional source observations: three sharps,
4/4, three treble clefs and a bass clef. The earlier auditor's absent-meter
silence is fixed to report **unavailable**, not a clean rhythm result.

No original event/tie labels changed and no recognition was rerun. The supplied
map accounts for all nine raw measures per part, including the orphan, and
records which source bars were merged or missing. Merged events are evaluated
at their exported location/onset; favorable realignment is not manufactured.

| Development source consistency | Before | After |
| --- | ---: | ---: |
| Complete event matches | 33/120 | 120/120 |
| Missing + extra complete-event error units | 208 | 0 |
| Unsupported marking candidates in the checked source grid | 15 | 0 |
| Matching observed tie endpoints | 2/16 | 16/16 |

Against these inputs, event error units removed: **208**, introduced: **0**.
Tie endpoint error units removed: **18**, introduced: **0**. These are
missing/extra units, **not 208 independently established musical mistakes**:
substituting one wrong event can remove both one missing and one extra unit.

## Verification and remaining work

- **105 clone-safe SH1991/accuracy fixtures pass**, including shifted-grid,
  orphan accounting, meter unavailable, rational tuplets, multi-voice timing,
  duplicated events, corrupted note types, unsupported-marking removal,
  explicit ties, source-header binding, and frozen-study drift/failure guards.
- **104 Node tests pass**; production build passes. Existing large-bundle
  warning remains unrelated to this research work.
- Both complete repaired scores pass the existing independent **parser
  implementation** across **116 staff-measures**. It is not an independent
  source observer.
- Both full-score offline OSMD renders pass measure-count/duration checks and
  were visually inspected. Browser network requests are blocked.
- **Whole scores accepted: 0; human tasks created: 0.** Lyrics, literal shapes,
  other slurs/notations, and repeat/endings are not established by these checks.
  The renders use conventional heads where shape is unresolved; this is not
  faithful four-shape publication. A surviving candidate slur is not certified
  merely because pitch/rhythm matches.

Next work remains agent-owned: independently produce source audits, accumulate
multi-print/scan positive and non-head labels, improve the classifier only on
development data, then test a newly reserved song without tuning on it. A
detector-integrated classifier must beat the existing recognizer end-to-end,
not merely classify source-centered crops. No broad reliability percentage is
justified yet.

## Evidence and replay

Aggregate counts, confusion table, phase labels and evidence hashes:
[`omr-accuracy-tracks-20261016.json`](omr-accuracy-tracks-20261016.json).
Raw scans, full numeric source labels, fitted pixel exemplars, raw/repaired
MusicXML, XML change audits and screenshots stay under ignored
`work/model-pilot/sh1991-v1/accuracy-tracks-v1/`. They are not clean-clone inputs.

```sh
# Clone-safe tests, without scans, Pillow, Java or classifier training.
python3 -m unittest discover -s tests -p 'test_sh1991_*.py'
npm test
npm run build

# Retained-artifact diagnostics; choose a NEW output path on replay.
python3 scripts/omr_score_audit.py \
  work/model-pilot/sh1991-v1/accuracy-tracks-v1/penn-test/raw/501t-penn-8a2061599c.mxl \
  --output /tmp/penn-raw-structure.json
python3 scripts/omr_source_repair.py \
  work/model-pilot/sh1991-v1/accuracy-tracks-v1/penn-test/raw/501t-penn-8a2061599c.mxl \
  work/model-pilot/sh1991-v1/accuracy-tracks-v1/penn-source-development.json \
  --map work/model-pilot/sh1991-v1/accuracy-tracks-v1/penn-development-map.json \
  --out /tmp/penn-development-replay
```

The original frozen study intentionally rejects the current development code
hashes. Inspect `penn-test/frozen-code/`, protocol, recognition receipt,
`needs-measure-map.json` and `frozen-disposition.json`, or the exact `0e76706`
commit. Do not weaken that guard or call the development extension a frozen
test pass. The initial and final training runs have the identical fixed recipe
and counts; the second merely pins the added test-inference adapter with a
saved runner snapshot, not a hyperparameter search.
