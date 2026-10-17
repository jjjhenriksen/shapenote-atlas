# Training-only barline diagnosis and selective fa-stem safeguard

Read the [measured result and rejection gates](../../docs/experiments/sh1991-barline-v2-20261015.md).
All patches target Audiveris `9e1e55cd2746037d059345881c53e6a6754bffbd`.
No application or canonical score changes are included.

## Patches

1. Apply the original `../audiveris-fa-v1/fa-heads.patch` to a **separate** clean
   checkout. Never patch the retained baseline or frozen fa-v1 engine.
2. `diagnostics.patch`: `atlas.barTrace=true` prints physical bars at entry/exit
   of every step and call stacks on removal. Default-off; no recognition policy.
3. `fa-stem-guard.patch`: exclusion decision/support diagnostics plus the active
   experiment. `atlas.faStemBarGuard=true` prefers a physical barline over a
   directly conflicting stem only when its current head support is nonempty
   and exclusively logical fa shapes. Default-off. Does not change column rules.
4. `FaStemBarGuardTest.java`: copy to
   `app/src/test/java/org/audiveris/omr/sig/` in that checkout.

The separate `fa-bar-guard.patch` and `FaBarGuardTest.java` archive an earlier
conflict-probe build. Its direct-fa-head policy was **never activated**;
`atlas.faBarGuard` remained false. Do not apply it alongside the active patch:
both patch `SIGraph`. The five probe runs are diagnostic confirmation only.
This archive preserves the actual executed binary’s source provenance.

From the Atlas root, using absolute paths in a separate Audiveris checkout:

```sh
git -C /absolute/separate/audiveris checkout 9e1e55cd2746037d059345881c53e6a6754bffbd
git -C /absolute/separate/audiveris apply /absolute/atlas/experiments/audiveris-fa-v1/fa-heads.patch
git -C /absolute/separate/audiveris apply /absolute/atlas/experiments/audiveris-barline-v2/diagnostics.patch
git -C /absolute/separate/audiveris apply /absolute/atlas/experiments/audiveris-barline-v2/fa-stem-guard.patch
cp experiments/audiveris-barline-v2/FaStemBarGuardTest.java /absolute/separate/audiveris/app/src/test/java/org/audiveris/omr/sig/
```

Then in the engine checkout, with Java 25 in `JAVA_HOME`:

```sh
./gradlew :app:installDist :app:test \
  --tests org.audiveris.omr.image.FaHeadPrototypeTest \
  --tests org.audiveris.omr.sig.FaStemBarGuardTest --no-daemon
```

A fresh build may have a different jar fingerprint. It is a new execution,
not an exact replay of archived engine bytes. Do not replace frozen engine
identities or cached receipts to disguise that difference.

## Historical recognition configuration

All runs used original full-frame scans for **26, 83t, 68b, 72b, 89**, verified
as training records. Constants in every arm:

```text
org.audiveris.omr.Main.persistBatchCliConstants=false
org.audiveris.omr.sheet.note.NoteHeadsBuilder.dumpTemplateNotes=true
```

| Arm | Engine | faHeads | JAVA_OPTS |
| --- | --- | --- | --- |
| off | original fa patch + stage diagnostics | false | `-Datlas.barTrace=true` |
| on | same diagnostic binary | true | `-Datlas.barTrace=true` |
| guard-off | separate conflict probe | true | `-Datlas.barTrace=true` (direct-head property unset/false) |
| stemguard-off | active stem patch | true | `-Datlas.barTrace=true -Datlas.faStemBarGuard=false` |
| revised | same active binary | true | `-Datlas.barTrace=true -Datlas.faStemBarGuard=true` |

Per-image `run.json` stores the complete actual launcher command (`-batch
-export`, constants, original input and separate output directory), input and
label hashes, output hash and engine fingerprint. Study engine metadata binds
patch hashes and JVM options; the last two arms also have `execution.json`.
The design/gates were frozen before the active safeguard was enabled.

The historical diagnostic/probe runs used `sh1991_pilot.run()` with two workers
and a 180-second per-image timeout, `JAVA_HOME` pointing at the retained Java 25
toolchain, and the exact environments above. These calls were new recognition,
not reused baseline receipts. Subsequent analysis reads the saved results only.

For the **retained, hash-matching engine and study layout**, the actual final
two-arm commands were:

```sh
python3 scripts/sh1991_barline_run.py --arm stemguard-off
python3 scripts/sh1991_barline_run.py --arm revised
```

They should now return cached receipts only. The wrapper verifies the exact
training cohort and refuses a changed dataset, engine/patch identity, runner
hash or JVM environment before using that arm’s cache. The generic pilot cache
does not itself bind JVM environment, which is why the wrapper adds this guard.
Never reuse the revised directory for a changed property or new engine. A new
experiment needs separate study/output paths and newly frozen metadata.

## Analysis-only replay

```sh
python3 -m unittest discover -s tests -p 'test_sh1991_*.py'
python3 scripts/sh1991_barline_trace.py --output /tmp/barline-replay.json
cmp docs/experiments/sh1991-barline-v2-20261015.json /tmp/barline-replay.json
```

The retained ignored `work/model-pilot/sh1991-v1/barline-v2/` contains the
protocol, design, original inventory, engine/test/config manifests and five
arm directories. The reporter verifies these, the original dataset and source
audit, original experiment files, original v1 libraries and each executed
engine, then rechecks source/label/input/export hashes and rescored agreement.
Its checked-in JSON is numeric/source-pointer evidence, not a raw engine log or
source-image distribution. Bar inventory deltas reconstruct every stage in
the primary off/on/revised arms; confirmation arms retain stage counts and
conflict/removal receipts without duplicating the inventory. In each case,
`logLineRange`, conflict/removal line numbers and file hashes preserve receipts.

No held-out acquisition, recognition, model training, paid compute, source
upload, source certification, gate relaxation or merge is part of this study.
