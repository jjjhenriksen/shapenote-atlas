# OMR research-tooling refactor and frozen evidence

This is a behavior-preserving maintenance step above PRs #475–#483, not another
recognition experiment or an accuracy claim.

## Shared ranking contract

`scripts/omr_exemplar_ranking.py` owns nearest-variant-per-literal-class ranking
for both the Pillow crop classifier and the NumPy population adapter. Each
backend still computes its own original distances. The shared helper preserves:

- distance, exemplar ID, scale, x-offset, y-offset ordering;
- one best variant per class, never one vote per transformed image;
- the original relative-margin denominator floor of 1;
- inclusive selective threshold, and abstention for tied or single-class banks;
- prediction, selective prediction, margin, exemplar and transform witnesses.

The separate top-k/contrast ablation ranker is deliberately unchanged: it uses
a different margin floor and class aggregation rule. Combining those recipes
would be a model change, not a refactor.

## Verification

- Five dependency-free ranking fixtures check exact witnesses, ordering, class
  minima, the low-distance margin floor, threshold equality and abstention.
- All 76 OMR fixtures and 105 SH1991 fixtures pass with Pillow 11.3.0 / NumPy 2.0.2.
- A read-only regression comparison against the saved consumed-development
  report checks **890 prediction records across seven page-held-out cohorts**
  and every applicable population. All eight output fields match exactly:
  prediction, selective prediction, relative margin, neighbor ID, neighbor
  group, distance, scale and offset. This is implementation equivalence on
  existing development evidence, not a fresh test or an accuracy improvement.
- No study runner, recognition process, reserved-page evaluation, source edit,
  archive regeneration or protocol rewrite is part of this refactor.

## Frozen runs remain historical

The complete pre-refactor implementation is retained in Git at
`1201c69a457e2dbf94799d6b5e0f27ab47b65d5c` (PR #483). All published research
reports, hashes and local frozen artifacts are unchanged. Inspect that revision
in a separate checkout for historical code; retained local source/toolchain
artifacts are still required for local-only paths. A Git revision alone does
not make those raw inputs publicly available.

The classifier and protocol code have changed, so existing frozen studies
correctly reject execution under this revision as code/input drift. Do not
update their hashes, reset consumed-source markers, or launch new recognition
to make a historical run pass. Read the retained reports instead. Any future
authorized study needs a new versioned protocol/output directory and must keep
already-consumed pages in development, not relabel them fresh held-out data.

The shared helper is now included in `omr_measure_study.current_protocol()`'s
input hashes; follow-up and localization protocols inherit that binding.
Changing the helper therefore cannot silently reuse a frozen future run.

This refactor adds no production recognition route, source certification,
corpus admission or whole-score acceptance. All research promotion boundaries
remain unchanged.
