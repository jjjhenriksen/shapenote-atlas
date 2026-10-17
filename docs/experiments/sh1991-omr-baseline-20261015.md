# SH1991 OMR pilot: baseline and simpler-input probes

Date: 2026-10-15. Advances [#471](https://github.com/jjjhenriksen/shapenote-atlas/issues/471); does **not** complete its source-reviewed model-adaptation acceptance criteria.

## Decision

**Simpler input helps a little, but is not a reliable transcription pipeline yet.** Keep these outputs as research candidates. Do not promote them to canonical scores or source-certified evidence.

Generic OMR has to solve two problems at once: identify printed symbols and reconstruct their musical relationships. Four-shape heads, dense lyrics, stems/beams, repeats, and four simultaneous vocal parts add opportunities for symbol and layout errors. A model designed around conventional round noteheads may have a vocabulary mismatch; this experiment does not isolate that cause.

We tested two inexpensive ways to make the input easier without changing the printed noteheads:

1. **Grayscale plus 2× enlargement:** rejected on the fixed five-image training probe. Pitch and duration recall both fell. Not evaluated on held-out images.
2. **One voice at a time:** improved pitch/duration recall, but harmed written measure/onset alignment. Do not replace whole-page recognition with this method.

Next recommendation: a shape-aware symbol recognizer with a shared system/barline alignment layer, preserving the original scan as the authority. First independently review a small paired subset and establish training-use permission; existing XML is a starting point, not sufficient gold data. Do not replace shape heads with ovals and then claim literal-shape recovery. No fine-tuned model was trained in this experiment.

Follow-up: the [210-head source-literal audit](sh1991-head-shape-audit-20261015.md) specifically singles out triangle-head retention/fill, while round/square/diamond locations fare much better in that small sample. This sharpens the next investigation; it is not a causal or learned-model result.

## Cohort and provenance

The existing corpus has 552 retained SH1991 MusicXML mappings. Their retained hashes were checked. Live catalogue lookup found paired printable PDFs, but those re-engravings are **not** the original edition scans. Original images were acquired separately from `sh1991.sacredharpbremen.org`.

The deterministic cohort contains 40 tune-scan images from SH1991, including images for top/bottom tune entries, not necessarily 40 complete physical book pages. Eight groups were selected in each of five page-number strata (last stratum includes 400+), with Samaria 26 and Edmonds 115 anchored. Split before recognition: **24 train / 8 validation / 8 test**.

Known shared printed pages, normalized titles, or exact transposition-invariant interval/duration sequences were unioned before splitting. This prevents leakage for those detected groups; it is not an exhaustive independent near-duplicate audit. The cohort covers only four-shape notation and one scan family. No cross-book generalization is demonstrated.

Where the selected catalogue XML was “as traditionally sung,” the paired original scan instead uses the catalogue's “as written” XML. This matters: Samaria's two versions have the same 295 pitched events, but differ in two pitch spellings. Every original image and selected XML has a retained URL and SHA256.

All 40 pairs remain `candidate-needs-independent-event-review`, with `trainingEligible=false`. The cohort XML has no lyric anchors; only one score has explicit notehead tags, which are not independently verified literal-source labels. Therefore lyrics and literal notehead/fill are not scored. Restricted source bytes, derived images, labels, engine outputs and toolchains remain in ignored `work/`; the committed [machine-readable report](sh1991-omr-baseline-20261015.json) contains only pointers, hashes, design and measured results.

## Results

“Recall” here means agreement with **unreviewed candidate XML**, not certified source accuracy. Missing exports remain in reference denominators. Pitch matches require exact step, alteration and octave; rhythm uses rational durations. Measures use written ordinal positions, without repeat unfolding.

### Raw Audiveris 5.11.0, all 40 images

| Measure | Result |
| --- | ---: |
| Parseable exports | 40/40 |
| Exact written pitch/duration/measure/onset event sequences | 0/40 |
| Matching part counts | 39/40 |
| Matching per-part measure counts | 4/40 |
| Reference / observed pitched events | 9,090 / 6,338 |
| Candidate pitch recall / precision | 54.0% / 77.4% |
| Candidate duration recall | 53.0% |
| Candidate written measure/onset recall | 26.1% |

An exported, parseable file is not a usable score. Samaria's log also contains exporter warnings/stack traces despite exit status zero and an exported MXL. None of these outputs was manually judged usable; correction minutes remain unmeasured.

### Predeclared training probe

Same five training images for both probes: **26, 83t, 68b, 72b, 89** (965 pitched reference events; 1,001 timed events). Selection rule, recorded before inference: at least +2 percentage points pitch recall, no more than 1 point duration regression, and no fewer completely exported source images. Onset was measured but was **not** a selection criterion; that omission limits the selection rule.

| Fixed five-image cohort | Pitch recall | Duration recall | Measure/onset recall |
| --- | ---: | ---: | ---: |
| Original input | 57.9% | 58.5% | 28.6% |
| Grayscale, full-frame 2× Lanczos | 55.1% | 57.0% | 24.4% |
| Separate voice images | 62.5% | 61.9% | 19.7% |

Enlargement failed the rule and was not taken to held-out evaluation. Voice isolation passed the predeclared pitch/duration rule, despite its onset regression. The unchanged method was then evaluated on the eight test images; no held-out tuning followed.

### Held-out eight-image comparison

| Same test images | Pitch recall | Duration recall | Measure/onset recall |
| --- | ---: | ---: | ---: |
| Original input | 62.2% | 58.2% | 29.2% |
| Separate voice images | 63.4% | 60.4% | 17.1% |
| Absolute change | +1.2 pp | +2.1 pp | −12.1 pp |

All 31 voice images exported (one test tune has three parts). Small pitch/duration gains do not outweigh the alignment regression. This is not evidence of production readiness, meaningful human time savings, or a successful learned adaptation. The sample is small and no statistical significance claim is made. Validation images were included in the raw baseline only, not used to choose these transforms.

## What “one voice at a time” means

Reuse the raw engine's detected staff geometry; require five-line staves and the supplied reference part-count metadata to agree. Keep full image width. Crop vertically with four-interline margins, clamped at adjacent-staff midpoints. Concatenate each voice's staves across systems with 64 white pixels between crops. No resampling, deskew, thresholding, staff removal, pitch insertion or head replacement is used. Original crop pixels are copied unchanged. Lyrics may be clipped and are outside the evaluated scope. The five training crop overlays and all four Samaria voice composites were visually inspected; that is not event-level source review.

Each voice reference is extracted from the selected XML without changing its events. Results are aggregated over all original reference mass. The expected part count and ordering come from reference metadata, so this is a **metadata-assisted layout probe**, not fully autonomous transcription. The raw and cropped pipelines are compared on pitch/duration/onset, not source-certified voice/staff attribution.

## Existing baseline is not forgotten

The retained 2026-08-29 SH2025 audits already document Audiveris attempts: Eagles' Wings 491 (202 raw vs 189 normalized pitched events and duration/empty-measure failures), Radiance 488 (topology and empty-measure disagreements), and Cunningham 561 (graph failure and 13 vs 12 measures). See #471 and `scripts/reconcile_{491_eagles_wings,488_radiance,561_cunningham}_source_audit.py`. These historical failures were not newly reproduced here. This experiment adds a pinned current-tool SH1991 baseline; it is not the first Audiveris trial or a controlled comparison with those older runs.

## Reproduce locally

Requirements: Python 3.12, Pillow 10.4.0 for acquisition/transforms, Java 25, and a local Audiveris executable. Clone-safe evaluator/geometry tests require only Python's standard library. No hosted inference, model download, account change or paid compute is required. Source acquisition needs network access; inference stays local.

Audiveris source: `https://github.com/Audiveris/audiveris`, commit `9e1e55cd2746037d059345881c53e6a6754bffbd` (5.11.0). Build using Java 25 with `./gradlew :app:installDist --no-daemon`. This run used a task-local Temurin JDK archive with SHA256 `61979887f7506a24a57439ff99adb8b3a7fc89977d9cfe3b8984f58a981b7b9d`. Its location is installation-specific; set `JAVA_HOME` normally. No global JDK/security settings were changed.

```sh
python3.12 -m unittest discover -s tests -p test_sh1991_pilot.py
python3.12 scripts/sh1991_pilot.py prepare
python3.12 scripts/sh1991_pilot.py baseline --audiveris /absolute/path/to/Audiveris
python3.12 scripts/sh1991_pilot.py prepare-scale-probe
python3.12 scripts/sh1991_pilot.py baseline --audiveris /absolute/path/to/Audiveris \
  --arm grayscale-2x --record 26 --record 83t --record 68b --record 72b --record 89
python3.12 scripts/sh1991_pilot.py summarize-scale-probe
```

`prepare` freezes local acquisition receipts and will not overwrite an existing dataset. A future live acquisition can differ: use the committed source pointers/hashes to identify drift, rather than claiming it reproduces these exact bytes. Original downloads are size-bounded and cached bytes hash-checked. Raw recognition uses two local workers and a 120-second per-image timeout by default.

The enlargement design/decision for this historical run is retained locally, with its decision and measurements in the committed JSON. To reproduce voice isolation after a complete raw baseline:

```sh
python3.12 scripts/sh1991_staff_probe.py prepare
python3.12 scripts/sh1991_pilot.py --work work/model-pilot/sh1991-v1/staff-probe-train \
  baseline --audiveris /absolute/path/to/Audiveris
python3.12 scripts/sh1991_staff_probe.py summarize
# Only if the training decision passes:
python3.12 scripts/sh1991_staff_probe.py prepare --phase test
python3.12 scripts/sh1991_pilot.py --work work/model-pilot/sh1991-v1/staff-probe-test \
  baseline --audiveris /absolute/path/to/Audiveris
python3.12 scripts/sh1991_staff_probe.py summarize --phase test
python3.12 scripts/sh1991_pilot.py verify
python3.12 scripts/sh1991_pilot_report.py
```

`verify` rechecks source/label/input/output hashes and rescores retained exports. Engine processes have bounded timeouts and failed pages retain reference denominators. Cached engine outputs are never mistaken for new inference. Initial raw/enlargement/training receipts preceded per-run engine-library fingerprints; the report explicitly distinguishes that limitation from the later held-out receipts. A relative `--work` reporting bug in the initial staff probe was fixed; its 20 retained exports were reevaluated without rerunning recognition, preserving the original commands and failure receipts.

## Remaining #471 gates

Independent event-level source review; authorized training data; literal shape/fill and lyric annotations; wrong-edition, obscured-notation and unsupported-semantic controls; a learned domain-adaptation comparison; independently assessed usable pages and human correction minutes. Keep deterministic provenance/semantic validators and existing human-review gates outside the recognizer. This baseline does not authorize source redistribution, upload, training spend, or promotion of candidates.
