# Audiveris fa-template v1 — rejected research prototype

Read the [decision and measured failures](../../docs/experiments/sh1991-fa-template-v1-20261015.md).
This patch is default-off, not a production fix. It is against Audiveris commit
`9e1e55cd2746037d059345881c53e6a6754bffbd` (5.11.0).
The archived patch preserves upstream CRLF/context bytes and its frozen hash;
the adjacent `.gitattributes` prevents text normalization/whitespace rewriting
of this evidence file only.

## Verify existing artifacts without rerunning recognition

From the Atlas root, with the retained ignored `work/model-pilot/sh1991-v1/`
present:

```sh
python3 -m unittest discover -s tests -p 'test_sh1991_*.py'
python3 scripts/sh1991_fa_experiment.py --prepare
python3 scripts/sh1991_fa_experiment.py --output /tmp/fa-v1-replayed.json
```

`--prepare` reconstructs or verifies only frozen protocol/engine metadata and
the two five-image **training-only** datasets. It refuses changed metadata,
changed source bytes, changed parent manifest, and a probe that is no longer
entirely in training. It does not download inputs or run recognition. It gets
the original frozen protocol/engine values from the committed JSON report.
No flag prepares held-out data. The summary command checks hashes, recomputes
score agreement and graph localization from retained outputs, and writes the
requested report plus the local gate decision. Numeric results should match;
`analysisScriptSha256` identifies the analysis implementation, not the engine.

For the subsequent [stage-survival trace](../../docs/experiments/sh1991-fa-survival-20261015.md),
also from the existing artifacts and without recognition:

```sh
python3 scripts/sh1991_fa_survival.py --output /tmp/fa-survival-replay.json
```

Original per-image receipts record the exact executable, constants, input,
output, command and engine fingerprint. `sh1991_pilot.py baseline` can reuse
them only for identical input/label/engine/command values; changed constants
cannot silently reuse the opposite arm. On resume, inspect receipts before
launching any recognition. A matching cached run is not new inference.

## Rebuild the engine independently

Prerequisites: Java 25, Audiveris build dependencies, and a clean, separate
Audiveris checkout at the pinned revision. Do not patch the retained baseline
checkout. Resolve the patch path from this Atlas checkout:

```sh
git -C /absolute/path/to/separate-audiveris-checkout rev-parse HEAD
git -C /absolute/path/to/separate-audiveris-checkout apply --check /absolute/path/to/atlas/experiments/audiveris-fa-v1/fa-heads.patch
git -C /absolute/path/to/separate-audiveris-checkout apply /absolute/path/to/atlas/experiments/audiveris-fa-v1/fa-heads.patch
cd /absolute/path/to/separate-audiveris-checkout
./gradlew :app:installDist :app:test --tests org.audiveris.omr.image.FaHeadPrototypeTest --no-daemon
```

The original four Java test results are recorded in the report's engine
metadata, including the test-XML SHA256. A new build can have different jar
hashes: do not overwrite the frozen v1 identity to call it an exact replay.
Record any changed binary/protocol as a new run/version with its own evidence.

## Original inference recipe (do not repeat completed runs)

With the **retained, fingerprint-matching v1 engine**, these commands describe
the original two arms. On the existing work directories they should only
return verified cached receipts, not launch inference. Use analysis-only
replay above for routine checking. Recognition uses the original images and
the frozen five-record datasets prepared above.

```sh
python3 scripts/sh1991_pilot.py --work work/model-pilot/sh1991-v1/fa-template-v1/off baseline \
  --audiveris /absolute/path/to/retained-v1/app/build/install/app/bin/Audiveris \
  --constant org.audiveris.omr.sheet.ProcessingSwitches.faHeads=false \
  --constant org.audiveris.omr.Main.persistBatchCliConstants=false \
  --constant org.audiveris.omr.sheet.note.NoteHeadsBuilder.dumpTemplateNotes=true
python3 scripts/sh1991_pilot.py --work work/model-pilot/sh1991-v1/fa-template-v1/on baseline \
  --audiveris /absolute/path/to/retained-v1/app/build/install/app/bin/Audiveris \
  --constant org.audiveris.omr.sheet.ProcessingSwitches.faHeads=true \
  --constant org.audiveris.omr.Main.persistBatchCliConstants=false \
  --constant org.audiveris.omr.sheet.note.NoteHeadsBuilder.dumpTemplateNotes=true
```

The executable path itself must match each recorded command, not just its
contents. Fresh-clone source acquisition is described in the
[baseline report](../../docs/experiments/sh1991-omr-baseline-20261015.md);
live bytes may differ. Exact historical replay requires matching retained
source/label/manifest hashes. Restricted scans, labels and engine outputs are
not committed. No data upload, training permission, paid compute, source
certification or promotion is implied by this recipe.
