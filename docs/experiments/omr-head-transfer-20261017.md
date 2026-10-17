# Unchanged head-proposal transfer: open heads and rest confusions

2026-10-17. Follow-up to [the consumed-development recovery](omr-head-proposals-20261017.md),
PR #485. This **retained negative result** blocks promoting that add-only pass.

## Freeze and source evidence

Selected **SH2025/531, Clayton**, the sixth source in the original hash-ranked
eligible list. The first five had already been consumed. No outcome-based
replacement was made. Catalogue metadata and generic historical recognition may
exist; this is a new complete-window source census for this experiment, not a
claim that the page has never been processed or seen anywhere.

Before viewing the source, froze the unchanged detector, classifier and
373-exemplar bank, native V7 engine/settings, add-only native priority, three
matching radii and failure policy. Code/input/dependency/engine hashes are
checked again before and after inference. Source selection uses metadata and
source byte hashes, not pixels or a recognized graph. One initial preparation
attempt stopped on an absent template-path field before writing any protocol
or viewing the source; the final runner resolves that field from its original
engine-input protocol. The successful freeze precedes all source inspection.

Then read the raw scan and an enlarged source-only crop. Recorded **all 29
pitched heads** in the pickup plus the next three complete measure spans across
four supplied staff windows: 11 round/open, 10 square/open, 7 triangle/open and
1 diamond/open. Source centers and labels are provisional same-agent readings,
**not independent gold**. The complete census was hash-locked before exactly
one new native recognition and automatic image-proposal inference. No previous
XML/graph was read as truth. No source-centered classifier arm was run.

## Results at the frozen primary radius (0.5 source interline)

| Arm | Candidates | Matched / 29 | Unmatched candidates | Correct literal labels / 29 |
| --- | ---: | ---: | ---: | ---: |
| Native + unchanged expanded classifier | 19 | 14 | 5 | 13 |
| Image-only, all dense cores | 2 | 0 | 2 | 0 |
| Image-only, selective squares | 2 | 0 | 2 | 0 |
| **Primary: native + selective squares** | **21** | **14** | **7** | **13** |

The square pass recovers **zero** heads and adds **two** unmatched candidates.
Geometric matched-candidate fraction decreases from 14/19 to 14/21. All 29
source heads and all candidates remain in the denominators. Unmatched native
nodes are not automatically certified false positives or extra exported notes.

At radius 0.35 the counts are identical. At the predeclared 0.75 sensitivity
radius, native and fused arms each match **16/29**, with **14/29** correct
literal labels; native has 3 unmatched candidates and fusion has 5. The
image-only arms still match none. We did not select a more favorable radius
after seeing those results.

### What the new evidence establishes

- **Rest confusion:** post-inference source-only enlargements show both added
  detections are rests, not pitched heads. Each passes the selective
  square/filled gate despite its classifier margin. This is observed artifact
  evidence, not an inference that every unmatched node must be a rest.
- **Open-head localization gap:** the filled-core image pass matches none of
  the 29 open heads. At the primary radius, native detection misses 15. This
  is outside the filled-head detector's intended positive coverage, but still
  matters to the overall add-only pipeline and its precision.
- **Diamond classification gap:** the matched open diamond is classified
  round/filled by the unchanged exemplar classifier. Locating a head does not
  establish its correct literal shape/fill.
- **No fresh filled-square recovery claim:** this all-open window cannot test
  whether the six-square recovery on consumed SH2025/219 transfers to another
  filled-head source. It does show that native-priority suppression alone
  does not protect every new source from bad additions.

The source census, parameters, engine, bank and thresholds were not changed
after viewing results. This source is now consumed: future development may
use it with explicit exposure labeling, but must not call another tuned run
an untouched validation result.

## Reproduction and evidence

New runner: `scripts/omr_head_transfer.py`. Local retained scans and engine
artifacts are required; a public clone cannot reproduce this source run.
Only aggregate counts and evidence hashes are in
[the companion JSON](omr-head-transfer-20261017.json). Raw scans, observation
coordinates, graphs, exemplar pixels and per-head pairs stay ignored in `work/`.

```sh
python scripts/omr_head_transfer.py --retained-root /path/to/retained-checkout \
  --out work/model-pilot/head-transfer-531-v1 --prepare
# Inspect source ONLY, record the complete census, then lock it:
python scripts/omr_head_transfer.py --retained-root /path/to/retained-checkout \
  --out work/model-pilot/head-transfer-531-v1 --labels /path/to/source-census.json
python scripts/omr_head_transfer.py --retained-root /path/to/retained-checkout \
  --out work/model-pilot/head-transfer-531-v1 --evaluate
```

Completed replay verifies protocol, source census, raw recognition and report
bytes without another engine run. A started-but-unreceipted engine run cannot
be retried implicitly. Engine failure preserves the failure and leaves native
and fused metrics unavailable, never invented as successful zero-count runs.
No historical study runner or frozen protocol is rewritten.

Seven new clone-safe fixtures verify source identity/completeness, unresolved
labels in the denominator, scope/coordinate checks, immutable raw/report reuse,
pre-inference source locks and no implicit engine retries. The existing CI
`test_omr_head_*.py` discovery includes them without changing the workflow.
Local validation: **99 OMR + 105 SH1991 fixtures pass** (204 total), including
the seven new transfer fixtures. Completed source-run replay is identical,
with no second recognition; retained input hashes remain unchanged. Shared
reader CI is a separate integration gate, not proof of source fidelity.

## Next bounded development

1. Use exposed development sources to distinguish rest/bar/beam ink from filled
   squares; retain the current rest failures and open-head noncoverage.
2. Develop automatic open-head localization and center-robust literal
   classification, with explicit square/open and diamond/open strata.
3. Freeze those interventions before the next source in the original order
   (SH2025/469), keep complete windows, and retain all failures. Scan-style
   diversity and a new filled-square positive transfer are still outstanding.

No reader/score/source edits, corpus admission, engine integration, deployment
or whole-score acceptance. Pitch/rhythm/exported-event accuracy and human
correction time remain unmeasured. **Whole scores accepted: 0. Safe to promote:
false.**
