# Frozen correction loop on four previously unprocessed pages

2026-10-16. Jacqueline asked to test on songs outside the work already used to
build the system. This is a fresh **scoped correction test**, not another
evaluation of the consumed original train/validation/test cohort.

## Novelty and selection

Before image acquisition or inference, freeze four deterministic hash-ranked
pages, one from each of four page-range strata. Exclude the entire original
40-image cohort by page and normalized title, plus pages identified in retained
source-transcription/OMR/experiment JSON and dedicated source-correction script
names. That conservatively excludes **186 known pages**; **356 catalogue
records** remain eligible. The selected pages are:

| Page | Song | New source hash differs from original cohort |
| --- | --- | --- |
| 144 | Jubilee | yes |
| 204 | Mission | yes |
| 303 | Heavenly Land | yes |
| 492 | Invocation (Second) | yes |

“Previously unprocessed” means absent from these recorded local cohorts and
correction artifacts, **not** absent from a model's pretraining or unknown to
Jacqueline. The underlying catalogue already contained metadata/structured
references; no candidate-reference XML was read to choose, label or score these
pages. Duplicate musical material beyond page/title/hash identity is not
independently ruled out. All four are still SH1991/Bremen scans, not cross-book
generalization.

## Protocol and execution

- Freeze correction commit `a250a7617426106f52a2d8b36a5f0cb3dfdeb081`, exact
  correction/renderer hashes, unchanged V7 engine identity and settings, cohort,
  scope and failure policy **before** new inference.
- Read the retained scans directly and freeze the first **two top-staff printed
  measures** per page before viewing new exports or reference XML. These are
  source-first agent observations, not human gold or independent verification.
- Recognize each full source page once, in a bounded local run. **4/4 export**.
  No source upload, paid compute, model training or recognition retuning.
- Feed those drafts and the source observations to the **unchanged correction
  code**; verify scope/archive preservation, a second semantic parser, and
  offline OSMD import/rendering. Inspect all four sources and rendered excerpts.
- Keep failed pages in the fixed denominator, quarantine all whole scores, and
  assign remaining work to the agent. Do not change labels after reading output.

The HTML source pages returned HTTP 403; their public static JPEG URLs returned
HTTP 200. The printed page numbers/titles were checked against the frozen
selection. No security challenge was solved or bypassed.

## Result

| Song | Matching opening segments before | After |
| --- | ---: | ---: |
| Jubilee | 2/2 | 2/2 |
| Mission | 2/2 | 2/2 |
| Heavenly Land | 2/2 | 2/2 |
| Invocation (Second) | 1/2 | 2/2 |
| **Total** | **7/8** | **8/8** |

The concrete repair is in Invocation (Second): restore the source-visible
opening **half rest**, moving the first F4 half note from onset 0 to onset 2
(quarter-note units). This is one observed repair opportunity, **not eight**.
All other observed pitch/rest/duration sequences remain unchanged.

All **4/4** scoped excerpts import/render with matching measure durations and
no page errors. All **78 SH1991 Python fixtures** pass, including five fresh-test
guard fixtures. These demonstrate a frozen writer/verification cycle works on
new inputs, with one new correction—not broad error-correction coverage.

## What did NOT pass the broader goal

Whole-score autonomous acceptance remains **unmet**. Visual inspection still
finds candidate markings outside this check's scope: Mission has an unsupported
`sf` and ornament/articulation candidates; Heavenly Land and Invocation retain
candidate articulation dots. A pitch/rhythm matcher and notation importer do
not catch those source-fidelity errors. Full staff/voice coverage, shape/fill,
lyrics, ties/slurs/repeats and a genuinely independent source-reading verifier
are still unfinished. Whole scores accepted: **0**; human tasks: **0**.

The source-observer's correctness is not independently measured here. Matching
the same source observations used for repair is a consistency check; new pages
and blinded ordering improve this test, but do not make it independent gold.
No confidence interval or broad success rate is justified by four pages and a
single observed error. This cohort is now **consumed**; do not tune a repair
against it and call another evaluation on it held-out evidence.

One setup failure was retained: the evaluation harness initially requested a
nested output directory. The frozen writer correctly rejected it. Only that
analysis adapter path was changed to a sibling directory; recognizer, correction
code, renderer, source observations and raw inference remained unchanged.
The original launcher and both logs remain local.

## Evidence and replay

Tracked aggregate evidence: `sh1991-agent-unseen-v1-20261016.json`.
Raw source scans, observations, exports, XML audit and screenshots remain local:

- `work/model-pilot/sh1991-v1/agent-unseen-v1-20261016/`
- `work/model-pilot/sh1991-v1/agent-unseen-v1-20261016-corrected/`

```sh
cd /Users/jacquelinehenriksen/Developer/atlas-prose-20261015
# Analysis-only replay; never run recognition again just for the report.
python3 scripts/sh1991_agent_unseen.py evaluate
python3 scripts/sh1991_agent_correction.py verify \
  --pilot-work work/model-pilot/sh1991-v1/agent-unseen-v1-20261016 \
  --out work/model-pilot/sh1991-v1/agent-unseen-v1-20261016-corrected
python3 -m unittest discover -s tests -p 'test_sh1991_*.py'
```

The original recognition launcher is frozen in the local pack; changing the
analysis harness must never silently rerun that study with a changed launcher.
Use a fresh protocol/cohort for subsequent engineering evaluations. Next agent
work: richer annotation/voice evidence and independent source-reading checks;
do not hand these errors to Jacqueline.
