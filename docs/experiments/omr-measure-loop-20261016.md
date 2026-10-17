# Measure-localized OMR improvement loop

2026-10-16. Follow-up to [grid integration](omr-grid-integration-20261016.md),
stacked on PR #480. Implements a bounded iteration across segmentation, crop
classification, a frozen reserved-source check, and honest outcome accounting.
No recognition rerun, score mutation, corpus admission, engine deployment or merge.

## Four connected steps

1. **Use the image grid:** `omr_measure_worklist.py` reads native Audiveris head
   boxes from the explicitly registered system, retaining native IDs and staff
   IDs. A head and its classifier footprint must fit in one proposed staff/span
   region. Boundary crossings, unknown staves, unresolved lattices and heads
   outside the supplied region stay counted and unresolved. Split/merge span
   statuses remain visible. No exported-event or MusicXML measure map is inferred.
2. **Classify localized crops in shadow:** `omr_measure_classifier.py` compares
   fixed grayscale crops with real training exemplars across six scales and
   nine one-pixel offsets. It minimizes squared distance within a fixed interior
   rectangle, exposing the winning exemplar/transform. A separate selective arm
   abstains on a relative competing-class margin below 0.08. Transform variants
   are not additional source examples. No pitch-derived shape labels are used.
3. **Freeze before the next source:** `omr_measure_study.py --prepare` binds
   code, recipe, Pillow version, original selection, training labels, source
   images and the reserved image by hashes before viewing that reserved scan.
   Observations are frozen before inference. Completed exact runs are reused;
   code/input drift fails rather than overwriting an earlier result.
4. **Track distinct outcomes:** reports expose correct/all targets, proposed/all
   targets, correct/proposed, abstentions, wrong proposals, fixes and regressions.
   They also retain **oracle review targets** (wrong labels + abstentions), not
   measured edits or time. The system does not know all its wrong answers.
   Human edits/minutes, detector recall and end-to-end accuracy remain `null`.

The concrete classifier is one fixed candidate, not a parameter search. Training
remains the original 229 provisional SH1991 crop targets on three consumed pages,
including 19 targeted non-head controls. Neither Penn, 184 nor the reserved page
is added to the fitted exemplar bank. Page-blocked diagnostics exclude the whole
test page. Old unsuccessful contour/render-back arms remain unchanged/disabled.

## Reserved source: Ephesus (SH2025 188)

Select the third record in the original hash-ranked eligible list: Penn and
And Jesus Crucified (184) were already consumed. No outcome-based page choice.
Generic archived recognition/metadata may exist; no earlier 188 score/reference
XML was opened as source truth. Novelty is **new-to-this-run evaluation**, not
never-processed material or an independent observer.

Freeze the recipe/inputs first; then inspect the raw scan and enlarged source-only
crops. Record the first six pitched heads on each of four opening-system staves,
music-only staff bands and all internal boundary witnesses. A source-only contact
sheet verifies the 24 labels and centers before predictions. These are provisional
same-agent observations, not independently audited gold. The sample includes seven
literal shape/fill classes; **filled diamond is absent**. No full-page detector,
false-positive rate or whole-song claim follows.

| Frozen comparison on the same 24 targets | Baseline | Scale/offset candidate | Selective candidate |
| --- | ---: | ---: | ---: |
| Correct literal shape/fill | 18/24 | **24/24** | **24/24** |
| Wrong proposals | 6 | 0 | 0 |
| Abstentions | 0 | 0 | 0 |
| Crop-target proposal coverage | 24/24 | 24/24 | 24/24 |
| Oracle review targets | 6 | 0 | 0 |

Both candidate arms fix six baseline errors and regress none on this sample.
This is a matched **75% to 100%** crop-label comparison, not a comparison with
the 9/24 result on a different song in the earlier study. It is also not proof
that human correction effort is zero. Localization is supplied, all predictions
are shadow proposals, and pitch/rhythm/lyrics are outside this measurement.

The unchanged grid matches **9/9 observed internal boundaries**, misses none,
and proposes **one extra at x=671** with support on three of four staves. Raw
source inspection shows aligned note stems in that area, not an additional
shared measure boundary. This is a retained failure, not removed from the
denominator or fixed after seeing the test. All 24 selected classifier footprints
fit proposed regions, so this extra does not alter their crop-label score.
It still prevents a claim of correct segmentation for the entire system.

**Ephesus is now consumed.** Any tuning using its errors is development; another
generalization check must reserve a different, appropriately grouped source
before observation. More source coverage and independent review remain necessary
before promoting a classifier or claiming source-certified accuracy.

## Native-head integration on preserved development graphs

| Native system | Native head boxes | Localized proposals | Boundary/band crossings | Outside supplied region |
| --- | ---: | ---: | ---: | ---: |
| Penn | 151 | 120 | 19 | 12 |
| Heavenly Land | 127 | 122 | 5 | 0 |

All 278 native boxes remain accounted for; none are silently dropped. These are
native graph-node counts, not source heads, distinct exported notes, corrected
events, detector recall or classification accuracy. Even a localized native box
may be a false detection. The same frozen classifier can attach shadow labels to
localized worklist entries; it does not turn the native shape into source truth.
All 120/122 localized boxes received shadow classifications. The selective gate
issued 97/115 labels respectively; remaining localized boxes abstained. These
are proposal counts with **no source-accuracy denominator** for the native heads.

Consumed-development classifier results and selective-proposal counts are retained
in the companion [aggregate JSON](omr-measure-loop-20261016.json), including all
regressions. They must not be pooled with Ephesus to inflate a held-out estimate.

| Consumed development cohort | Baseline correct | Candidate correct | Fixes | Regressions |
| --- | ---: | ---: | ---: | ---: |
| SH1991, whole-page-blocked folds | 176/229 | 186/229 | 17 | 7 |
| Penn | 26/48 | 39/48 | 14 | 1 |
| And Jesus Crucified (184) | 9/24 | 23/24 | 14 | 0 |

The candidate loses one net match on the SH1991 page 89 fold (52/56 to 51/56).
The selective arm also has a cost: on Penn it proposes 43/48 labels, with 36
correct, seven wrong and five abstentions. On 184 it proposes 21/24, all correct,
but three abstentions remain in the 24-target denominator. Selective confidence
is not calibrated probability, and abstention is not automatically an improvement.

## Replay and evidence boundaries

Local scans, labels, native graphs, scores, exemplar pixels and detailed predictions
remain ignored. `work/model-pilot/sh1991-v1/measure-loop-v1` retains the frozen
protocol, source observations/contact sheet, inference lock, development results
and reserved results. Worklists remain under `measure-worklists-v1` and
`measure-classified-worklists-v1`. Only aggregates, code and evidence hashes are
tracked. The original raw/corrected scores and prior failed runs are unchanged.

```sh
# Prepare BEFORE reading the reserved source; do not call an exposed page fresh.
python3 scripts/omr_measure_study.py --prepare
python3 scripts/omr_measure_study.py --development
python3 scripts/omr_measure_study.py \
  --labels work/model-pilot/sh1991-v1/measure-loop-v1/source-observations.json

# Label-free geometry worklist for an existing hash-bound graph/score pair.
python3 scripts/omr_measure_worklist.py /path/to/raw.mxl \
  --grid-manifest /path/to/manifest.json --out /tmp/new-measure-worklist
```

Python API: fit `omr_measure_classifier.fit(sh1991_symbol_classifier.samples())`,
then pass the bank and the study protocol hash as `model_binding` to
`omr_measure_worklist.run`. The binding is caller supplied; it must identify the
actual training/recipe protocol. It is not a source-certification or export map.
These commands require the preserved local artifacts and Pillow; they are not
clean-clone recognition commands. Code fixtures use tiny generated inputs.

## Disposition and verification

Retain the scale/offset candidate as the promising **shadow** classifier; do not
replace the recognizer. Retain the grid's false-positive failure for subsequent
development, keeping this test immutable. Next useful work is distinguishing
aligned stems from bars, broader grouped source evaluation and independently
reviewed targets—not silently correcting the reserved result.

- 14 new fixtures cover boundary-crossing abstention, complete native-ID
  accounting, unchanged inputs, native/archive integration, frozen drift,
  completed-run reuse, scale witnesses, tied/single-class abstention and metric
  denominator/effort boundaries.
- All 105 existing SH1991 and 31 existing OMR fixtures pass: **150 Python tests**.
- **104 Node tests and the production build pass** locally. The existing bundle
  size warning remains. No UI changes or new visual-accuracy claim.
- Shared CI explicitly runs `test_omr_measure_*.py` with pinned Pillow.

**Whole scores accepted: 0. Recognizer changed: no. Safe to promote: false.**
