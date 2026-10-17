# V4: repair the diagnostic evaluation before changing recognition

Date: 2026-10-15 America/Los_Angeles. Follow-up to
[V3](sh1991-fa-proximity-v3-20261015.md), on PR #475.

## Result

**The diagnostic evaluation is now explicit and reusable; source-certified
end-to-end accuracy and generalization are still unmeasured.** No recognition
code, template, gate, source label, historical report or held-out run changes.

The new engine-independent point evaluator separates detection, fill,
native-label competition, timing, export-layout witnesses and unavailable
gold accuracy. A small SH1991 adapter replays the hash-verified frozen V3
evidence through that evaluator. The
[general contract](omr-evaluation-contract.md) documents the reusable approach
and what must change before applying it to a broader benchmark.

## What the repaired breakdown reveals

| V3 source stratum | Retained / observed | Correct fill / retained |
| --- | ---: | ---: |
| Round filled | 42/42 | 42/42 |
| Round open | 27/27 | 27/27 |
| Square filled | 58/58 | 57/58 |
| Square open | 12/12 | 5/12 |
| Diamond filled | 5/8 | 3/5 |
| Diamond open | 1/1 | 1/1 |
| Triangle filled | 42/44 | 42/42 |
| Triangle open | 18/18 | 2/18 |

The three missing non-triangle heads are **all filled diamonds in Samaria**:
`26-s1-p2-n5`, `26-s1-p2-n12`, `26-s1-p2-n13`. Thus “other-shape retention”
is a localized diamond problem in this audit, not uniform damage across
ordinary shapes. Open-square fill is also poor and should accompany the
open-triangle investigation; fixing triangles alone could conceal this.

The new report supplies every missing/wrong-fill ID, page/shape/fill strata,
native-label counts and structural-stage counts, with both conditional and
all-source denominators. Triangle correct-fill recovery is **44/62** against
all source triangles, versus the historical conditional gate's **44/60**.
Neither denominator replaces the other. Plain `NOTEHEAD_BLACK`/`VOID` labels
do not distinguish round, square and diamond: no invented four-shape
classification accuracy is reported.

The three historical failures remain unchanged: fill **44/60 < 80%**,
non-triangle retention **145/148 < 98%**, and candidate pitch agreement
precision **775/1,276**, below **559/684 minus 0.02**. Gate comparisons use
exact counts rather than displayed rounding. Candidate XML remains unreviewed;
source-certified pitch precision is explicitly **unavailable**, not 60.7%.

## Replace the uninformative negative diagnostic

The evaluator reproduces the original final-stage floor: none of the 24
negative centers has a retained head in any arm. It explicitly disallows
using this set to claim a final false-positive reduction or precision gain.

The new full review queue contains **8 control, 143 V2 and 109 V3** retained
unmatched heads in the original audit interiors. These counts reproduce the
frozen report. No queued item is automatically labeled false.

Before reading new source crops, freeze a deterministic V3 selection: two
x-spread candidates from each occupied source window, deduplicating singleton
windows. This yields **21 locations across 11 occupied windows** on the three already
audited training scans. The
[selection](sh1991-eval-review-selection-20261015.json) records IDs, coordinates,
source pointers/hashes and the selection rule.

A single AI visually inspected two source-only contact sheets with small
center brackets, no predicted labels or graph overlays. The
[review](sh1991-eval-source-review-20261015.json) records:

- **2 centers overlapping genuine filled triangular heads**. Unmatched does
  not mean a distinct false note; coordinate/duplicate assignment matters.
- **19 centers without a notehead at the marked location**, often beside
  real heads, stems or flag fragments. These may be displaced or duplicate
  proposals; this is not proof of 19 distinct spurious exported notes.

This is an error-directed training sample, not an unbiased full-window
precision estimate or independent human certification. Pixels/contact sheets
remain local and ignored. Future interventions can reuse the frozen
locations, but must not treat training re-use as validation.

## Comparable template diagnostics, with the remaining limitation explicit

The evaluator pairs only logged proposals sharing source-point ID, triangle
orientation, slim-box center, anchor and seed path. Duplicate groups are
excluded explicitly, not collapsed to a favorable minimum; absent comparisons
remain absent. V3 has **1,623** such pairs at the 18 open-triangle points:
filled distance is lower in **725**, open distance in **898**.

These correlated search positions are not independent examples or an accuracy
score. This breakdown does not contradict the old **17/18 scanner-minimum**
finding: the aggregations answer different questions. It demonstrates why
comparing independent search minima is not enough to blame the open mask.
Even equal logged slim-box centers need not imply identical internal anchor
coordinates. A forced source-center/internal-anchor study remains necessary
before drawing that causal conclusion; no threshold or template is tuned here.

## Verification and next intervention

```sh
python3 -m unittest discover -s tests -p 'test_sh1991_*.py'
python3 scripts/sh1991_eval_diagnostics.py --prepare-review
python3 scripts/sh1991_eval_diagnostics.py --output /tmp/sh1991-eval-v4.json
cmp docs/experiments/sh1991-eval-diagnostics-v4-20261015.json /tmp/sh1991-eval-v4.json
```

Preparation verifies the immutable selection and regenerates identical local
contact sheets; it does not relabel sources or recognize music. Report replay
validates historical evidence, source/selection/review/contact hashes and
complete review coverage. The numeric report binds the two analysis scripts.
Clone-safe fixtures test null/unknown denominators, exact borderline gates,
label vocabulary, stage availability, negative floor, paired-proposal
identity, duplicate groups and deterministic sample selection.

Local verification: **54 Python fixtures pass**, the numeric replay is
byte-identical, and all **156 inventoried V2 files** retain their hashes.

**Next bounded study:** force comparable source-center/internal-anchor
open/filled evaluations, including the open-square and filled-diamond controls;
then choose one isolated recognition change. Preserve the frozen training
gates and require a pass before held-out evaluation. The four lost Bellevue
bar witnesses still need their separate source review. No fine-tuning,
generalization claim, promotion or merge is implied by this evaluation repair.
