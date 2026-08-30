#!/usr/bin/env python3
"""Validate complete, fail-closed dispositions for unknown key/mode assets."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_data import source_key_to_musicxml  # noqa: E402


def main() -> int:
    corpus = json.loads((ROOT / "public/corpus.json").read_text(encoding="utf-8"))
    report = json.loads((ROOT / "public/key-mode-reconciliation.json").read_text(encoding="utf-8"))
    expected = {}
    expected_resolved_missing_mode = {}
    for song in corpus.get("songs", []):
        for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook"):
            for book_id, preview in (song.get(field) or {}).items():
                ref = preview.get("scoreRef", "")
                if not ref or ref in expected_resolved_missing_mode or ref in expected:
                    continue
                asset = json.loads((ROOT / "public" / ref.lstrip("/")).read_text(encoding="utf-8"))
                declarations = asset.get("musicXmlKeyDeclarations") or []
                if (
                    (asset.get("keyEvidence") or {}).get("status") == "source-verified"
                    and declarations
                    and not any(item.get("modePresent") is True for item in declarations)
                ):
                    expected_resolved_missing_mode[ref] = (book_id, field, asset)
                if (asset.get("keyEvidence") or {}).get("status") == "unknown":
                    expected[ref] = (book_id, field, asset)

    records = report.get("records", [])
    by_ref = {record.get("scoreRef"): record for record in records}
    if set(by_ref) != set(expected) or len(records) != len(by_ref):
        raise SystemExit("key/mode reconciliation does not exactly cover unknown assets")
    for ref, (book_id, field, asset) in expected.items():
        record = by_ref[ref]
        if record.get("outcome") != "external-source-blocked" or record.get("safeToPromote") is not False:
            raise SystemExit(f"{ref}: unknown asset is not externally blocked/fail-closed")
        if record.get("keySignature"):
            raise SystemExit(f"{ref}: blocked asset has a key signature")
        if record.get("bookId") != book_id or record.get("assetField") != field:
            raise SystemExit(f"{ref}: reconciliation identity drift")
        raw = record.get("rawMusicXml", {})
        if raw.get("modePresent") and raw.get("modes") == []:
            raise SystemExit(f"{ref}: raw mode summary is inconsistent")
        candidate = record.get("secondaryKeyCandidate")
        if candidate and (not candidate.get("value") or not source_key_to_musicxml(candidate["value"])):
            raise SystemExit(f"{ref}: malformed secondary key candidate")
        external = record.get("externalSourceEvidence") or {}
        if external.get("status") != "external-source-blocked":
            raise SystemExit(f"{ref}: missing external-source-blocked evidence")
        if not external.get("missingEvidence") or not all(external.get("missingEvidence")):
            raise SystemExit(f"{ref}: external blocker has no precise missing-evidence statement")
        if not external.get("sourceUrls") or not all(external.get("sourceUrls")):
            raise SystemExit(f"{ref}: external blocker has no source locator")

    summary = report.get("summary", {})
    if (
        summary.get("unknownAssets") != len(expected)
        or summary.get("autonomouslyBlocked") != 0
        or summary.get("externalSourceBlocked") != len(expected)
    ):
        raise SystemExit("key/mode reconciliation summary is stale")
    if summary.get("safeToPromote") != 0 or summary.get("recordsStillWithoutAutonomousDisposition") != 0:
        raise SystemExit("key/mode reconciliation is not fail-closed")
    expected_books = Counter(book_id for book_id, _field, _asset in expected.values())
    if summary.get("byBook") != dict(sorted(expected_books.items())):
        raise SystemExit("key/mode reconciliation book counts are stale")
    resolved = report.get("resolvedMissingMode", [])
    resolved_by_ref = {record.get("scoreRef"): record for record in resolved}
    if set(resolved_by_ref) != set(expected_resolved_missing_mode) or len(resolved) != len(resolved_by_ref):
        raise SystemExit("resolved missing-mode ledger does not exactly cover source-keyed assets")
    for ref, (_book_id, _field, asset) in expected_resolved_missing_mode.items():
        record = resolved_by_ref[ref]
        evidence = asset.get("keyEvidence", {}) or {}
        if evidence.get("source") == "structured MusicXML source":
            raise SystemExit(f"{ref}: source-keyed missing-mode asset claims structured-source authority")
        raw_fifths = {
            str(item.get("fifths", ""))
            for item in asset.get("musicXmlKeyDeclarations", [])
            if item.get("fifths", "")
        }
        declared_key = str(asset.get("keySignature", ""))
        encoded = declared_key if ":" in declared_key else source_key_to_musicxml(declared_key)
        expected_fifths = encoded.split(":", 1)[0] if encoded else ""
        conflict = evidence.get("rawFifthsConflict")
        if expected_fifths and raw_fifths and (raw_fifths - {expected_fifths}) and not conflict:
            raise SystemExit(f"{ref}: resolved missing-mode conflict is not recorded")
        if conflict and conflict.get("status") != "preserved-conflict":
            raise SystemExit(f"{ref}: malformed preserved raw-fifths conflict")
        if conflict and set(conflict.get("conflictingFifths", [])) != raw_fifths - {expected_fifths}:
            raise SystemExit(f"{ref}: preserved raw-fifths conflict is incomplete")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
