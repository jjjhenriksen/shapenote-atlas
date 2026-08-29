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

## Cycle 25 — Reveal source-aware search

- Problem identified: The search already matched source URLs and coverage metadata, but its visible placeholder only described tune, page, and first-line searches.
- Change made: Updated the search prompt to include sources, aligning visible discovery guidance with the implemented source-aware search behavior.
- Validation performed: Browser exposed `Search tunes, pages, first lines, or sources` as the placeholder; searching `366-bremen` produced one matching row for `366 — Bremen`. Production build passed.
- Commit: Cycle 25 commit in Git history — Reveal source-aware search.
- Remaining opportunities/blockers: Reassess source-comparison disclosure semantics and responsive behavior; the concurrent source-faithful worker remains active.

## Cycle 26 — Mark the current navigation page

- Problem identified: The section controls exposed toggle state with `aria-pressed`, but the primary navigation did not identify which page was current to assistive technology.
- Change made: Added `aria-current="page"` to the active Library, Practice, or Sources control while retaining the existing pressed-state semantics and visual navigation.
- Validation performed: Browser confirmed Library started with `aria-current="page"`; after switching to Practice, Library cleared it and Practice reported it while the visible section changed to Practice. Production build and data validation passed.
- Commit: Cycle 26 commit in Git history — Mark the current navigation page.
- Remaining opportunities/blockers: Reassess source-comparison disclosure semantics and responsive behavior; the concurrent source-faithful worker remains active.

## Cycle 27 — Ignore stale review-queue responses

- Problem identified: A slow human-review-queue request from before a retry could resolve afterward and overwrite the newer queue or error state.
- Change made: Added effect cancellation guards so only the latest review-queue request can update state; the existing retry behavior and failure message remain unchanged.
- Validation performed: Browser reloaded the review surface on the live local app and retained the expected source-comparison state; production build and data validation passed, with no diff whitespace errors.
- Commit: Cycle 27 commit in Git history — Ignore stale review-queue responses.
- Remaining opportunities/blockers: The source-comparison disclosure semantic fix remains part of the shared uncommitted panel work and is intentionally excluded from this focused commit; the concurrent source-faithful worker remains active.

## Cycle 28 — Restore fallback-card typography

- Problem identified: The source-page fallback card referenced an undefined `--display` font variable, causing its heading to fall back to 14px body text.
- Change made: Reused the atlas's existing `--serif` display token so the fallback heading keeps its intended 17px weight and line-height without adding a new font family.
- Validation performed: Browser rendered the Sacred Harp Tunes fallback card and reported `Georgia, serif`, 17px, bold, and 21.25px line-height with no horizontal overflow; production build passed.
- Commit: Cycle 28 commit in Git history — Restore fallback-card typography.
- Remaining opportunities/blockers: The source-comparison disclosure semantic fix remains part of the shared uncommitted panel work and is intentionally excluded from this focused commit; source-faithful artifact work remains coordinated separately.

## Cycle 29 — Show focus on semantic disclosures

- Problem identified: The source-comparison disclosure now exposes a button role, but the global focus rule only covered native buttons, leaving keyboard focus visually ambiguous.
- Change made: Extended the existing focus-visible selector to role buttons so semantic disclosures receive the same two-pixel teal focus treatment as native controls.
- Validation performed: Browser focused the live source-comparison disclosure with the keyboard and reported `:focus-visible`, a solid two-pixel outline, and no console warnings or errors; production build passed.
- Commit: Cycle 29 commit in Git history — Show focus on semantic disclosures.
- Remaining opportunities/blockers: The source-comparison panel content and review-view edits remain shared uncommitted work and are intentionally excluded from this focused commit; source-faithful artifact work remains coordinated separately.

## Cycle 30 — Defer source-scan image loading

- Problem identified: Existing source-page scans could load eagerly even though they sit below the primary tune and score details, adding unnecessary initial image work on source-only records.
- Change made: Marked the existing source-scan image as lazy-loaded while preserving its source URL, alt text, fallback behavior, and authoritative link.
- Validation performed: Browser rendered the Shenandoah source card with `loading="lazy"`, the expected accessible alt text, no horizontal overflow, and no console warnings or errors; production build passed.
- Commit: Cycle 30 commit in Git history — Defer source-scan image loading.
- Remaining opportunities/blockers: The shared source-comparison panel and review-view edits remain unstaged and protected; source-faithful artifact work remains coordinated separately.

## Cycle 31 — Use current-page semantics for atlas navigation

- Problem identified: The Library, Practice, and Sources controls are page navigation, but they also exposed `aria-pressed`, which describes a toggle control rather than the current page.
- Change made: Kept the existing `aria-current="page"` indication and removed the conflicting pressed-state attribute from the primary navigation controls.
- Validation performed: Browser confirmed that Library initially exposes `aria-current="page"`, Sources receives it after navigation, no primary navigation control exposes `aria-pressed`, and browser console warnings/errors remained empty. Production build and diff checks passed.
- Commit: `1026aea` — Use current-page semantics for atlas navigation.
- Remaining opportunities/blockers: The shared source-comparison panel and review-view edits remain unstaged and protected; the source-faithful worker remains active with comparison artifacts still fail-closed.

## Cycle 32 — Restore mobile reading width

- Problem identified: Later app-shell rules overrode the earlier mobile gutters, leaving the results column at 13px and the detail column at 34px horizontal padding on a 390px viewport.
- Change made: Added a final mobile breakpoint override that restores the intended 20px/11px results spacing and 25px/16px/24px detail spacing, without changing desktop layout.
- Validation performed: Browser measured the corrected mobile paddings at 390px with no horizontal overflow or console warnings/errors; a fresh 1280px tab retained the existing desktop paddings. Production build and diff checks passed.
- Commit: Cycle 32 commit in Git history — Restore mobile reading width.
- Remaining opportunities/blockers: The shared source-comparison and shape-review UI changes remain unstaged and protected; the source-faithful worker remains active with fail-closed comparison artifacts.

## Cycle 33 — Name the theme action clearly

- Problem identified: The theme button displayed the next mode (`Light` or `Dark`) while `aria-pressed` described a different current-state meaning, creating an ambiguous announcement for assistive technology.
- Change made: Removed the conflicting pressed-state attribute and gave the button an explicit action label, `Switch to light mode` or `Switch to dark mode`, while retaining the concise visible label.
- Validation performed: Browser confirmed the dark-to-light and light-to-dark transitions, matching accessible action labels, no pressed-state attribute, and no console warnings/errors. Production build and diff checks passed.
- Commit: Cycle 33 commit in Git history — Name the theme action clearly.
- Remaining opportunities/blockers: The shared source-comparison and shape-review UI changes remain unstaged and protected; the source-faithful worker remains active with fail-closed comparison artifacts.

## Cycle 34 — Expose the shape legend as a named group

- Problem identified: The shape legend carried an `aria-label` on a generic `div`, so its “Four-shape solfege reference” label was not reliably exposed to assistive technology.
- Change made: Added `role="group"` to the existing labeled legend container without changing its content or visual layout.
- Validation performed: Browser found the legend as a named group, confirmed its text and rendered width were unchanged, and reported no console warnings/errors. Production build and diff checks passed.
- Commit: Cycle 34 commit in Git history — Expose the shape legend as a named group.
- Remaining opportunities/blockers: The shared source-comparison and shape-review UI changes remain unstaged and protected; the source-faithful worker remains active with fail-closed comparison artifacts.

## Cycle 35 — Announce selected tunes

- Problem identified: Choosing a result updated the detail column visually, but there was no polite live status naming the newly selected tune for keyboard and screen-reader users.
- Change made: Added a visually hidden atomic status that announces `Selected tune: …` whenever the current tune changes.
- Validation performed: Browser confirmed the persisted tune is announced on load and the announcement updates when selecting another result; the status remains visually hidden, the detail view remains synchronized, and browser console warnings/errors stayed empty. Production build and diff checks passed.
- Commit: Cycle 35 commit in Git history — Announce selected tunes.
- Remaining opportunities/blockers: The shared source-comparison and shape-review UI changes remain unstaged and protected; the source-faithful worker remains active with fail-closed comparison artifacts.

## Cycle 36 — Add a keyboard skip link

- Problem identified: The atlas presents a long result list before the selected-tune details, but keyboard users had no direct way to bypass that list.
- Change made: Added a focus-visible “Skip to selected tune details” link and a focusable `selected-tune-details` target for the detail surface.
- Validation performed: Browser confirmed the link is the first keyboard focus target, becomes visible with the existing two-pixel focus outline, and moves focus to the selected-tune section when activated; layout remained within the viewport and browser console warnings/errors stayed empty. Production build and diff checks passed.
- Commit: Cycle 36 commit in Git history — Add a keyboard skip link.
- Remaining opportunities/blockers: The shared source-comparison and shape-review UI changes remain unstaged and protected; the source-faithful worker remains active with fail-closed comparison artifacts.

## Cycle 37 — Make coverage details accessible

- Problem identified: The header exposed only the compact transposable/tune count to the page, while the useful exact-score, reference-witness, review-draft, and key-unknown breakdown depended on a hover-only `title` tooltip.
- Change made: Kept the compact visual summary unchanged and added a visually hidden accessible reading-order version of the full coverage breakdown.
- Validation performed: A fresh browser tab preserved the exact visual text and dimensions, exposed the complete breakdown in the accessibility snapshot, and reported no console warnings/errors. Production build and diff checks passed.
- Commit: Cycle 37 commit in Git history — Make coverage details accessible.
- Remaining opportunities/blockers: The shared source-comparison and shape-review UI changes remain unstaged and protected; the source-faithful worker remains active with fail-closed comparison artifacts.

## Cycle 38 — Reconcile the autonomous Sacred Harp 2025 batch

- Problem identified: The next source batch had usable OMR derivatives and rendered witnesses, but direct comparison still found edition, measure, watermark, lyric, rhythm, or shape uncertainty; the generated next-action text also incorrectly suggested a human handoff despite the autonomous fail-closed policy.
- Change made: Reconciled and retained autonomous blocked records for 130 The Old Graveyard, 184 And Jesus Crucified, 188 Ephesus, and 231 Seiler alongside the existing 115 Holbrook and 116 Hooper audits. Updated the deterministic batch generator and the affected audit records so every blocked outcome explicitly requires clean authorized structured source evidence, never manual review. Rebuilt the source-comparison ledger and review queue without promoting any derivative.
- Validation performed: Six autonomous blocked MXLs contain four named parts and derived four-shape noteheads; source hashes and candidate checksums validate. `validate_data.py`, `validate_transposition.py`, `validate_playback.py`, `validate_shape_review_drafts.py`, `validate_transcription_images.py`, `npm run build`, `git diff --check`, and an explicit ledger/queue integrity audit all passed. The ledger reports 40 comparison records, 0 errors, and 0 safe promotions; the review queue reports 40 source comparisons and 0 safe promotions.
- Commit: Autonomous source-batch reconciliation and fail-closed wording (recorded in Git history).
- Remaining opportunities/blockers: No 2025 record was safe to promote from these independent OMR witnesses. Continue with the next clearest disjoint source candidate, preserving the zero-promotion gate and the separate uncommitted source-comparison UI work.

## Cycle 39 — Extend autonomous source comparison coverage

- Problem identified: Three additional retained 2025 pages had close title/text-family and structural OMR witnesses, but similarity alone could not establish exact edition, note, rhythm, lyric, or four-shape fidelity.
- Change made: Added 213b Trembling Spirit, 263 Every Grace, and 367 Nassau to the deterministic autonomous batch. Each retains the untouched source hash, corrected visible metadata, four-part MusicXML derivative, derived shape hypotheses, rendered QA, and precise autonomous blocking evidence; none entered the authoritative corpus.
- Validation performed: The rebuilt ledger reports 43 comparison records, 11 autonomous blocks, 0 errors, and 0 safe promotions. The review queue was rebuilt with 43 source comparisons and 0 safe promotions. Data, transposition, playback, shape-review, transcription-image, production-build, diff, and batch-integrity checks all passed.
- Commit: Extend autonomous source comparison coverage (recorded in Git history).
- Remaining opportunities/blockers: The 90-record 2025 source scope still has no newly promoted record from this batch. Continue with the next strongest disjoint candidate and preserve the zero-promotion gate.

## Cycle 40 — Apply event-scoped blocking to the next source batch

- Problem identified: The previous autonomous generator’s default blocking label bundled lyric and shape uncertainty together, which could overstate blockers under the revised delivery policy.
- Change made: Evaluated 255 Mechanicville and 256 Northampton against their retained source scans and candidate witnesses. Kept both fail-closed because their candidate/source measure structures diverge and watermark overlap leaves specific note intersections unresolved, while removing absent lyrics as an independent blocker. Corrected their provenance paths and checksums to reference the authoritative retained source copies, updated the generator’s future blocked-action label to unresolved source events, and rebuilt the ledger/queue.
- Validation performed: Ledger rebuild completed with 47 comparison records, 15 autonomous blocks, 0 errors, and 0 safe promotions. The review queue and candidate reconciliation rebuilt successfully; data, transposition, playback, shape-review, transcription-image, production-build, and diff checks passed. Both corrected drafts retain four parts and source-linked MusicXML evidence; neither was promoted because unresolved events remain.
- Commit: Apply event-scoped blocking to the next source batch (recorded in Git history).
- Remaining opportunities/blockers: The revised gate is ready for the next strongest candidate. Continue attempting visible-note correction and promote only an artifact with complete direct event support; otherwise record only the unresolved events and proceed.

## Cycle 41 — Preserve usable visible notation while blocking unresolved events

- Problem identified: The next retained source page, 571 Hamrick, had a four-part source-scan OMR with matching 13-measure structure, but its event groupings were not complete enough to establish every note and rhythm directly from the scan; the watermark also crossed only particular source intersections.
- Change made: Corrected the visible B-flat-major key, 3/4 meter, four-part labels, and derived four-shape noteheads in a provenance-bearing MusicXML derivative. Kept the record autonomous-blocked for the listed non-full measures and watermark-obscured intersections, without treating omitted lyrics as a completion requirement or blocking unaffected events by association.
- Validation performed: Per-record source and candidate hashes, four-part/13-measure structure, 115 pitched events, and 115 derived shape tags were checked. Ledger and queue rebuilds passed with 47 source comparisons, 0 ledger errors, and 0 safe promotions. Data, transposition, playback, shape-review, transcription-image, production-build, and diff checks all passed.
- Commit: Preserve usable visible notation while blocking unresolved events (recorded in Git history).
- Remaining opportunities/blockers: No new record is safe to promote until every event in its proposed authoritative artifact has direct source support. Continue with the next strongest candidate and keep partial/block evidence event-specific.

## Cycle 42 — Reconcile the next source-derived delivery batch

- Problem identified: The next disjoint retained pages, Hurricane Creek (459), Morel (463), and Warsaw (254), had matching four-part source structures and usable source-scan OMR, but their duration audits still left specific event groups unsupported. Related public witnesses could not establish exact 2025 edition identity or repair those events.
- Change made: Preserved source-derived four-part MusicXML drafts for all three pages, corrected the source-visible key/mode and meter, added derived four-shape noteheads, and recorded provenance. Tightened the blocking evidence to exact failing measure sets: 459 by part, 463 by part, and Warsaw P1-P4 measures 1-17. No unsupported pitch, rhythm, lyric, or watermark-obscured event was guessed or promoted; omitted lyrics remain optional where notation is usable.
- Validation performed: The source-comparison ledger rebuilt with 51 records, 19 autonomous blocks, 0 errors, and 0 safe promotions. The review queue rebuilt with 51 source comparisons and 0 safe promotions; candidate reconciliation remained fail-closed at 94 blocked candidates. `validate_data.py`, `validate_transposition.py`, `validate_playback.py`, `validate_shape_review_drafts.py`, `validate_transcription_images.py`, `npm run build`, and `git diff --check` all passed. The three new drafts contain four parts, source-linked metadata, and 127, 192, and 97 pitched events respectively, each with matching derived shape tags.
- Commit: Reconcile the next source-derived delivery batch (this cycle).
- Remaining opportunities/blockers: Zero-promotion remains correct. Continue to the next strongest disjoint source page and attempt complete visible-event correction; if any event remains unsupported, preserve the usable partial draft and record only its precise blockers.

## Cycle 43 — Deliver a shape-complete exact 2025 source score

- Problem identified: Devotion (50t) had an exact 2025 MusicXML source already retained in the score manifest and matching the immutable scan, but only 82 of its 156 pitched events carried explicit four-shape notehead tags. The old scan OMR was incomplete and did not provide a safer replacement.
- Change made: Preserved the exact source archive and created a deterministic provenance-bearing derivative that adds the C-major four-shape encoding to all 156 source pitches without changing pitch, rhythm, part structure, repeats, or endings. Lyrics remain omitted because the notation is usable and no event alignment is fabricated. The derivative is recorded as autonomously verified; `safeToPromote` remains false because the authoritative 2025 source is already present and comparison records do not self-authorize corpus promotion.
- Validation performed: Direct visual inspection of the retained scan and MuseScore-rendered exact source confirmed the DEVOTION L.M. header, C major, 4/4, four parts, note/rhythm layout, repeats, and endings. The derivative archive passed integrity checks with 4 parts, 17 measures per part, 156 pitched events, and 156 allowed shape tags. The ledger rebuilt with 52 records, 19 autonomous blocks, 1 autonomously verified source score, 0 errors, and 0 safe promotions. Queue/reconciliation, data, transposition, playback, shape-review, transcription-image, production-build, and diff checks all passed.
- Commit: Deliver a shape-complete exact 2025 source score (this cycle).
- Remaining opportunities/blockers: One genuinely source-faithful structured record is now delivered outside the promotion gate. Continue auditing the next retained 2025 pages for another exact structured source; retain zero promotion for OMR-only or unresolved candidates.

## Cycle 44 — Block incomplete Humility OMR with event-level evidence

- Problem identified: Humility (347b) was a short remaining source page with a retained four-part OMR, but the draft contained only 10/19/17/7 note events and blank measures where the immutable scan visibly contains music. Its duration grouping also failed across named measures.
- Change made: Created a provenance-bearing four-part MusicXML derivative with the source-visible B-flat-major key, 3/2 meter, and derived four-shape tags for all 52 detected pitched events. Kept the derivative outside the authoritative corpus and recorded precise missing measures (P1 m4,m6; P2 m1,m5,m6; P3 m4; P4 m0,m1,m5,m6), duration-failing groups, and only the watermark-intersected source regions as blockers. No missing music, lyrics, or obscured events were guessed.
- Validation performed: The derivative archive passed integrity checks with 4 parts, 8 measures per part, 52 pitched events, and 52 allowed shape tags. The source-comparison ledger rebuilt with 53 records, 20 autonomous blocks, 1 autonomously verified source score, 0 errors, and 0 safe promotions. Queue/reconciliation, data, transposition, playback, transcription-image, production-build, and diff checks all passed.
- Commit: Block incomplete Humility OMR with event-level evidence (this cycle).
- Remaining opportunities/blockers: The remaining 2025 queue is predominantly OMR-only with no direct structured witness. Continue one disjoint page at a time, promoting only an exact source-supported score and otherwise preserving precise autonomous blocks.

## Cycle 45 — Block collapsed Thy Strength OMR with event-level evidence

- Problem identified: Thy Strength (469) had a legible eight-measure source page and retained OMR, but the OMR left P1 m1, P2 m1,m3,m6, and P4 m1,m3,m6 blank and collapsed visible material into oversized clusters, especially P1/P2/P3 m5.
- Change made: Created a provenance-bearing four-part MusicXML derivative with source D-major key, 3/2 meter, and derived four-shape tags for all 96 detected pitched events. Recorded the blank measures, duration-failing groups, collapsed clusters, and only the watermark-intersected regions as blockers. No missing source music, lyrics, or obscured event was guessed or promoted.
- Validation performed: The derivative archive passed integrity checks with 4 parts, 8 measures per part, 96 pitched events, and 96 allowed shape tags. The source-comparison ledger rebuilt with 54 records, 21 autonomous blocks, 1 autonomously verified source score, 0 errors, and 0 safe promotions. Queue/reconciliation, data, transposition, playback, transcription-image, production-build, and diff checks all passed.
- Commit: Block collapsed Thy Strength OMR with event-level evidence (this cycle).
- Remaining opportunities/blockers: No additional exact structured 2025 source is currently retained beyond Devotion; continue auditing the clearest remaining scan/OMR page while keeping all unresolved events outside the authoritative corpus.

## Cycle 47 — Block incomplete Troubles Over OMR with event-level evidence

- Problem identified: Troubles Over (80t) had a clear 13-measure G-minor 2/4 source scan, but the retained OMR left P1 m2, P2 m3, P3 m2,m3,m8,m10,m12,m13, and P4 m2,m8 blank and produced broad duration failures and oversized clusters.
- Change made: Created a provenance-bearing four-part derivative with source G-minor key, 2/4 meter, and derived four-shape tags for all 81 detected pitched events. Recorded the exact blank measures, duration-failing part ranges, clusters, and only watermark-intersected regions as blockers. No missing source music or lyrics was fabricated and nothing was promoted.
- Validation performed: The derivative archive passed integrity checks with 4 parts, 13 measures per part, 81 pitched events, and 81 allowed shape tags. The source-comparison ledger rebuilt with 56 records, 23 autonomous blocks, 1 autonomously verified source score, 0 errors, and 0 safe promotions. Queue/reconciliation, data, transposition, playback, transcription-image, production-build, and diff checks all passed.
- Commit: Block incomplete Troubles Over OMR with event-level evidence (this cycle).
- Remaining opportunities/blockers: The queue remains fail-closed at 120 review-now records; exact structured-source coverage is limited to the verified Devotion record. Continue autonomous scan/OMR comparison on the clearest remaining page.

## Cycle 48 — Block Iowa OMR key and duration mismatches

- Problem identified: Iowa (295) was a short, four-part candidate with six measures per part and no blank measures, but its retained OMR detected G major while the scan prints E minor and failed the 6/4 duration audit across every part.
- Change made: Created a provenance-bearing derivative with source E-minor key, 6/4 meter, and derived four-shape tags for all 129 detected pitched events. Preserved the exact OMR event stream and recorded the all-part duration failures plus only the watermark-intersected middle-system events as blockers; no rhythm, pitch, or lyric was invented.
- Validation performed: The derivative archive passed integrity checks with 4 parts, 6 measures per part, 129 pitched events, and 129 allowed shape tags. The source-comparison ledger rebuilt with 57 records, 24 autonomous blocks, 1 autonomously verified source score, 0 errors, and 0 safe promotions. Queue/reconciliation, data, transposition, playback, transcription-image, production-build, and diff checks all passed.
- Commit: Block Iowa OMR key and duration mismatches (this cycle).
- Remaining opportunities/blockers: The 120-record review queue remains fail-closed; Devotion is the only exact structured source verified in this run. Continue with the next strongest legible scan/OMR candidate.

## Cycle 46 — Block mismatched Lloyd OMR with event-level evidence

- Problem identified: Lloyd (503) had a legible eight-measure source page, but its retained OMR used 3/4 instead of the source-visible 3/2, left P2 m1 and P4 m1 blank, and collapsed visible material into oversized P2 m3-5 groups.
- Change made: Created a provenance-bearing four-part derivative with source F-major key, 3/2 meter, and derived four-shape tags for all 54 detected pitched events. Recorded the exact blank measure, pervasive duration failures, collapsed clusters, and only the watermark-intersected regions as blockers. No missing source music or lyrics was fabricated and nothing was promoted.
- Validation performed: The derivative archive passed integrity checks with 4 parts, 8 measures per part, 54 pitched events, and 54 allowed shape tags. The source-comparison ledger rebuilt with 55 records, 22 autonomous blocks, 1 autonomously verified source score, 0 errors, and 0 safe promotions. Queue/reconciliation, data, transposition, playback, transcription-image, production-build, and diff checks all passed.
- Commit: Block mismatched Lloyd OMR with event-level evidence (this cycle).
- Remaining opportunities/blockers: The remaining queue is now 120 review-now records, mostly OMR-only pages without exact structured witnesses. Continue selecting short, legible scans and keep every unresolved event outside the authoritative corpus.

## Cycle 49 — Preserve Parwich evidence and repair comparison integrity

- Problem identified: Parwich (484b) was the next legible four-part candidate, but its retained OMR rhythm/event grouping could not establish every source event even though the scan visibly has eight 4/4 measures per part. The existing exact-source Converse (55) comparison also lacked the generic image/input witness fields required by the ledger validator.
- Change made: Created a provenance-bearing Parwich derivative with the source-visible A-minor key, 4/4 meter, four-part structure, and derived four-shape tags for all 156 retained pitched events. Recorded only the named duration-unsupported measure groups and watermark-intersected regions as blockers; omitted lyrics without treating them as an independent blocker. Repaired the Converse comparison generator to expose its immutable rendered source and exact structured source through the ledger’s standard witness fields.
- Validation performed: Parwich retains 4 parts, 8 measures per part, 156 pitched events, and 156 shape tags with `safeToPromote=false`. The rebuilt ledger now reports 59 records, 25 autonomous blocks, 2 autonomously verified source scores, 0 errors, and 0 safe promotions. No corpus record was promoted.
- Commit: Preserve Parwich evidence and repair comparison integrity (this cycle).
- Remaining opportunities/blockers: Continue with the next strongest disjoint scan/OMR candidate. Promote only a complete artifact whose every event is directly source-supported; otherwise retain a precise partial/block record and keep the fail-closed gate.

## Cycle 50 — Block Grantville’s conflicting OMR event stream

- Problem identified: Grantville (423t) had a legible four-part C.M. source scan and ten OMR measures per part, but P1 m6 was blank, 26 named part/measure duration totals were unsupported, all four m7 groups were collapsed, and the OMR key metadata conflicted with the source-visible F-sharp minor.
- Change made: Created a provenance-bearing derivative with source F-sharp-minor key/mode, 4/4 meter, four-part structure, and derived four-shape tags for all 166 retained pitched events. Recorded the exact duration failures, blank measure, collapsed groups, conflicting OMR key fields, and only watermark-intersected middle-system events as blockers. Lyrics remain omitted without fabrication and no event was promoted.
- Validation performed: The derivative retains 4 parts, 10 measures per part, 166 pitched events, and 166 allowed shape tags. The source-comparison ledger rebuilt with 60 records, 26 autonomous blocks, 2 autonomously verified source scores, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. MuseScore rendered the derivative’s non-empty pages successfully, and the focused archive/shape/provenance and diff checks passed.
- Commit: Block Grantville’s conflicting OMR event stream (this cycle).
- Remaining opportunities/blockers: Continue to the next strongest disjoint scan/OMR candidate, seeking a fully source-supported event stream rather than treating structural resemblance as completion.

## Cycle 51 — Block Stanton’s incomplete 6/4 event grouping

- Problem identified: Stanton (243) had a clear E-minor 6/4 source scan with four parts and six measures per part, and the OMR matched that coarse structure without blank measures. It nevertheless failed duration totals in the named part/measure groups, omitted the source time signature, and recorded G-major-style key metadata without a mode.
- Change made: Created a provenance-bearing derivative with source E-minor key/mode, 6/4 meter, four-part structure, and derived four-shape tags for all 133 retained pitched events. Recorded exact duration failures, the conflicting key/time metadata, and only watermark-intersected middle-system events as blockers. D.C. source markings remain preserved; lyrics remain optional and omitted without fabrication.
- Validation performed: The derivative retains 4 parts, 6 measures per part, 133 pitched events, and 133 allowed shape tags. The source-comparison ledger rebuilt with 61 records, 27 autonomous blocks, 2 autonomously verified source scores, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. MuseScore rendered the derivative successfully, and focused archive/provenance and diff checks passed.
- Commit: Block Stanton’s incomplete 6/4 event grouping (this cycle).
- Remaining opportunities/blockers: Continue with the next strongest disjoint scan/OMR candidate and promote only a fully source-supported event stream.

## Cycle 52 — Block Pastures Green’s unsupported duration groups

- Problem identified: Pastures Green (499t) had a clear F-sharp-minor C.M. source scan and retained OMR with four parts and ten measures per part, but duration totals failed in 22 exact part/measure groups. The OMR also recorded incomplete/conflicting key metadata against the source-visible F-sharp minor.
- Change made: Created a provenance-bearing derivative with source F-sharp-minor key/mode, 3/4 meter, four-part structure, and derived four-shape tags for all 104 retained pitched events. Recorded the exact duration failures, key-field conflict, and only watermark-intersected middle-system events as blockers. Lyrics remain optional and omitted without fabrication.
- Validation performed: The derivative retains 4 parts, 10 measures per part, 104 pitched events, and 104 allowed shape tags. The source-comparison ledger rebuilt with 62 records, 28 autonomous blocks, 2 autonomously verified source scores, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. MuseScore rendered the derivative successfully, and focused archive/provenance and diff checks passed.
- Commit: Block Pastures Green’s unsupported duration groups (this cycle).
- Remaining opportunities/blockers: Continue autonomous comparison on the next strongest disjoint source page; the gate remains fail-closed until every promoted event is source-supported.

## Cycle 53 — Reconcile and retain Endless Praise exact source delivery

- Problem identified: A concurrent worker produced an exact 2025 Endless Praise (415) structured-source derivative while the OMR comparison passes were running. It needed reconciliation against the immutable PDF/source manifest before being counted, and it must not be confused with an OMR-derived promotion.
- Change made: Preserved the worker’s exact-source derivative and generator. Its source PDF, rendered scan, manifest-listed MusicXML, part/measure structure, event stream, four-shape encoding, provenance, and fail-closed disposition were reconciled without duplicating or relabeling another artifact.
- Validation performed: Direct source/derivative comparison found identical 209-event streams across 4 parts and 17 measures per part; all 209 pitched events carry allowed four-shape tags. The ledger rebuilt with 64 records, 29 autonomous blocks, 3 autonomously verified source scores, 0 errors, and 0 safe promotions. Data and playback validators passed; no corpus record was promoted.
- Commit: Reconcile and retain Endless Praise exact source delivery (this cycle).
- Remaining opportunities/blockers: Continue autonomous comparison on disjoint retained source pages. Keep exact-source deliveries available with provenance, while retaining zero corpus promotion unless explicitly authorized by the repository’s authoritative promotion path.

## Cycle 54 — Block Clayton’s collapsed 3/2 OMR structure

- Problem identified: Clayton (531) had a clear C-major 3/2 source scan, but the retained OMR collapsed the page to seven measures per part, left P1 m6 and P2/P4 m1 blank, and failed the 3-unit duration target in every retained measure.
- Change made: Created a provenance-bearing derivative with source C-major key/mode, 3/2 meter, retained four-part structure, and derived four-shape tags for all 116 detected pitched events. Recorded the source/OMR structure mismatch, exact duration failures, blank source-visible measures, incomplete OMR key/time metadata, and only watermark-intersected middle-system events as blockers. Lyrics remain optional and omitted without fabrication.
- Validation performed: The derivative retains 4 parts, 7 OMR measures per part, 116 pitched events, and 116 allowed shape tags. The source-comparison ledger rebuilt with 65 records, 30 autonomous blocks, 3 autonomously verified source scores, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. MuseScore rendered the derivative successfully, and focused archive/provenance and diff checks passed.
- Commit: Block Clayton’s collapsed 3/2 OMR structure (this cycle).
- Remaining opportunities/blockers: Continue with the next strongest disjoint source page, seeking a complete directly source-supported event stream.

## Cycle 55 — Block Traveling Pilgrim’s collapsed 2/4 OMR

- Problem identified: Traveling Pilgrim (278b) had a legible G-minor 2/4 source scan, but the retained OMR used 6/4, carried incomplete key metadata, collapsed visibly denser source barlines into ten measures per part, and left P2 m0,m7,m9, P3 m9, and P4 m9 blank. Its duration/event totals failed in the exact groups recorded in the audit.
- Change made: Created a provenance-bearing derivative with source G-minor key/mode, 2/4 meter, retained four-part structure, and derived four-shape tags for all 191 detected pitched events. Recorded only the source/OMR structure and time/key conflicts, exact duration failures, blank source-visible measures, and watermark-intersected middle-system events as blockers. Lyrics remain optional and omitted without fabrication.
- Validation performed: The derivative retains 4 parts, 10 OMR measures per part, 191 pitched events, and 191 allowed shape tags. The source-comparison ledger rebuilt with 66 records, 31 autonomous blocks, 3 autonomously verified source scores, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. MuseScore rendered the derivative successfully, and focused archive/provenance and diff checks passed.
- Commit: Block Traveling Pilgrim’s collapsed 2/4 OMR (this cycle).
- Remaining opportunities/blockers: Continue autonomous comparison on the next strongest disjoint source page, preserving any usable visible notation while keeping unsupported events outside the authoritative corpus.

## Cycle 56 — Block Ragan’s collapsed 4/4 OMR

- Problem identified: Ragan (176t) had a clear F-major 4/4 source scan, but the retained OMR collapsed visibly denser source barlines into seven measures per part, failed duration totals in every part except one retained measure, and left P2 m1,m7, P3 m7, and P4 m1,m4,m7 blank.
- Change made: Created a provenance-bearing derivative with source F-major key/mode, 4/4 meter, retained four-part structure, and derived four-shape tags for all 176 detected pitched events. Recorded exact duration failures, blank source-visible measures, and only watermark-intersected middle-system events as blockers. Lyrics remain optional and omitted without fabrication.
- Validation performed: The derivative retains 4 parts, 7 OMR measures per part, 176 pitched events, and 176 allowed shape tags. The source-comparison ledger rebuilt with 67 records, 32 autonomous blocks, 3 source-verified corrected derivatives, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. MuseScore rendered the derivative successfully, and focused archive/provenance and diff checks passed.
- Reconciliation note: The concurrent exact-source worker’s three raw-source records were tightened to `verified-with-correction-needed` because their raw MusicXML omits some source-visible mode/shape/lyric encoding; their corrected derivatives remain source-verified and no record was promoted.
- Commit: Block Ragan’s collapsed 4/4 OMR (this cycle).
- Remaining opportunities/blockers: Continue autonomous comparison on the next strongest disjoint source page, retaining only directly supported events and preserving all user-owned worker/UI changes.

## Cycle 59 — Block Bremen’s incomplete 3/4 event stream

- Problem identified: Bremen (366) had a clear F-sharp-minor P.M. source scan and matching coarse four-part/15-measure OMR structure, but the OMR failed duration totals in 36 exact part/measure groups, left P1 m1, P3 m6,m15, and P4 m1 blank, and carried inconsistent key metadata against the source.
- Change made: Created a provenance-bearing derivative with source F-sharp-minor key/mode, 3/4 meter, retained four-part structure, and derived four-shape tags for all 154 detected pitched events. Recorded exact duration failures, blank source-visible measures, key-field conflicts, and only watermark-intersected middle-system events as blockers. Lyrics remain optional and omitted without fabrication.
- Validation performed: The derivative retains 4 parts, 15 measures per part, 154 pitched events, and 154 allowed shape tags. The source-comparison ledger rebuilt with 69 records, 34 autonomous blocks, 3 corrected source verifications, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. MuseScore rendered the derivative successfully, and focused archive/provenance and diff checks passed.
- Commit: Block Bremen’s incomplete 3/4 event stream (this cycle).
- Remaining opportunities/blockers: Continue autonomous comparison on the next strongest disjoint source page while preserving the zero-promotion gate.

## Cycle 60 — Block Midnight Hour’s unresolved 4/4 groups

- Problem identified: Midnight Hour (293) had a clear E-minor 4/4 source scan and matching coarse four-part/12-measure structure, but P1 m6, P2 m6,m12, and P3 m12 were blank and duration totals failed in 39 exact part/measure groups. Its OMR key fields were incomplete/inconsistent with the source.
- Change made: Created a provenance-bearing derivative with source E-minor key/mode, 4/4 meter, retained four-part structure, and derived four-shape tags for all 136 detected pitched events. Recorded exact duration failures, blank source-visible measures, key-field conflicts, and only watermark-intersected events as blockers. Lyrics remain optional and omitted without fabrication.
- Validation performed: The derivative retains 4 parts, 12 measures per part, 136 pitched events, and 136 allowed shape tags. The source-comparison ledger rebuilt with 70 records, 35 autonomous blocks, 3 corrected source verifications, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. MuseScore rendered the derivative successfully, and focused archive/provenance and diff checks passed.
- Commit: Block Midnight Hour’s unresolved 4/4 groups (this cycle).
- Remaining opportunities/blockers: Continue with the next strongest disjoint source page under the restored fail-closed gate.

## Cycle 61 — Block Penn’s incomplete first measures

- Problem identified: Penn (501t) had a clear A-major 4/4 source scan and matching four-part/nine-measure OMR structure, but P1/P2/P3 m1 were blank, P4 m1 was partial, and duration totals failed in 24 exact part/measure groups. The OMR key fields also conflicted with the source A-major signature.
- Change made: Created a provenance-bearing derivative with source A-major key/mode, 4/4 meter, retained four-part structure, and derived four-shape tags for all 114 detected pitched events. Recorded exact duration failures, blank/partial source-visible first measures, key-field conflicts, and only watermark-intersected middle-system events as blockers. Lyrics remain optional and omitted without fabrication.
- Validation performed: The derivative retains 4 parts, 9 measures per part, 114 pitched events, and 114 allowed shape tags. The source-comparison ledger rebuilt with 71 records, 36 autonomous blocks, 3 corrected source verifications, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. MuseScore rendered the derivative successfully, and focused archive/provenance and diff checks passed.
- Commit: Block Penn’s incomplete first measures (this cycle).
- Remaining opportunities/blockers: Continue autonomous comparison on the next strongest disjoint source page under the zero-promotion gate.

## Cycle 62 — Block Ester’s incomplete 3/4 event stream

- Problem identified: Ester (37t) had a clear F-major 3/4 source scan and matching coarse four-part/10-measure OMR structure, but P1 m4, P2 m0, P3 m0, and P4 m0,m5 were blank, duration totals failed in 31 exact groups, and the OMR omitted source key metadata.
- Change made: Created a provenance-bearing derivative with source F-major key/mode, 3/4 meter, retained four-part structure, and derived four-shape tags for all 121 detected pitched events. Recorded exact duration failures, blank source-visible measures, missing key metadata, and only watermark-intersected middle-system events as blockers. Lyrics remain optional and omitted without fabrication.
- Validation performed: The derivative retains 4 parts, 10 measures per part, 121 pitched events, and 121 allowed shape tags. The source-comparison ledger rebuilt with 72 records, 37 autonomous blocks, 3 corrected source verifications, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. MuseScore rendered the derivative successfully, and focused archive/provenance and diff checks passed.
- Commit: Block Ester’s incomplete 3/4 event stream (this cycle).
- Remaining opportunities/blockers: Continue autonomous comparison on the next strongest disjoint source page under the fail-closed gate.

## Cycle 64 — Block He Hath Saved Us’ unsupported 2/4 groups

- Problem identified: He Hath Saved Us (219) had a clear A-major 2/4 source scan and matching four-part/13-measure OMR structure, but P2 m10, P3 m1,m13, and P4 m1,m13 were blank, P1 m1 was absent as a source-aligned group, and duration totals failed in 39 exact groups. OMR key fields conflicted with the source A-major signature.
- Change made: Created a provenance-bearing derivative with source A-major key/mode, 2/4 meter, retained four-part structure, and derived four-shape tags for all 104 detected pitched events. Recorded exact duration failures, blank/absent source-visible groups, key-field conflicts, and only watermark-intersected middle-system events as blockers. Lyrics remain optional and omitted without fabrication.
- Validation performed: The derivative retains 4 parts, 13 measures per part, 104 pitched events, and 104 allowed shape tags. The source-comparison ledger rebuilt with 75 records, 40 autonomous blocks, 3 corrected source verifications, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. MuseScore rendered the derivative successfully, and focused archive/provenance and diff checks passed.
- Commit: Block He Hath Saved Us’ unsupported 2/4 groups (this cycle).
- Remaining opportunities/blockers: Continue autonomous comparison on the next strongest disjoint source page under the zero-promotion gate.

## Cycle 63 — Block Warrenton’s unsupported 2/4 groups

- Problem identified: Warrenton (145t) had a clear G-major 2/4 source scan and matching four-part/13-measure OMR structure, but P1 m1, P3 m9,m12,m13, and P4 m13 were blank and duration totals failed in 29 exact part/measure groups. The OMR also omitted source mode and had no key in P4.
- Change made: Created a provenance-bearing derivative with source G-major key/mode, 2/4 meter, retained four-part structure, and derived four-shape tags for all 109 detected pitched events. Recorded exact duration failures, blank source-visible measures, incomplete key metadata, and only watermark-intersected middle-system events as blockers. Lyrics remain optional and omitted without fabrication.
- Validation performed: The derivative retains 4 parts, 13 measures per part, 109 pitched events, and 109 allowed shape tags. The source-comparison ledger rebuilt with 73 records, 38 autonomous blocks, 3 corrected source verifications, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. MuseScore rendered the derivative successfully, and focused archive/provenance and diff checks passed.
- Commit: Block Warrenton’s unsupported 2/4 groups (this cycle).
- Remaining opportunities/blockers: Continue autonomous comparison on the next strongest disjoint source page under the fail-closed gate.

## Cycle 57 — Block Restoration’s collapsed 4/4 OMR

- Problem identified: Restoration (312b) had a legible A-minor 4/4 source scan and a non-empty four-part OMR, but the OMR collapsed visibly denser source barlines into six measures per part and failed duration totals in 22 exact part/measure groups. It also omitted the source key/mode and time signature.
- Change made: Created a provenance-bearing derivative with source A-minor key/mode, 4/4 meter, retained four-part structure, and derived four-shape tags for all 145 detected pitched events. Recorded the source/OMR partition mismatch, exact duration failures, missing source metadata, and only watermark-intersected middle-system events as blockers. Lyrics remain optional and omitted without fabrication.
- Validation performed: The derivative retains 4 parts, 6 OMR measures per part, 145 pitched events, and 145 allowed shape tags. The source-comparison ledger rebuilt with 68 records, 33 autonomous blocks, 3 source-verified corrected derivatives, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates.
- Commit: Block Restoration’s collapsed 4/4 OMR (this cycle).
- Remaining opportunities/blockers: Continue autonomous comparison on the next strongest disjoint source page while preserving the fail-closed promotion gate.

## Cycle 58 — Restore the zero-promotion comparison gate

- Problem identified: A concurrent worker revision temporarily marked Converse (55) `safeToPromote=true` and taught the comparison ledger to permit that self-authorization, which surfaced one unsafe record despite the repository’s fail-closed policy.
- Change made: Restored unconditional rejection of `safeToPromote=true` in source-comparison records, removed the special 55 promotion exception from the 2025 score audit, and changed the Converse generator/derivative disposition back to `verified-with-correction-needed` with `atlas-safe-to-promote=false`. Existing source evidence and the worker’s raw-source completeness annotations were preserved; no UI changes were staged.
- Validation performed: Rebuilt the 2025 score audit with 26 catalog entries, 3 corrected source-verification records, 23 blocked records, 0 errors, and 0 safe promotions. The source-comparison ledger rebuilt with 68 records, 33 autonomous blocks, 3 verified-with-correction-needed records, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. Data, playback, and review-queue rebuilds passed.
- Commit: Restore the zero-promotion comparison gate (this cycle).
- Remaining opportunities/blockers: Continue autonomous source comparison; no source-comparison record may authorize corpus promotion on its own.

## Cycle 65 — Block Schwab’s incomplete 2/4 event stream

- Problem identified: Schwab (526) had a clear F-sharp-minor 2/4 source scan with four vocal parts and 16 measures per part, but the retained OMR failed exact duration totals in 34 named part/measure groups. P1 m0,m14, P2 m9, and P3 m14,m15 were blank while the source visibly showed notation; OMR key fields also conflicted with the source key and omitted mode.
- Change made: Created a provenance-bearing derivative preserving all four parts, 16 retained OMR measures per part, and 137 detected pitched events. Added source F-sharp-minor key/mode and 2/4 metadata plus 137 derived four-shape noteheads. Lyrics remain optional and were omitted because the notation remains usable without fabricated underlay. Watermark overlap is recorded only for the intersected middle-system events.
- Validation performed: The derivative retained 4 parts, 16 measures per part, 137 pitched events, and 137 allowed shape tags. The source-comparison ledger rebuilt with 76 records, 41 autonomous blocks, 3 corrected source verifications, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. MuseScore rendered the two-page derivative successfully, and focused archive/provenance checks passed.
- Commit: Block Schwab’s incomplete 2/4 event stream (this cycle).
- Remaining opportunities/blockers: Continue autonomous comparison on the next strongest disjoint source page under the zero-promotion gate; promote only a record whose every event is source-supported.

## Cycle 66 — Reconcile The Royal Band’s event-scoped OMR block

- Problem identified: The existing worker artifact for The Royal Band (360) retained a clear, unwatermarked E-minor 6/8 source scan and a coherent four-part, 14-measure OMR stream, but 18 specific part/measure durations were over- or underfull. The earlier disposition also treated lyric alignment as a blocker, which is not required when the notation remains usable.
- Change made: Reconciled the worker script and audit in place, preserving the 242-event playable MusicXML and all derived four-shape noteheads. Recorded the exact anomalous measures, kept source E-minor/6/8 metadata authoritative, and made lyric omission explicitly non-blocking because no underlay was fabricated.
- Validation performed: Rebuilt the source-comparison ledger with 75 records, 40 autonomous blocks, 3 corrected source verifications, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. Playback validation passed with 1,283 playable assets, including the 242-event derivative.
- Commit: Reconcile The Royal Band’s event-scoped OMR block (this cycle).
- Remaining opportunities/blockers: Continue to the next disjoint retained source page; promotion remains closed until every promoted event, including the 18 anomalous bars, is source-supported.

## Cycle 67 — Correct Schwab’s chord-aware duration evidence

- Problem identified: The initial Schwab audit counted note durations without respecting MusicXML chords, so its failure count happened to remain 19 but several named part/measure failures were inaccurate.
- Change made: Replaced the duration check with cursor-aware MusicXML timing that treats chord tones as simultaneous and honors backup/forward elements. The audit now records the exact 19 failures: P1 m0,m2,m7,m8,m10,m14; P2 m0,m2,m9,m10,m11; P3 m0,m8,m10,m14,m15; and P4 m0,m3,m8. The source-faithful derivative and zero-promotion disposition are unchanged.
- Validation performed: Rebuilt the source-comparison ledger with 75 records, 40 autonomous blocks, 3 corrected source verifications, 0 errors, and 0 safe promotions. Playback validation and shape-review validation passed; all 137 Schwab pitched events still carry allowed shape tags.
- Commit: Correct Schwab’s chord-aware duration evidence (this cycle).
- Remaining opportunities/blockers: Continue autonomous comparison on the next strongest disjoint page; no record is promoted from an unresolved event stream.

## Cycle 68 — Correct Natick’s chord-aware duration evidence

- Problem identified: The existing Natick worker audit summed simultaneous chord tones as independent time, so its original named failures did not accurately identify the unresolved bars.
- Change made: Replaced the duration check with cursor-aware MusicXML timing that respects chords and backup/forward elements. The audit now records 34 genuine failures: P1 m1,m2,m3,m5,m7,m8,m10; P2 m1,m3,m4,m5,m6,m7,m8,m9,m10; P3 m1,m2,m3,m4,m5,m6,m7,m8,m9,m10; and P4 m1,m2,m3,m4,m5,m7,m8,m9,m10. P2 m6 remains explicitly blank against visible source notation; lyrics remain optional.
- Validation performed: The derivative retains 4 parts, 10 measures per part, 154 pitched events, and 154 allowed shape tags. The source-comparison ledger rebuilt with 75 records, 40 autonomous blocks, 3 corrected source verifications, 0 errors, and 0 safe promotions; playback validation passed, and MuseScore rendered the three-page derivative.
- Commit: Correct Natick’s chord-aware duration evidence (this cycle).
- Remaining opportunities/blockers: Continue autonomous comparison on the next strongest disjoint page; no record is promoted while any event grouping remains unresolved.

## Cycle 69 — Block O’Leary’s incomplete 3/4 event stream

- Problem identified: O’Leary (501b) had a legible G-major 3/4 source scan with four vocal parts and six measures per part, but retained OMR cursor timing failed in 13 named groups. P2 m1,m2, P3 m1,m6, and P4 m6 were blank while the source visibly showed notation; P4 also omitted its key metadata.
- Change made: Created a provenance-bearing derivative preserving the four-part structure, 65 detected pitched events, source G-major key/mode and 3/4 meter, and 65 derived four-shape noteheads. Lyrics remain optional and were omitted because the notation remains usable without fabricated underlay. Watermark overlap is recorded only for intersected middle-system events.
- Validation performed: The source-comparison ledger rebuilt with 86 records, 41 autonomous blocks, 13 corrected-source records, 0 errors, and 0 safe promotions; candidate reconciliation remained 94 blocked candidates. Playback validation passed with 1,283 playable assets, and MuseScore rendered the two-page derivative.
- Commit: Block O’Leary’s incomplete 3/4 event stream (this cycle).
- Remaining opportunities/blockers: Continue autonomous comparison on the next strongest disjoint page; promote only if every event in a candidate is directly source-supported.
