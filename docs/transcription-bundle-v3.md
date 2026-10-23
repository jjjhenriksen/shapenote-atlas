# Opt-in lyric-observation research bundle v3

Related: [Atlas #523](https://github.com/jjjhenriksen/shapenote-atlas/issues/523)
and [Transcriber #74](https://github.com/jjjhenriksen/shapenote-transcriber/issues/74).
V3 distinguishes an internal lyric stream identifier from an observed printed
label. It preserves observations as metadata without claiming literal printed
label engraving, source accuracy, acceptance, or publication authority.

## Explicit version and profile

```sh
python3 scripts/import_transcription_bundle.py /private/synthetic-v3-bundle \
  --expected-manifest-sha256 PIN_FROM_EXPORT_OWNER --bundle-version 3 --verify-only
python3 scripts/import_transcription_bundle.py /private/synthetic-v3-bundle \
  --expected-manifest-sha256 PIN_FROM_EXPORT_OWNER --bundle-version 3
python3 -m unittest discover -s tests -p 'test_transcription_bundle*import.py' -v
```

The Python APIs add explicit `bundle_version=3` to `verify(directory, pin, ...)`
and `stage(directory, pin, root=ROOT, ...)`. The default remains v1. V1/v2 wire
contracts and their default rejection behavior remain unchanged; no old lyric
`number` is interpreted or upgraded into a printed-label observation.

Reading `schemaVersion=3` requires exactly one explicit profile:

| Profile | Ordered parts and clefs |
| --- | --- |
| `four-shape-three-monophonic` | P1, P2, P3; three ordered clefs |
| `four-shape-four-monophonic` | P1, P2, P3, P4; four ordered clefs |

Parts have equal, nonempty contiguous measure coverage. Existing four literal
shapes, monophonic rhythms, pitch/clef/key/meter, ties, beams, barlines, endings,
uncertainty and unavailable-semantics constraints remain in force. No fourth
part, verse, label, note or rest is guessed or padded.

The manifest uses `schemaVersion=3`, `readingContractVersion=3`, and the selected
profile. Report and comparison require matching contract version/profile. All
three require `literalPrintedLabelEngravingVerified=false`, as well as the
existing false source-certification/promotion flags. The report still requires
both second-parser flags true, unresolved measures empty, independent source
accuracy null, and repeat traversal explicitly unverified. Existing comparison
coverage/count bounds and exact-count binding without adjudication apply.

## Lyric observations

Every v3 lyric contains exactly `lineId`, `text`, `syllabic`, `printedLabel`.
`lineId` is a nonempty, part-scoped opaque internal underlay-stream identifier,
using the full Unicode [XML 1.0 Fifth Edition NMTOKEN grammar](https://www.w3.org/TR/REC-xml/#NT-Nmtoken).
Digits, colon and valid combining characters may occur at any position. IDs are
never normalized, renumbered or inferred from a printed label. Each event may
contain at most one lyric per line ID; the same ID may recur at later events or
in another part. Sparse streams remain sparse, and different streams may retain
the same printed label.

`text` is the literal nonempty sung text; whitespace remains literal. `syllabic`
retains `single`, `begin`, `middle`, or `end`. `printedLabel` is exactly one of:

```json
{"state":"present","text":" 01. "}
{"state":"absent"}
{"state":"unknown"}
```

Present text must be a nonblank string, and its Unicode characters and whitespace
are preserved exactly. Absent means no label at that attachment; a previous
word's label is never propagated. Unknown is a valid observation in a formal
reading but always quarantines an assembled bundle candidate, even when both
readings agree on unknown and their uncertainty lists are empty. Absent and
unknown cannot contain a `text` field. V3 never substitutes a legacy `number`.

## MusicXML observation table

MusicXML lyric `number` contains `lineId` only. Sung text and syllabic content
remain unchanged, including literal CR represented by a character reference.
A lyric `name` attribute or an added printed-label prefix in sung text is
rejected. Printed observations belong in exactly one
`identification/miscellaneous/miscellaneous-field`, named
`shapenote-lyric-observations-v3`; identification children are ordered rights,
then miscellaneous. No other miscellaneous fields, attributes or children are
supported. The field text is strict JSON:

```json
{
  "schemaVersion": 3,
  "kind": "shapenote-lyric-observations",
  "records": [
    {
      "partId": "P1",
      "measureIndex": 0,
      "eventIndex": 0,
      "lineId": "L7",
      "printedLabel": {"state": "present", "text": " 01. "}
    }
  ]
}
```

The typed composite key is `(partId, measureIndex, eventIndex, lineId)`, with
zero-based integer indexes. Record and JSON object-key order are immaterial.
The table must contain exactly every lyric attachment, with its exact state and
text; missing, duplicate, orphan, altered, unsupported or unknown records reject.
The table remains mandatory with `records=[]` when no lyrics exist. Duplicate
JSON keys, nonfinite numbers, extra fields and malformed tagged unions reject.

## Independent consumer and private staging

`scripts/transcription_bundle_v3.py` validates the v3 vocabulary and table,
compares every attachment against the reading and XML lyric stream IDs, and
reuses Atlas's own bounded notation validator internally. That common parser
retains DTD rejection across encodings (including the MXL container), required
child ordering, XML numeric lexical guards, and unknown-field rejection. The
v3 projection operates on the already checked tree so character-reference CR
is preserved. It imports no producer code, checkout, recognition dependency,
source image or source-reading artifact.

The fixed six-file bundle envelope, external manifest pin, every payload hash,
producer/assembly provenance, exact MXL/standalone XML identity, and private
atomic exact-byte staging remain required. Output is confined to ignored
`work/transcription-imports/<external-manifest-pin>/`, with a v3 receipt retaining
false authority and literal-engraving flags. Existing imports are never replaced.
No catalogue, public assets, UI, playback, admission or source acceptance changes
are included. Synthetic exchange checks establish representation agreement only.
