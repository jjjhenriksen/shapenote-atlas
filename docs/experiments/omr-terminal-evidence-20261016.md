# Barline terminal evidence and retained classifier failures

2026-10-16. Follow-up to [the measure loop](omr-measure-loop-20261016.md),
stacked on PR #481. Jacqueline correctly noted that a perfect 24-crop sample
does not make the system good enough. This iteration fixes a specific structural
failure and expands the next source-first check to 48 notehead targets.

## What changed—and what did not

The old detector accepted columns with at least 86% vertical ink coverage across
the staff. Ephesus's extra proposal at x=671 was supported by three aligned note
stems: each covered most of the staff, but failed at one terminal region.

`omr_terminal_grid.py` keeps the original candidates and adds evidence in two
short vertical windows, 0.2–0.65 staff interlines inward from the top and bottom
staff lines. At least 75% of each window must contain ink **on the same column**.
The original strict-majority-of-all-supplied-staves denominator remains. Rejected
columns/staff evidence stay in `unresolved`, not silently deleted. Full-height
aligned stems can still pass: this is a useful filter, not a barline proof.

`omr_terminal_worklist.py` connects this separately versioned stage to the saved
native graph/head adapter. It retains raw grid evidence, revised many-to-many
alignment, native IDs, ambiguous boxes and optional frozen shadow classification.
The existing audit command and old frozen studies are unchanged. No note movement,
MusicXML event mapping, source certification or automatic score acceptance.

## Consumed development: classifier changes did not earn selection

The original 229 SH1991 exemplars remain the training population. Penn, 184 and
now Ephesus are consumed development cohorts, never fresh tests again. SH1991
folds still exclude their entire test source page. No new source labels are
silently added to the bank.

`omr_crop_scoring.py` compares the unchanged exemplar/scale/offset bank using:
raw grayscale SSD; half-weight gradient distance; mean best-three distinct
exemplars per class; contrast normalization; 10%/25% contrast blends; and a
limited low-margin contrast fallback. Multiple transforms of one exemplar do
not become multiple votes. Confidence margins are not calibrated probabilities.

| Consumed cohort | Raw SSD | Gradient | Class top-3 | Contrast | 10% blend | 25% blend | Low-margin fallback |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SH1991 26 (89 targets) | 70 | 70 | 69 | 71 | 71 | 72 | 70 |
| SH1991 68b (84) | 65 | 65 | 62 | 74 | 68 | 71 | 69 |
| SH1991 89 (56) | 51 | 51 | 51 | 53 | 51 | 52 | 52 |
| Penn (48) | 39 | 39 | 38 | 34 | 38 | 38 | 38 |
| And Jesus Crucified (24) | 23 | 23 | 23 | 24 | 23 | 22 | 24 |
| Ephesus (24) | 24 | 24 | 24 | 24 | 24 | 24 | 24 |

The pre-source selection rule requires no net correct-target loss on any consumed
cohort, then maximizes total correct with fixed arm-order tie-breaking. Only raw
SSD and gradient qualify; gradient adds no correct targets, so **raw SSD stays
selected**. Aggregate gains from contrast do not erase its Penn regression.
These alternatives are retained as experiments, not deployed upgrades.

The first four-arm development run remains under `terminal-loop-v1`; its exact
code is retained locally and at commit `85b550a`. Before viewing the reserved
source, v2 adds the three limited contrast blends/fallbacks. Both development
reports remain; the v2 transfer freeze identifies the selected arm and report
hash. No source/test-output-driven retuning follows the reserved check.

The vectorized NumPy raw-SSD implementation exactly reproduces **325 stored
query outputs** from the preceding Pillow implementation: labels, exemplar IDs,
scales, offsets and distances. This is kernel equivalence, not a recognizer
accuracy gain or a measured speedup. NumPy 2.0.2 is research/CI-only; no reader
runtime dependency is added.

## Grid development results—do not pool with the reserved result

| Consumed source | Observed boundaries | Old misses / extras | Terminal misses / extras |
| --- | ---: | ---: | ---: |
| Penn | 11 | 0 / 0 | 0 / 0 |
| Heavenly Land | 16 | 0 / 0 | 0 / 0 |
| And Jesus Crucified | 5 | 0 / 0 | 0 / 0 |
| Ephesus | 9 | 0 / 1 | 0 / 0 |

All 41 observed boundaries remain; the known false proposal is rejected. This
is development on exposed pages, including post-inference witnesses from the
earlier geometry study—not an independent 41-boundary reliability estimate.

## Reserved source-first check: Troubles Over (SH2025 80t)

Choose the fourth original hash-ranked eligible record after Penn, 184 and 188.
Freeze code/input/dependency hashes, scoring selection and the scope before
viewing the source. Then read the original scan, freeze the first twelve pitched
heads per opening-system staff (or all if fewer), staff bands and every internal
boundary witness **before inference**. Left-to-right reading includes simultaneous
heads top-to-bottom: both alto pickup heads count. A source-only 48-crop contact
sheet checks the observations first. The original watermark remains untouched.

Generic archived OMR/metadata may exist; no prior 80t score/reference XML is opened
as truth in this run. Novelty is new-to-this-run source evaluation, not never
processed or independent gold. Labels are provisional same-agent visual readings.

| Reserved-system measurement | Old grid | Terminal grid |
| --- | ---: | ---: |
| Observed internal boundaries | 17 | 17 |
| Matched within four pixels | 17 | **17** |
| Missed | 0 | **0** |
| Extra proposals | 2 | **0** |

This is a genuine matched structural gain on the reserved source within supplied
bands. It is not automatic layout detection, repeat-semantic decoding, full-page
precision or independently certified segmentation.

**The note classifier is still imperfect:** 41/48 joint literal shape/fill labels
correct, seven wrong proposals. All 48 footprints fit the refined proposed spans;
no crop-target abstentions under the full-proposal arm. The unchanged classifier
therefore stays at 41/48—**no note-accuracy gain is claimed**. The selective arm
returns 40 correct, seven wrong and one abstention: here it discards a correct
answer and filters none of the errors. This failure remains visible.

The 48-target sample covers six literal classes, including one filled diamond;
open triangle and open diamond are absent. All are supplied positive centers,
not automatically detected heads. Wrong-target/oracle review count is seven,
not measured human edits/minutes or proof that the system knows every error.
**80t is now consumed.** Future tuning on it is development.

## Native integration and remaining bottleneck

Saved Penn/Heavenly Land native replays retain the same 120/122 localized boxes,
19/5 boundary-crossing boxes and 12/0 outside-region boxes, accounting for all
151/127 native boxes. The four prior candidate missing draft boundaries remain
located. Raw graphs, scores, prior results and source labels are unchanged.
Native proposal counts do not establish true-head recall or exported-event accuracy.

The next substantive note-recognition lever is a controlled expansion of
source-style/class coverage in the research training population, with whole-page
grouping and another untouched source reserved first. Existing consumed SH2025
observations can be considered explicitly, not secretly added to an old model.
An automatically localized complete-window evaluation and independent source
review are still needed before any dependable-transcriber claim.

## Replay, verification and evidence

Local artifacts: `work/model-pilot/sh1991-v1/terminal-loop-v1`, `terminal-loop-v2`
and `terminal-native-v1`. Scans, raw labels, contact sheets, native graphs, scores,
exemplar pixels and per-target predictions remain ignored. Tracked
[aggregate JSON](omr-terminal-evidence-20261016.json) contains counts, phase limits
and evidence hashes, including the retained failures. Completed exact runs reuse
results; changed code, source inputs, observations or selection fail closed.

```sh
# Use Pillow 11.3.0 and NumPy 2.0.2 in an isolated research environment.
python scripts/omr_followup_study.py --prepare
python scripts/omr_followup_study.py --development
python scripts/omr_followup_study.py --freeze-transfer  # BEFORE source inspection
python scripts/omr_followup_study.py \
  --labels work/model-pilot/sh1991-v1/terminal-loop-v2/source-observations.json

python scripts/omr_terminal_worklist.py /path/to/raw.mxl \
  --grid-manifest /path/to/manifest.json --out /tmp/new-terminal-worklist \
  --model-study work/model-pilot/sh1991-v1/terminal-loop-v2
```

These studies require preserved local inputs, not clean-clone scans or new
recognition. Clone-safe CI uses generated fixtures with pinned dependencies.

- **161 Python fixtures pass:** 105 SH1991, 45 prior OMR, 11 new terminal/scoring
  fixtures. New cases cover aligned short stems, unchanged majority denominator,
  full-height unresolved semantics, native integration/reuse, exact SSD witnesses,
  integer overflow, duplicate-variant voting, flat-contrast abstention and frozen
  code/selection guards.
- **104 Node tests and production build pass.** Existing bundle-size warning
  remains; no UI changed or new visual-accuracy claim.
- No fresh recognition, score edits, corpus admission, engine deployment or merge.

**Recognizer changed: no. Whole scores accepted: 0. Safe to promote: false.**
