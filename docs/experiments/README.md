# Historical OMR experiments

The isolated SH1991/SH2025 recognition experiments are retired from Atlas's
maintained tree. Active image-first transcription belongs to
[Shape-note Transcriber](https://github.com/jjjhenriksen/shapenote-transcriber);
Atlas retains its [pinned bundle consumer](../transcription-boundary.md).

## Recovery and provenance

All 134 removed files are preserved byte-for-byte at the published
[archive tag](https://github.com/jjjhenriksen/shapenote-atlas/tree/archive/omr-experiments-20261019),
which pins Atlas commit `744f0b588abae108aa0649202ae1601d58d90e3e`.
The [archive manifest](../provenance/omr-experiment-archive-20261019.json)
lists every removed path and its SHA-256: 41 scripts, 19 tests, 48 experiment
reports/contracts and 26 Audiveris patch/probe files.

Use the archive tag or its full commit SHA to inspect historical files:

```sh
git show 744f0b588abae108aa0649202ae1601d58d90e3e:scripts/omr_score_audit.py
```

Restore a needed historical path only in a separate research branch/worktree.
Archive reports retain their original limitations, failures and frozen-cohort
boundaries. They are not fresh results or an accepted recognition pipeline.
Do not rerun or tune consumed cohorts to validate this housekeeping change.

This is forward-only source-tree cleanup, not a history rewrite. No old commits,
branches, PRs, local worktrees, scans, frozen readings or generated scores are
deleted or relocated. The separate image-first research branch is unchanged.
The seven unmerged research PRs #485–#491 are also unchanged; they are not part
of this mainline archive and should not be merged merely to recover old work.

## Retained Atlas responsibilities

Catalogue/display/playback, source correction and audit tools, the semantic
MusicXML parser, edition/key reconciliation, existing public assets and the
research-only bundle verifier/stager are unchanged. In particular, the older
`run_clean_source_omr.py`, `run_cleaned_omr.py` and `audit_omr_drafts.py` commands
remain because existing catalogue reconciliation/verification still uses their
artifacts. This change does not remove every OMR-related word or workflow.

Only the retired experiment fixture commands and their Pillow/NumPy install
step are removed from reader CI. Reader tests, semantic/evidence fixtures,
bundle tests, playback/transposition validation, build and browser tests stay.
No score is promoted; this archive does not alter source-certification claims.
