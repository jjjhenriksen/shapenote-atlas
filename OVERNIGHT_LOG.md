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
- Remaining opportunities/blockers: Continue the restarted audit; existing uncommitted source-candidate comparison work is preserved and is not part of this cycle.

## Cycle 8 — Normalize selector accessible names

- Problem identified: The tune-book, source-key, and target-key native selectors inherited decorative chevron text in their accessible names, making exact screen-reader targeting unreliable.
- Change made: Added explicit accessible labels to all three selectors while preserving their existing visible labels, values, and behavior.
- Validation performed: Browser DOM checks found exactly one `Tune book`, `Source key`, and `Target key` combobox by exact accessible name; selecting `G major` enabled the target-key control and reported `Entered source key: G major`, while clearing it restored `Source key required` and disabled the target selector. `npm run validate-playback` and `npm run build` passed.
- Commit: Cycle 8 accessibility commit in Git history — Normalize selector accessible names.
- Remaining opportunities/blockers: Reassess the source-comparison path, tune persistence, playback feedback, and responsive behavior in additional cycles; no blocker currently.

## Cycle 9 — Restore the selected tune on reload

- Problem identified: Reloading the atlas restored the chosen edition and source-key overrides but discarded the tune being studied, returning the detail pane to the default record.
- Change made: Persist the selected tune ID per edition and restore it on startup, while validating the saved book and falling back to the default tune when storage is absent, malformed, or stale.
- Validation performed: Browser selected 2025 tune `26 Samaria`, confirmed its result button was pressed, reloaded the app, and confirmed `26 — Samaria` remained selected; browser console warnings/errors were empty. Production build passed after the change.
- Commit: Cycle 9 commit in Git history — Restore the selected tune on reload.
- Remaining opportunities/blockers: Reassess source-comparison messaging, review-queue failure feedback, playback feedback, and responsive behavior; no blocker currently.

## Cycle 10 — Surface review-queue failures

- Problem identified: A failed `human-review-queue.json` request was silently treated as an empty queue, which could make source-review status look complete when the review metadata was actually unavailable.
- Change made: Track review-queue load failure separately and show a scoped status message for non-structured source records while leaving corpus, coverage, and score data usable.
- Validation performed: A controlled local 503 for the review queue produced the accessible `Review status unavailable.` status while `80 shown · 576 source records` and the selected tune remained intact; the normal local app showed no status banner and no browser console warnings/errors. Production build passed after the change.
- Commit: Cycle 10 commit in Git history — Surface review-queue failures.
- Remaining opportunities/blockers: Reassess source-comparison interaction, playback feedback, and responsive behavior; no blocker currently.

## Cycle 11 — Keep the selected tune visible in capped lists

- Problem identified: Unfiltered sections display at most 80 rows; clearing a search for a tune beyond that window caused the selection-sync effect to replace the selected detail with the first visible tune.
- Change made: Keep the current selected tune as the final row when it falls outside the 80-row unfiltered window, preserving the cap and the existing filtered-search synchronization behavior.
- Validation performed: Browser reproduced the reset with 2025 source record `81b Windlesham` before the change; afterward, clearing the search kept `81b — Windlesham` selected, visible, and `aria-pressed="true"` in both Library and Sources (`80 shown`); browser console warnings/errors remained empty.
- Commit: Cycle 11 commit in Git history — Keep the selected tune visible in capped lists.
- Remaining opportunities/blockers: Reassess source-comparison interaction, playback feedback, and responsive behavior; the concurrent source-comparison task remains active.

## Cycle 12 — Retry review-queue loading in place

- Problem identified: When review metadata failed to load, the status message required a full page reload even though the rest of the atlas remained usable.
- Change made: Added a focused `Retry` action that re-fetches only the human-review queue and clears the unavailable status after a successful response.
- Validation performed: A controlled local proxy returned 503 on the first queue request; the browser showed the accessible unavailable status and `Retry` button while preserving `81b — Windlesham`. Clicking `Retry` succeeded on the next request, removed the warning, and restored the review-queue link; browser console warnings/errors remained empty. Production build passed.
- Commit: Cycle 12 commit in Git history — Retry review-queue loading in place.
- Remaining opportunities/blockers: Reassess source-comparison interaction, playback feedback, and responsive behavior; the concurrent source-faithful worker remains active.

## Cycle 13 — Scope review warnings to recorded coverage

- Problem identified: The review-queue failure banner used an undefined-coverage check that could classify ordinary records from another edition as source-review records.
- Change made: Require an actual coverage record before showing the unavailable review-status banner; structured records remain unaffected while non-structured source records retain the warning and retry action.
- Validation performed: With a controlled 503 queue response, Sacred Harp 1991 Library/New Britain showed no review warning, while Sacred Harp 2025 Sources/Windlesham still showed the warning and `Retry`; both selected records remained usable and browser console warnings/errors stayed empty. Production build passed.
- Commit: Cycle 13 commit in Git history — Scope review warnings to recorded coverage.
- Remaining opportunities/blockers: Reassess source-comparison interaction, playback feedback, and responsive behavior; the concurrent source-faithful worker remains active.

## Cycle 14 — Reset source-scan fallback across editions

- Problem identified: Source-scan image failures were reset when the tune changed, but not when the same tune switched to an edition with a different image URL; a prior failure could therefore hide the new edition's source image.
- Change made: Reset the source-scan fallback state when either the selected tune or its edition-specific image URL changes.
- Validation performed: Browser switched the selected `26 — Samaria` tune between Sacred Harp 1991 and Sacred Harp 2025 at the mobile breakpoint with no console warnings/errors; the production build passed.
- Commit: Cycle 14 commit in Git history — Reset source-scan fallback across editions.
- Remaining opportunities/blockers: Reassess source-comparison interaction, playback feedback, and responsive behavior; the concurrent source-faithful worker remains active.

## Cycle 15 — Announce transposition changes

- Problem identified: Choosing a target key updated the rendered score and visible transposition note, but the change was not explicitly announced to assistive technology.
- Change made: Marked the dynamic transposition note as an atomic polite status so target-key changes are announced without changing the visual presentation.
- Validation performed: Browser selected `G minor` for `366 — Bremen` and confirmed `Transposed +1 semitone from F# minor` exposed `role="status"`, `aria-live="polite"`, and `aria-atomic="true"`; browser console warnings/errors remained empty. Production build and data/transposition/playback validators passed.
- Commit: Cycle 15 commit in Git history — Announce transposition changes.
- Remaining opportunities/blockers: Reassess source-comparison interaction, playback feedback, and responsive behavior; the concurrent source-faithful worker remains active.

## Cycle 16 — Distinguish recording-source links

- Problem identified: Records with multiple recording-source pages exposed identical `Open recording source` link names, making the destinations ambiguous to screen-reader users.
- Change made: Added the source hostname to each recording link's accessible name while preserving the existing visible link text and layout.
- Validation performed: Browser inspection of `366 — Bremen` exposed distinct labels for `sacredharp.com` and `archive.org`; page identity remained correct, the rendered view was unchanged, and browser console warnings/errors stayed empty. Production build passed.
- Commit: Cycle 16 commit in Git history — Distinguish recording-source links.
- Remaining opportunities/blockers: Reassess source-comparison disclosure semantics, playback feedback, and responsive behavior; the concurrent source-faithful worker remains active.

## Cycle 17 — Distinguish source-record links

- Problem identified: Records with several authoritative source URLs exposed identical `Open source record` link names, including multiple links from the same host.
- Change made: Added the full source destination path to each source-record link's accessible name while preserving the existing visible text and layout.
- Validation performed: Browser inspection of `366 — Bremen` exposed four unique source-record labels for the edition index, source page, page image, and page route; page identity remained correct and browser console warnings/errors stayed empty. Production build passed.
- Commit: Cycle 17 commit in Git history — Distinguish source-record links.
- Remaining opportunities/blockers: Reassess source-comparison disclosure semantics, playback feedback, and responsive behavior; the concurrent source-faithful worker remains active.

## Cycle 18 — Retry the corpus load in place

- Problem identified: A failed initial `corpus.json` request left the atlas on an error screen that required a full page reload, unlike the recoverable score and review-queue states.
- Change made: Added a cancellable corpus-fetch attempt state and an accessible `Retry loading` action that re-fetches the corpus without reloading the page.
- Validation performed: A controlled local proxy returned 503 for the first corpus request; the browser showed the alert and retry control, then recovered to the atlas after clicking it. The normal local path showed the atlas with no alert or console warnings/errors.
- Commit: Cycle 18 commit in Git history — Retry the corpus load in place.
- Remaining opportunities/blockers: Reassess source-comparison disclosure semantics, playback feedback, and responsive behavior; the concurrent source-faithful worker remains active.

## Cycle 19 — Name the source-preservation action accurately

- Problem identified: The detail-header info control was announced as `Tune details`, although activating it only showed a source-preservation toast.
- Change made: Renamed the control's accessible label to `Show source preservation note` so its name matches the action and resulting feedback.
- Validation performed: Browser confirmed the new accessible button name, confirmed the old name was absent, and observed the source-preservation status toast after activation; page identity remained correct and browser console warnings/errors stayed empty.
- Commit: Cycle 19 commit in Git history — Name the source-preservation action accurately.
- Remaining opportunities/blockers: Reassess source-comparison disclosure semantics, playback feedback, and responsive behavior; the concurrent source-faithful worker remains active.

## Cycle 20 — Keep the latest toast visible

- Problem identified: Every toast scheduled an independent dismissal timer, allowing an earlier notification to clear a newer notification before the newer message had been visible for its full duration.
- Change made: Track one toast timer and cancel it before scheduling the latest notification's dismissal.
- Validation performed: Browser activated the source-preservation action twice with a 1.5-second gap; the latest toast remained visible after the first timer would have expired and disappeared only after the replacement timer elapsed. Page identity remained correct and browser console warnings/errors stayed empty.
- Commit: Cycle 20 commit in Git history — Keep the latest toast visible.
- Remaining opportunities/blockers: Reassess source-comparison disclosure semantics, playback feedback, and responsive behavior; the concurrent source-faithful worker remains active.

## Cycle 21 — Announce the initial loading state

- Problem identified: The initial `Loading the local atlas…` screen had no live-region semantics, so assistive technology could not reliably announce that the corpus was still loading.
- Change made: Marked the loading screen as a polite status region while leaving the error screen's alert semantics and retry path unchanged.
- Validation performed: A controlled local proxy delayed the corpus response; the browser exposed `Loading the local atlas…` as one status region while the request was pending, then replaced it with the atlas once loaded. Browser console warnings/errors remained empty.
- Commit: Cycle 21 commit in Git history — Announce the initial loading state.
- Remaining opportunities/blockers: Reassess source-comparison disclosure semantics, playback feedback, and responsive behavior; the concurrent source-faithful worker remains active.

## Cycle 22 — Keep playback aligned with key changes

- Problem identified: Changing the target key while playback was active updated the rendered notation but left already-scheduled audio playing at the previous transposition.
- Change made: Stop active playback when the target key is selected, nudged, or the entered source key changes, so audio never claims to match a different visible key.
- Validation performed: Browser started playback for `366 — Bremen`, selected `G minor`, and confirmed the control returned from `Stop` to `Play song` while the note reported `Transposed +1 semitone from F# minor`; browser console warnings/errors remained empty.
- Commit: Cycle 22 commit in Git history — Keep playback aligned with key changes.
- Remaining opportunities/blockers: Reassess source-comparison disclosure semantics, playback feedback, and responsive behavior; the concurrent source-faithful worker remains active.

## Cycle 23 — Announce lazy score loading

- Problem identified: The disabled `Loading…` playback control showed that a structured score was pending, but assistive technology had no live status for the lazy score request.
- Change made: Added a visually hidden polite status while a real structured score reference is loading, leaving the existing retry alert and loaded-state messaging unchanged.
- Validation performed: Browser opened the persisted `366 — Bremen` draft and observed `Loading the structured score…` in a status region while the score was pending; after loading, the status disappeared and `Play song` became available.
- Commit: Cycle 23 commit in Git history — Announce lazy score loading.
- Remaining opportunities/blockers: Reassess source-comparison disclosure semantics and responsive behavior; the concurrent source-faithful worker remains active.

## Cycle 24 — Explain playback interruption on key changes

- Problem identified: Playback correctly stopped when a tune or key changed, but the reason was silent for assistive-technology users and unclear when focus moved to the new control state.
- Change made: Added a polite live status for interruption reasons on tune, source-key, and target-key changes; ordinary manual Stop and natural playback completion remain quiet, and starting playback clears the notice.
- Validation performed: Browser played `366 — Bremen`, selected `G minor`, confirmed the control returned to `Play song`, retained the `Transposed +1 semitone from F# minor` status, and exposed `Playback stopped because the target key changed.`; a subsequent manual Stop produced no new interruption notice. Playback/transposition validators and production build passed.
- Commit: Cycle 24 commit in Git history — Explain playback interruption on key changes.
- Remaining opportunities/blockers: Reassess source-comparison disclosure semantics and responsive behavior; the concurrent source-faithful worker remains active.
