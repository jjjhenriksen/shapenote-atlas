# Internal-bar consensus v1 — rejected development version

This archived version recovers pixel-supported internal thin bars immediately
before `MeasuresBuilder` groups them. `atlas.barConsensus` defaults **off**.
It does not use annotated boundary coordinates or expected measure counts.

The candidate doubled Thy Strength/Clayton exported measures from 8 to 16, but
Penn's export **failed**: a new physical bar fell inside an existing column's
join tolerance, causing duplicate staff groups and an index error. Retain that
failure; never substitute a zero-event baseline or overwrite its recognition.

Use [v2](../audiveris-measure-consensus-v2/README.md) for the explicit column
collision safeguard. Both versions preserve their exact helper/test/hook bytes.
The [study report](../../docs/experiments/omr-measure-consensus-20261017.md)
records the failed, blocked and final paired-development phases separately.
