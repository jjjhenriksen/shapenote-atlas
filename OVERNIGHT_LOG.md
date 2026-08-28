# Overnight improvement log

## Cycle 1 — Source follow-up navigation

- Problem identified: The `Sources` navigation button only changed the section label; it still displayed the full edition library, so users could not focus on records that depended on source evidence or transcription work.
- Change made: `Sources` now filters to non-structured edition records, reports the source-record count, searches coverage status and next action, and keeps source statuses (`source`, `blocked`, `metadata`, or `mapping gap`) authoritative even when a review draft is also available.
- Validation performed: Browser baseline and post-change checks at `http://127.0.0.1:5173/`; Sacred Harp 1991 showed `2 shown · 2 source records`; Sacred Harp 2025 showed `80 shown · 576 source records`; searching `blocked` returned all six blocked 2025 records; page identity remained correct and console warnings/errors remained empty. `npm run validate-data`, `npm run validate-transposition`, and `npm run build` passed.
- Commit: `55dfebe` — Make source navigation show coverage follow-up records.
- Remaining opportunities/blockers: Review keyboard state semantics for navigation, tune selection, and part toggles; audit mobile layout and the source-key entry flow; no blocker currently.

## Cycle 2 — Accessible state semantics

- Problem identified: Active navigation, selected tune, and selected parts were communicated only through CSS classes, and result-count changes were not announced to assistive technology.
- Change made: Added `aria-pressed` to navigation, tune-result, and part-toggle buttons; grouped available-part toggles with an accessible label; and marked the result summary as a polite live region.
- Validation performed: Browser DOM inspection confirmed the expected true/false states, the parts group label, and `aria-live="polite"`; clicking Practice and toggling Treble updated the semantic states; page identity remained correct and browser console warnings/errors remained empty. Production build passed after the change.
- Commit: `d56bad4` — Expose atlas selection state to assistive technology.
- Remaining opportunities/blockers: Synchronize the selected detail with filtered result sets; audit mobile layout and the source-key entry flow; no blocker currently.

## Cycle 3 — Filtered-selection synchronization

- Problem identified: Filtering or switching sections could hide the selected tune from the result list while leaving its unrelated detail pane visible.
- Change made: When a non-empty filtered result set no longer contains the selected tune, the atlas selects its first visible result. True no-result searches preserve the last detail so the user can recover by clearing or changing the query.
- Validation performed: Browser checks confirmed Sources selected its first visible record and matched its detail heading, Practice did the same, searching `Samaria` selected Samaria, and a no-result search preserved the selected detail; page identity remained correct and browser console warnings/errors remained empty. Production build passed after the change.
- Commit: `ea8660b` — Keep tune details aligned with filtered results.
- Remaining opportunities/blockers: Audit mobile layout and the source-key entry flow; review score-loading and playback failure states; no blocker currently.

## Cycle 4 — Recoverable lazy-score failures

- Problem identified: A failed lazy MusicXML request left the primary control in an indefinite `Loading…` state with no explanation or recovery path.
- Change made: Added explicit score-load error state, an accessible alert, and an enabled `Retry loading` action that starts a fresh request; normal score loading remains unchanged.
- Validation performed: `npm run build` passed. A temporary local proxy returned a controlled 503 for score assets; the browser then showed `Retry loading`, exposed the explanatory alert, kept retry enabled, and returned to the retrying state after activation. The normal app path still reached `Play song` with no alert and no browser console warnings/errors.
- Commit: `b6723c7` — Make lazy score loading recoverable.
- Remaining opportunities/blockers: Audit mobile layout and the source-key entry flow; review playback permission/failure feedback; no blocker currently.

## Cycle 5 — Persist the selected book

- Problem identified: The app saved `sh-corpus-dashboard-book` but always initialized the book selector to Sacred Harp 1991, so the saved edition preference was discarded on reload.
- Change made: Initialize the selected book from the validated saved book ID, falling back safely to Sacred Harp 1991 when storage is unavailable or stale.
- Validation performed: Browser selected Sacred Harp 2025, confirmed `506 transposable · 590 tunes`, reloaded the page, and confirmed Sacred Harp 2025 and the same summary persisted; page identity remained correct and browser console warnings/errors remained empty. Production build passed after the change.
- Commit: `48ae825` — Restore the saved tune book on reload.
- Remaining opportunities/blockers: Audit the source-key entry flow and playback permission/failure feedback; review whether selected tune persistence is useful; no blocker currently.

## Cycle 6 — Search recorded source metadata

- Problem identified: The search contract mentioned source metadata, but its index omitted recorded source URLs and evidence URLs, so source-domain queries such as `fasola` and `shapenote` returned no records.
- Change made: Include edition metadata URLs, coverage URLs, edition evidence URLs, and source-image URLs in the normalized search terms while retaining existing title, page, first-line, and catalog metadata matching.
- Validation performed: Browser search on Sacred Harp 2025 returned 80 matches for both `fasola` and `shapenote`; Sources mode kept the same query constrained to `576 source records` and displayed source statuses; page identity remained correct and browser console warnings/errors remained empty. Production build and data/transposition validators passed after the change.
- Commit: `72c998f` — Search the atlas by recorded source URLs.
- Remaining opportunities/blockers: Audit the source-key entry flow and playback permission/failure feedback; review whether selected tune persistence is useful; no blocker currently.

## Cycle 7 — Keep entered source keys correctable

- Problem identified: Once a user entered a source key for a key-unknown score, the selector disappeared, leaving no way to correct or clear a potentially mistaken saved choice.
- Change made: Keep the source-key selector visible while the resolved key is user-entered, with copy that makes the correction path explicit; source-verified keys still use the authoritative metadata path.
- Validation performed: Browser confirmed a persisted `G major` choice remained editable, changing it to `A major` kept transposition enabled, and clearing it restored `Source key required` with target-key selection disabled; page identity remained correct and browser console warnings/errors remained empty. Production build passed after the change.
- Commit: Cycle 7 commit in Git history — Keep manually entered source keys editable.
- Remaining opportunities/blockers: No required improvements remain after final whole-app validation; no blocker.
