# A Glimpse of Thee — four-measure opening review draft v1

Direct source inspection and export: **2026-09-11**.

The first **four complete measures in all four printed voices** now have a
source-backed, editable MusicXML candidate: **60 pitched notes, 60 directly read
notehead shapes, and 16 quarter-note units per voice**. There are no rests in
this excerpt. This is a partial, human-correctable review draft, not a complete
tune or exact-edition certification. `safeToPromote=false`.

## Source and identity

- Original [author page](https://www.sacredharptunes.com/author/jesse/a-glimpse-of-thee/)
  and [source PDF](https://media.sacredharptunes.com/jesse_325.pdf).
- Retained one-page PDF SHA-256:
  `86c05b5b9441859f740ded45efad776a093bd2926a2c79bc15e75e2b978b8338`.
- Printed heading: **A GLIMPSE OF THEE. L.M.D.**; text attribution **Isaac Watts,
  1707**; music attribution **Jesse Pearlman Karlsberg, 2009**.
- Stable catalogue ID:
  `sacredharptunes a-glimpse-of-thee — A Glimpse of Thee L.M.`.
  The source's **L.M.D.** differs from the catalogue's **L.M.**; the discrepancy
  is recorded, not silently reconciled or used to alter the catalogue.
- The exact retained source and fresh 400-DPI opening crop were inspected. The
  evidence records crop command/hash, staff calibrations, approximate note
  coordinates, pitches, glyphs, durations, and onsets. The coordinates are manual
  source observations, not an automatic optical audit or a reconstruction from
  the candidate pitches.

## What is and is not encoded

All four parts retain the printed one-sharp signature and literal clefs: three
G-clef lines and one F-clef line. No unprinted octave shift or major/minor mode
is supplied. Printed F-sharps in the second and fourth voices are explicit.

The opening bars contain clear oval, triangle, square, and diamond noteheads,
including their open/filled states. Each fourth bar has two pairs of beamed
eighth notes; those visible beams are encoded. All four bars sum to exactly
four quarter-note units in every voice.

Lyrics are deliberately unencoded. The printed numbered stanzas and compact,
multiline underlay still need voice-specific alignment; their presence is not a
license to assign text to notes. The rest of the tune, including later repeats
and first/second endings, is **omitted, not silence**. No final barline or
complete-song navigation is invented at the excerpt boundary.

## Files and verification

- [Editable MusicXML](sacredharptunes-glimpse-opening-candidate-v1.musicxml)
- [Source observations and limitations](sacredharptunes-glimpse-evidence-v1.json)
- [Builder and exported-byte verifier](build_and_verify.py)
- [Focused verification receipt](verification.json)

```sh
python3 work/openclaw-sacredharptunes-glimpse-20260911/build_and_verify.py
```

The verifier checks the retained source hash and actual exported XML; derives
pitch independently from staff coordinates and key signature; verifies all
written type/dot durations, shapes, onsets, and bar totals; and runs Atlas's
semantic parser, score parser, and draft playback-duration validator. The parsed
event stream is compared note-for-note against exported pitch, timing, and
shape data. Unknown mode stays unknown in the parsed score.

The builder refuses to replace differing issued candidate, evidence, or receipt
bytes. All previous source packages are unchanged. Candidate SHA-256:
`23f6b29246f5e5763a54bfcbd871052af26e363b245b38623017d385282cdab1`.

These checks establish this opening package's integrity; they do not establish
whole-tune fidelity, aggregate application/browser readiness, or deployment.

## Publication handoff

The package is ready for independent integration review. Publish only the
MusicXML, evidence, README, builder, and verification receipt as appropriate.
**Do not stage or publish the retained source PDF or any renders.** The 2009
source remains local-only under the current project boundary. Public source
comparison must link to the original external PDF URL above. The existing
publisher's source-copy behavior must not be used for this record without an
external-source-link path.

This lane changed only its new `work/` directory. No canonical, public,
application, shared script, or program documentation files were edited; no Git,
public attachment, browser validation, or deployment is claimed.

Next source work: extend the same four voices from printed measure 5; retain
the exact four-measure prefix in a new version. Audit stanza/voice underlay and
later repeat/ending structure separately, without inferring either from the
opening.
