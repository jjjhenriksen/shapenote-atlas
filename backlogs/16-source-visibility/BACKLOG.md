# P2 — Surface source health and provenance clearly

## Goal

Expose the existing source-health and provenance state in the dashboard so a
user can tell whether a link is cached, externally checked, unavailable,
reference-only, or authoritative.

## Current evidence

- `public/source-health.json` covers 3,738 URLs in the current offline report.
- Retained originals and hashes exist for many source images and candidates.
- Source links, scans, candidate PDFs, and review evidence are shown in
  separate places, but the source-health result is not a visible first-class
  UI surface.

## Work

- Inspect current source links and health schema before adding UI.
- Add concise per-record source status and provenance scope where it helps a
  user make a decision; avoid dumping raw health data into the main reader.
- Distinguish exact source, alternate witness, scan, recording, candidate,
  cached evidence, remote failure, and drift.
- Keep offline and live-check timestamps/limitations explicit.

## Acceptance

- A selected record's source area explains what is authoritative and what is
  evidence-only.
- Health failures never hide the retained original or silently substitute a
  new URL.
- The UI remains usable for records with many source links and for records
  with none.
- Build, startup, browser, and accessibility checks pass.

## Ownership

Current UI status (2026-09-05): selected-record source-health timestamps, current/cached/budget distinctions, retention states, and provenance labels are surfaced. Historical cache counts below are baseline evidence only; refreshed health truth remains owned by the health lane.

Own source-health/provenance presentation in `src/main.jsx` and
`src/styles.css`, plus UI fixtures. Do not edit `scripts/check_source_health.py`
or source manifests; coordinate with the source-health worker for schema
changes.
