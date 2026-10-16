# Image-grounded OMR proposals and a second SH2025 transfer check

2026-10-16. Follow-up to [the whole-song repair study](omr-accuracy-tracks-20261016.md),
stacked on PR #478. Jacqueline requested the four proposed changes and then
asked that completed actions be checked before resuming after a timeout.

## Recovery and scope

The local checkout was clean at `b41876f`, matching the published #478 head.
No new image-geometry implementation, saved new-idea run, or running recognition
process was found. Existing recognition, failed Penn evaluation, source labels,
repaired scores and frozen protocols were preserved. No recognition rerun,
MusicXML mutation, corpus admission or merge was performed.

Implemented four **experimental, read-only components**, not a recognizer upgrade:

| Component | Implementation | Boundary |
| --- | --- | --- |
| Shared barline scaffold | Five-line staff-lattice detection; full-staff vertical coverage; fixed-width cross-staff clustering; strict-majority support with per-staff evidence | Supplied music-only staff bands, not page-layout detection. Does not infer measure count, meter, or repeat semantics. |
| Geometry-based noteheads | Binary outer-contour profiles and interior-density features, fixed three-neighbor voting; raw and staff-masked ablation arms | Source-centered crops; no notehead detector. Joint literal shape/fill prediction, not pitch-derived labels. |
| Synthetic printing stress | Actual Bravura/Leland music-font glyphs; staff line/space, schematic up/down stem strokes, blur, skew, ink spread and reduced resolution | Synthetic nuisance controls, not valid whole-score engraving or real scan accuracy. |
| Local render-back ranking | Symmetric source/render edge distance, alternative font/orientation hypotheses, explicit weak/ambiguous abstention | Registered local notehead crops only; not full-score rendering, registration or hypothesis search. |

Code: `scripts/omr_image_geometry.py`, `omr_bar_grid.py`, `omr_image_study.py`
and `omr_image_transfer.py`. No existing recognizer code or deployment was changed.

## Development: retain gains AND regressions

The existing 229 provisional labels on three consumed SH1991 pages were reused,
with the same leave-one-page-out grouping and exact raw-pixel baseline. Penn
remains consumed development data, never relabeled as an untouched test.

| Cohort / arm | Baseline matches | Candidate matches | Fixes | Regressions |
| --- | ---: | ---: | ---: | ---: |
| SH1991, raw contour | 176/229 | 171/229 | 18 | 23 |
| SH1991, staff-masked contour | 176/229 | 181/229 | 25 | 20 |
| Penn, raw contour | 26/48 | 27/48 | 7 | 6 |
| Penn, staff-masked contour | 26/48 | 16/48 | 2 | 12 |
| Penn, local render-back | 26/48 | 10/48 | 4 | 20 |

Penn render-back abstains on 29/48 examples and makes nine wrong proposals.
Abstentions remain in the total denominator and count as lost coverage when the
baseline was correct; they are not silently removed to improve the percentage.

### The crop-edge problem

The initial grid comparison used old source-segment crop edges with a one-staff-
interline tolerance. Penn matched 11/11 internal boundaries; Heavenly Land
matched only 12/16, with five extra proposals. These exact initial results remain
in the retained report and tracked aggregate.

Subsequent direct scan review found several Heavenly Land crop edges did not
coincide with printed bars. Its broad opening crop also admitted an aligned
meter glyph as a false bar candidate. A crop edge is **not** a certified barline.
The original repair observations/maps were not rewritten or declared invalid as
pitch/rhythm labels; their crop-edge limitations are now explicit.

A separate, disclosed **post-inference same-agent development review** supplied
approximate internal-boundary witnesses and music-only horizontal regions,
excluding signatures and closing double/final bars. The unchanged grid algorithm
proposed 11/11 Penn and 16/16 Heavenly Land internal boundaries, with no extra
proposals within those regions, at four-pixel matching tolerance. This is not
blind validation. Unsupported marks are retained separately, not promoted to bars.

### Synthetic cross-font stress

Clean glyphs from the opposite font supply templates/training, then all nine
fixed conditions are evaluated in the test font. Alternate triangle orientation
coverage differs: Leland lacks E0C8/E0C9, but has E0BF/E0C0; both fonts cover all
eight shape/fill classes. Missing alternates are disclosed, not rendered as
empty glyph examples. No source page is augmented or altered.

| Test font | Samples | Pixel baseline | Masked contour | Render-back | Render abstentions | Render wrong proposals |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bravura | 90 | 62 | 60 | 47 | 36 | 7 |
| Leland | 72 | 64 | 40 | 40 | 24 | 8 |

Neither geometry nor render-back establishes a useful cross-font replacement.
All 18 synthetic blank/staff/stroke negative controls abstain under render-back,
but they do not establish a real detector false-positive rate. Per-condition
results and glyph inventory are retained in the aggregate JSON. A local Bravura
contact sheet was visually inspected; no glyph pixels or scans are published.

## Reserved transfer: And Jesus Crucified (SH2025, 184)

Use the next SHA256-ranked eligible record after Penn in the prior selection,
not an outcome-based new choice. Generic archived OMR and catalogue metadata
already exist. No earlier 184 draft/reference XML was opened as an answer key.
Novelty is **new-to-this-run source evaluation**, not never-processed material,
unseen pretraining, or independent human gold.

Before opening this source, freeze code, recipe, training-input/font hashes,
selection, source hash, and scope: the first six pitched heads in each of four
opening-system staves (24 heads), and that system's internal barlines. Read the
raw scan, then freeze literal labels, manual centers, bands and boundary witnesses
before any predictions. All 24 selected heads happen to be filled: no open-fill
transfer claim follows.

The first transfer runner stopped on a training-image path-subscript typo **before
any test prediction or grid computation**. Its protocol, runner and failure
receipt remain. Correct only that path plumbing and prepare a new protocol
directory, retaining identical image algorithms, models, thresholds and source
observations. The second preparation was after source reading, not a second
pre-source freeze. No output-driven tuning or replacement page was used.

| Frozen arm | Baseline matches | Candidate matches | Fixes | Regressions | Abstentions | Wrong proposals |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Raw contour | 9/24 | 9/24 | 0 | 0 | 0 | 15 |
| Staff-masked contour | 9/24 | 7/24 | 1 | 3 | 0 | 17 |
| Local render-back | 9/24 | 5/24 | 0 | 4 | 17 | 2 |

The unchanged shared-grid algorithm proposes **5/5 opening-system internal
boundaries**, with zero misses/extras against the frozen provisional witnesses
at four-pixel tolerance. This includes the internal repeat boundary, counted once.

**Disposition:** retain the bar scaffold as the promising next integration path.
Do not deploy either classifier change or local render-back. Five boundaries on
one source-first page are a narrow transfer observation, not a reliability rate,
end-to-end recognition improvement, or whole-song acceptance. This test is now
consumed; any future tuning on it is development.

## Verification and replay

- 105 existing SH1991 fixtures and 18 new image/transfer fixtures pass locally.
- 104 Node tests and production build pass; the existing large-bundle warning
  remains. No reader/UI changes or new browser-accuracy claim.
- New fixtures cover cross-staff missing evidence and denominator preservation,
  aligned stems without a majority, ambiguous/no staff lattice, invalid bounds,
  non-mutating analysis masks, contour/fill separation, extra-ink penalties,
  abstention, class-variant ambiguity, one-to-one boundary scoring, frozen input
  drift, training/test-source overlap, and completed-result reuse without inference.
- **Recognizer changed: no. Whole scores accepted: 0. Safe to promote: false.**

Python image runs require Pillow and retained local scans/fonts/labels. Fixture
modules import without Pillow; image fixtures explicitly skip if it is absent.
No new dependency was added to the reader or CI. Clone-safe checks:

```sh
python3 -m unittest discover -s tests -p 'test_sh1991_*.py'
python3 -m unittest discover -s tests -p 'test_omr_image_*.py'
npm test
npm run build
```

Standalone grid use accepts a hash-bound bands JSON with `sourceSha256` and
`bands: [[x0,y0,x1,y1], ...]`. Bands must localize the same musical system in
all voices; x bounds should exclude clef/key/meter and closing double bars.

```sh
python3 scripts/omr_bar_grid.py /path/to/source.jpg \
  --bands /path/to/staff-bands.json --out /tmp/new-grid-proposals

# Exact completed local runs are reused, not re-executed; drift is rejected.
python3 scripts/omr_image_study.py
python3 scripts/omr_image_transfer.py \
  --labels work/model-pilot/sh1991-v1/image-transfer-v1/source-observations.json
```

Aggregates and local evidence hashes:
[`omr-image-geometry-20261016.json`](omr-image-geometry-20261016.json).
Failed/completed protocols, predictions, source observations, scan inspections,
font exemplars and synthetic sheets remain ignored under
`work/model-pilot/sh1991-v1/image-geometry-v1`, `image-geometry-v2`,
`image-transfer-v1`, and `image-transfer-v2`. They are not clean-clone inputs.
