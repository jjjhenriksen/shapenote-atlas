#!/usr/bin/env python3
"""Validate the additive semantic-fidelity ledger and its corpus join."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public" / "corpus.json"
LEDGER = ROOT / "public" / "semantic-fidelity-ledger.json"
ALLOWED = {
    "verified-structured-source-serialization",
    "review-only-alternate-witness",
    "review-only-draft",
    "blocked-no-retained-source",
    "blocked-missing-retained-source",
    "blocked-source-parse-failure",
    "blocked-semantic-diff",
    "blocked-missing-asset",
    "rejected-source-mismatch",
}
TAXONOMY_KEYS = {
    "draft-is-not-authoritative-source",
    "event-stream-diff",
    "measure-count-diff",
    "repeat-ending-semantics-not-modeled-in-generated-asset",
    "sound-navigation-semantics-not-modeled-in-generated-asset",
    "lyrics-not-modeled-in-generated-asset",
    "shape-notehead-count-differs",
    "key-declaration-differs",
    "time-signature-differs",
    "retained-source-mxl-unavailable",
    "manifest-source-path-missing",
    "witness-is-not-exact-edition-source",
    "source-checksum-drift",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    records = ledger.get("records", [])
    taxonomy = set((ledger.get("coverage", {}) or {}).get("differenceTaxonomy", {}).keys())
    if taxonomy != TAXONOMY_KEYS:
        raise SystemExit("semantic-fidelity difference taxonomy is stale")
    expected: set[tuple[str, str, str, str]] = set()
    for song in corpus.get("songs", []):
        for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook"):
            for book_id, preview in (song.get(field) or {}).items():
                if preview.get("scoreRef"):
                    expected.add((f"{song.get('id', '')}::{book_id}/{str(song.get('songNo', '')).lower()}", field, preview.get("scoreRef", ""), book_id))
    actual: set[tuple[str, str, str, str]] = set()
    if ledger.get("safeToPromote", 0) not in (0, False, None):
        raise SystemExit("semantic fidelity ledger must remain fail-closed")
    if ledger.get("summary", {}).get("safeToPromote") != 0:
        raise SystemExit("semantic fidelity summary must remain fail-closed")
    for record in records:
        status = record.get("status")
        if status not in ALLOWED:
            raise SystemExit(f"invalid semantic-fidelity status: {status!r}")
        if record.get("safeToPromote") is not False:
            raise SystemExit(f"record is not fail-closed: {record.get('mappingId')}")
        key = (record.get("mappingId", ""), record.get("field", ""), record.get("assetRef", ""), record.get("bookId", ""))
        if key in actual:
            raise SystemExit(f"duplicate semantic-fidelity mapping: {key}")
        actual.add(key)
        asset = ROOT / record.get("assetPath", "")
        if record.get("assetExists") is not True or not asset.is_file():
            raise SystemExit(f"missing semantic-fidelity asset: {record.get('mappingId')}")
        if record.get("assetSha256") and sha256(asset) != record.get("assetSha256"):
            raise SystemExit(f"asset checksum drift: {record.get('mappingId')}")
        source = record.get("sourcePath")
        if source and record.get("sourceExists"):
            source_path = ROOT / source
            if not source_path.is_file():
                raise SystemExit(f"source path is marked present but missing: {source}")
            if record.get("sourceSha256") and sha256(source_path) != record.get("sourceSha256"):
                raise SystemExit(f"source checksum drift: {record.get('mappingId')}")
        if status == "verified-structured-source-serialization":
            comparison = record.get("sourceComparison", {})
            if comparison.get("eventStreamsExactAfterRecordedTransform") is not True or comparison.get("measureCountsExactAfterRecordedTransform") is not True:
                raise SystemExit(f"verified record lacks exact event-stream comparison: {record.get('mappingId')}")
            if record.get("differences", []).count("event-stream-diff"):
                raise SystemExit(f"verified record contains event-stream diff: {record.get('mappingId')}")
    if actual != expected:
        missing = sorted(expected - actual)[:5]
        extra = sorted(actual - expected)[:5]
        raise SystemExit(f"semantic-fidelity corpus join mismatch; missing={missing}, extra={extra}")
    if ledger.get("summary", {}).get("mappingRecords") != len(records):
        raise SystemExit("semantic-fidelity mapping count is stale")
    comparison_count = sum(isinstance(record.get("sourceComparison"), dict) for record in records)
    if ledger.get("summary", {}).get("retainedSourceComparisons") != comparison_count:
        raise SystemExit("semantic-fidelity retained-source count is stale")
    if ledger.get("summary", {}).get("nonComparableMappings") != len(records) - comparison_count:
        raise SystemExit("semantic-fidelity non-comparable count is stale")
    counted = {}
    differences = {}
    measure_dispositions = {}
    for record in records:
        counted[record["status"]] = counted.get(record["status"], 0) + 1
        for difference in record.get("differences", []):
            if difference not in taxonomy:
                raise SystemExit(f"unclassified semantic-fidelity difference: {difference}")
            differences[difference] = differences.get(difference, 0) + 1
        comparison = record.get("sourceComparison", {})
        for part in comparison.get("parts", []) if isinstance(comparison, dict) else []:
            disposition = str(part.get("measureCountDisposition", "not-compared"))
            measure_dispositions[disposition] = measure_dispositions.get(disposition, 0) + 1
    if counted != ledger.get("summary", {}).get("statusCounts"):
        raise SystemExit("semantic-fidelity status counts are stale")
    if differences != ledger.get("summary", {}).get("differenceCounts"):
        raise SystemExit("semantic-fidelity difference counts are stale")
    if measure_dispositions != ledger.get("summary", {}).get("measureDispositionCounts"):
        raise SystemExit("semantic-fidelity measure disposition counts are stale")
    print(json.dumps({"mappingRecords": len(records), "uniqueAssets": len({r.get('assetRef') for r in records}), "statusCounts": counted, "errors": len(ledger.get('errors', []))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
