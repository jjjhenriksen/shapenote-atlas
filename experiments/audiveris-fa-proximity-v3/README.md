# Fa-only proximity v3 — training experiment, still rejected for promotion

Read the [measured report](../../docs/experiments/sh1991-fa-proximity-v3-20261015.md).
The source-linked benchmark and numeric result are under `docs/experiments/`.
Restricted pixels, contact sheets, logs, graphs and binaries stay ignored.

## Separate build

Use a clean separate Audiveris checkout at
`9e1e55cd2746037d059345881c53e6a6754bffbd` with Java 25. Do not modify the
retained baseline, fa-v1 or v2 builds. Apply these patches in order:

```sh
git -C /absolute/separate/audiveris apply /absolute/atlas/experiments/audiveris-fa-v1/fa-heads.patch
git -C /absolute/separate/audiveris apply /absolute/atlas/experiments/audiveris-barline-v2/diagnostics.patch
git -C /absolute/separate/audiveris apply /absolute/atlas/experiments/audiveris-barline-v2/fa-stem-guard.patch
git -C /absolute/separate/audiveris apply /absolute/atlas/experiments/audiveris-fa-proximity-v3/fa-proximity.patch
```

Copy `../audiveris-barline-v2/FaStemBarGuardTest.java` to
`app/src/test/java/org/audiveris/omr/sig/`, and `FaBarProximityTest.java` to
`app/src/test/java/org/audiveris/omr/sheet/note/`. The original fa patch includes
its four-test source. From the engine checkout:

```sh
./gradlew :app:installDist :app:test \
  --tests org.audiveris.omr.image.FaHeadPrototypeTest \
  --tests org.audiveris.omr.sig.FaStemBarGuardTest \
  --tests org.audiveris.omr.sheet.note.FaBarProximityTest --no-daemon
```

Only `NoteHeadsBuilder` changes beyond v2. `atlas.faBarProximity` defaults off;
it rejects logical fa proposals whose slim template bounds intersect an
already detected physical bar area. No blanket bar freeze or ordinary-head
veto is added. Template distance/hole probes are diagnostic only. The source
test exercises default-off behavior, all fa orientations/fills, ordinary
heads, disjoint/boundary-only boxes and absence of detected bars.

## Frozen historical execution

The retained study is `work/model-pilot/sh1991-v1/fa-discrimination-v3/` and
the engine is its separate sibling toolchain checkout
`toolchain/audiveris-fa-proximity-v3/`. All three arms have the same binary,
original full-frame training inputs **26, 83t, 68b, 72b, 89**, two workers and
180-second per-image timeout. Original source/label hashes are verified.

```sh
python3 scripts/sh1991_fa_proximity.py --run control
python3 scripts/sh1991_fa_proximity.py --run v2-control
python3 scripts/sh1991_fa_proximity.py --run candidate
```

These are the actual commands used. Do not repeat completed inference.
With retained matching code, metadata and engine, they can use cached receipts;
any dataset, runner, engine/patch, probe-file or JVM environment drift must
create a separate experiment rather than overwriting the arm's configuration.
A new independent build may have different jar hashes; it is not an exact
historical replay. Never replace frozen identities to disguise that change.

`execution.json` binds the runner SHA256, Java home/options, engine and
constants. Per-image `run.json` records the full launcher command, input/label
hashes, export hash and scoring receipt. Every arm sets:

```text
org.audiveris.omr.Main.persistBatchCliConstants=false
org.audiveris.omr.sheet.note.NoteHeadsBuilder.dumpTemplateNotes=true
-Datlas.barTrace=true
-Datlas.faStemBarGuard=true
-Datlas.templatePoints=/absolute/retained/study/probe-points.tsv
```

`faHeads` is false only in `control`; `atlas.faBarProximity` is true only in
`candidate`. The TSV contains source filename, benchmark ID, x and y, not
labels. Its hash is frozen with the engine metadata. It includes the unchanged
210-head observations and 24 separately source-reviewed non-head points; no
held-out points are prepared or read. The engine filters rows to its input
filename and logs proposals within 0.5 staff interline of each point.

## Analysis-only replay

```sh
python3 -m unittest discover -s tests -p 'test_sh1991_*.py'
python3 scripts/sh1991_fa_proximity.py --output /tmp/fa-proximity-replay.json
cmp docs/experiments/sh1991-fa-proximity-v3-20261015.json /tmp/fa-proximity-replay.json
```

This mode invokes no recognition. It verifies benchmark/probe/patch/engine
identities, training-only cohorts, original v2 inventory, per-image receipts,
source/label/input/export hashes and rescored agreement, then compares both
controls with the previous frozen results. The report records raw graph/log
hashes and template-probe line numbers; an identical report demonstrates
analysis reproducibility, not independent musical correctness.

The separate verification JSON records the executed runner and focused Java
test XML hashes/counts. These remain inspection receipts, not proof of source
accuracy. No promotion, held-out tuning, model training, source upload, paid
compute, application-code changes or merge is authorized by this recipe.
