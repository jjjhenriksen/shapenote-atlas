# P2 — Verify source-link health and integrity

## Goal

`/goal` Add source-health verification for every external scan, source page, recording, and MusicXML witness used by the dashboard. Detect unreachable, redirected, changed, or content-drifted sources while preserving immutable retained copies.

## Current evidence

- Mapping checks pass, but they do not prove that external URLs remain reachable or unchanged.
- Source manifests and retained originals already provide hashes for many local artifacts.

## Agent-08 audit evidence — 2026-08-30

- Added a read-only, fail-closed audit at `scripts/agent-08_source_health_audit.py` with validation at `scripts/agent-08_validate_source_health_audit.py`; focused tests are in `tests/test_agent-08_source_health_audit.py`.
- The offline report is `work/agent-08-source-health/agent-08-source-health.json`. It inventories 7,604 distinct URLs across all 11 books, with timestamp, final URL, status, role, evidence scope, retention disposition, and explicit cached-versus-not-checked-offline state for every URL.
- The existing public cache is unchanged and contains 3,738 records from `2026-08-30T04:10:53.129086+00:00`; 3,737 match the current inventory and one cache-only URL remains (`https://shapenote.net/music.htm`). The current corpus exposes 3,867 URLs absent from that cache because the prior URL walker skipped scalar values inside arrays.
- Retention checks found 1,165 retained structured-source originals exact, 90 immutable source scans exact, and 94 candidate PDFs exact as generated review copies. No local checksum or byte-count drift was found. Candidate PDFs and OMR/draft/review artifacts remain generated working copies, not source authority.
- The audit preserves and hashes all 72 current 81b-named files, finding six exact duplicate groups; originals, retained source scans, duplicate copies, and working derivatives were not deleted or replaced.
- A separate live smoke artifact at `work/agent-08-source-health/agent-08-source-health-live-smoke.json` checked 40 bounded URLs: all 40 were reachable; 7,564 remain explicitly `not-checked-budget`.

## Work

- Inventory all source URLs by edition and role: exact source, reference witness, scan, recording, metadata page.
- Check HTTP status, redirects, content type, and checksum where a retained copy exists.
- Report changed/removed sources without replacing the local authoritative copy automatically.
- Keep network failure, source drift, and missing local retention as separate dispositions.

### Remaining blockers

- Full live coverage has not been run; the live smoke is not evidence for the 7,564 budget-excluded URLs.
- Remote content hashes are not fetched by the HEAD/range probe, so external body drift remains unknown even where a retained local hash is exact.
- 6,280 URL records have no manifest-bound local retention, including 126 recording URLs; 32 of the 122 official 2025 scan URLs lack a retained source-image manifest entry.
- The 1,165 structured-source originals are hash-verified retained files, but the score manifest does not itself declare an immutable flag; that provenance policy remains an external/manual assertion.

## Acceptance

- Every URL has a health result with timestamp, status, final URL, and evidence scope.
- Drift never silently rewrites a retained original or promotes a replacement.
- Checks are bounded, repeatable, and safe to run offline with cached evidence.

## Ownership

Own source-health scripts/manifests and retention reports. Do not delete or overwrite retained originals.
