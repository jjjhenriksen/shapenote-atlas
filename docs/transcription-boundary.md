# Transcription ownership boundary

2026-10-19. The active image-first transcription workflow now belongs to
[Shape-note Transcriber](https://github.com/jjjhenriksen/shapenote-transcriber).
Atlas owns catalogue/display/playback and any future acceptance/import decisions.

The extraction retains six relevant commits from the Atlas research branch
`research/image-first-transcription-20261019` at
`975082ddd9759921c31bd83ad2088bdcc9b3eddf`. Their rewritten hash mapping and
byte-checked baseline manifest live in the transcriber's `docs/provenance/`.
Atlas history was not rewritten. This active workflow was not on Atlas main;
there was no mainline active implementation to delete. Older OMR experiments
are now [archived outside the maintained tree](experiments/README.md), with a
hash manifest and a pinned recovery tag. Shared catalogue/source diagnostics
and all local historical evidence remain intact.

The earlier OMR lineage and the research stack from Atlas PRs #485–#491 now
belong to the transcriber's isolated `research/legacy-omr/` subtree. Its migration
manifest maps all retained commits and source branch heads. Those source PRs
must not be merged into Atlas to recover the research; use the destination repo.

Do not merge the old image-first research branch into Atlas to install the
transcriber. Make future active transcription changes in the new repository.
The original research worktree and ignored evidence roots stay available for
provenance, not as a second maintained production implementation.

## Artifact interface (v1)

The transcriber exports a directory containing `bundle.json` and exactly:
`candidate.musicxml`, `candidate.mxl`, `report.json`, `resolved-reading.json`,
`comparison.json`. Its `docs/bundle-v1.md` owns the wire specification.

The manifest declares `schemaVersion=1`,
`kind=shapenote-transcription-bundle`, `status=research-candidate`, source hash,
producer repository/full commit/dirty marker/exporter hash, and SHA-256 for each
payload. `sourceCertified` and `safeToPromote` must both be false. The importer
checks the fixed file list, external manifest pin, every payload hash,
report/reading/source bindings, report eligibility and MXL/XML consistency.
Malformed JSON structures, archives and XML are rejected before staging, with
an error message and exit status 2. This includes checking XML well-formedness;
it does not establish musical correctness or source accuracy.
An archived score with a declared uncompressed size different from the candidate
XML is rejected before decompression, since its bytes cannot match the candidate.

Atlas has a deliberately independent stdlib-only verifier/stager:

```sh
python3 scripts/import_transcription_bundle.py /private/bundle \
  --expected-manifest-sha256 HASH_FROM_EXPORT --verify-only
python3 scripts/import_transcription_bundle.py /private/bundle \
  --expected-manifest-sha256 HASH_FROM_EXPORT
python3 -m unittest discover -s tests -p test_transcription_bundle_import.py -v
```

The pin must come from the exporting owner/receipt, not be silently computed by
the importer from an untrusted directory. Hash integrity is not authenticity,
source accuracy, semantic validation or acceptance. Actual assembly writer
hashes remain in the reports; the exporting HEAD is not falsely attributed to
historical frozen assembly.

Staging is confined to ignored
`work/transcription-imports/<manifest-sha256>/bundle/`, with a separate Atlas
import receipt. No output-path override, promotion flag, public asset/catalogue
write or playback integration is provided. Staging never makes a score accepted.
The bundle and receipt are written to a temporary sibling before publishing the
complete import directory. Failed writes are cleaned up so the same pin can be
retried; existing import directories are not replaced.
Full source/reader/adjudication evidence stays in its retained local evidence
root; the compact exchange bundle is not a substitute for that archive.

No transcriber checkout, import path, symlink, submodule, npm/Python dependency,
source scan or generated real score is added to Atlas. A new bundle schema
requires explicit consumer changes. Future accepted-score publication needs a
separate acceptance contract, not reinterpretation of a research candidate.

The separate [proposed acceptance-declaration v1](transcription-acceptance-v1.md)
adds a read-only local schema check for future decision records. Passing that
check does not grant acceptance or change the verifier/stager boundary.

## Explicit three-part v2 profile

The separate [three-part research bundle v2](transcription-bundle-v2.md) adds an
opt-in `--bundle-version 2` / `bundle_version=2` consumer for exactly three
monophonic four-shape parts. Its independent parser checks supported reading/XML
semantics and version/profile/count agreement before the same private atomic
staging. Default v1 behavior remains unchanged and rejects v2. This extension
does not certify sources or authorize catalogue, public, UI or playback changes.
