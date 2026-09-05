# Shape-Note Atlas browser audio replay plan

Replay this plan at `http://127.0.0.1:5173/audio-harness.html`. Keep the
dashboard UI unchanged. The page-level `#audio-trace` JSON is the source for
the compact receipt; record counts and first frequencies, not the entire array.

The required browser cases are:

- `source-verified-major`: Sacred Harp 1991 -> `26 Samaria`, source `Ab major`; play all four parts, stop, set target `G major`, play, stop.
- `source-verified-minor`: Sacred Harp 2025 -> `41 Evening Hymn`, source `B minor`; play all four parts, stop, set target `C minor`, play, stop.
- `unknown-key-entry`: Cooper Book 2012 -> `28t Will Guide Us Till We Die (Aylesbury)`; enter source `C minor`, play all four parts, stop, set target `D minor`, play, stop.
- `reference-witness`: Sacred Harp 2025 -> `26 Samaria`; confirm the reference-witness presentation, then play all four parts and stop.
- `review-draft`: Sacred Harp 2025 -> `80t Troubles Over`; confirm the draft-only notice and source-observed `G minor`, play all four parts, stop, set target `C minor`, play, stop.
- `partial-parts`: Sacred Harp 1991 -> `26 Samaria`; deselect Bass, play the remaining three parts, and stop.
- `target-key-change`: while `partial-parts` is playing, select `G major`; confirm the Stop control disappears, Play returns, and the cancellation notice names the target-key change.
- `automatic-end`: on `review-draft`, play all parts and wait for the short song to finish; confirm Play is back, Stop is absent, and each oscillator has both its scheduled stop and end cleanup stop.
- `target-reset`: set Samaria to target `G major`, switch to Sacred Harp 2025 -> Evening Hymn, and confirm the target resets to source `B minor`.

For every case, capture page identity, `contextAvailable`, `consoleErrors`,
`harnessErrors`, and the post-action Play/Stop state. The tracked receipt
validator derives expected event counts and frequencies from the referenced
score assets.
