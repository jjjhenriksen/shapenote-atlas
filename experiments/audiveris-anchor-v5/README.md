# V5 — explicit source-center and internal-anchor diagnostics

Training-only; not a recognition change. Upstream Audiveris is pinned at
`9e1e55cd2746037d059345881c53e6a6754bffbd`. Use a **new** checkout, apply the
four patches in the [V3 recipe](../audiveris-fa-proximity-v3/README.md), then
apply `probe-call.patch` and copy `ForcedTemplateProbe.java` into
`app/src/main/java/org/audiveris/omr/sheet/note/`. Build with retained Java 25:

```sh
./gradlew :app:installDist --no-daemon
```

The frozen [protocol](protocol.json) predates execution. The label-free local
TSV consists of source filename, observation ID, existing staff ID, x and y
for all 210 frozen positive source-head observations. No held-out or new
source labels are prepared. Diagnostic mode is enabled only by
`-Datlas.forcedTemplatePoints=/absolute/path/to/points.tsv`; without that
property the helper returns immediately.

At each fixed source center and the unchanged 3x3 pixel grid, score native
round BLACK/VOID, diamond and both fa filled/open pairs. For each of three
anchors, score both independent center placement and exactly common internal
anchor placement derived from the filled template. Log actual pivots,
origins, slim centers/sizes, foreground/background/hole errors, ignored
pixels and distances. These evaluations bypass scanner vetoes but **create
no proposals**. Generic BLACK/VOID controls on source squares do not become
square-classification accuracy. Repeated grid positions are not independent
musical examples.

Actual execution, local receipts and replay:

```sh
python3 scripts/sh1991_anchor_probe.py --run off
python3 scripts/sh1991_anchor_probe.py --run forced
python3 scripts/sh1991_anchor_probe.py --output /tmp/atlas-anchor-v5.json
```

Do not repeat completed recognition. Local study is
`work/model-pilot/sh1991-v1/anchor-v5/`, separate engine is its sibling
`toolchain/audiveris-anchor-v5/`. Cache reuse requires identical protocol,
point file, runner, engine, JVM options, constants, source and label hashes.
A different build is a different fingerprint, not historical replay.

Both same-binary arms must preserve frozen V3 candidate written events and
metrics. Replay rejects missing grids, duplicate identities and unequal
internal anchors in paired anchor mode. Source pixels, full raw logs,
engines and exports remain ignored. No musical acceptance, final precision,
mask-causality or production-promotion claim follows from this diagnostic.

Patch context contains normalized line endings. Apply these new patches with
`git apply --ignore-whitespace /absolute/path/to/patch` against the retained
CRLF upstream sources; this does not relax artifact fingerprint checks.
