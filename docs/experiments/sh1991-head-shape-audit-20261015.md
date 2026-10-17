# SH1991 diagnostic: triangles stand out

Date: 2026-10-15. Follow-up to the [40-image baseline](sh1991-omr-baseline-20261015.md), advancing [#471](https://github.com/jjjhenriksen/shapenote-atlas/issues/471).

Follow-up experiment: the [opt-in fa-template v1](sh1991-fa-template-v1-20261015.md)
recovers many more triangle heads but fails fill, other-head, and score-level
gates. It is a rejected training-only prototype, not a production fix.

## Finding and next decision

**The strong association is with triangular heads, not non-round heads generally.** In a source-literal audit of 210 printed noteheads on three training scans, the retained Audiveris graph contains heads at 10 of 62 triangle locations. All 148 round/square/diamond locations have retained heads after two explicitly documented coordinate-offset adjudications.

| Printed head | Source observations | Automatic coordinate matches | After visual adjudication |
| --- | ---: | ---: | ---: |
| Round | 69 | 69 | 69 |
| Square | 70 | 68 | 70 |
| Diamond | 9 | 9 | 9 |
| Triangle | 62 | 10 | 10 |

**All nine retained filled triangles are labeled `NOTEHEAD_VOID`**, a separate fill-state error. The one retained open triangle is also labeled void, consistent with its printed fill. Matched non-triangle heads have the observed open/filled state in this sample.

Recommendation: investigate **Sacred Harp fa-triangle recognition/retention, both fill states and stem orientations**, before assuming every shape needs a new model or starting a broad fine-tune. Inspect head templates, head–stem associations and graph rejection paths. A narrowly targeted change should be compared with the original engine on fresh, independently reviewed data, retaining the separate measure-alignment test. Do not redraw notes in the canonical source or derive missing printed shapes from pitch/key.

This is strong diagnostic evidence, **not a controlled causal experiment** or proof that the neural classifier itself is the failing stage. A head can be detected internally and subsequently rejected before the saved graph. Nothing here quantifies how much of the full transcription error, timing error, or human correction time a triangle fix would recover.

## Source-first method

- Fixed sample before detailed per-head matching: all pitched head centers in original x range `[250, 1050)` on all four staves of the **first system** of training images **26 Samaria, 68b Ortonville, and 89 The Church's Desolation**. Rests are excluded. These are 12 staff windows; no held-out image was used.
- Enumerate visible notes and observe literal round/square/diamond/triangle and open/filled state from original scan crops, not MusicXML tags, key, scale degree, or Audiveris head labels. Read staff half-line positions directly for localization. Staff-line geometry comes from the retained engine layout, not its head detections.
- Source-only cards have a 2× viewing enlargement and an original-x ruler. Original bytes are unchanged. Small source-pixel footprint checks refine x centers where unambiguous; the bounded recipe is recorded in the JSON. All 12 source-only point overlays were visually inspected before labels were frozen. One rounded-corner diamond was resolved using a larger original-context crop before matching.
- Match those frozen positions against saved `<head>` nodes, not serialized MusicXML event order. Primary criterion: one-to-one, distance-only greedy matching within **0.5 staff interline**. Neither source shape nor fill enters the matching cost. Test the predeclared 0.35 and 0.75 radii as sensitivity checks.
- Read chord membership from the graph's containment edges and count staff assignment separately. All matched heads in this audit are assigned to the expected staff and belong to a head chord. That does not prove successful or correct export.
- Inspect source/graph overlays afterward. Two square anchors land on the right edge rather than the center of their glyphs. Their detected heads are visibly present. Preserve the original annotations, automatic matches, and all three-radius results; record the two post-match adjudications separately. No triangle label or coordinate was changed after matching.

The annotations are **single-AI visual observations**, not independent human source certification or training-ready ground truth. The reviewer knew the earlier aggregate baseline results; this was not a fully blinded trial. Every head was visually judged legible in its local source context; there is no quantitative scan-quality-matched intervention.

## Fill and scan checks

After the explicit visual adjudications:

| Stratum | Triangles with retained heads | Other shapes with retained heads |
| --- | ---: | ---: |
| Filled | 9/44 | 108/108 |
| Open | 1/18 | 40/40 |
| Samaria 26 | 7/17 | 67/67 |
| Ortonville 68b | 2/29 | 47/47 |
| The Church's Desolation 89 | 1/16 | 34/34 |

Thus the gap is present within both fill strata and all three source scans, rather than merely comparing dark filled shapes with light open ones or one good scan with one poor scan. Duration, stem direction, staff position, connected ink, and local crowding remain possible confounders; these are not 210 independent experimental units. Only three scans and one font/edition family were sampled. In particular, nine diamonds are far too few to establish generally reliable diamond recognition.

Automatic matching sensitivity (before the two visual adjudications):

| Radius, in interlines | Round | Square | Diamond | Triangle |
| --- | ---: | ---: | ---: | ---: |
| 0.35 | 69/69 | 67/70 | 9/9 | 9/62 |
| 0.50, primary | 69/69 | 68/70 | 9/9 | 10/62 |
| 0.75 | 69/69 | 69/70 | 9/9 | 10/62 |

The main triangle finding is stable across these tolerances. This measures **retained graph-head localization**, not end-to-end note recall, correct pitch, rhythm, literal-shape classification, false-positive rate, or readable pages. The corresponding graph labels are conventional `NOTEHEAD_BLACK`/`NOTEHEAD_VOID`; a successful position match does not mean Audiveris preserved the printed four-shape identity.

## Evidence and replay

The [machine-readable audit](sh1991-head-shape-audit-20261015.json) includes the 210 numeric observations, source URLs/hashes, graph hashes, frozen annotation/design hashes, per-shape/fill/scan/staff counts, matching-radius sensitivity, and both post-match adjudications. No source images, MusicXML, OMR graph bytes, or crop pixels are published. It explicitly sets source certification, training eligibility and causal-effect establishment to false.

Original source-only cards, frozen annotation receipts, and overlays remain under ignored `work/model-pilot/sh1991-v1/head-shape-audit-v1/`. Exact replay requires the retained original scans and raw Audiveris `.omr` files from the baseline, not merely a clone. A new inference run can produce different archive hashes and must be treated as new evidence.

```sh
python3.12 -m unittest discover -s tests -p 'test_sh1991*.py'
python3.12 scripts/sh1991_head_audit.py replay
```

`replay` hash-checks the retained source/graph artifacts and independently recomputes all matches, counts, sensitivity tables and explicit adjudications from the saved numeric labels. It does **not** certify that those literal labels are correct. For the original local annotation receipts:

```sh
python3.12 scripts/sh1991_head_audit.py render
python3.12 scripts/sh1991_head_audit.py analyze
```

`render` reads draft source-only annotations, and `analyze` requires the frozen source-only-review status and matching design hash. The initial sampling/card creation and literal labeling were performed locally; the published numeric observations are the replayable analysis input, not a claim of automatic annotation. All graph/shape test fixtures are clone-safe and use only Python's standard library. No additional inference, training, source upload, canonical score edit, or review-gate change was needed for this audit.
