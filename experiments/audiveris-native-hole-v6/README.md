# V6 — native Fa hole reassignment, default off

A single-cause training-only intervention following V5. The frozen
[protocol](protocol.json) preserves every original selection gate.
Create another checkout at upstream
`9e1e55cd2746037d059345881c53e6a6754bffbd`, apply the four
[V3 patches](../audiveris-fa-proximity-v3/README.md), then `native-hole.patch`.
Copy `NativeFaHoleTest.java` into
`app/src/test/java/org/audiveris/omr/sheet/note/`. Build with retained Java25:

```sh
./gradlew :app:installDist :app:test --tests org.audiveris.omr.sheet.note.NativeFaHoleTest --no-daemon
```

`atlas.nativeFaHole` defaults off. When on, a chosen filled logical fa
candidate may be reassigned to its same-orientation hollow partner if its
hole white ratio meets the **existing 0.2 threshold**. This is evaluated at
the exact filled candidate internal anchor and preserves its match grade,
as the pre-existing generic BLACK-to-VOID rule does. No mask, search,
threshold, stem/bar guard or proximity change accompanies the intervention.
The generic rule remains unchanged regardless of the flag. Tests cover
orientation, ordinary behavior, all unrelated shapes, and default-off.

The local study and engine are separate `native-hole-v6/` and
`toolchain/audiveris-native-hole-v6/` directories. Execute sequential arms:

```sh
python3 scripts/sh1991_native_hole.py --run reference
python3 scripts/sh1991_native_hole.py --run v3-control
python3 scripts/sh1991_native_hole.py --run candidate
python3 scripts/sh1991_native_hole.py --output /tmp/atlas-native-hole-v6.json
```

Reuse completed fingerprint-matched receipts, not duplicate inference.
Two workers and a 180-second/page timeout are fixed. Replay requires the
fa-off reference to match frozen V3 control and hole-off comparator to match
frozen V3 candidate, including written events, counts, topology, source-head
retention and candidate-reference metrics. Candidate metrics remain
unreviewed-reference agreement, not source-certified accuracy. No held-out
work, source upload, default enablement, promotion or merge.

Patch context contains normalized line endings. Apply these new patches with
`git apply --ignore-whitespace /absolute/path/to/patch` against the retained
CRLF upstream sources; this does not relax artifact fingerprint checks.
