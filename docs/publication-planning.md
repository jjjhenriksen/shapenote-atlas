# Read-only publication planning (v1 bundle)

`plan_transcription_publication.py` binds a proposed acceptance declaration to a
verified v1 bundle, a caller-supplied corpus snapshot, and an explicit inventory
of prior decisions. It prints JSON only. It does not stage, publish, edit a
mapping, copy source images, or certify music. Exit status is always **2**:
execution remains blocked even when a plan is internally consistent.

```sh
python3 -B scripts/plan_transcription_publication.py DECISION.json BUNDLE_DIR \
  --expected-manifest-sha256 OWNER_SUPPLIED_PIN \
  --corpus public/corpus.json --inventory PRIVATE_INVENTORY.json
```

Inventory format (one row per existing decision/version):

```json
{"schemaVersion":1,"records":[{"recordId":"exact-record-id","edition":"sh2025","decisionId":"prior-version","manifestSha256":"64-lowercase-hex-digits"}]}
```

An empty inventory is an explicit caller assertion, **not** evidence that no
prior publication exists. The command hashes the corpus and inventory snapshots;
it cannot establish their completeness/currentness. Its stdout may contain
private evidence metadata and existing score provenance: keep it private.

Output identifies exact record/edition mapping, partial extent, proposed version,
XML/MXL byte hashes, predecessor omissions and version collisions, proposed UI
labels, unsupported semantics, restrictions and declared gate states. Duplicate
or missing target records fail closed. It never joins by title. A replacement is
only a proposed diff; original assets and mappings remain untouched.

`authorityVerified`, `evidenceVerified`, `acceptance`, `sourceCertified` and
`safeToPromote` remain false. The declaration's owner/evidence assertions are not
independently authenticated. A separately authorized reviewer must verify exact
scope, source fidelity, rights, all gates, and the completeness of the inventory
before any future mutating command can be designed or used. Valid JSON, passing
parser tests, and consistent hashes do not grant approval.

This command intentionally uses the existing **v1** provenance checker. Opt-in
v2/v3 bundle consumers do not silently broaden this planner's accepted schema.
Synthetic tests exercise read-only behavior, partial and rejected proposals,
wrong/ambiguous mappings, changed bundle bytes, malformed inventories, and
predecessor/version collisions. They do not validate any real score.
