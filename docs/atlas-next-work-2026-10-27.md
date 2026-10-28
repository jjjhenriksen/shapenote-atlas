# Atlas: worthwhile next work — 2026-10-27

## Evidence and scope

Inspected live `main` at `303d0ea5` (PR #528), README, active backlog,
`docs/BACKLOG_OWNERSHIP.md`, acceptance contracts, current reader/generator/audio
code, all **427 open issues**, and both open PRs. Priorities below are based on
user journeys and dependencies, not issue volume. This is a local engineering
audit, not hosted/native acceptance or a fresh music/source review.

Open PRs are #513 (Social Harp source-reading evidence) and #514 (bounded native
QA evidence). Neither implements the comparison integration below. Preserve their
human/source gates and original credit; neither is an ordinary ready-to-land fix.

## Ranked software work

### 1. Connect existing edition relationships to the reader — implemented here

**User outcome:** from a tune, inspect each related edition's score availability,
follow its catalogue record, and open its explicitly recorded source.

Before this change `src/main.jsx` exposed `editionReconciliation` only as a badge;
the alternate-edition button existed only inside the no-score fallback and reused
the selected ID. A reference score suppresses that fallback. Moreover Ester 37t
has separate 1991 and 2025 IDs, so same-ID switching is insufficient.

The current corpus contains 628 records with reconciliation metadata representing
538 distinct relation IDs. These are catalogue relations, not 538 proven identical
musical works. The new collapsed comparison panel joins by explicit relation ID
and edition; missing/duplicate targets fail closed. It does not join on titles,
borrow a score, copy a key, infer identity, or promote a draft. It exposes source
links and per-edition asset status, with an explicit warning that an unlisted
change does not establish identical music/text. Keyboard-operable native details
and links preserve edition-specific deep links, including split records.

This is record/evidence comparison, **not side-by-side notation comparison**.
The latter should be built only with two explicitly selected witnesses and
independent provenance/extent labels; no synchronized audio assumption.

### 2. Reduce the initial catalogue critical path

**Owner:** Atlas. The existing `reader-data.spec.js` cold-load checks on this
change measured 29.4–29.5 seconds to catalogue visibility and 30.5 seconds to
playability at 1.6 Mbps / 150 ms latency / 4x CPU slowdown, cache disabled.
The catalogue response was 3,713,156 decoded and transferred bytes. These are
local Vite development-server observations, **not hosted production timings**.
The byte-budget tests pass, but passing a 4 MB budget is not a fast first journey.

Next: measure the built hosted path and content encoding; split catalogue loading
by book or use a smaller discovery index while preserving cross-edition relation
resolution and search semantics. Keep a compact relationship index independent
of lazy book details. Add a user-outcome latency budget, not only a byte ceiling.
Existing lossless per-tune lazy details should be retained, not rebuilt. This
unblocks finding, notation and playback together on slower connections.

### 3. Finish the acceptance-to-publication handoff, in bounded stages

**Owner:** Atlas. **Anchor:** [#495](https://github.com/jjjhenriksen/shapenote-atlas/issues/495).
**Leverage:** enables many producer outputs without repetitive manual assembly.

Do not start by inventing an importer: staging already exists, and #497/#503/#509
implemented proposal validation and provenance checks. Opt-in v2 and v3 consumers
also landed (#522/#524). `scripts/validate_transcription_acceptance.py` deliberately
returns `acceptance: false`, `authorityVerified: false`, `evidenceVerified: false`.

Next bounded engineering deliverable: a read-only publication-plan command that
consumes pinned bundle + separately authorized exact-scope decision, reports
predecessor/version collisions, exact mapping changes, downloadable byte hashes,
UI labels, unsupported semantics, rights restrictions and blocking gates. Test
with synthetic fixtures, including rejected/ambiguous/partial scopes. It must
change no public assets and must not interpret a valid declaration as approval.
Actual admission/publication remains a separately authorized subsequent step.

### 4. Make download actions consistent across selected witness types

**Owner:** Atlas. **User outcome:** obtain the exact witness being displayed,
with edition, draft version, original-versus-derived status and limitations intact.

`PublishedDraftActions.jsx` has editable and original-witness links;
`ShapeReviewDraftPanel` has a review download. Ordinary exact/reference display
has no equivalent named MusicXML action in its source strip, and the engraving
component does not supply one. Users must hunt through generic source links.
This is an integration/discoverability gap, not proof that the source file is lost.

Next change: one shared witness-action model used by all score states; provide
only available, policy-permitted original files. Distinguish external links from
local downloads. Never silently export a transposed/derived rendering as the
original. Regression proof should verify actual downloaded XML/MXL bytes and
failure/retry behavior, not just presence of an anchor. Native download support
was already fixed in #515; exercise it rather than reimplement it.

### 5. Close release-journey proof and accessibility gaps

**Owner:** Atlas. **Anchors:** [#57](https://github.com/jjjhenriksen/shapenote-atlas/issues/57),
[#58](https://github.com/jjjhenriksen/shapenote-atlas/issues/58).

Keep the existing local browser suite; it already covers search, filter changes,
score failures/retries, notation, real Web Audio frequency ratios, cancellation,
and repeat controls. Extend acceptance coverage around complete journeys:
find → select edition/witness → read → download → practice → return/share.

PR #514 explicitly leaves audible audio, exact sounded repeat order, disconnected
offline use and human source acceptance open. CI scheduling tests and a moving
progress bar do not settle those. Native download and server lifecycle bugs
reported during that QA have since landed as #515/#516; do not rank them as open
implementation defects. Capture new exact-build native/hosted receipts after the
fixes, preserving the historical QA rather than relabeling it.

Accessibility follow-up: screen-reader reading order for notation plus its textual
alternative, keyboard transport/edition navigation, 200% zoom, and 320px layout.
The new panel uses native semantics and focus styles; that does not constitute a
whole-app WCAG or VoiceOver pass. No new global accessibility defect is asserted
without a reproducer.

### 6. Reconcile the maintainer entrypoint with current work

`OPENCLAW_BACKLOG.md` has a current ownership preface but still calls ATLAS-01 the
default next task and describes its branch as pending. Its own preface says #472
already merged it. Replace conflicting dispatch prose with a current work index
that separates software, producer tasks, acquisition, and acceptance. Preserve
dated receipts and historical counts. This is inexpensive work that prevents
repeated investigation and duplicate assignments, not a reason to close musical
coverage issues in bulk.

## Work that is not a software backlog substitute

| Work | Correct ownership / gate |
| --- | --- |
| A Glimpse of Thee beyond m4, Zion's Dove extension, Afton/Devotion/Portsmouth underlay | Transcriber produces source-backed candidates; Atlas admits/publishes and verifies reader/download/playback behavior. Existing producer #9–#13 remain open. |
| New Salem/Something New printed shape and lyric evidence | Transcriber #14/#15; rendering already exists, missing source semantics are not a renderer bug. |
| Hundreds of notation batches | Follow the bounded producer book task indexes (#27–#37), not new Atlas transcription workers. Atlas originals retain exact mapping/acceptance. |
| Exact witness recovery | Producer #38 and record-specific dependencies; acquiring an identifiable edition is not coding a fallback to a different source. |
| Social Harp 221 versus historical 222 | Source/inventory reconciliation, Atlas #54 and draft PR #513. Reader agreement or covered-leaf counts are not a publisher counting rule. |
| Explicit human image decisions and publication rights | Preserve the required named decision and scope. Technical parser/hash/render tests do not waive these. |
| Seven-shape / unsupported texture production | Transcriber capability contract first; versioned Atlas consumer only when supported. Never coerce into four-shape/four-part input. |

## Already addressed; do not redispatch

Recent merged work includes invalid-link recovery (#528), toolchain fixes (#526),
book-filter recovery (#521), native server/download repairs (#516/#515), score
response identity checks (#508), late-note envelope deadlines (#504), and bundle
validation/provenance work (#498/#501/#503/#509). Written-order and encoded-repeat
scheduling are already implemented in `practice.js`/`audioPlayback.js`; remaining
source fidelity and audible order evidence are distinct from adding that feature.

## Delivery boundaries

No source acquisition/transcription, accepted mapping, notation bytes, source
certification, publication rights, existing PR body, or deployment was changed.
Validation: 135 JavaScript tests and all 66 local Chrome browser tests passed;
production build and all three comparison tests against the built preview passed. Playback validator inspected 1,334 assets, preserving
one quarantined draft; transposition validator preserved all 1,334 assets.
Desktop/mobile keyboard comparison and the mobile screenshot were checked.
The initial default Chromium attempt could not launch because its bundled
executable was absent; installed Chrome was used explicitly. No Safari,
VoiceOver, native-window, audible-output or hosted-release verification is claimed.
The complete source-dependent aggregate suite was not run in this clean worktree.
