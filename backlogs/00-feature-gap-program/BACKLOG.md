# Sacred Harp dashboard feature-gap program

## Purpose

This is the coordination backlog for the remaining gaps found in the
2026-08-30 adversarial feature audit. Each workstream is delegated as its own
`/goal` task. Workers must inspect the current shared checkout first, preserve
user-owned changes, and keep source-faithful data fail-closed.

## Current baseline

- 3,547 corpus records across 11 books.
- 1,317 structured score assets; 1,167 edition score mappings and 475
  reference mappings are exposed in the current corpus.
- 3,035 edition records remain in the transcription/source queue.
- 90 current Sacred Harp 2025 records still lack an exact verified score; 0
  are safely promoted.
- 13 source-aligned 2025 records remain correction-needed/review-only.
- 448 Sacred Harp 1991/2025 shared pairs are mapped, but repeat/ending
  semantics remain unavailable across the reconciliation.
- Official/reference playback and transposition are verified; OMR drafts
  remain isolated review material.

## Workstreams

| ID | Workstream | Backlog | Ownership boundary |
| --- | --- | --- | --- |
| A | All-book exact notation coverage | `01-transcribe-2025/BACKLOG.md` plus the all-book queue | Structured notation acquisition/transcription only; no UI |
| B | Correction-needed source records | `04-correction-needed/BACKLOG.md` | The 13 correction-needed records only |
| C | Semantic fidelity engine | `05-semantic-fidelity/BACKLOG.md` | Corpus comparison/diff ledger only |
| D | Four-shape source verification | `06-shapes/BACKLOG.md` | Shape evidence and validation only |
| E | Browser playback verification | `07-browser-audio/BACKLOG.md` | Harness and playback proof only |
| F | 1991/2025 edition reconciliation | `08-edition-reconciliation/BACKLOG.md` | Shared-pair mapping and semantic reconciliation only |
| G | 2025 additions and queue meaning | `09-additions-queue/BACKLOG.md` | Additions identity and queue joins only |
| H | Source health and integrity | `10-source-health/BACKLOG.md` | URL health, retention, and hashes only |
| I | Startup and packaged deployment | `11-startup-deployment/BACKLOG.md` | Launch/package/runtime proof only |
| J | Reproducible verification and docs | `12-reproducible-validation/BACKLOG.md` plus stale documentation | Aggregate receipt, counts, and documentation only |
| K | Lyrics, repeats, and endings | `14-lyrics-repeats/BACKLOG.md` | Musical-semantic data/rendering; do not own comparison ledger generation |
| L | Practice workflow | `13-practice-workflow/BACKLOG.md` | Practice UI/audio controls only; no score-data rewrites |
| M | Discovery and navigation | `15-discovery-navigation/BACKLOG.md` | Search/filter/deep-link UI only; no notation changes |
| N | Source-health visibility | `16-source-visibility/BACKLOG.md` | Source-health/status presentation only; no health collector changes |

## Coordination rules

- Every worker prompt must begin with `/goal` and name the backlog it owns.
- Workers may edit only their owned backlog, source files, and generated
  outputs. UI workers must not edit `scripts/build_data.py` or transcription
  artifacts. Data workers must not edit `src/main.jsx` or `src/styles.css`
  unless their backlog explicitly says so.
- Preserve immutable source images, raw MusicXML, review-only gates, and both
  duplicate `81b` artifacts. Never promote OMR/imagegen output by implication.
- Run the narrowest relevant validator first, then the aggregate verifier and
  build when shared generated data or UI changes.
- A passing invariant is not the same as a finished feature. Each worker must
  report what remains unavailable and why.
- Keep source material and working evidence private. A private GitHub remote is
  allowed under the parent task's explicit authorization; do not publish the
  repository, source scans, or review artifacts publicly.

## Program acceptance

- Every workstream has a named task, a current owner, and an explicit status.
- No two active workers edit the same source subsystem.
- Completed work includes current-state evidence, not only a plan or green
  syntax check.
- Unresolved source limitations remain explicit rather than being hidden by a
  generic review label.
