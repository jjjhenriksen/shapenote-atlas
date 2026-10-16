# V7 — majority-observable Fa foreground, default off

All nine unchanged **training** gates pass. This is not source-certified
accuracy or production acceptance. [Frozen protocol](protocol.json).

Create a new Audiveris checkout at
`9e1e55cd2746037d059345881c53e6a6754bffbd`, apply the four
[V3 patches](../audiveris-fa-proximity-v3/README.md), then apply
[V6](../audiveris-native-hole-v6/native-hole.patch) and `support.patch`
with `git apply --ignore-whitespace` (upstream has CRLF context). Copy
`FaSupportTest.java` into `app/src/test/java/org/audiveris/omr/sheet/note/`.
With retained Java25:

```sh
./gradlew :app:installDist :app:test --tests org.audiveris.omr.sheet.note.FaSupportTest --no-daemon
```

The single new intervention is `atlas.faSupport`, default off. A logical Fa
proposal must have at least half its expected foreground pixels observable
(in bounds and not neutralized). The exact majority boundary was frozen
before inference; no sweep or fitted per-source rule. Ordinary templates,
barline handling and all original thresholds remain unchanged. V6 native
hole reassignment is fixed on in the fa-on comparator/candidate.

Read-only scanner support diagnostics use 234 frozen benchmark points plus
21 already-reviewed retained unmatched centers, supplied as label-free TSV.
They do not create proposals, read new source labels or establish musical
precision. Both comparator arms reproduce historical event sequences and
metrics before differences are interpreted.

```sh
python3 scripts/sh1991_fa_support.py --run reference
python3 scripts/sh1991_fa_support.py --run v6-control
python3 scripts/sh1991_fa_support.py --run candidate
python3 scripts/sh1991_fa_support.py --output /tmp/atlas-support-v7.json
```

Completed receipts are immutable and fingerprint-checked. Do not repeat
recognition; local study and separate engine are `support-v7/` and
`toolchain/audiveris-support-v7/` beneath `work/model-pilot/sh1991-v1/`.
Original held-out policy now permits **one** fixed evaluation on its eight
existing test images after freezing engine/patch/constants. Test outcomes
must not tune this version; prior baseline/voice tests mean the cohort is
held out from these interventions, not never previously seen. No source
upload, paid compute, enablement in the app, production promotion or merge.
