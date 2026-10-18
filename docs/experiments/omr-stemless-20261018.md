# Stemless whole-note recognition v1: useful stage evidence, rejected candidate

2026-10-18. Follow-up to [the terminal diagnosis](omr-terminal-diagnosis-20261018.md)
and PR #490. **Consumed development, not held-out evaluation or a working score
repair. The broad candidate fails its preservation gate and stays disabled.**

## What changed

A separate Audiveris engine adds explicit stemless whole-note families for
narrow ovals, white squares, and both Fa orientations. Existing Bravura glyphs
supply the templates; logical duration is a whole note, not a half note with a
missing stem. Square/Fa noteheads retain their MusicXML motif. Ordinary native
acceptance/grade thresholds are unchanged. New families are gated by both
`atlas.stemlessHeads` (default false) and `faHeads`.

An automatic whole-page range scan supplies candidates, with no note centers,
terminal coordinates, expected counts or source-event labels entering the
recognizer. Physical-bar intersections and nearby extending stem seeds veto
new candidates. Stage tracing logs all retained heads and current chord/voice
links at HEADS, REDUCTION, CHORDS, RHYTHMS and PAGE.

[Engine patch and reproduction instructions](../../experiments/audiveris-stemless-v1/README.md).
Raw source scans, coordinates, XML, graphs, logs and labels remain ignored/local;
[public JSON](omr-stemless-20261018.json) contains aggregate metrics and hashes.

## Controls and provenance

Exactly **six invocations** completed: property off/on on Thy Strength, Penn
and Clayton. All three same-binary off controls exactly reproduce the retained
paired-v3 on-arm `sh1991_pilot.score` inventories before candidate execution.
This means written-event spelling/order, duration/onset, staff/voice, measure
durations and lyric/notehead counts; not identical XML or every notation field.
The completed earlier studies, binaries, receipts and frozen cohorts were not
modified or retried.

Recipe, engine distribution/Java sources, Java toolchain, native tests, Python
import closure, prior artifacts and source observations were hash-bound before
inference. One invocation per arm/source; started-without-receipt blocks retry.
No threshold sweep or outcome-driven recognition revision was performed.

## New causal evidence: lost by REDUCTION, not absent at HEADS

The earlier diagnosis could only see the final graph and template-fit logs.
Automatic stage snapshots now refine that picture:

| Off-arm terminal region | HEADS exit | REDUCTION exit | CHORDS exit | PAGE exit |
| --- | ---: | ---: | ---: | ---: |
| Thy Strength retained head objects | 20 | 0 | 0 | 0 |
| Penn retained head objects | 11 | 0 | 0 | 0 |
| Clayton retained head objects | 22 | 1 | 1 | 0 |

These are **provisional graph objects**, not source-correct note counts. For
Thy Strength/Penn, existing terminal candidates are lost between HEADS exit and
REDUCTION exit (the interval also includes STEMS). This does not identify every
individual removal operation or prove a single exact rejection reason.

The new whole-note families can survive into chords, voices and exported music.
That establishes a real integration path; it does **not** establish precision.

## Why the candidate is rejected

| Page | Exported measures per part, off → on | Existing staff-measure spans unchanged | New-family heads in final graph |
| --- | --- | ---: | ---: |
| Thy Strength | 16 → 17 | 25/64 | 59 |
| Penn | 11 → 13 | 27/44 | 23 |
| Clayton | 16 → 17 | 19/64 | 79 |

**101/172 existing spans change.** Span identity uses physical graph bounds,
not shifted measure numbers or an event-sequence zip. Every formerly exported
span must preserve its full written-event list; missing/resegmented spans fail.
An added final measure is not success.

Penn's full provisional source-event inventory supplies the strongest semantic
check (same-agent observations, not independent gold):

| Penn complete-event units | Off | On |
| --- | ---: | ---: |
| Source events | 120 | 120 |
| Matched events | 46 | 31 |
| Missing units | 74 | 89 |
| Extra units, including orphan measures | 102 | 141 |
| Missing + extra | **176** | **230** |
| Closing events matched | 0/4 | 1/4 |

The recovered closing event is the observed E4 whole note in part 2; the other
three closing events remain missing. The candidate also retains **two new
heads before Penn's directly observed musical onset**, exposing a header-region
false-positive path. It is not a terminal-only or non-regressing repair.

Thy Strength's source grid covers structure/header only; whole-song pitch and
lyric correctness there is unavailable. Clayton has no full source-event grid.
There are no all-rest measures in the Penn labels and no explicit courtesy-only
negative cohort. These are coverage gaps, not passing negative tests. Stem/bar
geometry guards and native unit tests do not establish rest/courtesy precision.

## Verification and retained analyzer failure

- Engine build passes. **4 new native tests + 11 retained bar-consensus tests
  pass**, no skips. They check whole durations/stemless membership, valid closed
  glyph templates and extending-stem geometry. The first template test exposed
  missing test-time symbol initialization; fixed before experiment freeze.
- **164 OMR + 105 SH1991 = 269 Python tests pass**, no skips in the retained
  Pillow/NumPy environment. New fixtures cover observed-zero versus unavailable
  stages, chord/voice counts, span preservation, no implicit retries, completed
  receipt reuse, control rejection and legitimate cautionary IDs.
- All recognition receipts completed before the original analyzer stopped on
  duplicate native IDs: non-exported final `CAUTIONARY` stacks intentionally
  reuse preceding measure IDs. The frozen runner was retained unchanged.
- A separate **read-only** analyzer excludes only non-exported cautionary stacks
  from label lookup and writes outside the recognition tree. Ambiguous exported
  IDs/missing physical spans still fail. No event normalization or rerun.
- Analysis/public-summary replay verifies input and receipt hashes and produces
  identical bytes without launching recognition.

```sh
python3 scripts/omr_stemless_analysis.py \
  --study /retained/stemless-v1/run --out /retained/stemless-v1-analysis
python3 scripts/omr_stemless_public.py \
  --study /retained/stemless-v1/run --analysis /retained/stemless-v1-analysis \
  --out /public/aggregate.json
```

Local evidence root: `work/model-pilot/stemless-v1/`; repaired analysis:
`work/model-pilot/stemless-v1-analysis/`. The original runner's automatic
analysis failure is retained; use the separate analyzer for these receipts.

## Next implementation boundary

Do not broaden the whole-note template scan or weaken reduction globally.
A new version should trace candidate creation/removal and isolate whole-note
proposals from existing stemmed music: e.g. defer new candidates until ordinary
reduction is complete, then require native musical-region eligibility and
explicit hollow-glyph support before chord construction. The hypothesis is
unmeasured, not a claimed solution. Freeze a new policy/recipe before inference;
retain v1's false positives and failed denominators.

No fresh sources opened, reserved cohort used, source upload, model training,
canonical score correction, reader enablement, merge, deployment or promotion.
**Whole scores accepted: 0. Safe to promote: false.**
