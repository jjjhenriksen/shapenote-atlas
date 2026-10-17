# OMR evaluation: reusable evidence contract

This contract separates observable recognition outcomes from conclusions the
available labels cannot support. It does not replace or relax any frozen
experiment's selection gates.

## Evidence layers

| Layer | Denominator and observation | What it does not establish |
| --- | --- | --- |
| Source head detection | All enumerated source heads in frozen review windows; spatial one-to-one matches, without source shape/fill in the matching cost | Correct pitch, distinct exported notes, full-page precision |
| Fill | Report both correct fill / judged retained heads and retained correct fill / all known-fill source heads | Missing heads must not disappear from the all-source denominator |
| Shape | Source-shape strata and engine-native labels; explicit unsupported vocabulary | An ordinary BLACK/VOID label is not a round/square/diamond classification |
| Structural survival | Retained, stem/chord, measure, voice, timed slot, unique export-layout witness | A scheduled note is not necessarily correct; a missing unique witness is not proof of export deletion |
| Candidate XML agreement | Pitch/duration/onset agreement against the fixed candidate reference | Unreviewed reference XML is not source gold |
| Error-directed source review | Source pixels at selected retained unmatched locations; `head`, `non_head`, `uncertain` and review notes | An unmatched head is not automatically false; a source-empty center is not proof of a distinct extra exported event |
| Generalization | A later frozen grouped validation/test evaluation after the unchanged training selection rule passes | Re-analysis of exposed training scans is not a generalization result |

## Requirements

- Freeze source IDs, coordinates, selection rule and provenance before using
  the reviewed labels for a new intervention. Keep historical annotations,
  explicit adjudications, engines, reports and gates unchanged.
- Use label-blind one-to-one spatial matching. Declare the matcher/radius;
  preserve sensitivity analysis. Do not mix a new matching policy into old
  numbers without separately naming and comparing it.
- Report page and shape/fill strata, counts and denominators. Empty or
  unsupported quantities are unavailable (`null`), never a successful zero.
  Missing stage evidence is distinct from an observed absent stage.
- Compare count thresholds exactly. Never round a borderline result into a
  pass. Show source-certified precision as unavailable until there is a
  complete, appropriate source-grounded prediction denominator.
- If all arms have zero retained detections on negative points, flag the
  final-stage floor. Proposal veto counts cannot establish final precision.
- Review actually retained unmatched locations, including real-head overlaps
  and displaced duplicates. Preserve uncertainty and selection bias. A
  targeted diagnostic sample is not a population precision estimate.
- Template distance comparisons must expose position, orientation, anchor,
  search path, veto and missing-pair information. Scanner minima at different
  positions are not fixed-center comparisons. Equal logged slim-box centers
  still do not prove equal internal anchor coordinates. Correlated proposals
  are not independent accuracy observations.
- Bind reports to input/evidence/code hashes and provide analysis-only replay.
  Source pixels and restricted engine artifacts remain local.

## Current reusable implementation

`scripts/omr_point_eval.py` has no SH1991 paths or engine dependencies. Its
`summarize_points`, `threshold_check`, `negative_diagnostic` and
`paired_proposals` functions implement the count, availability and comparison
rules. Callers supply frozen spatial assignments and an explicit native-label
decoder; this module does not silently rematch or fabricate source labels.

`scripts/sh1991_eval_diagnostics.py` is the SH1991 adapter. It verifies and
reuses the frozen V3 artifacts; enumerates the retained-unmatched review
queue; draws source-only review cards locally; validates complete review
coverage; and produces a separately named diagnostic report. It invokes no
recognizer and reads no held-out source images.

Before using this beyond the current three training scans, expand source-first
annotations across tunes, print conditions, all four shapes, both fill states
and genuine confusing non-head marks. Keep tune/scan families grouped across
splits, freeze an adequate full-window prediction denominator, and obtain
independent review for any claimed source gold. The single open-diamond
example in the current audit is insufficient for that general claim.
