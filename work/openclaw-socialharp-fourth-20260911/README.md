# Social Harp: fourth source-identity batch — 2026-09-11

Direct visual review of five unedited Poppler renders resolves the next five
unresolved catalogue identities after subtracting all three prior supplements.

| Record | PDF leaf / printed page | Observed literal heading | Opening region |
| --- | --- | --- | --- |
| 125 ANIMATION | 125 / 125 | ANIMATION. | Top |
| 127 OLNEY | 127 / 127 | OLNEY. | Top |
| 129 MEAR | 129 / 129 | MEAR. | Bottom, below HARMONY. Concluded. |
| 131 NEWBERRY | 131 / 131 | NEWBERRY. | Top |
| 133 MERCY'S FREE | 133 / 133 | MERCY’S FREE. | Top |

The literal heading retains the printed apostrophe; matching normalizes only
that punctuation. Page identity is not a notation transcription or exact-edition
notation audit. No lyrics, keys, shapes, pitches, score mappings or public data
were changed. The 221-record / 222-historical-count discrepancy remains open.

Combined reviewed identities: **87 → 92**. Unresolved: **134 → 129**.
Next: **134 THE HARVEST FIELD**, then **135 THE BLOOMING WILDERNESS**.

## Evidence and verification

The JSON pins the retained PDF, original map, all three predecessor supplements,
and the five full-leaf renders by SHA-256. Heading bounding boxes refer to the
1800 × 1133 renders included in this package. Existing artifacts are unchanged.

Run from repository root:

```sh
python3 work/openclaw-socialharp-fourth-20260911/verify.py
```

Passed 2026-09-11: exact next-five selection, no duplicate identities, dependency
hashes, valid coordinates, printed page / catalogue identity parity and coverage
arithmetic. The verifier checks integrity; direct image inspection establishes
the recorded observations. No app build or aggregate verification is claimed.

The original baseline and retained PDF remain local prerequisites, at the paths
pinned in the supplement. They were copied into the isolated checkout only after
matching the previous supplement's hashes. The public Git clone alone does not
contain the retained PDF. See `docs/OPENCLAW_HANDOFF.md` for evidence restoration.

To reproduce a render (substitute the requested page for N):

```sh
pdftoppm -f N -l N -singlefile -scale-to 1800 -png \
  work/luna-program-20260904/source_only/retained-sources/socialharp-1855-imslp-scan.pdf \
  work/openclaw-socialharp-fourth-20260911/renders/leaf-N
```
