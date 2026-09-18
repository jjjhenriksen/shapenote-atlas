---
title: "Two very long goals, and what they actually built"
date: 2026-09-18
author: Jacqueline Henriksen
description: "A Shape-Note Atlas build diary: a thirty-hour goal, a second long implementation run, and the work that continued after the OpenClaw handoff."
---

# Two very long goals, and what they actually built

One of my Shape-Note Atlas goals ran for almost thirty hours. Another carried this session through more than a million accounted tokens, a group of GPT-5.6 Luna tasks, and a succession of score corrections that sometimes amounted to moving one syllable to the right note.

Both helped the project. Neither finished the music.

This is a diary of those runs and the work they made possible. The Atlas is a searchable reader and practice space for shape-note music across eleven books and editions. It has to keep track of which source a score came from, what can be played or transposed, and what still needs to be transcribed. A tune can have a familiar name and still be the wrong edition. A score can render beautifully and still have the wrong rhythm.

Those distinctions turned out to account for a lot of the work.

## August 27–29: the almost-thirty-hour goal

The earlier run lives in a Codex task called “Sacred Harp — Backlog Coordinator.” Its objective was to establish source-faithful, edition-aware coverage: verified notation and playback where structured sources existed, an acquisition or transcription path for missing songs, and separate treatment of the 1991 and 2025 Sacred Harp editions.

Its final goal receipt recorded **29 hours, 51 minutes, 13 seconds** and **13,125,012 accounted tokens**. That is the goal system's recorded usage, not a cost estimate or a measurement of thirty uninterrupted hours of useful reasoning. The calendar interval was longer, and the record includes waiting, verification, and coordination.

I wanted the agent to keep working beyond a single answer. The goal gave it somewhere to return after each smaller task: inspect what exists, find the next problem, make a change, verify it, and continue. The surrounding work also included an overnight improvement task with its own running log. That log reached seventy numbered cycles, mixing application improvements with source-comparison work.

Some of the useful changes were ordinary reader problems. The Sources navigation initially changed a label without actually narrowing the library to source follow-up records. Filtering could hide a selected tune while leaving its unrelated detail pane visible. A failed score request could leave the reader saying “Loading…” indefinitely. Manually entering a source key could make the selector disappear, leaving no way to correct the choice.

Those problems became specific changes: real source filtering, synchronized selection, a retry path, and an editable source-key control. The accessibility work included announced selection states, clearly named controls, a keyboard skip link, and coverage details that did not depend on hovering over a tooltip. The overnight log records browser checks for these behaviors, rather than only recording that a file had changed.

The source work was slower. Optical music recognition produced files that could be parsed and rendered, but direct comparisons still found missing notes, conflicting meter, blank measures where the scan visibly contained music, and uncertain shape information. Those files needed an explicit disposition. Otherwise, a successful import could quietly become a claim that the score was correct.

By the long goal's closing report, the catalogue contained 3,547 songs and 4,202 edition records. Playback validation covered 1,283 assets. There were still 167 assets with unknown source keys; the interface allowed explicit key entry rather than silently treating them as major. The run also retained separate metadata for 448 shared 1991/2025 songs and recorded source-backed dispositions for the ninety current 2025 records in that missing-notation review scope.

The goal was marked complete. The narrower result was useful: more of the application worked, and uncertainty had become inspectable. But those ninety dispositions did not mean ninety finished transcriptions. Several outcomes were documented reasons to withhold a score. That matters when reading an old “goal complete” message beside a much larger unfinished catalogue.

The record also contains stretches of repeated checks on a still-active worker with no new result. Persistence prevented abandoned work, but it could produce a lot of activity without changing the project. I want that included in the diary too. The duration alone does not tell me how useful the run was.

## September 4–5: asking what was still unfinished

The next substantial session began with a direct request: look at the Shape-Note Atlas, tell me precisely what was unfinished, and start implementing it. I added that the other books and editions needed attention as well.

That sounds simple until “unfinished” has to be counted. The catalogue, available notation, alternate witnesses, review drafts, retained scans, and unverified source links all describe different things. I asked where a reported figure of 7,590 URLs came from. It turned out to be exact-string deduplication of web addresses under the song records; 3,857 were absent from the earlier health cache. It was not a count of missing scores, and it was not the same scope as the broader source-health inventory.

This was a useful starting point. Before an agent could clear a backlog, it had to explain what the backlog measured.

I asked for GPT-5.6 Luna tasks to implement the work. The responsibilities were divided among runtime verification, data and music semantics, practice and discovery, source health, existing-book notation, source-only books, and 2025 corrections. I also asked whether this work should have a persistent goal, then asked Codex to write it.

The resulting goal covered all books and editions, source-supported implementation, application failures, and final verification. It explicitly prohibited inventing missing music or treating an incomplete draft as verified. That qualification stayed important through the rest of the session.

The saved history contains 51 goal-continuation prompts. The last visible usage counter was **1,505,835 tokens**. I am treating that as a recorded checkpoint, not a final billing total. Unlike the earlier thirty-hour run, this session did not end with a defensible claim that the whole objective was complete. It reached a verified application checkpoint and then a handoff, with source work still open.

## The build that passed with the wrong dependency

One of the clearest benefits of continuing was finding a problem after the application appeared to have passed verification.

An isolated-checkout report said all twenty required checks passed. Its dependency check reported Vite 7.3.6, matching the lockfile. Further down, the actual build output said Vite 8.2.1.

The checkout had no local dependency installation. The build had found a Vite executable in an ancestor directory on the computer. The validator had compared the package declaration with the lockfile, so it could pass without proving what software actually ran.

That changed the implementation. The dependency check now inspects installed package versions and verifies that the local Vite executable resolves to the expected package. Focused tests cover missing installations, version drift, and missing or incorrect local executables. The fix was committed as [`bdd6c49`](https://github.com/jjjhenriksen/shapenote-atlas/commit/bdd6c49e5208aa9bb9c09f4a9872e6917cdefed2).

A fresh checkout then installed the locked dependencies, built with Vite 7.3.6, passed browser and startup checks, and passed all twenty required checks. Its tracked files stayed clean, and its committed source-health report remained unchanged. The previous report was preserved as rejected evidence for a locked-dependency build.

The long goal helped here because there was still a next step after “the tests passed”: read what actually ran and resolve the contradiction.

## The music moved a few notes at a time

The transcription work made the same problem visible at a smaller scale.

In Devotion, an early audit treated the opening pickup as though it were the following full measure. That produced a supposed mismatch between the scan and the retained MusicXML. Reviewing the barline corrected the premise: the pickup matched the raw first measure, and only the lyric-bearing voices should receive its opening word.

Later versions added directly supported syllables and kept the source notes, durations, repeats, and endings intact. Some additions were then withdrawn because their coordinates or word-to-note relationships had not actually been established. One version introduced lyric-extension markers without closing them. The next removed those markers and withheld an unsupported word while retaining four supported continuation anchors.

Afton exposed a different problem. The audit file eventually contained observations for all the note shapes, but most of those observations were absent from the exported MusicXML. The evidence and the deliverable had drifted apart. By v24, the exported score contained all 251 directly audited noteheads with explicit fill states, and the coordinator checked them by part, measure, and note index.

Zion's Dove had similar export failures: overlapping onsets after a half note, duplicated appended events, lost opening lyrics, and coordinate tables that could not describe the printed notes. Fixing the explanatory JSON was not enough. The actual score had to be checked again.

This is where a long-running agent was useful and where it needed the most supervision. It could preserve versions, run comparisons, carry a correction into another file, and return to the next measure. It could also confidently produce a test that repeated the same wrong table as the implementation. More execution did not remove the need for direct source review.

## September 6 onward: making the work transferable

I asked for a handoff document so my OpenClaw agent could start working on the project. The document and a verification receipt were committed in [`bda087c`](https://github.com/jjjhenriksen/shapenote-atlas/commit/bda087c10209e739b9b5dce8291a6cc9c4a3e6cb).

The handoff had to explain a practical limitation: cloning the repository did not recover all the evidence used to validate it. Many retained scans, source files, and unfinished candidate versions were local-only. A verified evidence bundle contained 2,602 files, about 216 MB, but even that bundle was not a complete backup of the transcription lanes.

Writing down those dependencies made the work more transferable. It also kept the new agent from mistaking an empty task folder for the real checkout or an old milestone for the latest score.

The continuation brought another important decision. On September 7, I prioritized publishing useful, human-correctable review drafts without waiting for every lyric or shape question to be settled. That changed the delivery policy. A practice draft could become available with clear limitations, a source link, and a correction path; it still could not claim exact-edition verification.

That let the earlier careful work reach the reader. The subsequent commits published Afton and Zion's Dove drafts, thirteen SH2025 correction drafts, and notation for New Salem and Something New. Further work added an opening for A Glimpse of Thee, completed the page-identity mapping for the existing Social Harp catalogue, and implemented playback that follows encoded repeats with cancellation.

These are different kinds of progress. Completing 221 Social Harp page identities helps a reader find the source. It does not supply 221 transcribed scores. Publishing a correctable draft makes practice possible sooner. It does not erase the remaining review work.

## September 18: what the two goals left behind

The September 18 audit found eighteen pinned human-correctable publications and 138 validated review draft assets. The application again passed twenty required checks, this time at a later implementation commit with fresh browser evidence. The audit also corrected an obsolete limitation that still described New Salem repeat playback as unavailable even though it had been implemented.

The all-book mapping gap remained substantial: 3,047 missing mappings plus thirteen SH2025 correction records. Those 3,060 records are an inventory of outstanding work, not 3,060 individually diagnosed impossibilities. The current [backlog](../../OPENCLAW_BACKLOG.md) separates concrete next tasks from dated reports.

Looking across both long goals, the useful result is cumulative. The earlier run improved the reader and made source distinctions explicit. The September run caught integration failures, preserved and corrected transcription evidence, and made a fresh-checkout result reproducible. The OpenClaw continuation used that foundation to publish more usable material and extend the application.

There were costs: repeated status checks, misleading completion language, source corrections that needed to be corrected again, and time spent proving that an export contained what its audit already claimed. I would not turn either run's duration or token count into a productivity score.

What I can point to is more concrete: a source-key choice that remains editable, a build that proves which dependency ran, a note shape that is actually present in the score, and a draft a singer can open and correct. The next agent has those artifacts, their limitations, and a backlog that says where to continue. That is how the long goals helped move the Atlas along.

---

*Written from the saved August 27–29 and September 4–5 Codex session records, the overnight improvement log, Git history, and the September 18 project audit. Dates and counts describe those checkpoints. This is a build diary, not a claim that all notation is complete or that a repository push verifies the live website. [Evidence and editorial notes](2026-09-18-two-long-goals-sources.md).*
