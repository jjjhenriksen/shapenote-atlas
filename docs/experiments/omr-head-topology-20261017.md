# Open-head topology and thin-ink rejection

2026-10-17. Follow-up to [the unchanged Clayton transfer failure](omr-head-transfer-20261017.md),
PR #486. A default-off research intervention, not integrated into the recognizer
or reader. All source observations remain provisional same-agent readings,
**not independent gold**. Correct literal labels mean shape/fill agreement at
geometrically matched automatic centers, not pitch/rhythm or exported-note accuracy.

## Intervention and development exposure

Keep the earlier detector, classifier and experiment files unchanged. New
`scripts/omr_head_topology.py` operates only on pixels and supplied staff windows:

- Find bounded four-connected white regions inside black outlines; join small
  vertically adjacent fragments split by staff lines. Centers come from these
  regions, never from observed source-head centers or native graph nodes.
- Reject rectangular staff/bar cells bounded by **distinct** detected staff
  lines. Cap hole sizes and fragment unions relative to automatic staff spacing.
- Require at least 0.72 interline of contiguous central ink before allowing an
  old dense-core candidate to proceed to the selective square/filled gate.
  Thin rests are rejected by geometry, not by labeling unmatched nodes as rests.
- Use the unchanged **373-exemplar bank** for both proposal types. Holes must
  independently obtain a selective open label; topology never forces a label.
- Preserve every native center and label. Retain the old 0.75-interline
  native-priority suppression rule; do not silently repair native mistakes.

Development used the **already-consumed** complete censuses on SH2025/219 and
531. No new exemplars were added. One preliminary geometry diagnostic and v1
analysis are retained locally. A synthetic bisected-square fixture exposed an
incorrect same-line staff-cell veto; fixed that before v2 and the transfer
freeze. The development aggregates are unchanged between v1 and v2. No tuning
was performed after the seventh source was inspected or evaluated.

## Consumed-development results, fixed 0.5-interline matching

| Source / arm | Candidates | Matched | Unmatched candidates | Correct literal labels |
| --- | ---: | ---: | ---: | ---: |
| 219 native | 33 | 27/33 | 6 | 27/33 |
| 219 native + old squares | 39 | 33/33 | 6 | 33/33 |
| **219 native + topology** | **39** | **33/33** | **6** | **33/33** |
| 531 native | 19 | 14/29 | 5 | 13/29 |
| 531 native + old squares | 21 | 14/29 | 7 | 13/29 |
| **531 native + topology** | **31** | **26/29** | **5** | **25/29** |

On Clayton, both previously confirmed rest additions are rejected; twelve
correctly labeled heads are added. The unfiltered hole arm localizes and
labels all 29 heads but also has one unmatched candidate. The selective hole
gate retains 28 correct heads with no unmatched candidates. This does not make
the primary pipeline perfect: native-priority suppression blocks useful nearby
holes, and the retained native diamond remains wrongly labeled. These are
explicit limitations, not silently corrected outputs.

## Pre-source-frozen seventh-source test

Selected **SH2025/469, Thy Strength**, seventh in the original hash-ranked
eligible list. The first six had been consumed. No outcome-based substitution.
Generic historical processing and metadata may exist; this is a newly frozen
complete-window census, not a claim of globally untouched data.

Before viewing the scan, froze code, parameters, unchanged bank inputs,
development report, dependencies, V7 engine/settings, matching and failure
policy. Then read the scan and a source-only enlargement and locked **all 32
pitched heads** in the first four complete written measure spans, across four
supplied staff windows. The census includes 30 open heads and two filled heads:
12 triangle/open, 10 round/open, 7 square/open, one diamond/open, one
triangle/filled and one diamond/filled. No graph/XML served as source truth.
Source bytes and source/head denominators were not changed after inference.

Exactly one new native recognition was run after census lock. Every arm uses
the same windows and label-blind geometric matching. All counts and predeclared
radii are retained, including negative results.

| Arm | Candidates | Matched / 32 | Unmatched candidates | Correct literal labels / 32 |
| --- | ---: | ---: | ---: | ---: |
| Native | 25 | 20 | 5 | 20 |
| Native + old selective squares | 28 | 20 | 8 | 20 |
| Holes, before selective gate | 33 | 29 | 4 | 29 |
| Selected topology proposals | 28 | 28 | 0 | 28 |
| **Primary: native + topology** | **35** | **30** | **5** | **30** |

**Ten additional correct heads, no additional unmatched candidates**, compared
with the unchanged native baseline. All three fixed radii, 0.35/0.5/0.75,
produce the same counts. The final candidate matched fraction is **30/35**,
not 100%; the five unmatched native detections are retained. Unmatched graph
heads are not automatically extra exported notes or source-certified errors.

### Retained gaps

- Two round/open heads remain missed: one has no hole proposal, the other has
  the correct nonselective label but fails the unchanged selective-margin gate.
  No threshold relaxation or post-result rerun was performed.
- All seven square/open and both diamond strata match with correct labels in
  the primary arm. This does not resolve the separate retained Clayton native
  diamond failure or establish broad diamond generalization from two heads.
- The thickness guard rejects three rest-shaped dense-core detections visible
  in the source, and also rejects a filled triangle. It is a gate for optional
  **square additions**, not a general filled-head detector. Native retains the
  correctly labeled filled triangle and diamond in this test.
- There are no filled squares in this transfer window. Fresh-source positive
  filled-square recovery and broader scan-style generalization remain untested.
- Supplied staff-window localization, damaged/broken outlines, watermark
  interference, native-priority suppression and classifier abstentions remain
  important limitations. This page is now consumed for future development.

## Evidence and reproduction

Only code, aggregate counts and hashes are published in
[the companion JSON](omr-head-topology-20261017.json). Scans, coordinates,
per-head predictions/pairs, raw graphs and exemplar pixels stay local/ignored.
Original #485/#486 studies and their artifacts remain unchanged.

```sh
python scripts/omr_head_topology_study.py --retained-root /retained/checkout \
  --clayton-root /retained/head-transfer-531-v1 --out work/model-pilot/topology-development-v2
python scripts/omr_head_topology_transfer.py --retained-root /retained/checkout \
  --clayton-root /retained/head-transfer-531-v1 \
  --development-root work/model-pilot/topology-development-v2 \
  --out work/model-pilot/topology-transfer-469-v1 --prepare
# Only after this freeze: inspect source, record complete census, and lock it.
python scripts/omr_head_topology_transfer.py --retained-root /retained/checkout \
  --out work/model-pilot/topology-transfer-469-v1 --labels /source-only/census.json
python scripts/omr_head_topology_transfer.py --retained-root /retained/checkout \
  --out work/model-pilot/topology-transfer-469-v1 --evaluate
```

A public clone lacks retained private/local inputs and cannot reproduce the
source run. Completed replay verifies frozen inputs/code, source census,
raw recognition and report hashes, without another recognition. Both completed
reports replayed unchanged. A started/unreceipted engine invocation cannot
retry implicitly; failed native inference omits native/fused metrics rather
than presenting a successful zero-count baseline.

**Validation:** 113 OMR + 105 SH1991 fixtures pass (**218 total**), including
14 new pixel/topology, gate, protocol/replay, source-command, raw-byte drift and
native-failure controls. Existing CI `test_omr_head_*.py` discovers the suite.
Fixtures and shared CI check implementation/accounting, not musical acceptance.

Next bounded work: source-blind handling of broken outlines and selective
abstention, plus native-priority collision evidence. Freeze any new recipe
before the next original source, **SH2025/254, Warsaw**. Do not call a tuned 469
rerun new-source validation.

No reader/score/source edits, engine integration, model recipe changes, corpus
admission, deployment or human-effort measurement. **Whole scores accepted: 0.
Safe to promote: false.**
