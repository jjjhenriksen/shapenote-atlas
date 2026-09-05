#!/usr/bin/env python3
"""Validate the provenance and fail-closed policy of clean-source candidates."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "work" / "source-transcriptions" / "2025" / "clean-source-candidates.json"
OMR_RUN = ROOT / "work" / "omr" / "clean-source-omr-run.json"
RECONCILIATION_ROOT = ROOT / "work" / "source-transcriptions"


def main() -> int:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors: list[str] = []
    records = payload.get("records", [])
    seen: set[tuple[str, str]] = set()
    seen_local_paths: set[str] = set()
    candidate_keys: set[str] = set()
    for item in records:
        identity = (str(item.get("songNo", "")).lower(), item.get("pdfUrl", ""))
        if identity in seen:
            errors.append(f"duplicate candidate: {identity}")
        seen.add(identity)
        candidate_key = str(item.get("candidateKey", ""))
        if not candidate_key or candidate_key in candidate_keys:
            errors.append(f"candidate key is missing or duplicated: {identity}")
        candidate_keys.add(candidate_key)
        if item.get("status") != "candidate-source-needs-edition-comparison":
            errors.append(f"candidate is not fail-closed: {identity}")
        if item.get("editionVerified") is not False or item.get("structuredScoreAdmissible") is not False:
            errors.append(f"candidate is marked admissible: {identity}")
        if not item.get("pdfUrl", "").startswith("https://"):
            errors.append(f"candidate is missing a public PDF URL: {identity}")
        local = item.get("localPdf", "")
        if local:
            if local in seen_local_paths:
                errors.append(f"candidate local PDF path is reused: {local}")
            seen_local_paths.add(local)
            path = ROOT / local
            if not path.is_file():
                errors.append(f"candidate PDF is missing: {local}")
                continue
            data = path.read_bytes()
            if not data.startswith(b"%PDF"):
                errors.append(f"candidate is not a PDF: {local}")
            if hashlib.sha256(data).hexdigest() != item.get("sha256"):
                errors.append(f"candidate checksum changed: {local}")
        omr_input = item.get("omrInputPdf", "")
        if omr_input:
            path = ROOT / omr_input
            if not path.is_file() or not path.read_bytes().startswith(b"%PDF"):
                errors.append(f"candidate OMR input is missing or not a PDF: {omr_input}")
            elif item.get("omrInputSha256") and hashlib.sha256(path.read_bytes()).hexdigest() != item["omrInputSha256"]:
                errors.append(f"candidate OMR input checksum changed: {omr_input}")
            elif item.get("omrInputPages") != 1:
                errors.append(f"candidate OMR input is not single-page: {omr_input}")
        historical_omr_input = item.get("historicalOmrInputPdf", "")
        if historical_omr_input:
            historical_path = ROOT / historical_omr_input
            if historical_path.exists():
                errors.append(f"historical candidate derivative unexpectedly exists: {historical_omr_input}")
            if item.get("historicalOmrInputStatus") != "missing-historical-bytes-preserved":
                errors.append(f"historical candidate derivative status is not preserved: {identity}")
            if not item.get("historicalOmrInputSha256"):
                errors.append(f"historical candidate derivative hash is missing: {identity}")
    if errors:
        raise SystemExit("\n".join(errors))
    omr_payload = json.loads(OMR_RUN.read_text(encoding="utf-8")) if OMR_RUN.exists() else {}
    omr_records = omr_payload.get("records", [])
    seen_omr_keys: set[str] = set()
    for item in omr_records:
        candidate_key = str(item.get("candidateKey", ""))
        if candidate_key in seen_omr_keys:
            errors.append(f"duplicate clean-source OMR candidate key: {candidate_key}")
        seen_omr_keys.add(candidate_key)
        if candidate_key not in candidate_keys:
            errors.append(f"clean-source OMR has no current candidate: {candidate_key}")
        if item.get("editionVerified") is not False or item.get("reviewRequired") is not True:
            errors.append(f"clean-source OMR is not fail-closed: {item.get('candidateKey', '')}")
        for artifact in item.get("draftArtifacts", []):
            path = ROOT / artifact
            if not path.is_file() or not zipfile.is_zipfile(path):
                errors.append(f"clean-source OMR artifact is missing or invalid: {artifact}")
    reconciliation_files = sorted(RECONCILIATION_ROOT.glob("**/*-reconciliation.json"))
    for path in reconciliation_files:
        item = json.loads(path.read_text(encoding="utf-8"))
        label = str(item.get("record", path.name))
        if item.get("status") not in {"blocked", "verified"}:
            errors.append(f"invalid reconciliation status: {label}")
        if item.get("status") == "blocked" and item.get("safeToPromote") is not False:
            errors.append(f"blocked reconciliation is promotable: {label}")
        if item.get("status") == "blocked" and not item.get("blockingFindings"):
            errors.append(f"blocked reconciliation has no findings: {label}")
        authority = item.get("sourceAuthority", {})
        source_path = authority.get("path")
        if source_path:
            source = ROOT / source_path
            if not source.is_file():
                errors.append(f"reconciliation source is missing: {label}: {source_path}")
            elif authority.get("sha256") and hashlib.sha256(source.read_bytes()).hexdigest() != authority["sha256"]:
                errors.append(f"reconciliation source checksum changed: {label}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(json.dumps({"candidates": len(records), "downloadedPdfs": sum(bool(item.get("localPdf")) for item in records), "omrRecords": len(omr_records), "reconciliationFiles": len(reconciliation_files), "errors": []}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
