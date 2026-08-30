#!/usr/bin/env python3
"""Build the source-comparison ledger from explicit human/audit records.

Comparison records are separate from the playable corpus. This builder checks
that referenced local witnesses still exist and have the recorded checksums,
then emits a compact public index. It never turns a comparison into a score
and refuses an unsafe promotion flag unless the record explicitly carries the
required review status.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from review_dispositions import comparison_disposition


ROOT = Path(__file__).resolve().parents[1]
COMPARISON_ROOT = ROOT / "work" / "source-transcriptions" / "2025"
OUTPUT = ROOT / "public" / "source-comparison-ledger.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_checks(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    comparison_status = str(payload.get("comparisonStatus", ""))
    is_source_audit_status = (
        comparison_status.startswith("autonomously-")
        or comparison_status in {"external-source-blocked", "source-external-blocked"}
    )
    is_corrected_source_record = (
        is_source_audit_status
        or comparison_status == "verified-with-correction-needed"
    )
    source_authority = payload.get("sourceAuthority", {})
    candidate = payload.get("candidateWitness", {})
    if is_corrected_source_record and payload.get("correctedDraft"):
        witnesses = [
            (
                "sourceAuthority",
                source_authority.get("sourceImagePath") or source_authority.get("sourcePdfPath", ""),
                source_authority.get("sourceImageSha256") or source_authority.get("sourcePdfSha256", ""),
            ),
            (
                "inputOmr",
                payload.get("inputOmr", {}).get("path") or candidate.get("candidateMusicXmlPath", ""),
                payload.get("inputOmr", {}).get("sha256") or candidate.get("candidateMusicXmlSha256", ""),
            ),
            ("correctedDraft", payload.get("correctedDraft", {}).get("path", ""), payload.get("correctedDraft", {}).get("sha256", "")),
        ]
    elif is_source_audit_status and payload.get("reviewDraft"):
        # A source-shape-only autonomous block has no alternate candidate
        # witness. Verify the immutable page, selected source-scan OMR, and
        # retained shape-review derivative instead.
        witnesses = [
            (
                "sourceAuthority",
                source_authority.get("sourceImagePath") or source_authority.get("sourcePdfPath", ""),
                source_authority.get("sourceImageSha256") or source_authority.get("sourcePdfSha256", ""),
            ),
            (
                "sourceScanOmr",
                payload.get("sourceScanOmr", {}).get("path", ""),
                payload.get("sourceScanOmr", {}).get("sha256", ""),
            ),
            (
                "reviewDraft",
                payload.get("reviewDraft", {}).get("path", ""),
                payload.get("reviewDraft", {}).get("sha256", ""),
            ),
        ]
    elif is_source_audit_status and candidate.get("candidateMusicXmlPath"):
        # A source-only autonomous block may have no clean PDF or OMR draft.
        # Still verify the immutable scan and the exact-edition MXL checksum;
        # absence of a corrected draft is part of the blocked decision.
        witnesses = [
            (
                "sourceAuthority",
                source_authority.get("sourceImagePath") or source_authority.get("sourcePdfPath", ""),
                source_authority.get("sourceImageSha256") or source_authority.get("sourcePdfSha256", ""),
            ),
            (
                "candidateMusicXml",
                candidate.get("candidateMusicXmlPath", ""),
                candidate.get("candidateMusicXmlSha256", ""),
            ),
        ]
    elif is_source_audit_status and payload.get("inputOmr", {}).get("path"):
        # A retained Audiveris container can be the only structured witness
        # when MusicXML export failed.  It is intentionally verified as an
        # OMR container, never treated as a playable MusicXML candidate.
        witnesses = [
            (
                "sourceAuthority",
                source_authority.get("sourceImagePath") or source_authority.get("sourcePdfPath", ""),
                source_authority.get("sourceImageSha256") or source_authority.get("sourcePdfSha256", ""),
            ),
            (
                "inputOmr",
                payload.get("inputOmr", {}).get("path", ""),
                payload.get("inputOmr", {}).get("sha256", ""),
            ),
        ]
    else:
        witnesses = [
            ("sourceAuthority", payload.get("sourceAuthority", {}).get("sourceImagePath", ""), payload.get("sourceAuthority", {}).get("sourceImageSha256", "")),
            ("candidatePdf", payload.get("candidateWitness", {}).get("candidatePdfPath", ""), payload.get("candidateWitness", {}).get("candidatePdfSha256", "")),
            ("candidateMusicXml", payload.get("candidateWitness", {}).get("candidateMusicXmlPath", ""), payload.get("candidateWitness", {}).get("candidateMusicXmlSha256", "")),
        ]
    for label, relative, expected in witnesses:
        if not relative:
            errors.append(f"{label} path is missing")
            continue
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"{label} file is missing: {relative}")
            continue
        if expected and sha256(path) != expected:
            errors.append(f"{label} checksum mismatch: {relative}")
    return errors


def main() -> int:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in sorted(COMPARISON_ROOT.glob("*-comparison.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        queue_id = str(payload.get("queueId", ""))
        if not queue_id.startswith("sh2025/"):
            errors.append(f"{path.name}: queueId must start with sh2025/")
        if payload.get("safeToPromote") is True:
            errors.append(f"{path.name}: source comparison records cannot self-authorize promotion")
        errors.extend(f"{path.name}: {error}" for error in local_checks(payload))
        record = dict(payload)
        record["auditFile"] = str(path.relative_to(ROOT))
        record["canonicalRecordId"] = queue_id
        record["disposition"] = comparison_disposition(record)
        records.append(record)

    records.sort(key=lambda item: item.get("queueId", ""))
    status_counts: dict[str, int] = {}
    disposition_counts: dict[str, int] = {}
    for record in records:
        status = str(record.get("comparisonStatus", "not-recorded"))
        status_counts[status] = status_counts.get(status, 0) + 1
        state = record["disposition"]["state"]
        disposition_counts[state] = disposition_counts.get(state, 0) + 1
    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "edition": "Sacred Harp, 2025 Edition",
        "status": "review-only" if not errors else "invalid",
        "policy": "This ledger records direct source/candidate comparison work. Disposition state is canonical workflow metadata; it does not alter the immutable source or authorize notation promotion unless safeToPromote is explicitly true.",
        "summary": {
            "records": len(records),
            "safeToPromote": sum(bool(item.get("safeToPromote")) for item in records),
            "statusCounts": status_counts,
            "dispositionCounts": disposition_counts,
            "humanReviewRequired": sum(item["disposition"]["humanReviewRequired"] for item in records),
            "reviewAvailable": sum(item["disposition"]["reviewAvailable"] for item in records),
            "errors": len(errors),
        },
        "errors": errors,
        "records": records,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
