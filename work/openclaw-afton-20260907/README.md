# Afton continuation — 2026-09-07

## Goal and result

Resolve source-supported measure-8 lyric underlay across P1–P3 without guessing or changing notation. Partial milestone delivered: v25 adds eight directly observed P2/P3 anchors. P1's unhyphenated `ripened harvest` still requires syllable-level review. The candidate remains `safeToPromote=false`.

- Candidate: [afton-full-song-candidate-v25.musicxml](afton-full-song-candidate-v25.musicxml)
- Source observations, hashes, exact changes and remaining gaps: [afton-v25-review.json](afton-v25-review.json)
- Reproducible builder and preservation verifier: [build_and_verify.py](build_and_verify.py)
- Fresh Poppler rendering: `afton-m8-source-300dpi.png` (retained PDF page 1, 300 DPI, crop 2535/300/440/950).

The new sidecar is a delta review receipt, not a copy of the stale v24 serialization tables. All prior candidates and sidecars remain unchanged. No canonical public data, source scan, repository instructions, dependency files, or lane handoffs were edited.

## Verification

Run from the established repository: `python3 work/openclaw-afton-20260907/build_and_verify.py`.

- Exported MusicXML parses with the Atlas semantic parser.
- All 251 pitched notes and 251 explicit noteheads preserved.
- Removing exactly the eight added lyric elements yields structural equality with all of v24, including prior lyrics, pitches, durations, key declarations and navigation.
- Source PDF and v24 hashes checked before generation.
- P1 and bass m8 lyrics remain absent; no new lyric-extension markers or verse numbers.
- `python3 scripts/verify_dependencies.py`: passed; React/React DOM 19.2.8, Vite 7.3.6.
- `python3 tests/test_agent_10_reproducible_validation.py`: 12 tests, 11 passed, one filesystem error reading existing `public/shapenote-2025-score-audit.json` (Errno 11, Resource deadlock avoided). Not a clean aggregate verification.

## Initial inventory and delivery boundaries

Read current tracked JSON: 3,547 songs; 4,202 coverage records; 3,047 transcription-queue records; 13 correction-needed records; 90 image-review records; 448 shared-edition pairs. Thus the handoff's 3,060-row outstanding scope remains visible; this isolated candidate clears no canonical queue row.

`git status` and `git log` failed with `mmap failed: Resource deadlock avoided`; one bounded Git configuration retry also failed. Current HEAD and tracked ownership could not be established. Existing agent processes are present but cannot establish file ownership from that alone. All new work is confined to this separately named directory. No staging, commit, push, reset, cloud hydration repair, or dependency reinstall attempted.

Command Center root responded HTTP 200, but the documented menu LaunchAgent and menu process were absent. No authenticated dashboard or briefing-freshness claim; no service repair or operational dispatch attempted.

## Next bounded task

Directly inspect P1 m8 syllable boundaries and P3 m12 `dis-` / `play,` alignment. Preserve unknown melisma semantics. Re-establish readable Git state before committing or pushing a scoped review artifact; do not regenerate canonical data merely to work around unavailable files.

## Atomic commit follow-up

Git access was restored by regenerating one derived pack index from its readable pack in a temporary directory. The unreadable original index was preserved with an `.unreadable-20260907` suffix; Five subsequently unreadable Git tree objects were restored from a separate GitHub object copy after verifying their exact object hashes; their unreadable originals were also preserved. No refs, tracked content, or unrelated working files were replaced. Established parent: `bda087c10209e739b9b5dce8291a6cc9c4a3e6cb`. The index was empty before staging; unrelated untracked files remain untouched.

The builder/verifier passed again, including the Atlas semantic parser. Independent read-only review confirmed source/candidate hashes, eight-anchor-only structural changes, and non-promotion flags. The 12-test preflight again produced 11 passes and the same filesystem error; this is not full application validation.

Commit scope is exactly the five files in this directory: report, builder, candidate, receipt, and source crop. This deliberately tracks the isolated review artifact beneath otherwise ignored `work/`; it does not promote it. Reproduction still requires the local retained PDF and v24 predecessor at the receipt paths, as described in the main handoff. No push or service repair is part of this follow-up.
