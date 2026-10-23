# Proposed transcription acceptance declarations, v1

**Status: PROPOSED, 2026-10-22.** This is a separate decision-record proposal for
[Atlas #495](https://github.com/jjjhenriksen/shapenote-atlas/issues/495), plus a
read-only local declaration validator. It does not implement policy approval,
score admission, publication, promotion, source certification or rights review.
Issue #495 remains open for those decisions and real evidence. No contract or
behavior of the [v1 verifier/stager](transcription-boundary.md) changes.

A valid declaration can contain `decision: accept`, `reject` or `blocked`.
`accept` describes the owner's **claimed admission decision for the declared
record, edition and extent**. It does not authorize publication. The validator
always returns `acceptance: false`, `authorityVerified: false`,
`evidenceVerified: false`, `sourceCertified: false` and `safeToPromote: false`.
These are statements about what this tool establishes, not an assessment of
whether an independently authorized human decision is substantively correct.

## Local use and proof limits

```sh
python3 scripts/validate_transcription_acceptance.py /private/decision.json
python3 -m unittest discover -s tests -p test_transcription_acceptance.py -v
```

Exit 0 means `valid-declaration`; exit 2 means `invalid-declaration`. The tool
reads the supplied JSON and writes its result to stdout. It does not fetch
locators, open a source image, read a bundle, recompute file hashes, authenticate
a reviewer, verify legal rights, run playback, or write catalogue/public files.
It validates exact fields/types, pin syntax, required references and specified
contradictions. The existing bundle verifier independently checks bundle bytes
against the **out-of-band expected manifest hash**; copying a digest into this
record does not perform that verification or prove who supplied it.

Keep actual records and evidence in ignored/private storage. The committed
[example](../tests/fixtures/transcription-acceptance/synthetic-accepted-declaration.json)
is entirely synthetic: its hashes, owner, reviewer and evidence locators have no
real referents. It exercises an admission declaration with publication blocked.
Passing that fixture provides no source, policy or rights evidence.

## Closed record shape

All objects reject extra/missing fields; versions, enums, booleans and lowercase
hexadecimal pins are strict. Duplicate JSON keys, evidence IDs and repeated
references are rejected. The synthetic example contains the complete shape.

| Field | Required declaration |
| --- | --- |
| `schemaVersion`, `kind`, `contractStatus` | `1`, `shapenote-transcription-acceptance-decision`, `proposed`. This is not a new producer bundle version. |
| `decisionId`, `recordedAt` | Owner-assigned immutable decision identifier; ISO timestamp with timezone. Corrections create a new decision and retain its predecessor. |
| `subject` | Exact `recordId`, `edition` and `extent`: description, explicit source pages, part IDs, measure IDs, and `completeWork` boolean. No `*` wildcard. Partial scope must remain labeled partial. Scope accuracy is a human responsibility. |
| `bundle` | Bundle schema 1, external `manifestSha256`, `sourceSha256`, actual assembly `actualWriterSha256`, and the five fixed payload hashes. Producer repository, **full 40-digit exporting revision**, dirty marker and exporter hash are distinct from the actual historical writer. Preserve both. |
| `bundle.researchFlags` | Original `sourceCertified: false`, `safeToPromote: false`, including after an admission declaration. Never rewrite a research bundle as an accepted artifact. |
| `privateEvidenceLocator` | Nonempty opaque `private://...` retained archive identifier. This declaration does not check privacy, accessibility or retention. |
| `evidence` | Receipts with unique `id`, typed `kind`, nonempty `locator`, receipt `sha256` and `subjectSha256`. Locators are opaque data, never instructions or auto-opened URLs. |
| `owner` | Named decision owner and `authorizationEvidence` references. A human must establish that this separate authority covers the particular record/edition/extent and intended operation. The tool cannot establish authority. |
| `decision`, `decisionReasons` | `accept`, `reject` or `blocked`, plus nonempty reasons. Rejection/mismatch remains explicit and is not repaired from parser or engraving results. |
| `humanImageReview` | `matched`, `mismatch` or `unreviewed`; exact source hash and the same extent; reviewer, timezone-aware review timestamp, human-image evidence references and note. An unreviewed gate uses null reviewer/time. A completed review requires all of these declarations. |
| `assessments` | Every assessment below, each with `disposition`, typed `evidence` references and explanatory `note`. No omnibus validated flag. |
| `unsupportedSemantics`, `uncertainties`, `policyRestrictions` | Explicit lists, including empty lists. These apply to the declared extent. Keep unsupported constructs, ambiguous readings, source restrictions and remaining human gates visible. |
| `remainingBlockers` | Separate `admission` and `publication` lists. A blocked disposition needs its corresponding nonempty list. |
| `publication` | Separate `permitted`, `blocked` or `not-requested` claim. No source redistribution or publication follows from admission. |
| `predecessors` | `none` with an empty `records` array, or `preserved` with predecessor decision IDs, manifest pins and preservation evidence. Never self-reference or overwrite historical decisions/evidence. The tool cannot discover undeclared predecessors. |
| `residualAtlasIssues` | Explicit Atlas issue URLs, including unresolved source/image/policy/release work. Validation cannot close them; producer completion cannot resolve Atlas obligations. |

## Independent assessments and reference bindings

Every disposition is `passed`, `failed`, `unknown` or `not-applicable`, with a
nonempty note. `passed`/`failed` require evidence; unknown/not-applicable retain
explicit notes and may have no evidence. Evidence kind must exactly equal the
assessment name. Evidence receipts bind to the manifest hash except
`sourceFidelity` and `humanImage` (source hash), `xmlDownload` (standalone XML
payload hash), and `mxlDownload` (MXL payload hash). Authorization references use
kind `authorization` and the current manifest hash; preservation references use
kind `predecessor` and the prior manifest hash. These are declaration bindings,
not verification that a receipt actually supports its claim.

- `integrity` and `parsing` record byte checks and structural/parser checks.
- `engraving` records visual usability; `usefulPartial` records usefulness of the
  declared partial extent. Neither establishes exact source fidelity.
- `sourceFidelity` records exact-source comparison for the entire declared
  extent; `exactMapping` records the exact catalogue/edition/extent relationship.
- `publicationRights` records rights for the intended distribution scope,
  separately from source fidelity, mapping and internal admission. Record scope,
  license/restrictions and authorization in the retained evidence/note. Source
  image redistribution requires its own applicable permission; a score license
  must never silently stand in for it.
- `xmlDownload`, `mxlDownload`, `uiLabels`, `writtenPlayback` and
  `encodedRepeatPlayback` record exact downloadable bytes, honest complete/partial
  and source-status labels, written-order playback and encoded-repeat playback.
  Download receipt subject pins must match the declared candidate payloads.
- `hostedReleaseQa` and `nativeReleaseQa` remain separate release checks. A target
  outside the intended release can be explicitly not-applicable with a reason;
  a local/fixture result must never be labeled as hosted or native proof.

`accept` requires passed integrity, parsing, exact mapping and source fidelity,
a matched named human image review, and no admission blockers, unsupported
semantics, uncertainties or policy restrictions within the declared extent.
A source mismatch forces failed source fidelity. A `blocked` record retains at
least one admission blocker. Rejection reasons remain mandatory even when
source comparison was not performed.

A publication-permitted declaration additionally requires passed engraving,
publication rights, download bytes, UI labels and both playback assessments,
resolved hosted/native QA (passed or explicitly not-applicable), and no
publication blockers. Useful-partial status is recorded independently and
cannot stand in for any gate. An internally admitted source-faithful extent can
therefore coexist with unknown rights and blocked publication.

## Work still required under #495

Maintainers must approve or revise this proposed schema, determine who may make
each decision and which policy restrictions apply, and review real retained
source evidence and permission scope. Any eventual admission/publication system
needs separately authorized implementation, immutable decision/evidence retention,
exact byte verification and migration/release policy. This local validator adds
no moving Transcriber imports, automatic promotion, source redistribution,
public asset writes, issue closure or playback integration.
