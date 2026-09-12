# Afton v27 — partial measure-4 underlay, 2026-09-11

## Result

Eight directly inspected lyric onsets are now serialized in the actual
MusicXML export:

| Part | Measure | Note indices | Added text |
| --- | --- | --- | --- |
| P1 | 4 | 1, 2, 3, 4 | `vides` / `the` / `sun` / `and` |
| P2 | 4 | 3, 4 | `joy` / `and` |
| P3 | 4 | 1, 2 | `we` / `but` |

P1 `vides` is an `end` syllable continuing the existing printed m3 `pro-`;
the other seven additions are printed monosyllables. No word was split to fill
a note, no verse number was assigned, and no extender was inferred from a beam.

All **251 pitched notes, 251 explicit noteheads, 12 rests, and 68 complete
written measures** are preserved. Lyric anchors increase from 150 to **158**.
The only other change is the candidate title's v26 → v27 label.
`safeToPromote=false`; this remains an isolated review candidate.

## Exact source and limits

Direct inspection used page 1 of the already-published
[`mnharmony-afton-v25-source.pdf`](../../public/review-publications/mnharmony-afton-v25-source.pdf),
SHA-256 `6ba40c10dbdfa9b93e16f67ae34619254c88004367d802f07a6eddd156047192`.
Poppler rendered fresh 600-DPI m4 detail and 400-DPI m3–m5 context. The
[review evidence](afton-v27-review.json) records exact crop commands, printed
word bounds, approximate notehead centers, added anchors, and remaining gaps.
The context shows `pro-` before the P1 m4 bar and `rain,` after it.

This is **partial m4 improvement**, not a claim that all three underlay lines
are complete:

- P2 `wonder,` is printed as one unhyphenated word over the first two notes;
  its syllabic division is not supplied by the source, so n1–n2 remain absent.
- P3 `see thy` is compact and offset from the later note centers; the
  `see` onset could not be confidently distinguished between n3 and n4.
  Neither those words nor their multi-note spans are guessed.
- The final beamed pairs have no newly encoded lyric extenders.
- P1 m8 `ripened harvest`, inherited syllabic-label issues, P2 second-system
  alignment, other multi-note spans, and unknown mode remain in the inventory.
- Page 2's empty-stave disposition and the absent printed bass lyric line
  are v26 observations, not new missing-music claims. No bass lyrics are added.

All v26 pitches, shapes, durations, source signature, navigation, and existing
lyrics—including the corrected P3 m12 n5 `dis` anchor—are unchanged. This
focused pass is not a fresh independent audit of every source note.

## Files and verification

- [Candidate MusicXML](afton-full-song-candidate-v27.musicxml)
- [Exact delta, source observations, and remaining inventory](afton-v27-review.json)
- [Reproducible builder/exported-byte verifier](build_and_verify.py)
- [Focused verification receipt](verification.json)

Run from the repository root:

```sh
python3 work/openclaw-afton-v27-20260911/build_and_verify.py
```

The verifier checks the source and both work/published v26 candidate hashes;
parses the actual exported XML; removes exactly the eight declared additions
and reverses the title update to establish full v26 structural preservation;
checks all written durations; and exercises Atlas's semantic parser, score
parser, and draft playback-duration validator. It does not imply aggregate
application/browser validation or a verified-edition promotion.

Candidate SHA-256:
`8bb4f0d2e9ba93047b19e2cfce480478a6abb481f882dc3a8bc6604c3550c80e`.

## Publication handoff

Ready for the coordinator's independent review and manifest-backed review
publication. All new source renders/text extracts are ignored under
`local-only/`; **do not stage or publish them**. This package references
existing source bytes and supplies no additional public scans. All previous
candidate/evidence files are preserved. No Git, public, canonical, script,
application, or shared documentation files were changed by this lane.
