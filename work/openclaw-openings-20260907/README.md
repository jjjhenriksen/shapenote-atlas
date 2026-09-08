# Two zero-mapping-book openings — 2026-09-07

Completed the handoff's bounded **first complete opening measure across every printed voice** for New Salem (Kentucky Harmony) and Something New (Shenandoah Harmony). These are editable, intentionally very short practice candidates, not complete tunes or certified exact-edition transcriptions.

## Deliverables

| Record | Candidate | Literal first bar, voices top to bottom |
| --- | --- | --- |
| `kentucky 10 — New-Salem` | [MusicXML v1](kentucky-new-salem-opening-candidate-v1.musicxml) · [evidence](kentucky-new-salem-evidence-v1.json) | Common time: half rest, then half note C5 / F3 / F4 / F3 |
| `shenandoah 10 — Something New` | [MusicXML v1](shenandoah-something-new-opening-candidate-v1.musicxml) · [evidence](shenandoah-something-new-evidence-v1.json) | 6/8: dotted-quarter rest, then dotted-quarter note B♭4 / F4 / F4 / B♭3 |

Each file contains four parts, one complete bar per part, four pitched notes and four rests. Part names are neutral printed-voice numbers: this avoids inventing voice labels. Printed clefs are preserved (New Salem G/F/G/F; Something New G/G/G/F); no unprinted octave shift is applied.

## Source review and limits

Direct visual review used the retained `kentucky-010-new-salem.pdf`, rendered with Poppler to `renders/kentucky.png`, and retained `shenandoah-010-something-new.jpg`. Both pages print page 10. Evidence pins the original bytes and the candidates with SHA-256 and records each note's staff coordinates. Kentucky coordinates are in the 1780×1376 displayed image and explicitly convert to the 2200×1700 retained render; Shenandoah coordinates use the original 1654×1157 image.

The retained pages explicitly print “F Major.” and “B♭ Major.” respectively. Those observations are preserved in evidence; MusicXML encodes the visible one-/two-flat signatures but omits mode, lyrics and notehead shapes for this bounded draft. This is deliberate incomplete transcription, not a claim that the page lacks that material. The rest of each tune is omitted, not encoded as silence. No final barline or repeat is invented at the excerpt boundary.

Book association comes from the retained-source lane and record mapping; this work does **not** newly authenticate the historical edition of these clean engraved witnesses. `reviewRequired=true`, `safeToPromote=false` refer to exact-source certification. Human-correctable partial publication may proceed under the user's early-publication instruction, provided those limits remain visible.

## Verification

Run from any working directory:

```sh
python3 /Users/jacquelinehenriksen/Documents/Codex/2026-08-27/sacred-harp-dashboard/work/openclaw-openings-20260907/verify_candidates.py
```

Both candidates pass source/candidate hashes, actual exported part and note counts, clef retention, duration/type/dot consistency, complete measure timing, onset parity, signature alterations, and staff-coordinate-to-pitch parity. No lyrics, shapes, mode, ties or repeat topology were accidentally serialized. Coordinate checks audit transcription consistency; they do not replace the direct visual review or constitute OMR proof.

Builder and verifier require only Python's standard library. The verifier currently requires retained source files at their evidence paths. Rendering is not required to rerun it. No app integration, browser validation, Git staging or commit was performed by this lane; the coordinator owns those steps. Earlier lane files were not changed.
