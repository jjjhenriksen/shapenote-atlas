#!/usr/bin/env python3
"""Validate an agent-08 source-health report without mutating its inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import importlib.util
from pathlib import Path

AUDIT_SCRIPT = Path(__file__).resolve().parent / "agent-08_source_health_audit.py"
AUDIT_SPEC = importlib.util.spec_from_file_location("agent_08_source_health_audit", AUDIT_SCRIPT)
assert AUDIT_SPEC and AUDIT_SPEC.loader
AUDIT = importlib.util.module_from_spec(AUDIT_SPEC)
AUDIT_SPEC.loader.exec_module(AUDIT)
DEFAULT_OUTPUT = AUDIT.DEFAULT_OUTPUT
KNOWN_BOOKS = AUDIT.KNOWN_BOOKS
ROOT = AUDIT.ROOT
load_json = AUDIT.load_json


HEALTH_STATUSES = {"reachable", "redirected", "unreachable", "network-error", "cached", "not-checked-offline", "not-checked-budget"}
LOCAL_STATUSES = {"exact", "drifted", "missing"}


def validate(report_path: Path) -> list[str]:
    errors: list[str] = []
    payload = load_json(report_path)
    if not payload:
        return [f"report is missing or invalid JSON: {report_path}"]
    if payload.get("version") != "agent-08-source-health-v1":
        errors.append(f"unexpected report version: {payload.get('version')}")
    records = payload.get("records")
    if not isinstance(records, list):
        return errors + ["records must be a list"]
    urls = [record.get("url") for record in records if isinstance(record, dict)]
    if len(urls) != len(set(urls)):
        errors.append("duplicate URL records")
    for record in records:
        if not isinstance(record, dict):
            errors.append("non-object source record")
            continue
        url = str(record.get("url", ""))
        if not url.startswith(("http://", "https://")):
            errors.append(f"invalid URL: {url}")
        if record.get("status") not in HEALTH_STATUSES:
            errors.append(f"invalid health status for {url}: {record.get('status')}")
        for field in ("checkedAt", "finalUrl", "evidenceScope", "healthMode", "driftDisposition", "remoteHashScope"):
            if not record.get(field):
                errors.append(f"missing {field}: {url}")
        if not isinstance(record.get("books"), list):
            errors.append(f"books must be a list: {url}")
        if not isinstance(record.get("roles"), list) or not record.get("roles"):
            errors.append(f"roles missing: {url}")
        if not isinstance(record.get("references"), list) or not record.get("references"):
            errors.append(f"references missing: {url}")
        for evidence in record.get("localEvidence", []):
            if not isinstance(evidence, dict):
                errors.append(f"non-object local evidence: {url}")
                continue
            path_text = str(evidence.get("path", ""))
            path = (ROOT / path_text).resolve()
            try:
                path.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"local evidence escapes project root: {url}: {path_text}")
                continue
            if evidence.get("status") not in LOCAL_STATUSES:
                errors.append(f"invalid local status: {url}: {path_text}")
                continue
            if evidence.get("authority") == "source-authority" and evidence.get("kind") == "review-working-copy":
                errors.append(f"working copy marked source authority: {url}: {path_text}")
            if evidence.get("status") == "exact":
                if not path.is_file():
                    errors.append(f"exact evidence is missing: {url}: {path_text}")
                    continue
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if evidence.get("expectedSha256") and digest != evidence.get("expectedSha256"):
                    errors.append(f"local checksum changed after report: {url}: {path_text}")
                expected_bytes = evidence.get("expectedBytes")
                if expected_bytes not in (None, "", path.stat().st_size):
                    errors.append(f"local byte count changed after report: {url}: {path_text}")
            if evidence.get("status") == "drifted" and evidence.get("actualSha256") == evidence.get("expectedSha256"):
                errors.append(f"drifted evidence has equal hashes: {url}: {path_text}")

    inventory = payload.get("inventory", {})
    if inventory.get("urlCount") != len(records):
        errors.append("inventory urlCount does not match records")
    report_books = set(inventory.get("books", []))
    if report_books != KNOWN_BOOKS:
        errors.append(f"book inventory mismatch: {sorted(report_books)}")
    summary = payload.get("summary", {})
    if summary.get("totalUrls") != len(records):
        errors.append("summary totalUrls does not match records")
    expected_health = {status: sum(record.get("status") == status for record in records) for status in sorted({record.get("status") for record in records})}
    if summary.get("byHealthStatus") != expected_health:
        errors.append("summary byHealthStatus does not match records")
    duplicate = payload.get("duplicate81b", {})
    if duplicate.get("duplicateGroupCount") != len(duplicate.get("duplicateGroups", [])):
        errors.append("81b duplicateGroupCount does not match groups")
    for group in duplicate.get("duplicateGroups", []):
        files = group.get("files", [])
        if len(files) < 2:
            errors.append("81b duplicate group has fewer than two files")
        for entry in files:
            path = ROOT / str(entry.get("path", ""))
            if not path.is_file():
                errors.append(f"81b duplicate file missing: {path}")
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != group.get("sha256"):
                errors.append(f"81b duplicate hash changed: {path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = args.report if args.report.is_absolute() else ROOT / args.report
    errors = validate(report)
    if errors:
        raise SystemExit("\n".join(errors))
    payload = load_json(report)
    print(json.dumps({"report": str(report), "records": len(payload["records"]), "books": len(payload["inventory"]["books"]), "errors": []}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
