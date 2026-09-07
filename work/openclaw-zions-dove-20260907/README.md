# Zion's Dove: bounded second-system continuation

Reviewed 2026-09-07. **Isolated review candidate; safeToPromote=false.** No canonical files or historical lane files were changed.

## Direct source review

Retained source: `work/luna-program-20260904/existing_books/assets/christian-harmony/batch-01/scans/10-zions-dove.jpg` (1654 × 1119; SHA-256 in verification.json). The complete source image was opened and visually reviewed; this work covers only the second-system bar x≈438–502.

| Voice | Directly observed pitches | Durations | Printed lyric anchor |
| --- | --- | --- | --- |
| Treble | E-flat5 → B-flat4 | half, half | `dove,` at first note |
| Alto | A-flat4 → G4 | half, half | none printed at this staff |
| Tenor | C5 → E-flat5 | half, half | `be;` at first note |
| Bass | E-flat3 | whole | none printed at this staff |

Upper voices have visible two-note curves joining distinct pitches, serialized as slurs, never ties. The three upper-note pairs are hollow with stems; the bass hollow note is stemless. Pitches were read from staff position and the printed four-flat signature, not inferred from notehead shape. Alto G4 lies around y827 (second-system bottom staff line y839); v19/v20's y833 coordinate would describe a different staff position and is not reused.

The word `dove,` occupies this bar around x442–489; `The` begins after its right barline, around x509. Likewise `be;` lies around x455–483 and `And` begins around x495–531, anchored to the following bar's note. No second-note words are printed within this bar. Slurs and lyric extension semantics are kept separate: no extension markers are guessed.

## Version correction

The top-level handoff named v17 as latest exported; the current local lane handoff additionally lists v20, which exists. Its appendix inherited the provisional v19 error (`land`/`And` in Tenor, and `The` on Treble's second note). V21 is intentionally based on the reviewed **exact v17 prefix**, superseding only that rejected v20 appendix. V20 and all previous issued versions remain unchanged.

## Artifacts and proof

- `ch7-10-first-system-candidate-v21.musicxml`: first system plus three second-system bars.
- Matching JSON: event stream and explicit source/gap notes.
- `build_verify.py`: bounded exporter and exported XML/JSON preservation checks.
- `verification.json`: actual output hashes and check results.

Run from the repository: `python3 work/openclaw-zions-dove-20260907/build_verify.py`.

Verification passed: seven notes added (2/2/2/1), two new lyric anchors, all four v17 XML part prefixes and JSON event prefixes preserved exactly. All voices end at cumulative onset 56; 159 pitched notes total. All 33 historical candidate/evidence JSON and MusicXML files checked remained byte-identical. No noteheads, ties, or lyric extension markers were added. This checks preservation and serialization, not full printed-edition fidelity or application/browser behavior.

## Exact remaining gaps

1. Continue the second system after x502; later notes, lyrics, navigation, first/second endings and final boundary are not yet transcribed.
2. Audit new printed notehead shapes/fill directly before adding shape tags. Staff-position pitches do not supply glyph proof.
3. Alto and bass have no separately printed lyric lines in this source layout; do not manufacture voice-specific underlay from Treble/Tenor.
4. Full candidate source review and promotion gates remain outstanding. Mode remains unknown.

Parent coordinator owns atomic staging/commit/push. This lane performed no Git mutation.
