# P2 — Verify source-link health and integrity

## Goal

`/goal` Add source-health verification for every external scan, source page, recording, and MusicXML witness used by the dashboard. Detect unreachable, redirected, changed, or content-drifted sources while preserving immutable retained copies.

## Current evidence

- Mapping checks pass, but they do not prove that external URLs remain reachable or unchanged.
- Source manifests and retained originals already provide hashes for many local artifacts.

## Work

- Inventory all source URLs by edition and role: exact source, reference witness, scan, recording, metadata page.
- Check HTTP status, redirects, content type, and checksum where a retained copy exists.
- Report changed/removed sources without replacing the local authoritative copy automatically.
- Keep network failure, source drift, and missing local retention as separate dispositions.

## Acceptance

- Every URL has a health result with timestamp, status, final URL, and evidence scope.
- Drift never silently rewrites a retained original or promotes a replacement.
- Checks are bounded, repeatable, and safe to run offline with cached evidence.

## Ownership

Own source-health scripts/manifests and retention reports. Do not delete or overwrite retained originals.
