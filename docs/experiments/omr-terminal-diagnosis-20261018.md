# Missing terminal music: head recognition precedes cautionary handling

2026-10-18. Follow-up to [internal-bar consensus](omr-measure-consensus-20261017.md)
and PR #489. **Consumed-source diagnosis, not a recognition fix, held-out test,
source-certified score, or permission to promote.**

## Checkpoint reconciled before continuing

The completed paired-v3 study has six successful recognition receipts and its
final analysis. Its engine, runner, source images, source observations, and raw
artifacts remain unchanged. PR #489 was verified open, not merged. No old study
invocation was retried. Work is isolated on a new follow-up branch.

## What the retained graphs actually say

Thy Strength's directly observed final bar is distinct, containing the closing
music on “be.” But the saved engine graph has **no heads, head chords, voices,
or timed slots in that entire final physical span**, in any of four parts.
Penn has the same absence. Both spans have retained terminal barline objects.

| Retained final region | Thy Strength | Penn |
| --- | ---: | ---: |
| Source measures per part (existing observations) | 17 | 12 |
| Exported measures per part | 16 | 11 |
| Graph head chords in final span, each part | 0 | 0 |
| Graph voices in final span, each part | 0 | 0 |
| Timed slots in final stack | 0 | 0 |
| Saved final stack duration | 0 | 0 |
| Saved final stack classification | CAUTIONARY | CAUTIONARY |

Native `MeasureFixer.isEmpty` treats a zero-actual-duration stack as empty
(except multiple rests / measure repeats). Its final-stack branch marks that
stack cautionary; `PartwiseBuilder.processPart` then skips cautionary measures.
This source path explains the downstream label and omission. It does **not**
establish when the heads disappeared: final snapshots are not stage traces.
Calling this solely an exporter deletion of recognized music was too strong.

Simply clearing `CAUTIONARY` would not recover those missing musical events.
The final-region recognition must be diagnosed upstream before changing the
general courtesy rule or creating an empty placeholder measure.

## Two separate logging-only diagnostic invocations

Used the exact existing consensus-v2 engine distribution and the successful
paired-v3 on-arm settings. Only `atlas.templatePoints` changed: eight approximate
source-selected terminal centers, frozen before invocation, select existing
read-only scanner log lines. They are not automatic detections, supplied
recognition proposals, source labels, target counts, or per-source repairs.

Exactly **two new invocations** completed, one for each already-consumed page.
Both reproduce the retained `sh1991_pilot.score` inventory exactly: written-order
pitch/rest spelling, duration, onset, staff, voice, measure durations, part names,
and lyric/notehead **counts**. This does not assert byte-identical XML, matching
lyric text, every notation field, or source accuracy. Final-span graph summaries
also agree. Old source images, settings and binary were not modified.

### Scanner evidence, not accepted heads

The existing engine searches the terminal centers: scanner evaluations were
logged for all eight. For the conventional `WHOLE_NOTE` template:

| Page / four terminal centers | Minimum logged distances |
| --- | --- |
| Thy Strength | 0.455, 0.521, 0.509, 0.501 |
| Penn | 0.436, 0.473, 0.545, 0.545 |

Lower is better. Every observed whole-template minimum is above the native
source-default `Template.maxDistanceLow = 0.40`. BREVE minima are also above
0.40 at all eight centers. This is a real template-fit mismatch in the sampled
neighborhoods; not proof of every rejection or a calibrated source-accuracy
metric. These probes do not log early bar/competitor vetoes or every head's
creation/removal event.

At Thy Strength's upper circle, `NOTEHEAD_VOID` reaches **0.134**; the two
terminal Fa-like heads have `NOTEHEAD_FA_LEFT_VOID` minima **0.164 / 0.168**.
Penn's circle reaches **0.185**, and its two terminal triangles have
`NOTEHEAD_FA_UP_RIGHT_VOID` minima **0.189 / 0.192**. These are **stem-based**
template fits, not retained musical objects, correct durations, or certified
literal shapes. A low minimum can be for the wrong family. The square-headed
parts do not gain a square-family recognition claim from a Fa/oval fit.

Native `ShapeSet.HeadsFa` contains filled/void **stem-based** shapes only; the
stemless set has no native Fa family in this retained engine. Conventional whole
templates and the source's narrow stemless shape-note glyphs therefore warrant
a separate, default-off recognition intervention. Do not weaken global template
or support thresholds based on these eight consumed centers.

## Reproducibility and tests

`scripts/omr_terminal_diagnosis.py` freezes the source/comparator/engine/code
fingerprints, records starts before launching, refuses started-but-unreceipted
retries, reuses completed receipts, and blocks probe interpretation on a score
inventory mismatch. Reports are immutable and hash-bound. Missing probe lines
remain unavailable, never zero-error observations.

- **7 new diagnostic fixtures pass**: missing/unknown probe identities, final
  region attribution, no-retry, completed receipt reuse, input drift, and the
  exact-inventory gate.
- **152 OMR + 105 SH1991 = 257 tests pass**, no skips using the retained
  Pillow/NumPy environment. System Python's first run skipped 22 dependency-
  requiring cases; the full-environment rerun completed all of them.
- Analysis-only replay is byte-identical; it launches no recognition.
- Raw scans, coordinates, graphs, exports, points, and logs stay ignored/local.
  The [public JSON](omr-terminal-diagnosis-20261018.json) contains aggregate
  results and hashes only. Source hashes do not confer publication rights.

Local diagnostic root: `work/model-pilot/terminal-diagnosis-v1/run/`.

```sh
python3 scripts/omr_terminal_diagnosis.py --freeze /local/config.json --out /new/run
python3 scripts/omr_terminal_diagnosis.py --run --analyze --out /new/run
# For the completed run: verification/analysis only, no recognition
python3 scripts/omr_terminal_diagnosis.py --analyze --out /retained/run
```

## Next justified work

In a **new version**, add an automatic stage trace (HEADS → REDUCTION → CHORDS
→ RHYTHMS → PAGE → export) for stemless candidates, then test source-style
whole-note families through actual chord/duration/voice/export integration.
Require negative courtesy-only/rest/barline regions and preservation of all
existing written-event spans; an extra exported measure alone is not success.
Retain this diagnosis unchanged, including all failed fits and missing objects.

No engine behavior change, score correction, app enablement, source upload,
fresh-source reliability claim, training, promotion, deployment, or merge.
**Whole scores accepted: 0. Safe to promote: false.**
