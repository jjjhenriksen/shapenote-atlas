# New Salem and Something New — first-system review drafts v2

Direct source review and export: 2026-09-07. This package extends the published
v1 opening bars without changing them or any source/publication files.

| Candidate | Complete bars per voice | Pitched notes | Added pitches | Printed curves |
| --- | ---: | ---: | ---: | --- |
| [New Salem v2](kentucky-new-salem-first-system-candidate-v2.musicxml) | 8 | 80 (20 each) | 76 | Four distinct-pitch slurs in bar 2 |
| [Something New v2](shenandoah-something-new-first-system-candidate-v2.musicxml) | 7 | 111 (28/27/28/28) | 107 | Four same-pitch ties in bar 5 |

Each draft now covers the **whole first printed system across four voices**.
New Salem lasts 32 quarter-note units per voice; Something New lasts 21.
Each includes its original four opening rests, for 84 and 115 total events.

## Sources and observations

- New Salem: retained `kentucky-010-new-salem.pdf`, printed page 10,
  SHA-256 `f4ba7e2ead70aa38bfc626f017b4a4e060487f95eaeda05f1b67f98f78db8251`.
  Directly viewed the retained 2200×1700 page render at 1780×1376 display scale.
  The first system ends at displayed x≈1727; its last bar is a whole note in each voice.
- Something New: retained `shenandoah-010-something-new.jpg`, printed page 10,
  SHA-256 `36ccec1996b58e05135b7f9cdaeff7a9a57bfe3994ecc13171903f7a1895655c`.
  Directly viewed the original 1654×1157 image. The first system ends at x≈1641.
- The two `*-evidence-v2.json` files pin candidates, predecessors, predecessor
  evidence, source bytes, and review image bytes. Every added note has its
  observed center, staff calibration, bar boundaries, written duration, and
  cumulative within-bar onset. Coordinates are recorded manual observations,
  not automatic optical recognition or coordinates reconstructed from pitches.
- Printed key labels remain `F Major.` and `B♭ Major.` in evidence only.

## Verification

Run from the repository root:

```sh
python3 work/openclaw-openings-v2-20260907/verify_candidates.py
```

[Current receipt](parser-receipt.json) records both candidates passing:

- Canonical XML equality of every entire v1 first measure, preserving attributes,
  clefs, key signatures, meter, rests, pitches, and durations. Only document-level
  title/coverage metadata changes outside the appended measures.
- All added XML pitches checked against independent staff-coordinate calculations
  and the inherited key signature, with observed spellings checked separately.
- Every measure metrically complete; note type/dot durations and cumulative onsets
  agree; coordinates are inside their bars and in left-to-right order.
- Source curve endpoints are complete and correctly distinguished as ties versus
  slurs. No lyric, notehead, mode, final barline, or repeat is invented.
- Negative controls reject v1 changes, displaced pitch, inconsistent duration,
  and a missing source curve even without relying on candidate hashes.
- Atlas `parse_score` and draft-duration validation accept both. Comparing actual
  parser events against the XML proves all rests, pitches, onsets, durations, and
  tie endpoints are retained; no event-stream repair was required.

`build_candidates.py` is reproducible and refuses to overwrite candidate/evidence
versions with differing bytes. V1 files remain unchanged.

## Publication and remaining work

These are usable **partial, human-review-required practice drafts**. They retain
`safeToPromote=false` for exact-edition certification; this does not prohibit the
authorized review-publication path. The coordinator owns manifest/publication
updates, app/browser QA, and Git operations. This package makes no commit, push,
browser-rendering, or public-deployment claim.

Later systems remain omitted, not silence. Lyrics and printed notehead shapes
remain unencoded. No octave adjustment or mode interpretation is inferred from
vocal convention or the printed key label. Exact-edition provenance is unchanged.
The next notation batch can extend the second systems as new versions; the
current first-system drafts need not wait for that work to become available.
