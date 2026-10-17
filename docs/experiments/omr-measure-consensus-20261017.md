# Recovering internal bar structure: Thy Strength 8 → 16 measures

2026-10-17. Follow-up to [export survival and acceptance evidence](omr-export-acceptance-20261017.md),
PR #488. This is **consumed-source development**, not a new held-out result,
general reliability claim or source-certified score.

## What changed

The retained Thy Strength logs show MEASURES deleting physical barline columns
when too few staves retain recognized bars. An unchanged cross-staff image
diagnostic nevertheless finds vertical ink at every printed internal boundary.
The new, separate engine restores missing **internal thin bars** from that pixel
evidence before `MeasuresBuilder` constructs/groups measures.

The intervention is `atlas.barConsensus`, **default off**. It uses native staff
geometry and original binary pixels, not supplied boundary coordinates, source
event labels, a target count, another scan edition, or repaired XML. Strong
cross-staff ink is still a proposal, not semantic proof. Existing bars/groups
remain unchanged. Added physical graph bars are synthetic/no-glyph and logged;
source images are never rewritten.

## Final paired-development result

Same binary/settings per pair; property off versus on. All three final off
controls reproduce their archived written-event inventories and lyric/notehead
counts exactly. The earlier nonmatching control is separately retained below.

| Source / measured scope | Off | On |
| --- | ---: | ---: |
| Thy Strength exported measures, each of four parts | 8 | **16** |
| Thy Strength observed internal boundaries matched / 16 | 8 | **16** |
| Thy Strength unmatched extra internal boundaries | 0 | **0** |
| Penn exported measures, each of four parts | 9 | **11** |
| Penn observed internal boundaries matched / 11 | 8 | **11** |
| Penn unmatched extra internal boundaries | 0 | **0** |
| Clayton exported measures, each of four parts | 8 | **16** |

Thy Strength has **17** directly observed written measures and Penn **12**.
Their last written regions are still classified `CAUTIONARY` rather than
exported. **Neither song is complete.** Clayton's full source grid was not newly
annotated: its 8→16 count is not proof of sixteen correct source measures.

Thy Strength's source-to-export geometry map covers 6→16 of its 17 source spans
per part; Penn's covers 5→11 of 12. Merged/ambiguous/cautionary regions stay
null and every unused exported measure is an explicit orphan. Source event
pitches never force a favorable alignment. Boundary tolerance is four pixels.

### Musical improvement is smaller, and mixed

Against Penn's unchanged provisional 120-event full-song observations, using
the **same exact-span geometry alignment recipe in both new arms**:

| Complete event accounting | Off | On |
| --- | ---: | ---: |
| Matching pitch/rest + duration + onset + staff + voice events / 120 | 25 | **46** |
| Missing event units | 95 | 74 |
| Extra event units, including orphan measures | 129 | 102 |
| Missing + extra complete-event units | **224** | **176** |
| Matching observed playback tie endpoints / 16 | 2 | 3 |

Error-unit set differences: **127 removed, 79 introduced**, net 48 fewer.
These are map-dependent missing/extra complete-event units, including orphan
physical-span identities, **not 127 independently certified fixes or 79 newly
proven musical errors**. Moving an unresolved event between orphan and mapped
contexts changes error identities. A substituted event can count twice.
Regressions coexist with gains; this is not a zero-regression musical result.

The earlier reported 33/120 and 208 error units used Penn's manually reviewed
development map. They are not the baseline of this new geometry-only comparison:
it abstains on merged regions instead of choosing a source measure within them.
Do not compare 46 to 33 as though the maps and denominators were interchangeable.

Known opening source-head retention does not regress at any of the three
retained radii (0.35/0.5/0.75 interline): Thy Strength stays **20/32**, with
18 timed/export-presence witnesses; Clayton stays **14/29**, with 14 witnesses.
The ten separate topology proposals are still not integrated into the engine.
Full-image graph head counts decrease, but unreviewed removed heads are not
automatically false positives. No new shape/fill or full-source event accuracy
is established for Thy Strength or Clayton.

## Retained development history — no erased failures

1. **Engine v1, strict protocol:** 3 off + 3 on runs. All off controls match.
   Thy Strength/Clayton improve to 16 measures; Penn's on arm fails to export.
   A pixel-supported proposal lies inside a different existing column's native
   joining distance. Occupied column cells leave unequal staff-group lengths,
   causing `MeasuresBuilder.buildStaffBarlines` to raise an index error. Penn
   on metrics remain unavailable, not zero. This version fails its gates.
2. **Engine v2, strict protocol:** adds only collision/ungrouped-neighbor
   abstention, using native column tolerances; nine original + two new Java
   tests pass. Three off controls run. Penn differs by a leading header-only
   rest/empty region, shifting its exported grid from 9 to 8. The strict
   contract stops **before any on run**. This result remains blocked.
3. **Same v2 engine, explicit paired protocol v3:** separately freezes a control
   policy preserving the exact archival result and allowing only rest/empty
   spans entirely before directly observed source music to vary. Every
   source-overlapping physical-span event plus lyric/notehead counts must
   match. A pitched omission, changed source event or trailing orphan cannot
   use that exception. Three new off + three on runs complete. All three off
   controls happen to match archives **exactly**; the exception is not used.
   Final candidate exports all sources and passes the bounded aggregate gates.

The blocked control variability is not causally diagnosed or disguised as an
exact replay. All **15 new recognition invocations** are disclosed: 6 + 3 + 6.
No original frozen engine/run was overwritten or implicitly retried. Code,
settings, source and label bytes are locked before each active phase. Coverage
thresholds were not swept; no Warsaw source or new validation cohort was opened.

## Evidence, tests and replay

Engine helper/test/hook bytes are versioned under
[`audiveris-measure-consensus-v1`](../../experiments/audiveris-measure-consensus-v1/README.md)
and [`v2`](../../experiments/audiveris-measure-consensus-v2/README.md).
Both are built from the same upstream revision plus the unchanged V7 source
recipe, in separate retained checkouts. Original V7 binaries remain unchanged.

- Current engine suite: **11 Java tests pass**, including actual synthetic
  pixel scanning, staff-majority/duplicate voting, broken/wide ink, column join
  collisions and ungrouped neighboring proposals. Rejected v1's final suite:
  **9 Java tests pass**; those tests did not prevent its real export failure.
- **13 new Python fixtures pass; all 145 OMR + 105 SH1991 = 250 Python tests
  pass**, no skips with retained Pillow 11.3.0 / NumPy 2.0.2. They cover merged
  and cautionary maps, equal-count wrong grids, orphans, changed musical events,
  rest-only header normalization, candidate gates, no-retry, artifact/path drift,
  unavailable failed exports and simultaneous fixes/regressions.
- Recognition replay verifies engine/inputs/artifact bytes without inference.
  Final analysis replays byte-identically. Original topology and export-audit
  evidence hashes are checked unchanged; raw source/score artifacts stay local.

The [companion JSON](omr-measure-consensus-20261017.json) contains aggregate
metrics and evidence hashes, never scans, coordinates or per-head XML joins.
Local roots: `work/model-pilot/measure-structure-v1/`,
`measure-structure-v2/`, and `measure-structure-paired-v3/`.

```sh
python3 -m unittest discover -s tests -p 'test_omr_*.py'
python3 -m unittest discover -s tests -p 'test_sh1991_*.py'
python3 scripts/omr_measure_consensus_paired.py --replay --out /retained/v3/run
python3 scripts/omr_measure_consensus_study.py --paired \
  --study /retained/v3/run --out /new-analysis \
  --thy-grid /frozen/thy-grid.json --penn-grid /frozen/penn-grid.json \
  --thy-heads /frozen/thy-heads.json --clayton-heads /frozen/clayton-heads.json
```

Fresh public clones lack the retained source/config/engine inputs. Public CI
checks clone-safe Python fixtures and the unchanged reader application; it does
not build the private local engine or independently certify music.

## Remaining work

The next structural target is **terminal-bar / cautionary-region handling**:
the genuine final source regions still do not export. Diagnose that with exact
source, physical-bar and stage witnesses before changing a general courtesy
rule or forcing a final measure. Opening key/clef recognition remains wrong;
no source-header fixes are bundled into this bar-only intervention.

After complete structure, integrate selective heads through stem/chord/rhythm
and exported events, with full-song source audits. Independent source-reading
verification, literal shapes/fill, lyrics and remaining markings are still
missing. Unknowns and corrections stay agent-owned.

No app enablement, canonical score edits, model training, source upload,
fresh-source reliability claim, corpus admission, deployment or merge.
**Whole scores accepted: 0. Safe to promote: false.**
