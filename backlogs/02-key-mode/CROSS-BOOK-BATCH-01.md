# Cross-book key/mode remediation — bounded batch 01

## Scope

This batch started from the canonical key/mode reconciliation and prioritized
SH2025 secondary/cross-edition candidates. It used direct inspection of the
current-edition Sacred Harp Bremen scan headers only when the printed key and
mode were legible. No key or mode was inferred from melody, raw fifths, a
cross-edition candidate, or a missing MusicXML `<mode>` element.

## Source-backed resolutions

The following 31 SH2025 records now carry source-verified key/mode evidence in
the generated corpus. Each witness is retained by URL and SHA-256 in
`keyEvidence`:

- `27t` — Bethel: F minor
- `37t` — Ester: F major
- `78` — Stafford: A major
- `135` — Olney: F major
- `145t` — Warrenton: G major
- `154` — Rest for the Weary: Eb major
- `176t` — Ragan: F major
- `178t` — Africa: Eb major
- `211` — Whitestown: E minor (corrects the non-authoritative G-major candidate)
- `274t` — The Golden Harp: F# minor (corrects the non-authoritative A-major candidate)
- `278b` — Traveling Pilgrim: G minor (corrects the non-authoritative G-major candidate)
- `282` — I'm Going Home: F major
- `330t` — Fellowship: E minor (corrects the non-authoritative G-major candidate)
- `333` — Family Circle: A major
- `347b` — Humility: Bb major
- `347t` — Christian’s Farewell: Bb major
- `360` — The Royal Band: E minor
- `364` — Southwell: E major
- `423t` — Grantville: F# minor
- `452b` — Martin: F major
- `497b` — Supplication: A minor
- `497t` — Natick: A major
- `499b` — At Rest: F major
- `501b` — O’Leary: G major
- `503` — Lloyd: F major
- `508` — Sermon on the Mount: Eb major
- `565b` — The Hill of Zion: A major
- `565t` — Hebron: Bb major
- `77t` — The Child of Grace: A minor
- `313b` — Cobb: A minor
- `445` — Passing Away: C major

## Reconciliation counts

| State | Unknown assets | SH1991 | SH2025 | Cooper 2012 | Southern Harmony |
| --- | ---: | ---: | ---: | ---: | ---: |
| Before | 201 | 68 | 37 | 75 | 21 |
| After | 170 | 68 | 6 | 75 | 21 |

The current report has no remaining secondary/cross-edition candidates and 170
raw MusicXML assets without a usable source-encoded key/mode declaration. Forty-two
source-verified assets have an explicit key while their raw MusicXML omits
`<mode>`; 20 raw-fifths conflicts are explicitly preserved. Safe promotions
remain 0.

All 170 unresolved records now have the explicit disposition
`external-source-blocked`, with a precise missing-evidence statement and
source locator. The autonomous-blocked count is 0. Unknown mode remains
unknown; this is a disposition change, not a fabricated key or mode.

## Validation

- `python3 scripts/validate_key_mode_reconciliation.py` passes.
- `python3 scripts/validate_transposition.py` passes: 1,317 assets; 170
  unknown; 0 OMR-detected non-draft assets.
- Python compilation passes for the key/mode scripts.

The generator, canonical corpus/report, and key/mode validator were the only
owned surfaces changed. UI files and active transcription/image workers were
not modified.

## Follow-up lead check

The Fasola 1991 page for `29t Fairfield` was checked directly. It exposes the
tune, words, music, and meter, but no explicit key or mode, so `sh1991/29t`
remains `external-source-blocked` with the Fasola page retained as its source
locator. No key or mode was inferred from that page.
