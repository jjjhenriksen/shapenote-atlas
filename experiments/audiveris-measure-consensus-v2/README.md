# Internal-bar consensus v2 — default-off, development only

Read the [measured results and retained failures](../../docs/experiments/omr-measure-consensus-20261017.md).

## Engine recipe

Create a **separate** Audiveris checkout at
`9e1e55cd2746037d059345881c53e6a6754bffbd`. Reproduce the existing
[V7 source recipe](../audiveris-support-v7/README.md), then apply only this
directory's `hook.patch` with `git apply --ignore-whitespace` (upstream uses
CRLF) and copy `BarConsensus.java` into
`app/src/main/java/org/audiveris/omr/sheet/rhythm/`. Copy the test into the same
package under `app/src/test/java/`. Never change an engine bound by old receipts.

Using the retained Java 25 toolchain, in the separate engine checkout:

```sh
./gradlew :app:installDist :app:test \
  --tests org.audiveris.omr.sheet.rhythm.BarConsensusTest --no-daemon --offline
```

`atlas.barConsensus=false` leaves the original path unchanged. With the property
true, before native measure construction:

1. Use original binary pixels and native five-line staff geometry. Abstain on
   unsupported/mixed systems; never reduce the original staff denominator.
2. Scan interior columns only, excluding one interline at staff ends. Require
   at least 0.86 full-staff vertical coverage; retain widths at most 0.35
   interline, complete-link clusters within 0.35 interline, and a strict staff
   majority (minimum two). These thresholds are unchanged from v1.
3. Add a synthetic thin bar only on a pixel-supporting staff lacking a native
   bar within 0.5 interline. Preserve native groups, source pixels and labels.
   These graph additions have **no glyph**, and are explicitly logged as such.
4. Before insertion, abstain if a proposed de-skewed column would join a
   different existing native column, using the engine's own join tolerance plus
   rounding. Also abstain on nearby ungrouped proposal pairs; do not invent
   double/repeat relations. This is the v1 failure fix, not a coverage sweep.

Cross-staff long stems/artifacts can still imitate bars. These tests do not
prove generic barline precision. Final/double/repeat-group reconstruction,
header recognition and source-head integration are deliberately outside this
intervention.

## Execution contracts

`omr_measure_consensus_run.py` retains the original strict archive-control
contract. `omr_measure_consensus_paired.py` is the **separate v3 execution
protocol**, not a changed v2 receipt: it records any archival mismatch and
permits only a source-bound rest/empty header-orphan exception when every
source-overlapping physical-span event and lyric/notehead count remains exact.
The completed v3 controls actually matched the archives **exactly**, so the
exception was not used in the final comparison. Header-region variability in
the blocked v2 control remains a disclosed limitation.

Both runners require a frozen explicit config and the same three consumed
source IDs in order: 469, 501t, 531. Configs bind source images, prior exports
and graphs, source observations, engine/source/test artifacts, Java, template
points, runner, settings and failure policy. `--freeze CONFIG --out NEW`
creates the protocol; `--run --out NEW` runs off controls before any on arm;
`--replay --out COMPLETE` only verifies existing receipts. A started but
unreceipted invocation cannot retry. Use a genuinely new, disclosed development
version for changed code/settings/policy, not a renamed rerun as fresh evidence.

Restricted configs and raw artifacts remain ignored/local. A new public clone
cannot run source experiments without those inputs. No reserved Warsaw source
was opened; no training, source upload, reader enablement, promotion or merge.
