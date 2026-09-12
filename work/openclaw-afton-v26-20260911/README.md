# Afton v26 — source-semantic continuation, 2026-09-11

## Result

The printed P3 measure-12 **`dis-` belongs to note 5**, the D5 beginning the
final beamed eighth-note pair. V25 placed it at note 3. V26 moves only that lyric
anchor, preserving its `begin` label and the following m13 n1 `play,` (`end`).
The title now correctly identifies a full-song v26 review candidate instead of
its inherited first-system/v16 label.

All **251 pitched notes, 251 explicit noteheads, 12 rests, 150 lyric anchors,
and 68 complete written measures** remain. No pitches, durations, shapes, fills,
source signature, navigation, other lyric placements, extenders, or verse
numbers were changed. `safeToPromote=false`; no verified-edition promotion.

## Exact source and boundary

Inspection used the already-published
[`mnharmony-afton-v25-source.pdf`](../../public/review-publications/mnharmony-afton-v25-source.pdf),
SHA-256 `6ba40c10dbdfa9b93e16f67ae34619254c88004367d802f07a6eddd156047192`.
Fresh Poppler 600-DPI detail and a 400-DPI multi-voice context crop establish
this printed onset independently of the old sidecar. Coordinate receipts and
PDF text bounds are in [the review evidence](afton-v26-review.json).

The PDF has **two pages**, not one: page 1 contains all notation and ends at the
final barline; page 2 contains an empty four-stave print artifact, not missing
later music. There is no printed bass lyric line in either system. Neither
absence is a reason to invent more notation or copy treble words into the bass.

P1 m8 prints the unhyphenated `ripened harvest` run. Its exact syllabic division
is not established, so this candidate adds no P1 m8 lyrics. The new evidence
also explicitly inventories the missing printed m4 underlay in all three treble
voices, P2 second-system alignment, inherited syllabic-label issues, unmarked
multi-note spans, and the unknown mode. Full notation extent does not mean full
lyric fidelity.

## Files and verification

- [Candidate MusicXML](afton-full-song-candidate-v26.musicxml)
- [Source observations, exact delta, and remaining gaps](afton-v26-review.json)
- [Reproducible builder and exported-byte verifier](build_and_verify.py)
- [Focused verification receipt](verification.json)

Run from the repository root:

```sh
python3 work/openclaw-afton-v26-20260911/build_and_verify.py
```

The verifier checks the existing source and both v25 candidate hashes, parses
actual exported XML, reverses exactly the lyric move/title update and compares
the complete v25 structure, checks all 68 written measure durations, and passes
the Atlas semantic parser, score parser, and draft playback-duration validator.
It is **focused package proof**, not aggregate application/browser verification
or a fresh independent audit of all 251 source notes.

New source renders and PDF text extracts are ignored under `local-only/`.
**Do not stage or publish them.** The package references existing source bytes;
it introduces no additional public scans. All predecessors remain unchanged.

## Publication handoff

Ready for the coordinator's independent source review and existing
manifest-backed review-publication flow. Keep prior v25 artifacts available.
Candidate SHA-256:
`168d501730ef27027bc8e304f34a9c8d450794399aefac3212fe0141d8cc7d2b`.
No Git or public/canonical data mutations were made by this lane.
