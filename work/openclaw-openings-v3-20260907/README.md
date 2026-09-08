# New Salem and Something New — full-notation review drafts v3

Direct source review and export: 2026-09-07. Both candidates now cover the **entire
written notation extent on their retained pages**, across all four printed
voices. Lyrics and printed shape glyphs are still unencoded; these remain usable,
human-correctable review drafts, not certified exact-edition scores.

| Candidate | Bars per voice | Pitched notes | Added vs v2 | Linear quarter-note units per voice |
| --- | ---: | ---: | ---: | ---: |
| [New Salem v3](kentucky-new-salem-full-notation-candidate-v3.musicxml) | 16 | 167 (42/42/42/41) | 87 | 64 |
| [Something New v3](shenandoah-something-new-full-notation-candidate-v3.musicxml) | 15 | 235 (59/58/60/58) | 124 | 45 |

## Direct source evidence

- New Salem: printed page 10, retained `kentucky-010-new-salem.pdf`, SHA-256
  `f4ba7e2ead70aa38bfc626f017b4a4e060487f95eaeda05f1b67f98f78db8251`.
  Directly viewed the retained 2200×1700 render at 1780×1376 display scale.
  The second system adds bars 9–16, including half rests at bar 9, eight
  distinct-pitch slurs, and a terminal backward-repeat barline.
- Something New: printed page 10, directly viewed the retained 1654×1157 JPG,
  SHA-256 `36ccec1996b58e05135b7f9cdaeff7a9a57bfe3994ecc13171903f7a1895655c`.
  The second system adds bars 8–15, three slurs and five ties. P2 bar 9's slur
  returns to F4 through G4; equal endpoints do not make that three-note curve a tie.
- Each evidence JSON pins source, review image, candidate, predecessor XML and
  predecessor evidence hashes. Added events retain directly observed note centers,
  bar boundaries, staff calibration, spellings, written durations and onsets.
  These are manual observations, not coordinates reconstructed from the pitches.
  First-system coordinate evidence remains in the hash-pinned v2 predecessor.
- Printed `F Major.` / `B♭ Major.` labels remain evidence; mode is still unset.
  No octave transposition, lyrics, notehead shape or unseen notation is invented.

## Distinct terminal navigation boundaries

**New Salem:** terminal repeat dots plus a thin/thick barline are visible in all
four voices near displayed x1695–1727. A backward repeat is encoded in every
part's final measure. Neither system opening prints a forward-repeat sign. No
forward repeat sign or explicit repeat count was invented. The parser receipt
proves the 64-quarter-unit **linear written-order event stream**, not app repeat
navigation. Playback can remain linear until the navigation behavior is separately
validated; editable MusicXML retains the observed backward repeat.

**Something New:** the terminal boundary is a plain thin/thick barline, without
repeat dots. The dots near x1611 are duration dots on the final half notes near
x1589. The final measures therefore contain one dotted half each; no repeat is
encoded. Both tunes have their full written pitch/rhythm extent, even though
lyrics, shape glyphs and exact-edition certification remain unfinished.

## Verification

```sh
python3 work/openclaw-openings-v3-20260907/build_candidates.py
python3 work/openclaw-openings-v3-20260907/verify_candidates.py
```

[Parser receipt](parser-receipt.json) records both passing:

- Every complete v2 measure and the part list match canonical XML exactly.
- Appended XML pitches agree with independently calculated staff positions and
  inherited key-signature alterations; literal clefs remain unchanged.
- All bars are metrically complete; type/dot durations and onsets agree. Rest
  presence, note order and coordinates inside each printed bar are checked.
- All existing and appended tie/slur endpoints and the two different terminal
  barline topologies match their observations. No lyric/mode/shape additions.
- Negative controls reject predecessor drift, appended pitch or duration changes,
  omitted terminal boundaries and missing appended source curves, without relying
  only on candidate hashes.
- Atlas `parse_score` and draft-duration validation pass; the actual parsed event
  stream equals XML pitches, rests, durations, onsets and ties. New Salem has
  175 events including eight rests; Something New has 239 including four rests.
- Re-running the builder is byte-identical; it refuses differing existing outputs.

All changes are confined to this new directory. V1/v2 sources and evidence,
public assets, publishers and program docs are untouched. The coordinator owns
publication, UI/playback QA and Git. No commit, push or deployment is claimed here.
