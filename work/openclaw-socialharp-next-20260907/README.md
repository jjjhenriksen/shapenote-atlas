# Social Harp: second five source identities — 2026-09-07

The next five unresolved entries, excluding the original 67 mappings and the first five-entry supplement, were rendered from the retained PDF and directly inspected. PDF leaves below are one-based; printed numbers and literal headings were read independently from the images.

| Catalogue record | PDF leaf | Printed page | Literal heading |
| --- | ---: | ---: | --- |
| socialharp 108 — DERRETT | 108 | 108 | DERRETT. |
| socialharp 109 — COLUMBUS | 109 | 109 | COLUMBUS. |
| socialharp 110 — SHOUTING SONG | 110 | 110 | SHOUTING SONG. |
| socialharp 111 — THE MORNING TRUMPET | 111 | 111 | THE MORNING TRUMPET. |
| socialharp 113 — ETERNAL HOME | 113 | 113 | ETERNAL HOME. |

All five contain notation. This is page-identity review only: no music, lyrics, mode, or shapes were imported or certified. These five headings are legible and match their catalogue titles after removing terminal punctuation. The first five supplement entries (101/103/104/105/107) and original map remain byte-for-byte unchanged.

Combined source-page mapping increases **72 → 77**; unresolved source identities decrease **149 → 144**. This does not increase structured-score coverage. The **221 catalogue records versus 222 historical count** discrepancy remains unresolved.

## Files and provenance

- `socialharp-page-map-supplement-v2.json`: additive five-record map; pins original map, previous supplement, retained PDF, and each inspected render by SHA-256.
- `verify.py`: verifies dependency hashes, exact next-five selection, disjoint IDs, source linkage, preserved inventory, and combined coverage arithmetic. Integrity checks do not themselves prove visual truth.
- `renders/leaf-{108,109,110,111,113}.png`: full-leaf Poppler renders at scale-to 1800, retained locally for reproducible review.

Retained source: `work/luna-program-20260904/source_only/retained-sources/socialharp-1855-imslp-scan.pdf`.

PDF SHA-256: `562db348cf414b27c0c3e40da38cca0a8c39a11f2007abec370f9ddcae1bc331`.

Original-map SHA-256: `8b30106fb48d2467d70063d684ac144887b02e3cfec4470da103dc13d2c90963`.

## Verification

From repository root:

```sh
python3 work/openclaw-socialharp-next-20260907/verify.py
```

Passed on 2026-09-07: five reviewed source identities, 77 combined mapped, 144 unresolved, original inputs unchanged, notation not imported. No application, playback, deployment, or exact-notation verification is claimed. No Git staging or commit was performed by this worker.

To reproduce each local render, substitute the leaf number for `N`:

```sh
pdftoppm -f N -l N -singlefile -scale-to 1800 -png work/luna-program-20260904/source_only/retained-sources/socialharp-1855-imslp-scan.pdf work/openclaw-socialharp-next-20260907/renders/leaf-N
```

Next source-identity batch begins at unresolved entry 115, THE SAINT'S DELIGHT; select from the original unresolved array after subtracting both supplements, not by assuming every successive page is unresolved.
