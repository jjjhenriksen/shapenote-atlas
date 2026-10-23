# Opt-in three-part research bundle v2

Related: [Atlas #519](https://github.com/jjjhenriksen/shapenote-atlas/issues/519)
and [Transcriber #68](https://github.com/jjjhenriksen/shapenote-transcriber/issues/68).
The default importer remains bundle v1 and rejects v2. Select v2 explicitly:

```sh
python3 scripts/import_transcription_bundle.py /private/synthetic-bundle \
  --expected-manifest-sha256 PIN_FROM_EXPORT_OWNER --bundle-version 2 --verify-only
python3 scripts/import_transcription_bundle.py /private/synthetic-bundle \
  --expected-manifest-sha256 PIN_FROM_EXPORT_OWNER --bundle-version 2
python3 -m unittest discover -s tests -p test_transcription_bundle_import.py -v
```

The Python API adds `bundle_version=1` to `verify(directory, pin, ...)` and
`stage(directory, pin, root=ROOT, ...)`. Set `bundle_version=2` explicitly.
V2 does not accept v1 under that selection, guess part counts, or pad a fourth
part. Only `schemaVersion=2`, `readingContractVersion=2`, and
`profile="four-shape-three-monophonic"` are supported by its manifest.
The report and comparison require matching contract version/profile metadata;
the resolved reading requires schema version 2 and that profile. The report also
requires `secondParserProfileSemanticsPassed=true`, alongside the existing
pitch/rhythm flag. All applicable source certification/promotion flags remain
literal false, and independent source accuracy remains null.

The six-file envelope, external manifest pin, every payload SHA-256, producer and
assembly provenance, and exact archived/standalone XML identity remain required.
V2 rejects duplicate JSON keys, nonfinite JSON numbers, unknown fields in the
manifest/producer/report/comparison or supported reading structures, unsupported
versions, mismatched counts, unresolved uncertainty, and false authority claims.
Comparison issues may retain disagreements resolved by adjudication; their count
must match the report's adjudicated units. Audit findings remain evidence data.

## Supported music

The reading contains exactly ordered `P1`, `P2`, `P3` parts, three ordered clefs,
and equal, nonempty measure coverage indexed contiguously from zero. Names and
title retain their literal strings. An absent title uses the documented writer
default; a null title serializes as an empty title. Measure bounding boxes remain
finite, nonempty, nonnegative pixel-coordinate rectangles; this consumer does
not open or verify an image.

Each part remains monophonic with contiguous event onsets. Supported types are
whole, half, quarter, eighth and sixteenth notes, with zero through two dots and
matching positive rational quarter-note durations. Integral pitch alterations,
integer octaves, four literal shapes (`triangle`, `round`, `square`, `diamond`),
open/filled heads, rests, explicit ties, lyric numbers/text/syllabic values,
numbered beams, barline styles, repeat directions/counts, bracket endings, and
literal `endingLabel` are supported. Declared unavailable semantics remain in
the pinned reading and reports. Optional uncertainty lists must be empty.
Unknown features, seven shapes, extra voices/staves, chords, tuplets, grace notes,
noncontiguous onsets, fractional pitch alterations, and literal barline-stroke
decorations are rejected rather than discarded.

`scripts/transcription_bundle_v2.py` is an independent stdlib-only implementation
of this wire contract. It imports no producer code. Its `verify_profile(reading,
xml_raw)` validates the reading and compares independently parsed MusicXML to
its supported semantics. The parser admits only the declared MusicXML subset,
including ordered IDs/names/clefs, key/time, measure/event coverage, pitch/rhythm,
literal shape/fill, lyrics, beams, ties, repeats, bracket endings, and ending
labels. It rejects unknown XML elements/attributes and document type/entities.
This verifies agreement between the two representations, not musical accuracy
against source pixels.

## Staging and authority

Verified bytes are atomically staged only under ignored
`work/transcription-imports/<external-manifest-pin>/bundle/`, with a v2 import
receipt recording the contract version/profile and false authority flags.
Staging copies the exact bytes verified in memory, preserves the pin and
provenance, and never replaces an existing import. There is no destination
option into catalogue/public assets, acceptance or publication, UI integration,
playback admission, or source certification. Source evidence remains separately
retained. Synthetic round trips prove only the bounded exchange contract.
