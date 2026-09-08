# Social Harp: third source-identity batch - 2026-09-07

The next ten unresolved records, excluding the original 67 mappings and both five-entry supplements, were directly inspected on eight freshly rendered PDF leaves. PDF leaves are one-based; printed numbers, literal headings and page regions were read independently from the images.

| Catalogue record | PDF leaf | Printed page | Literal heading | Position |
| --- | ---: | ---: | --- | --- |
| 115 THE SAINT'S DELIGHT | 115 | 115 | THE SAINT'S DELIGHT. | Above opening system |
| 116 REPENTANCE | 116 | 116 | REPENTANCE. | Above opening system |
| 117 PILGRIM | 117 | 117 | PILGRIM. | Upper right, following Repentance's conclusion |
| 118b SWEET HEAVEN | 118 | 118 | SWEET HEAVEN. | Bottom tune |
| 118t WINDHAM | 118 | 118 | WINDHAM. | Top tune |
| 119 WEBSTER | 119 | 119 | WEBSTER. | Beneath PART III.; page number at lower right |
| 120b ABBEVILLE | 120 | 120 | ABBEVILLE. | Bottom tune |
| 120t CORINTH | 120 | 120 | CORINTH. | Top tune |
| 121 PRIMROSE HILL | 121 | 121 | PRIMROSE HILL. | Above opening system |
| 123 PLENARY | 123 | 123 | PLENARY. | Above opening system |

All ten records have notation and legible headings. The `t`/`b` catalogue suffixes identify top/bottom tunes; they are **not** part of the printed page number. Repentance's opening is on leaf 116, with `REPENTANCE. Concluded.` at upper left of leaf 117; that repeated continuation heading does not create an additional record or displace Pilgrim's separate opening. Identity review does not imply the full notation was transcribed or audited.

Combined source-page mappings increase **77 to 87**; unresolved identities decrease **144 to 134**. The original map and both previous supplements remain byte-for-byte unchanged. No public data, score mapping, lyrics, mode, noteheads or other notation were changed. The **221 catalogue records versus 222 historical count** discrepancy remains unresolved; shared-page identities do not settle it.

## Files and provenance

- `socialharp-page-map-supplement-v3.json`: additive ten-record map; pins original map, both previous supplements, retained PDF and every inspected render by SHA-256. Each heading includes a pixel bounding box in its 1800 x 1133 full-leaf render for convenient human review.
- `verify.py`: checks dependency hashes, exact next-ten selection, disjoint record IDs, source linkage, top/bottom suffix handling, valid image coordinates, preserved inventory and combined coverage arithmetic. These checks establish integrity, not visual truth independently.
- `renders/leaf-{115,116,117,118,119,120,121,123}.png`: eight full-leaf Poppler renders, retained locally; no scan pixels were edited.

Retained source: `work/luna-program-20260904/source_only/retained-sources/socialharp-1855-imslp-scan.pdf`.

PDF SHA-256: `562db348cf414b27c0c3e40da38cca0a8c39a11f2007abec370f9ddcae1bc331`.

Original-map SHA-256: `8b30106fb48d2467d70063d684ac144887b02e3cfec4470da103dc13d2c90963`.

## Verification and continuation

Run from the repository root:

```sh
python3 work/openclaw-socialharp-third-20260907/verify.py
```

Passed on 2026-09-07: ten reviewed identities on eight leaves, 87 combined mapped, 134 unresolved, original dependencies unchanged and no notation imported. No app, playback, deployment or exact-notation verification is claimed. Worker performed no Git staging or commit.

Reproduce each local render, substituting the leaf number for `N`:

```sh
pdftoppm -f N -l N -singlefile -scale-to 1800 -png work/luna-program-20260904/source_only/retained-sources/socialharp-1855-imslp-scan.pdf work/openclaw-socialharp-third-20260907/renders/leaf-N
```

The next unresolved record is **125 ANIMATION**, followed by **127 OLNEY**. Select subsequent records from the original unresolved array after subtracting all three supplements. No source-access blocker was encountered in this batch.
