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

### What happened during those thirty hours

The saved checkpoints make the progression easier to see. These times are California time (PDT), and mark when a result was reported, not the exact minute every change was made. The goal opened at **11:39 a.m. on August 27** and closed at **5:13 a.m. on August 29**: about 41½ hours on the calendar, with 29 hours and 51 minutes recorded by the goal system. Work from supporting tasks appears here when the coordinator received or checked it.

| Checkpoint | What changed, and what it made possible |
| --- | --- |
| **Aug. 27, 12:52 p.m. — playback** | A song-finished timer mixed seconds and milliseconds, stopping playback after about half a second. After the fix, browser checks found playback still active beyond two seconds. This was a concrete failure behind an apparently working Play button. |
| **1:24 p.m. — notation and transposition** | Four-shape noteheads rendered, minor-key handling improved, and a browser check transposed G major to D major. Northampton retained its F-sharp-minor identity; source recordings stayed labeled as references. |
| **1:49–2:36 p.m. — edition corrections** | The apparent set of 24 exact 2025 scores became fourteen exact scores and ten references from other editions. The audit also corrected Lisbon's identity and removed an unsupported 264b entry. Useful coverage could grow without inflating exact-edition coverage. |
| **3 p.m. — reviewable OMR output** | Six recognition drafts were packaged with scans, PDFs, hashes, measure counts, warnings, and review checklists. A generated score now came with the evidence needed to question it. It was still a draft. |
| **9:09–9:38 p.m. — honest source-key and coverage controls** | Pitch-bearing files without a key gained an explicit, editable source-key choice, kept separate from source metadata. A catalogue-joining fix also recovered existing page and PDF links. All 4,202 edition records then had structured notation, a queued source reference, or an explicit blocked status. |
| **10:11 p.m. — recovering existing music** | Historical page-suffix mappings recovered fifteen same-book MusicXML scores. Thirty more 2025 records gained clearly labeled cross-edition witnesses. This was progress through better matching of existing material. |
| **Aug. 28, 1:18–5:33 a.m. — source preparation** | Image preparation preserved originals and produced traceable working copies. Candidate-source handling grew to 94 isolated OMR drafts; a collision bug was fixed so different compositions could not overwrite or share results. Edited images and recognition output remained unverified. |
| **5:38 a.m. — playback validation** | A new validator checked 1,283 structured assets containing 283,244 events for timing, pitch, and schedulable notes. A browser check exercised source-key selection, transposition, and playback. These checks established that the encoded music could run; they did not establish that every note matched a scan. |
| **11:17–11:26 a.m. — stricter source review** | All ninety records in the missing-2025-score scope had retained source images, observations, and review entries. A supposedly strong match for Trembling Spirit was rejected, shrinking the review-draft set. Removing a false match was part of the progress. |
| **5:14–5:45 p.m. — thirteen promising files** | An audit of 26 official MusicXML downloads separated thirteen 2025 correction candidates from thirteen alternate-edition sources. The candidate audit reported no observed pitch/rhythm mismatch, but every candidate lacked lyrics and explicit mode, and twelve lacked shape tags. None was ready for exact-edition promotion. These became the correction records revisited in September. |
| **11:32–11:36 p.m. — edition-specific meaning** | The run checked separate metadata for 448 shared songs and corrected minor-mode handling. Samaria's different keys and Rockbridge's different meters illustrated why a shared title could not stand in for an edition-specific score. |
| **Aug. 29, 4:44–4:48 a.m. — closing the review scope** | All ninety missing-2025 records had evidence-backed dispositions, with no new score promoted as verified. A final Devotion browser check exercised its four-part score, playback, and transposition from C to D, including stopping playback safely during the change. |
| **5:12–5:13 a.m. — final accounting** | The closing audit retained 167 unknown-key assets rather than applying unsupported keys. The goal receipt then reported completion, 29 hours 51 minutes 13 seconds, and 13,125,012 accounted tokens. The application and review machinery had advanced; the missing transcriptions remained missing. |

The sequence matters to me more than the duration. The first afternoon repaired things a singer could encounter immediately. The following night recovered sources and made the outputs easier to inspect. The later work tested the limits of those sources and recorded why apparently promising files still needed correction. The September run could start from those specific files and findings instead of repeating the whole search.

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

### September's goal, checkpoint by checkpoint

Again, these are reported checkpoints in California time. The later goal's record shows how an initially successful integration became a more demanding verification exercise.

| Checkpoint | What moved forward |
| --- | --- |
| **Sept. 4, 7:03–7:22 p.m.** | The URL-count explanation established what the audit was measuring. Seven Luna tasks then took responsibility for runtime, data semantics, practice and discovery, source health, and notation across all eleven books. |
| **8:13–8:23 p.m.** | The persistent goal was created. Integration review found that quarantined scores could still reach playback, found repeat/ending problems, and caught an omitted half rest in Afton. The work became a set of concrete failures to fix. |
| **8:51–9:03 p.m.** | All 220 “missing repeat semantics” flags turned out to be tempo instructions classified incorrectly. Another audit found that a fallback had displaced specific alternate witnesses. The unfinished-notation inventory settled on 3,047 missing mappings plus thirteen correction records. |
| **9:19–9:52 p.m.** | Integration first passed nineteen checks, then twenty with shared-edition reconciliation included. The goal stayed active because source transcription and provenance review remained unfinished. |
| **Sept. 5, 2:13 p.m.** | A later passing run had regenerated its own health report. The audit found a stale URL count and required verification against unchanged committed evidence. A green result needed an identifiable set of inputs. |
| **2:39–2:52 p.m.** | Build output exposed the wrong Vite installation. The validator was strengthened, the fix pushed, and a fresh locked-dependency run passed all twenty required checks with a clean tracked checkout. |
| **2:55–2:56 p.m.** | Afton v24's actual export matched all 251 audited noteheads. Devotion v10 retained supported anchors while removing unsupported extension metadata. Another browser run passed; the music work still had open gaps. |
| **Sept. 6, 3:52 p.m.** | The OpenClaw handoff was pushed with the verified checkpoint, next tasks, and the local-only evidence dependencies. This was the transition to another working session, not a claim that the all-book goal had finished. |

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

### The OpenClaw continuation has a history too

The saved OpenClaw conversation adds something Git alone cannot show: the decisions between the commits. On September 7, its first response narrowed the handoff to one Afton lyric problem. I clarified that I meant orchestration of the entire project. Later that afternoon I asked it to publish useful drafts promptly wherever a human could correct the output. Those instructions changed what the next batches delivered.

The timeline below combines dated OpenClaw messages with repository commits. Times are California time. Session reports describe what was checked then; they are not fresh verification of the live site today.

| Checkpoint | Work and decision |
| --- | --- |
| **Sept. 7, 12:43–12:48 p.m. — picking up the handoff** | I asked OpenClaw to read the handoff and set a goal. It produced Afton v25 with eight source-supported lyric anchors while preserving 251 pitches and noteheads. Filesystem errors initially prevented committing. |
| **1:16–1:19 p.m. — restoring the full scope** | I asked for orchestration and quick, atomic commits, then clarified that the goal covered the whole handoff. The response explicitly returned to all eleven books, with one coordinator responsible for Git and separate source-review tasks. |
| **3:59–4:14 p.m. — changing the publication threshold** | I asked for prompt publication where human correction was possible. The session then reported Afton and Zion's Dove published as practice drafts, with downloads, evidence, known gaps, and correction links. Exact-edition verification stayed separate. |
| **5:20 p.m. — delivering across books** | The next report recorded thirteen SH2025 correction publications, ten reviewed Trumpet page identities, and five Social Harp mappings. Browser checks covered all thirteen drafts and 52 download links. Score overflow on mobile was still acknowledged. |
| **5:33–6:13 p.m. — from openings to complete written notation** | New Salem and Something New first received opening-measure drafts, then complete 16- and 15-measure notation drafts. The same cycle repaired voice-label overlap, mobile overflow, and publication validation. Its closing report recorded twenty required checks passing and Social Harp at 87 reviewed identities. Lyrics and shape review remained unfinished. |
| **Sept. 11, 8:53–9:25 p.m. — completing a source-identity pass** | Repository commits show Social Harp progressing through successive reviewed batches to 221 mapped catalogue identities and zero unresolved identities in that catalogue. This completed the page-finding task, not 221 scores; the historical 221/222 inventory discrepancy remained separate. |
| **9:07–9:45 p.m. — improving what readers could use** | Commits corrected and extended Afton lyrics, published the four-measure A Glimpse of Thee opening, added playback following encoded repeats, moved practice controls before the score, preserved literal notehead geometry, and improved resumable source checks. These are commit checkpoints, not a reconstruction of each task's working time. |
| **Sept. 12, 1:13–2:24 p.m. — explaining the product** | A separate OpenClaw session first reported a clearer README and guide, then a hosted documentation route, then a nineteen-page documentation library. Its final report recorded 37 passing tests, successful deployment, checks of twenty HTML routes and their assets, and a live browser check. |

There is also a limit worth preserving in this history. I asked for autonomous background continuation on September 7, but the tracked closing report did not establish a background scheduler. Two bare `/goal start` attempts in the conversation returned usage instructions. Those messages do not prove that another persistent goal was running. What the record does establish is a sequence of requested continuations, delivered batches, commits, and verification receipts.

This makes the handoff more than a document at the end of the first session. It carried source decisions into later work, while my follow-up instructions changed the delivery policy. The project could make imperfect but inspectable music available, improve it in versions, and tell readers how to correct it.

## September 18: what the two goals left behind

The September 18 audit found eighteen pinned human-correctable publications and 138 validated review draft assets. The application again passed twenty required checks, this time at a later implementation commit with fresh browser evidence. The audit also corrected an obsolete limitation that still described New Salem repeat playback as unavailable even though it had been implemented.

The all-book mapping gap remained substantial: 3,047 missing mappings plus thirteen SH2025 correction records. Those 3,060 records are an inventory of outstanding work, not 3,060 individually diagnosed impossibilities. The current [backlog](../../OPENCLAW_BACKLOG.md) separates concrete next tasks from dated reports.

Looking across both long goals, the useful result is cumulative. The earlier run improved the reader and made source distinctions explicit. The September run caught integration failures, preserved and corrected transcription evidence, and made a fresh-checkout result reproducible. The OpenClaw continuation used that foundation to publish more usable material and extend the application.

There were costs: repeated status checks, misleading completion language, source corrections that needed to be corrected again, and time spent proving that an export contained what its audit already claimed. I would not turn either run's duration or token count into a productivity score.

What I can point to is more concrete: a source-key choice that remains editable, a build that proves which dependency ran, a note shape that is actually present in the score, and a draft a singer can open and correct. The next agent has those artifacts, their limitations, and a backlog that says where to continue. That is how the long goals helped move the Atlas along.

---

*Written from the saved August 27–29 and September 4–5 Codex session records, the overnight improvement log, OpenClaw continuation and documentation sessions, Git history, and the September 18 project audit. Dates and counts describe those checkpoints. This is a build diary, not a claim that all notation is complete or that a repository push verifies the live website. [Evidence and editorial notes](2026-09-18-two-long-goals-sources.md).*
