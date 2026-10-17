# Expanded research bank and complete-window automatic-head evaluation

2026-10-16. Follow-up to [terminal grid evidence](omr-terminal-evidence-20261016.md),
stacked on PR #482. Jacqueline authorized the next two substantive steps:
broader source-style training examples and automatic head-localization evaluation.
This implements both, without confusing an improved crop classifier with an
improved automatic transcription pipeline.

## Explicit NEW training populations

`omr_training_population.py` builds three hash-bound research populations:

| Population | Targets | Source pages | Composition |
| --- | ---: | ---: | --- |
| Legacy | 229 | 3 | Original provisional SH1991 observations, including 19 targeted non-heads |
| Expanded | **373** | **7** | Legacy + 144 consumed SH2025 positives from Penn, 184, 188 and 80t |
| SH2025-only control | 144 | 4 | Only those consumed SH2025 positives; no new negatives |

No previous model is silently refitted. These are new in-memory exemplar banks
and an immutable local population manifest. Labels remain provisional research
observations, not independently certified training gold or admitted score data.
The targeted negative examples are not an unbiased false-positive population.

Keep the exact earlier grayscale crop/scale/offset/distance recipe. Whole source
pages/canonical edition–tune groups are excluded from their evaluation fold;
source hashes cannot cross fold boundaries, and duplicate-byte aliases are
rejected. This is not a random crop split or a tune-family independence claim
beyond the supplied canonical grouping. The new vectorized population adapter
exactly reproduces **373 preceding legacy query outputs**: labels, exemplar IDs,
scales, offsets and distances. No accuracy or speed gain is attributed to that
kernel equivalence.

## Consumed development: page-held-out bank comparisons

| SH2025 test page, entirely excluded from fitting | Legacy | Expanded | SH2025-only |
| --- | ---: | ---: | ---: |
| Penn | 39/48 | **43/48** | 42/48 |
| And Jesus Crucified (184) | 23/24 | 23/24 | 23/24 |
| Ephesus (188) | 24/24 | 24/24 | 18/24 |
| Troubles Over (80t) | 41/48 | **44/48** | 43/48 |

Expanded fixes seven legacy errors and introduces none across these SH2025
folds: 127/144 to 134/144. These are **consumed-page development diagnostics**,
not a fresh 144-target generalization estimate. The source-only control loses
six correct Ephesus targets; those regressions remain in the report.

The pre-source selection rule requires no net correct-target loss on any of
the four consumed SH2025 cohorts, then maximizes correct targets with a fixed
tie-break. Expanded is selected for the explicitly known SH2025 target edition.
No edition is inferred from a truth label. The old SH1991 bank is left unchanged.

Additional SH1991 page-held-out diagnostics are retained, not silently promoted:
expanded scores 82/89, 65/84 and 52/56 versus legacy 70/89, 65/84 and 51/56.
The middle fold has two fixes and two regressions despite no net count loss.

## Reserved source: He Hath Saved Us (SH2025 219)

Use the fifth original hash-ranked eligible source, after the four consumed
SH2025 pages. Freeze code, data, source hash, dependencies, population selection,
engine identity/settings and evaluation scope **before viewing this source**.

The frozen scope is the opening system's first four written measure spans,
including pickup when present, across all four staves. Enumerate **every pitched
head** inside four complete supplied staff windows, not the first N positives.
After direct source-only enlarged-window/contact-sheet review, freeze the census
before recognition or classification: **33 heads (8, 8, 9, 8 by staff)**. The
windows end at the printed fourth-span boundary around x=416. Original watermark
and source bytes remain untouched.

All 33 heads happen to be filled: twelve round, ten square and eleven triangle.
There is no open-fill or diamond transfer observation. Source positions and
literal labels are same-agent provisional readings, not independent gold.
Generic old recognition/metadata may exist; no earlier 219 score/reference XML
or native graph was opened as source truth. Novelty is new-to-this-run source
evaluation, not never-processed or unseen-pretraining material.

## One automatic localization run, independent of the census centers

`omr_localization_study.py` launches **one unchanged V7 Audiveris run** on the
original full image after the source census is frozen. It retains engine/JAR,
Java executable, template-point, command, input, log, raw graph and raw export
hashes. It does not feed the observed centers to the recognizer. Completed
receipts are reused; a started or failed run is not silently rerun/replaced.
Existing sources, scores and prior studies remain unchanged; one new raw machine
draft/export is retained locally, not admitted or corrected.

Read native centers only after recognition. Require the original image path,
single-image identity and dimensions; unsupported registration or missing native
bounds fails explicitly. Native IDs are system-namespaced. Filter by the complete
frozen windows without selecting predictions by their class or truth match.
All head nodes remain eligible, including possible nonscheduled/orphan nodes;
head nodes are not guaranteed exported notes.

For classification at automatic centers, compute staff lattices from the source
window pixels and use their detected spacing. Do **not** substitute observed
head coordinates or observed per-head spacing. Unresolved lattices/out-of-image
crops abstain while detections remain counted. Separate source-centered runs
diagnose the classifier without pretending to measure automatic detection.

`omr_localization_eval.py` uses a separately named label-blind maximum-cardinality,
minimum-total-distance one-to-one matcher, restricted to the same staff window.
Shape/fill never enters its cost. The primary radius is 0.5 source interline,
with frozen 0.35 and 0.75 sensitivity arms. Distances are quantized to one
millionth of an interline. This does not rewrite earlier greedy-matcher results.

## Reserved results: better crop classification, unchanged localization ceiling

| Measurement on the same complete 33-head census | Legacy bank | Expanded bank |
| --- | ---: | ---: |
| Correct at observed source centers | 32/33 | **33/33** |
| Native predictions inside the windows | 33 | 33 |
| One-to-one spatial matches at 0.5 interline | 27/33 | 27/33 |
| Observed heads without a match | 6 | 6 |
| Unmatched native predictions | 6 | 6 |
| Correct literal labels at matched automatic centers / all source heads | **27/33** | **27/33** |
| Correct literal labels among the 27 matched centers | 27/27 | 27/27 |
| Selective correct labels / all source heads | 24/33 | 27/33 |
| Selective abstentions among all 33 native predictions | 5 | 2 |

Both full-proposal pipelines reach **81.8%** spatially matched, correctly labeled
source heads in these windows. Expanded improves the assisted crop result by one
but does **not** improve that automatic-center/all-source metric. All three
matching radii give the same 27 matches, six misses and six unmatched predictions.
No tolerance is enlarged after seeing the result.

The entire graph contains 174 native heads; 33 are in the evaluated windows, all
members of head chords. **Equal source/prediction counts do not imply accuracy.**
All six unmatched source heads are filled squares. Post-output source-only crops
of the six unmatched native centers show watermark/staff/beam-crossing regions.
This diagnostic queue does not revise the frozen census or certify population
false-positive rates; geometric unmatched predictions can generally include
displacement, duplicates or possible extras. The matching definition and radius
remain explicit. Nothing establishes pitch/rhythm, lyrics or correct exported
events, even for chord-member nodes.

The raw selective gate retains the same geometric candidate denominator here;
abstentions are reported, not used to hide unmatched predictions or missing
source heads. Human correction edits/time and exported-event accuracy stay null.

**219 is now consumed.** The next concrete bottleneck is candidate head
localization—particularly filled squares and background rejection—not another
claim that a perfect source-centered sample establishes dependable transcription.
Any detector intervention must be developed/versioned on exposed data, then
reserve another complete-window source before inspection.

## Artifacts, replay and checks

Local ignored `work/model-pilot/sh1991-v1/expanded-localization-v1` retains the
development/transfer protocols, population manifest, complete census, source-only
contact sheets, engine receipt/raw outputs, per-target comparisons and localization
review queue. Only code, aggregates and evidence hashes are published in
[the companion JSON](omr-expanded-localization-20261016.json). Raw scans, labels,
exemplar pixels, graph archives and score XML are not uploaded.

```sh
# Pinned research dependencies: Pillow 11.3.0, NumPy 2.0.2; no reader dependency.
python scripts/omr_localization_study.py --prepare
python scripts/omr_localization_study.py --development
python scripts/omr_localization_study.py --freeze-transfer  # BEFORE source view
python scripts/omr_localization_study.py \
  --labels work/model-pilot/sh1991-v1/expanded-localization-v1/source-observations.json
```

Running the last command again verifies/reuses the exact recognition/evaluation;
it does not launch inference again. A fresh checkout lacks the retained local
inputs/engine; CI uses tiny generated fixtures, not restricted scans.

- **176 Python fixtures pass:** 105 SH1991 + 56 prior OMR + 15 new population,
  matcher, registration, inference-reuse and automatic-center wiring contracts.
  Tests specifically cover a greedy-matching cardinality failure, shape-blind
  matching, missed-source denominator retention, unknown literal truth, whole-page
  exclusion, duplicate source aliases, real automatic crop coordinates, refusal
  to fill missing detections with truth centers, and no blind recognition retry.
- **104 Node tests and production build pass.** Existing bundle warning remains;
  no UI changed or new visual-acceptance claim. CI runs the new suite explicitly.
- No engine change, automatic score repair, existing-score mutation, corpus
  admission, deployment or merge. **Whole scores accepted: 0. Safe to promote: false.**
