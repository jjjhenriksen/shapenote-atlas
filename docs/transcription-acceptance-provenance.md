# Read-only declaration/bundle provenance check

The [proposed acceptance declaration](transcription-acceptance-v1.md) validates
syntax and internal declarations. The [v1 bundle verifier](transcription-boundary.md)
checks independently pinned bundle bytes. These checks can both pass while the
declaration names different producer, source, writer or payload pins.

`scripts/check_transcription_acceptance_provenance.py` compares those two inputs
without staging them or changing either existing API. It is an engineering aid
for preparing a draft human review under
[Atlas #495](https://github.com/jjjhenriksen/shapenote-atlas/issues/495).
It does not execute acceptance policy or make a human decision.

```sh
python3 scripts/check_transcription_acceptance_provenance.py \
  /private/decision.json /private/bundle \
  --expected-manifest-sha256 HASH_FROM_EXPORTING_OWNER
python3 -m unittest discover -s tests -p test_transcription_acceptance_provenance.py -v
```

The expected manifest SHA-256 is mandatory and must come independently from the
exporting owner/receipt. Do not compute a supposedly trusted pin from the input
bundle and pass it back to this command. Hashes establish byte consistency;
they do not authenticate the owner who supplied the pin.

## Receipt contract, version 1

The command reads the declaration once, validates that snapshot, and binds the
receipt to its exact bytes as `declarationSha256`. Semantically equal JSON with
different whitespace has a different pin. It calls the existing bundle
`verify()` function and consumes only the returned manifest/payload snapshots.
It never reopens a payload to discover the writer or calculate a comparison pin.
Duplicate provenance keys in the captured manifest/report are rejected rather
than silently selecting the last value.

A receipt has `schemaVersion: 1`,
`kind: shapenote-transcription-provenance-check`, and:

| Field | Meaning |
| --- | --- |
| `status` | `consistent` only when both inputs validate and all named provenance fields match; otherwise `blocked`. |
| `declarationSha256` | Exact captured declaration-byte hash, including for malformed JSON. Null if the declaration could not be read. |
| `expectedBundleManifestSha256` | Explicit external pin supplied by the caller. |
| `verifiedBundleManifestSha256` | Captured manifest hash after successful bundle verification and unambiguous provenance parsing; otherwise null. |
| `declarationValid` | The captured declaration passed the existing proposed syntax/consistency validator. This does not approve its decision. |
| `bundleIntegrityVerified` | The existing v1 bundle checks and unambiguous manifest/report parsing passed. This is not source-image accuracy. |
| `declaredDispositions` | Original admission/publication, human-image and assessment dispositions, limitations, policy restrictions, remaining blockers and residual Atlas issues. Null when the declaration is invalid. These remain **declared**, not verified human judgments. |
| `mismatches` | Each differing `field`, `declared` value and `verified` value. |
| `blockers` | `invalid-declaration`, `bundle-verification-failed`, or `provenance-mismatch`, each with a diagnostic detail. |

Comparison covers bundle schema/manifest/source, the four named producer fields
(repository, full revision, dirty marker, exporter hash), all five fixed payload
hashes, actual assembly `report.writerSha256`, and original research flags.
The actual writer is compared separately from the exporting revision/exporter;
historical writer and exporter hashes can legitimately differ. Extra manifest
or producer metadata supported by the existing verifier does not cause a false
mismatch in the named provenance fields.

Exit 0 means byte consistency only. A matching `reject` or `blocked` declaration
can therefore exit 0; unknown source/rights assessments remain unknown. Existing
admission/publication blockers are preserved under `declaredDispositions`; they
are separate from this check's byte-consistency blockers. Exit 2 means malformed,
unavailable, unsupported, unverified or mismatched inputs. The JSON receipt goes
to stdout; missing required CLI arguments use normal argument-parser errors.

## Proof and storage boundaries

Every receipt retains `acceptance: false`, `authorityVerified: false`,
`evidenceVerified: false`, `sourceCertified: false` and `safeToPromote: false`.
Here `evidenceVerified` refers to retained human/source/rights evidence, not the
bundle-byte integrity checks described above. Consistent pins do not prove
record/edition/extent mapping, source-image fidelity, reviewer authority, private
archive retention, publication rights, playable correctness or release readiness.
The bundle contains no source image or independent human approval to establish
those claims. The acceptance policy remains proposed and human review stays
separate.

The standalone command writes no input, staging, catalogue, public asset or local
module-cache files. It never calls `stage()`, opens evidence locators, imports a
Transcriber checkout or publishes a score. Keep real declarations, bundles,
source evidence and any redirected receipts in ignored/private storage. Tests
use only synthetic bundles and the existing wholly synthetic declaration.
