# Fa proximity v3: topology recovers; precision and fill still block promotion

Date: 2026-10-15 America/Los_Angeles. Continues the
[v2 barline diagnosis](sh1991-barline-v2-20261015.md) on
[PR #475](https://github.com/jjjhenriksen/shapenote-atlas/pull/475).

## Decision

**Retain as a measured training improvement, not a promotable recognizer.**
With one additional, default-off fa-only template proximity veto, the five
training scans have **89 measure stacks**, matching the control's count, and
**57 audited triangle locations receive timed slots**. Candidate-reference
pitch recall rises from v2's **55.6% to 80.3%**, duration recall from **52.9%
to 68.2%**, and written measure/onset recall from **21.4% to 40.1%**.

**Three original gates still fail:** triangle fill, non-triangle retention and
candidate pitch precision. V3 is rejected for promotion and held-out evaluation.
No gates are relaxed, no model is trained, and nothing is merged.

## Source review and frozen diagnostic benchmark

The remaining v2 bar losses had mixed ordinary/fa head support. A preliminary
nine-crop exploration of surviving support heads showed fa candidates at
vertical/staff-line crossings with no notehead; it also showed a genuine
ordinary round head near a conflict. That is a reason to avoid a blanket
all-head veto. Those exploratory crops are not scored benchmark rows.

Before new recognition, freeze a **234-location training benchmark**:

- The unchanged 210-head audit and its two existing coordinate adjudications.
  It covers round, square, triangle and diamond heads in both fill states.
- Twenty-four new non-head centers: six x-spread physical-bar midpoint samples
  from each of the four training scans with residual mixed-support losses.
  A single AI visually reviewed source-only contact crops before inference.
  Each marked center is a vertical/staff-line crossing with no notehead.
  This does not certify the vertical mark as a musically correct barline.
- Frozen IDs, coordinates, source/hash pointers, original selection/conflict
  lines, review-contact hash and provenance in the
  [numeric benchmark](sh1991-fa-discrimination-benchmark-20261015.json).
  Source pixels and contact sheets stay in ignored `work/`.

The positive strata are 58 filled/12 open squares, 42 filled/27 open rounds,
44 filled/18 open triangles, and 8 filled/**1 open diamond**. The sparse
diamond/open stratum cannot support a robust generalization claim. Neither
the old audit nor the new negative labels are independently human certified.
Negatives are error-directed training diagnostics, not an unbiased precision
sample. They were not reselected after seeing the new results.

## Isolated intervention and controls

In a separate engine checkout, add `atlas.faBarProximity` (default false).
When enabled, reject a **logical fa-template proposal** if its slim box
intersects the area of any physical `BarlineInter` already present at HEADS.
Upstream already rejects all templates near **frozen** bars/connectors; this
adds a fa-only check around physical bars that need not be frozen. It does not
freeze bars, reject ordinary templates, alter the measure-column rule, or
change masks, anchors, fill decisions, classifier vocabulary or source pixels.

The v2 fa-only-stem conflict safeguard remains **on and unchanged** in both
the v2 comparator and the candidate. Thus this experiment measures the
incremental proximity veto on top of v2. It does not establish the veto's
standalone effect without that safeguard. Physical bar candidates can be
wrong; this rule can suppress a real fa head near a false bar. It remains a
research policy, not a source-certification rule.

All three arms use the **same newly built binary**, original full-frame scans
for **26, 83t, 68b, 72b, 89**, identical constants except the declared switches,
and batch-constant persistence disabled:

| Arm | faHeads | Existing v2 safeguard | New proximity veto |
| --- | --- | --- | --- |
| Control | false | true, no logical fa heads to act on | false |
| V2 control | true | true | false |
| V3 candidate | true | true | true |

The two controls reproduce their earlier written events, score metrics,
topology, head audit and head-survival totals exactly on all five images.
This validates the diagnostic/default-off paths at those levels; it is not a
claim of byte-identical archives or independently correct scores. Fifteen new
training recognition runs were performed. No held-out pixels or labels were
used to tune this experiment, and no second parameter setting was tried.

## Barline and downstream comparison

| Evidence across five training scans | Control | V2 | V3 |
| --- | ---: | ---: | ---: |
| Physical bars after HEADS and STEMS | 410 | 410 | 410 |
| Physical bars after REDUCTION | 391 | 327 | 396 |
| Initial REDUCTION bar removals | 19 | 83 | 14 |
| Physical bars after MEASURES | 404 | 304 | 404 |
| Final physical bars | 402 | 302 | 403 |
| Deleted partial columns | 1 | 25 | 1 |
| Final measure stacks, including courtesy | 89 | 64 | 89 |
| Non-cautionary stacks | 88 | 64 | 88 |
| Timed-slot heads / retained heads | 687/735 | 1,045/1,480 | 1,282/1,360 |
| Exported timed pitched notes | 684 | 1,032 | 1,276 |

The v3 per-image stack counts are **18, 16, 19, 18, 18**, matching the control's
counts. Equal counts do **not** certify measure boundaries, source correctness
or candidate-reference event alignment. The final extra physical bar is not
automatically an improvement.

At REDUCTION exit, source-geometry/glyph comparison finds **73 bar witnesses
restored and four previously retained witnesses lost**, for a net gain of 69
over v2. The four losses are in Bellevue. This is not a uniform no-regression
result, and those witnesses have not been independently certified as true or
false bars. The per-image changes (restored / newly lost) are Samaria **15/0**,
Vale of Sorrow **16/0**, Ortonville **23/0**, Bellevue **19/4**, and Church's
Desolation **0/0**.

| Source-audited survival | Control | V2 | V3 |
| --- | ---: | ---: | ---: |
| Triangles retained, of 62 | 10 | 58 | 60 |
| Triangles with timed slots | 8 | 44 | 57 |
| Triangles with unique export layout witnesses | 8 | 43 | 54 |
| Correct fill among retained triangles | 1/10 | 43/58 | 44/60 |
| Other shapes retained, of 148 | 148 | 144 | 145 |
| Other shapes with timed slots | 142 | 125 | 137 |
| Other shapes with unique export witnesses | 141 | 98 | 108 |
| Other retained heads labeled fa | 0 | 40 | 41 |
| Unmatched graph candidates in audit interiors | 8 | 143 | 109 |

Other-shape damage remains. In particular, **145/148 = 97.972973%**, which is
**below** the 98% retention threshold; rounding it to “98%” cannot make it
pass. Other-shape fill correctness is **135/145**, versus 148/148 in control.
Recovered open triangles have correct fill only **2/18** times. Unmatched
graph nodes and ambiguous graph/export joins remain review workload, not
source-certified false positives or proven export deletions.

## What the template-distance probes do and do not show

The engine records actual scanner-proposed evaluations within 0.5 interline
of each frozen benchmark point: shape, slim-box center, distance, hole-white
ratio where available, anchor, seed/range path, veto decision and log line.
The report retains the minimum raw and minimum non-vetoed distance per shape.
These are **local scanner proposals**, not exhaustive forced scoring at one
identical center/anchor, calibrated probabilities, or a full confusion matrix.
Missing proposals are explicit, not treated as zero distance or correct rejection.

- All 24 non-head points receive probe evaluations. V3 vetoes **1,448 fa
  evaluation attempts** in their neighborhoods. That is not 1,448 unique
  candidates or source-certified false positives.
- **No arm has a retained head within the evaluation radius of any of those
  24 centers.** This negative set has a final-stage floor effect: it cannot
  establish a reduction in final false-positive rate. The broader unmatched
  window count improves, but remains unreviewed candidate workload.
- At all 18 open-triangle source points, both filled and open fa proposals
  are observed in the fa-on arms. The minimum raw filled-fa distance is lower
  than the minimum raw open-fa distance at **17/18** points in both v2 and v3.
  That is consistent with the persistent fill failure, but does not isolate
  mask quality from center/anchor search, competing orientations or grading.
  No new fill threshold is selected from these results.

The benchmark therefore supplies useful source-linked evidence and exposes
its own limitation. It is not used to claim that negative discrimination or
all-four-shape accuracy has been solved.

## Existing score gates, unchanged

Agreement is against the same **unreviewed candidate XML**, not independently
certified source music: 965 pitched and 1,001 timed reference events.

| Candidate-reference agreement | Control | V2 | V3 |
| --- | ---: | ---: | ---: |
| Pitch recall | 57.9% | 55.6% | 80.3% |
| Pitch precision | 81.7% | 52.0% | 60.7% |
| Duration recall | 58.5% | 52.9% | 68.2% |
| Written measure/onset recall | 28.6% | 21.4% | 40.1% |
| Candidate-reference insertions | 2 | 210 | 356 |

V3 passes the control, triangle-retention-gain, pitch-recall-gain, duration,
onset and export-count gates. **Three failures remain:** triangle fill
73.3% < 80%; other-shape retention 97.972973% < 98%; pitch precision 60.7%,
well below the allowed control loss of 2 percentage points. More exported
notes are not proof of better music, and candidate-reference insertions are
not independently source-certified errors. No held-out evaluation is allowed
by the unchanged training selection rule.

## Verification, artifacts and next study

- **44 clone-safe Python tests passed**, including four new probe-accounting
  tests for vetoed versus allowed minima, absent proposals, line/anchor
  provenance and malformed/nonfinite distances.
- **15 focused Java tests passed:** five new proximity boundary tests, six
  unchanged v2 safeguard tests and the four existing fa-template tests.
- **156 inventoried v2 study files remain byte-identical.** Prior engines,
  outputs, source images, annotations and numeric reports are not replaced.
- [Numeric result](sh1991-fa-proximity-v3-20261015.json),
  [verification receipts](sh1991-fa-proximity-v3-verification-20261015.json),
  frozen benchmark and [engine recipe](../../experiments/audiveris-fa-proximity-v3/README.md)
  retain configurations, commands/hash pointers, source/head survival and
  template probes. Restricted scans, logs, engine builds and graph archives
  remain local and ignored.

```sh
python3 -m unittest discover -s tests -p 'test_sh1991_*.py'
python3 scripts/sh1991_fa_proximity.py --output /tmp/fa-proximity-replay.json
cmp docs/experiments/sh1991-fa-proximity-v3-20261015.json /tmp/fa-proximity-replay.json
```

Next, freeze this result and examine the open-triangle fill competition with
**fixed-center, fixed-anchor template evaluations** on source-reviewed crops.
The scanner minima recorded here are not that experiment. Broaden negative
review around **actually retained** unmatched candidates rather than reusing a
floor-effect set to claim precision gains. Inspect the four newly lost
Bellevue bar witnesses before interpreting their correctness. Keep precision,
fill, other-shape, duration and onset gates; do not tune on held-out material
or begin fine-tuning to bypass these failures. This remains progress toward
#471, not completion of source fidelity or independent acceptance.
