# Shared image grid integrated into native-score auditing

2026-10-16. Follow-up to [the image-geometry study](omr-image-geometry-20261016.md),
stacked on PR #479. This connects the successful barline prototype to the
existing score-audit command. It does **not** deploy the unsuccessful notehead
or render-back classifiers, change the recognition engine, or edit scores.

## What is integrated

`omr_score_audit.py --grid-manifest` now runs a hash-bound image-grid stage and
attaches `gridAlignment` to its normal diagnostics. Without the option, its
previous output is unchanged and it does not require Pillow.

The new `omr_grid_alignment.py` adapter reads saved Audiveris `.omr` stack
coordinates directly, rather than misusing MusicXML engraving coordinates as
source pixels. It requires an explicit sheet/system, a single-image input,
matching native input path and dimensions, and ordered, nonoverlapping supplied
music-only bands matching one five-line staff per native part. Unregistered,
resized, reordered, multistaff or unsupported inputs fail explicitly; they are
not automatically resized or mapped by measure count.

Image boundaries match draft boundaries only when each has exactly one candidate
within four pixels. Collisions remain ambiguous. The adapter proposes clipped
per-staff crop boxes and retains **many-to-many** span/stack overlap:

- One saved measure spanning several image segments is a split proposal.
- Several saved measures within one image segment are a merge proposal.
- Mixed overlaps, missing staff lattices, missing coverage and special stacks
  remain review findings, not repairs.
- Native stack indices remain distinct even when their display IDs repeat.
- Native adjacent left/right joins can differ by one rounding pixel. Their
  shared coordinate is canonicalized before matching, then mutually unique
  image matches are snapped; both raw and aligned extents are retained.

The output contains **no usable MusicXML measure map** (`measureMap: null`).
It does not replace the explicit reviewed map required by `omr_source_repair.py`.
Stack indices are not guaranteed to equal exported measure indices. The first
and last proposed spans are clipped by music-only x bounds, not certified
complete measure crops. Unsupported single-staff marks remain in the raw grid.
No pitch, rhythm, lyric, repeat semantic, or note-to-export correspondence is
inferred. Agreement is labeled a geometry-consistent **proposal**, not approval.

## Consumed-development replay

No new page was consumed, and no recognition was rerun. Existing Penn and
Heavenly Land source images, native graphs, raw exports, source readings and
earlier experiment runs remain unchanged. Source labels, expected measure
counts and prior repair maps are **not inputs** to the alignment algorithm.

| Saved graph | Image internal boundaries | Draft boundaries in region | Matched | Image-supported boundaries missing from draft |
| --- | ---: | ---: | ---: | ---: |
| Penn (SH2025 501t) | 11 | 8 | 8 | 3: x=420.5, 641.5, 815.5 |
| Heavenly Land (SH1991 303) | 16 | 15 | 15 | 1: x=802.5 |

Penn yields six proposed spans sharing three native measures, plus a final
special-stack review. Heavenly Land yields two spans sharing one native
measure. These locate candidate merged-measure failures automatically, but
**four located discrepancies are not four corrected boundaries**. The detector
and supplied bands were developed on these pages in #479. There is no new
independent accuracy, whole-song improvement, or correction acceptance claim.
Part-specific omissions can also exist despite a shared native system stack;
this stage does not establish each exported part's completeness.

The first integration replay exposed false tiny overlaps where native adjacent
left/right joins differed by a rounding pixel. That result remains under ignored
`grid-integration-v1`. The explicitly versioned v2 applies the native-join rule
above and removes that artifact; source labels and image detector settings did
not change. This is disclosed development, not a second independent test.

Compact results and evidence hashes:
[`omr-grid-integration-20261016.json`](omr-grid-integration-20261016.json).
Raw scans, graph archives, scores, manifests and detailed crop proposals remain
local under ignored `work/model-pilot/sh1991-v1/grid-integration-v2`.

## Invocation and provenance

Requires Pillow for the optional image stage. Example manifest (paths can be
absolute or relative to the manifest directory):

```json
{
  "coordinates": "original-source-pixels; no registration transform",
  "sheetNumber": 1,
  "systemId": "1",
  "scoreSha256": "<SHA256 of the score passed on the command line>",
  "source": {"path": "source.jpg", "sha256": "<SHA256>"},
  "graph": {"path": "source.omr", "sha256": "<SHA256>"},
  "bands": {"path": "bands.json", "sha256": "<SHA256>"}
}
```

Bands retain #479's `sourceSha256` and `bands: [[x0,y0,x1,y1], ...]` schema.
Use original recognition receipts when preparing the manifest: the graph stores
an input path/dimensions, **not its original input hash**. Caller-supplied hashes
bind this analysis to chosen artifacts; they do not reconstruct or independently
prove the historical engine input or score/graph musical correspondence.

```sh
python3 scripts/omr_score_audit.py /path/to/raw.mxl \
  --grid-manifest /path/to/manifest.json \
  --output /tmp/new-audit/audit.json
```

Detailed alignment and protocol are saved beside the audit in `audit-grid/`.
Code, recipe, manifest, score, source, bands and graph hashes bind the protocol.
Completed exact runs are reused without image inference; changed inputs require
a new output directory. Input drift during analysis is rejected. Invalid optional
grid inputs stop the requested integrated audit; omit the flag to run only the
original score diagnostics. No silent success fallback is used.

## Verification and next boundary

- 13 new fixtures cover native archive/CLI integration, missed and extra bars,
  equal-count displaced grids, matching collisions, special duplicate IDs,
  missing lattice/evidence, native rounding joins, immutable inputs, exact-run
  reuse, input hash drift, path/dimension/staff-order rejection and unchanged
  default score auditing.
- 105 existing SH1991 and 18 image/transfer fixtures pass: **136 Python tests**.
- Without site packages, nine pure integration fixtures pass and four image
  fixtures explicitly skip. CI now installs pinned Pillow 11.3.0 and runs both
  grid and image/transfer suites, so image integration does not silently skip.
- 104 Node tests and the production build pass locally. No UI changed; no new
  browser visual claim. The existing large-bundle warning remains.

The next integration boundary is graph-head localization and explicit
source-reviewed event reassignment into these proposed segments. Shared grid
agreement alone cannot move MusicXML notes or certify their rhythm. **Whole
scores accepted: 0. Recognizer changed: no. Safe to promote: false.**
