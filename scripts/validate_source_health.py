#!/usr/bin/env python3
"""Validate the source-health report and retained-file evidence."""

from __future__ import annotations

import hashlib
import json

from check_source_health import OUTPUT, ROOT, inventory_sources


NETWORK_STATUSES = {"reachable", "redirected", "unreachable", "network-error", "cached", "not-checked-offline", "not-checked-budget"}
LOCAL_STATUSES = {"exact", "drifted", "missing"}


def main() -> int:
    if not OUTPUT.is_file():
        raise SystemExit(f"source-health report is missing: {OUTPUT}")
    try:
        payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"source-health report is invalid JSON: {exc}") from exc
    records = payload.get("records", [])
    if not isinstance(records, list):
        raise SystemExit("source-health records must be a list")
    errors: list[str] = []
    expected_urls = set(inventory_sources())
    actual_urls = [record.get("url") for record in records if isinstance(record, dict)]
    if len(actual_urls) != len(set(actual_urls)):
        errors.append("duplicate URL records")
    if set(actual_urls) != expected_urls:
        errors.append(f"inventory mismatch: report={len(set(actual_urls))}, current={len(expected_urls)}")

    for record in records:
        if not isinstance(record, dict):
            errors.append("non-object source-health record")
            continue
        url = str(record.get("url", ""))
        if not url.startswith(("http://", "https://")):
            errors.append(f"invalid URL: {url}")
        if record.get("status") not in NETWORK_STATUSES:
            errors.append(f"invalid network status for {url}: {record.get('status')}")
        for field in ("checkedAt", "finalUrl", "evidenceScope"):
            if not record.get(field):
                errors.append(f"missing {field}: {url}")
        if not isinstance(record.get("roles"), list) or not record.get("roles"):
            errors.append(f"missing roles: {url}")
        if not isinstance(record.get("references"), list) or not record.get("references"):
            errors.append(f"missing references: {url}")
        for evidence in record.get("localEvidence", []):
            path_text = str(evidence.get("path", ""))
            path = (ROOT / path_text).resolve()
            try:
                path.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"local evidence escapes project root: {url}: {path_text}")
                continue
            if evidence.get("status") not in LOCAL_STATUSES:
                errors.append(f"invalid local status for {url}: {evidence.get('status')}")
            if evidence.get("status") == "exact":
                if not path.is_file():
                    errors.append(f"exact local evidence is missing: {url}: {path_text}")
                    continue
                data = path.read_bytes()
                expected_hash = str(evidence.get("expectedSha256", ""))
                if expected_hash and hashlib.sha256(data).hexdigest() != expected_hash:
                    errors.append(f"local checksum changed after report: {url}: {path_text}")
                if evidence.get("actualBytes") not in (None, len(data)):
                    errors.append(f"local byte count changed after report: {url}: {path_text}")
            if evidence.get("status") == "drifted" and evidence.get("actualSha256") == evidence.get("expectedSha256"):
                errors.append(f"drifted evidence has equal hashes: {url}: {path_text}")

    summary = payload.get("summary", {})
    if summary.get("totalUrls") != len(records):
        errors.append("summary totalUrls does not match records")
    computed_statuses = {status: sum(record.get("status") == status for record in records) for status in sorted({record.get("status") for record in records})}
    if summary.get("byStatus") != computed_statuses:
        errors.append("summary byStatus does not match records")
    if errors:
        raise SystemExit("\n".join(errors))
    print(json.dumps({"report": str(OUTPUT), "records": len(records), "errors": []}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
