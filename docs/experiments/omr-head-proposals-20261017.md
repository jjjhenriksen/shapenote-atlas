# Image-only filled-core proposals: consumed-development recovery

2026-10-17. Follow-up to [expanded automatic localization](omr-expanded-localization-20261016.md)
and the shared-ranker refactor. The next bottleneck was six missing filled
squares, not another supplied-center classifier improvement.

## Scope and development exposure

This is a **new development experiment on already-consumed SH2025/219**.
The complete 33-head source census and four supplied opening-system windows are
unchanged. No fresh page was selected or inspected, no source was relabeled,
and no previous frozen study was executed under changed code.

There was one exploratory geometry diagnostic with the initial fixed recipe,
then an immutable v1 analysis. The retained v2 analysis adds raw-artifact byte
bindings to completed replay; detector parameters, classifier population,
primary arm and results are identical. This is not a pre-source freeze, a
held-out result, or evidence of generalization. Both local runs remain retained.
No parameter sweep or outcome-based selection of a different primary arm was
performed.

## Detector and conservative fusion

`omr_head_proposals.py` detects a five-line staff lattice from each supplied
window. It scans a copy of the original grayscale pixels using integral-image
counts: a core of 0.7 × 0.6 detected interline, at least 90% ink below grayscale
110. Eight-connected response islands yield automatic bounding-box centers.
Responses extending beyond 1.5 × 1.2 interlines are vetoed as extended ink.
These are explicit development choices, not learned or source-certified rules.

The detector receives **only image pixels and staff-window boxes**. It does not
receive annotated centers, literal labels, expected head counts, XML, native
graph nodes or matched-source IDs. No source center is substituted later.
Unresolved staff lattices produce no proposals, not invented spacing.
The threshold can reject pale background marks; it neither removes watermarks
from the source nor establishes robust background rejection across scans.

Classify actual proposal centers with the unchanged expanded 373-exemplar bank
from seven consumed pages; 219 is explicitly excluded. The reconstructed bank
exactly reproduces all eight output/witness fields for **33 archived native
queries**. This is a replay check, not independent classifier validation.

The primary arm is **native-plus-selective-squares**, defined in the new recipe:
keep every archived native center and label, consider only selectively
square/filled image proposals, and suppress proposals within 0.75 detected
interline of a same-staff retained center. Native predictions take priority;
no center moves, native deletions, transitive cluster merging or truth-based
deduplication. All proposals and veto/suppression decisions stay in the local
audit trail. The existing native predictions and their classifier outputs come
from the hash-verified historical report; recognition is not rerun.

## Complete-window development results

All rows use the same label-blind maximum-cardinality/minimum-distance matcher.
The 0.35, 0.5 and 0.75 source-interline radii give the same counts.
Neither literal labels nor native chord membership enter the matching cost.

| Arm | Candidates | Spatial matches / 33 | Unmatched candidates | Correct literal labels / 33 |
| --- | ---: | ---: | ---: | ---: |
| Archived native + expanded classifier | 33 | 27 | 6 | 27 |
| Image-only, all dense cores | 33 | 33 | 0 | **25** |
| Image-only, selective square gate | 17 | 17 | 0 | **10** |
| **Primary: native + selective squares** | **39** | **33** | **6** | **33** |

The primary arm adds six correctly labeled filled squares. Square matches
increase from **4/10 to 10/10**; round 12/12 and triangle 11/11 matches remain.
Six unmatched native predictions remain: this pass does **not** eliminate the
old artifact detections. The geometric matched-candidate fraction is 33/39,
not 100%. Unmatched detections are not independently certified false positives
or proof of extra exported notes.

### Retained failure: localization is not correct classification

The image-only arm finds all 33 locations within the declared tolerance, but
its shifted automatic centers yield only **25/33** correct literal labels.
The selective square gate includes **seven non-square heads** despite their
selective classifier margins. Eleven gated proposals are suppressed near
native detections: the four already-detected squares and those seven wrong
literal labels. The other sixteen raw image proposals are excluded by the
classifier gate, not erased from the raw-candidate diagnostic denominator.

Fusion succeeds here because it preserves better native centers and labels,
not because the new square gate is a reliable standalone detector/classifier.
It would be wrong to promote the image-only arm or report a 100%-precise
automatic transcription pipeline. No open-head or diamond transfer observation
exists in these all-filled round/square/triangle windows.

## Evidence and replay

Only aggregates and evidence/code hashes are published in
[the companion JSON](omr-head-proposals-20261017.json). Original scans, exemplar
pixels, census coordinates, per-head predictions, matching pairs, graphs,
exports and local audit reports remain ignored under `work/`.

```sh
# Requires the retained local inputs, not available in a fresh public clone.
# Pillow 11.3.0 / NumPy 2.0.2, as in shared CI.
python scripts/omr_head_proposal_study.py \
  --retained-root /path/to/retained-atlas-checkout \
  --out work/model-pilot/image-head-proposals-v2
```

The study writes only its new output directory. It verifies the old source,
census, population, protocol/receipt chain and raw recognition hashes without
calling a historical runner or engine. It binds current detector, classifier,
geometry, matching and runner code, dependency versions, source bytes and raw
artifacts. Completed replay checks those bindings and the new report hash
before reuse. Drift fails closed; use another versioned output directory,
never reset or rewrite a historical protocol. Replay requires the exact code
revision and retained inputs; it is not permission to mutate frozen evidence.

## Verification and next decision

- **15 new clone-safe fixtures** cover pixel-derived centers/translation,
  source-image immutability, gray/beam/bar controls, open-head noncoverage,
  missing lattices, invalid windows, nontransitive/native-priority fusion,
  actual automatic crop coordinates, source-leakage rejection, all-candidate
  denominators, completed-report/code drift and raw-artifact hash binding.
- **92 OMR + 105 SH1991 fixtures pass.** Restricted source files are not CI
  dependencies. Existing Node/build/browser checks remain the landing gate.
- Identical completed-analysis replay verified; old inputs/raw recognition
  artifact hashes remain unchanged. No new recognition or external upload.

This justifies a **separately frozen complete-window test on another source**
before changing or promoting this detector. Freeze this recipe, bank, native
priority, tolerances and output policy before viewing that page, retain every
source/candidate denominator, and include literal-center failures. Broader
scan-style, open-fill and diamond coverage remains outstanding. Any subsequent
center-refinement/classifier intervention belongs to exposed development and a
new protocol; do not tune it on a consumed fresh-page result.

No score repair, corpus admission, engine integration, deployment or whole-score
acceptance. Pitch/rhythm/exported-event accuracy and correction time remain
unavailable. **Whole scores accepted: 0. Safe to promote: false.**
