# Agent-owned correction cycle, first bounded implementation

2026-10-16. This is a new engineering task after the completed overnight study,
not a retuning of its frozen recognizer. Jacqueline explicitly rejected doing
human correction; remaining source work belongs to the agent. The old pilot's
supervised-human-editing recommendation is superseded, not silently rewritten.

## Implemented and exercised

`scripts/sh1991_agent_correction.py` consumes the saved pilot's source-image
observations, binds source/crop/draft hashes, repairs **separate copies** of all
eight saved V7 exports, and verifies the written archives with the existing
`agent_03_semantic_musicxml` parser. It does **not** read candidate-reference XML
or rerun recognition. It is a bounded repair pass plus verifier/requeue, not an
autonomous full-score source-reading service.

| Observed opening scope | Before | After |
| --- | ---: | ---: |
| Input-observation-matching segments | 3/16 | 16/16 |
| Mismatching segments | 13/16 | 0/16 |
| Separate repaired score copies | 0 | 8 |
| Excerpts imported/rendered with matching durations | — | 8/8 |
| Whole scores accepted | 0 | **0** |
| Human tasks created | 0 | **0** |

This is **repair-input consistency**, not a newly measured 100% source-accuracy
claim. Scope is top staff, first two opening segments, on the already exposed
validation/pilot cohort only. The prior observations are agent-authored and
reference-exposed. No new held-out evaluation or generalization claim is made.

Repairs correct literal rests, pitch, duration and resulting onsets; spurious
chords/extra voices in these observed monophonic segments are replaced by the
observed sequence. Unchanged segments are left alone. Outside the targeted
segments, XML structure and musical events must remain unchanged. All non-score
ZIP members remain byte-identical. In-segment non-event context is retained;
direction offsets are adjusted only to preserve the original absolute anchor.

Every changed segment retains its original XML in the local audit. Its new
notes encode only observed pitch/rest/duration: candidate note decorations
(shapes, stems, lyrics, ties/slurs, etc.) are **not guessed onto new notes**.
That is an explicit incomplete derivative, not a claim that these source fields
are absent. Original exports are immutable. The copies embed quarantine and
scope labels, and no reader/public/corpus asset changes.

## Verification and remaining findings

- Twelve clone-safe new tests cover genuine archive repair, spurious voices,
  rests, accidentals, dotted/rational durations, pickup number 0, independent
  parser disagreement, out-of-scope corruption, preservation of unchanged note
  decorations, direction timing, immutable replay, source drift, ownership and
  admission-policy tampering. All **73 SH1991 Python fixtures pass**.
- `scripts/sh1991_agent_render.mjs` loads scope-only excerpts through Atlas's
  existing OpenSheetMusicDisplay 2.2.1 in isolated headless Chrome. All page
  network requests are blocked. **8/8** import and render without page errors;
  imported segment durations equal the saved observations. All eight rendered
  excerpts and corresponding source cards were inspected by the same agent.
- The browser check is an independent **notation importer**, not independent
  recognition. The second Python parser similarly checks the repair's declared
  input, not the correctness of that input against source pixels.
- Render inspection exposes still-unverified candidate markings: e.g. `sf` in
  Union, `p` in Soldier of the Cross, and articulation dots in Parting Friends.
  Source note shapes, lyrics, slurs/ties/repeats, complete staff/voice coverage,
  segmentation across repeat-starts and whole-score acceptance remain incomplete.
- MuseScore's first local export produced no output; offscreen export failed
  because this installation has only the Cocoa platform plugin. Neither attempt
  counts as verification. Logs are retained locally; the successful renderer is
  the explicit OSMD fallback, without installing or changing system software.

## Replay (local evidence retained; no network or recognition)

```sh
cd /Users/jacquelinehenriksen/Developer/atlas-prose-20261015
python3 scripts/sh1991_agent_correction.py run
python3 scripts/sh1991_agent_correction.py verify
python3 scripts/sh1991_agent_correction.py excerpts
node scripts/sh1991_agent_render.mjs
python3 -m unittest discover -s tests -p 'test_sh1991_*.py'
```

Output directory:
`work/model-pilot/sh1991-v1/agent-correction-v1-final-20261016/`.
Contains `inputs.json`, `report.json`, eight `*-partial-repair.mxl` files,
`agent-tasks.json`, scoped excerpts, rendered PNGs and `render-receipt.json`.
These artifacts and source scans remain local/ignored. Tracked
`sh1991-agent-correction-v1-20261016.json` records hashes and aggregate proof
without distributing scans or original score XML. An existing result cannot be
overwritten after changing the writer or observations: use a new `--out` directory.

The render check needs existing project npm dependencies and a local compatible
Chromium or installed Chrome. Source files are not included in a fresh clone;
the clone-safe tests require neither those files nor a browser.

## Exact next agent-owned work

1. Add a richer scoped source-evidence schema: arbitrary staff/part/measure spans,
   explicit boundaries, shapes/fill, note decorations and repeat/tie attachments;
   preserve unsupported information and quarantine disagreements rather than
   inferring it. The current adapter deliberately handles only opening top-staff
   pitch/rhythm observations and is not a general full-score transcriber.
2. Start with Union's spurious dynamic and Big Creek's full four-part score.
   Read retained scan pixels directly, saving observations in **new** evidence
   files, never editing the frozen pilot or substituting unreviewed reference XML.
3. Apply that evidence in a new derivative, run scope-preservation, two-parser,
   import/render and source-comparison checks, and route unresolved fields back
   to the **agent**. No handoff to Jacqueline and no automated corpus promotion.
4. Build a genuinely separate source-reading verification lane and test it on a
   newly frozen, unconsumed source cohort before asserting unattended reliability.
   No source upload or paid-model service is authorized by this implementation.

`agent-tasks.json` is a local task manifest, **not a scheduled background worker**.
No jobs, source uploads, recognizer changes, model training, merge or promotion
were performed. This first slice executes real corrections; full-tune autonomous
correction/verification is still an engineering goal, not a delivered capability.
