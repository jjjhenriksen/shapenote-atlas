# Stemless whole-note families v1 — default-off development prototype

Adds narrow oval, hollow square, and two native Fa-oriented **whole-note**
families. Their templates use existing Bravura half-head / square-white glyphs,
but their logical duration is a whole and their graph semantics are stemless.
Square and Fa motifs are preserved through MusicXML export; do not alias them
to percussion or simply relabel a stemmed half-note after export.

## Reproduce the engine

Start from a **separate copy** of the [measure-consensus-v2 engine recipe](../audiveris-measure-consensus-v2/README.md),
including its V7 prerequisites, at Audiveris commit
`9e1e55cd2746037d059345881c53e6a6754bffbd`.
Apply `stemless.patch` using `git apply --ignore-whitespace` (upstream has CRLF).
Copy `StemlessHeadsTest.java` into
`app/src/test/java/org/audiveris/omr/sheet/note/`.
Never rebuild or modify an engine bound by a previous experiment.

```sh
./gradlew :app:installDist :app:test --offline --no-daemon \
  --tests '*StemlessHeadsTest' --tests '*BarConsensusTest'
```

`atlas.stemlessHeads` defaults to false. With it true **and** `faHeads=true`,
the ordinary automatic whole-page range scanner considers the four families.
No source coordinates, terminal position, expected notes, or measure counts are
provided to recognition. Native acceptance distance and grade thresholds remain
unchanged. New families cannot be seeded by stems; any physical-bar intersection
or nearby vertical seed extending at least one interline beyond the head vetoes
them. The native Fa support guard also applies to the new Fa variants.

These guards are not evidence of universal precision: missed/broken stems,
short rests, ornaments and courtesy symbols can still be mistaken for notes.
Do not enable the feature in the reader or promote from a few recovered heads.

## Stage tracing

`atlas.stemlessTrace=true` logs all retained head identities and geometry at
entry/exit of HEADS, REDUCTION, CHORDS, RHYTHMS and PAGE, with current chord,
duration and voice. Explicit count records distinguish an observed zero from
missing traces. Logs contain source geometry and stay local. Export is checked
from the resulting graph/MusicXML, not inferred from a head count.

## Frozen experiment

`scripts/omr_stemless_study.py` freezes source bytes, prior successful receipts,
the engine distribution and Java sources, native tests, local Python import
closure, source observations, settings and failure policy. Its same-binary
**off** arm must exactly reproduce the three retained paired-v3 **on** arm
inventories before any candidate runs. No archival normalization exception.

```sh
python3 scripts/omr_stemless_study.py --freeze /local/config.json --out /new/run
python3 scripts/omr_stemless_study.py --run --out /new/run
# Completed run: separate read-only analyzer; never new recognition
python3 scripts/omr_stemless_analysis.py --study /retained/run --out /new/analysis
```

A started-but-unreceipted invocation cannot retry. A completed receipt is reused.
Input drift blocks replay. Any changed recipe requires a disclosed new version;
never overwrite a failure or call another use of these pages held-out evidence.

The experiment compares every pre-existing physical-span event list, preserving
changed and orphan spans. Penn has full provisional source event observations;
Thy Strength's retained source grid supports structure/header checks only, not
whole-song pitch/lyric accuracy. Clayton is a regression comparator without a
full source-event grid. Source-certified whole-score accuracy remains unavailable.

Raw scans, labels, geometry, graphs, XML and logs stay ignored/local. Public
results contain aggregate measurements and hashes only. No source upload,
training, canonical score edits, app enablement, merge, deployment or promotion.

## Retained analyzer failure and repair

All six recognition receipts completed successfully. The frozen original
analyzer then stopped on legitimate duplicate native stack IDs: a non-exported
`CAUTIONARY` final stack reuses the preceding musical measure ID. The original
runner remains unchanged/hash-bound; do not run its `--run` or `--analyze` to
recover this analysis. `omr_stemless_analysis.py` is a separate read-only repair
writing outside the retained recognition tree. It excludes **only** non-exported
cautionary stacks from label lookup. Ambiguous exported identities and missing
physical spans still fail. No event normalization, rerun, or evidence rewrite.
