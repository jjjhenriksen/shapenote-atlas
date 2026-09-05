#!/usr/bin/env python3
"""Validate the additive 1991/2025 shared-edition reconciliation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public" / "corpus.json"
REPORT = ROOT / "public" / "shared-edition-reconciliation.json"
EDITIONS = ("sh1991", "sh2025")
FIELDS = ("title", "keyMode", "meter", "timeSignature", "lyrics", "repeatEndings", "parts", "notation")
ALLOWED_STATUSES = {
    "unchanged",
    "changed",
    "unavailable",
    "alternate-witness-only",
    "changed-alternate-witness",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    expected = {
        (str(song.get("songNo", "")).lower(), str(song.get("id", "")))
        for song in corpus.get("songs", [])
        if set(EDITIONS).issubset(song.get("books", []))
    }
    errors: list[str] = []
    records = report.get("records", [])
    seen: set[tuple[str, str]] = set()
    expected_records = {
        (str(song.get("songNo", "")).lower(), str(song.get("id", ""))): song
        for song in corpus.get("songs", [])
        if set(EDITIONS).issubset(song.get("books", []))
    }
    source = report.get("source", {})
    if source.get("corpus") != "public/corpus.json":
        errors.append("report source corpus path is not canonical")
    if source.get("corpusSha256") != sha256(CORPUS):
        errors.append("report corpus checksum is stale")
    if report.get("summary", {}).get("safeToPromote") != 0:
        errors.append("report safeToPromote must be zero")
    for index, record in enumerate(records):
        identity = record.get("identity", {})
        key = (str(identity.get("songNo", "")).lower(), str(identity.get("songId", "")))
        if key in seen:
            errors.append(f"duplicate pair: {key}")
        seen.add(key)
        if record.get("relationId") != f"sh-edition:{key[0]}":
            errors.append(f"record {index}: relationId does not match canonical song number")
        if key not in expected:
            errors.append(f"record {index}: not a current shared corpus pair: {key}")
        song = expected_records.get(key)
        if song:
            for book in EDITIONS:
                for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook"):
                    current = (song.get(field) or {}).get(book)
                    reported = (record.get("witnesses", {}).get(book) or {}).get(field)
                    if bool(current) != bool(reported):
                        errors.append(f"record {index} {book}/{field}: witness presence contradicts corpus")
                    if current and reported:
                        if reported.get("scoreRef") != current.get("scoreRef"):
                            errors.append(f"record {index} {book}/{field}: scoreRef contradicts corpus")
                        expected_role = "exact-edition" if field == "scoreByBook" else ("alternate-reference" if field == "referenceScoreByBook" else "review-draft")
                        if reported.get("role") != expected_role:
                            errors.append(f"record {index} {book}/{field}: role contradicts corpus")
        if set(record.get("editions", {})) != set(EDITIONS):
            errors.append(f"record {index}: edition metadata is not exactly 1991 and 2025")
        if set(record.get("witnesses", {})) != set(EDITIONS):
            errors.append(f"record {index}: witness map is not exactly 1991 and 2025")
        comparisons = record.get("comparisons", {})
        if set(comparisons) != set(FIELDS):
            errors.append(f"record {index}: comparison fields are incomplete")
        for field in FIELDS:
            status = comparisons.get(field, {}).get("status")
            if status not in ALLOWED_STATUSES:
                errors.append(f"record {index} {field}: invalid status {status!r}")
            if status == "unavailable" and not comparisons.get(field, {}).get("reason"):
                errors.append(f"record {index} {field}: unavailable requires a reason")
        promotion = record.get("promotion", {})
        if promotion.get("safeToPromote") is not False:
            errors.append(f"record {index}: promotion gate is not explicitly false")
        for book in EDITIONS:
            for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook"):
                witness = (record.get("witnesses", {}).get(book) or {}).get(field)
                if witness and witness.get("role") == "exact-edition" and field != "scoreByBook":
                    errors.append(f"record {index}: non-score witness incorrectly labeled exact-edition")
    if seen != expected:
        missing = sorted(expected - seen)
        extra = sorted(seen - expected)
        if missing:
            errors.append(f"missing shared pairs: {missing[:12]}" + (" ..." if len(missing) > 12 else ""))
        if extra:
            errors.append(f"unexpected shared pairs: {extra[:12]}" + (" ..." if len(extra) > 12 else ""))
    samaria = next((record for record in records if str(record.get("identity", {}).get("songNo", "")).lower() == "26"), None)
    if samaria:
        key_comparison = samaria.get("comparisons", {}).get("keyMode", {})
        if key_comparison.get("status") != "unavailable" or key_comparison.get("values") != {"sh1991": "Ab major", "sh2025": ""}:
            errors.append("Samaria 26 regression: exact key comparison must remain unavailable")
        sh2025_metadata = expected_records.get(("26", samaria.get("identity", {}).get("songId", "")), {}).get("metadataByBook", {}).get("sh2025", {})
        if sh2025_metadata.get("keyCandidate", {}).get("value") != "F minor" or sh2025_metadata.get("keyEvidence", {}).get("status") != "unknown":
            errors.append("Samaria 26 regression: F-minor candidate must remain explicitly unverified")
        if samaria.get("comparisons", {}).get("notation", {}).get("status") != "alternate-witness-only":
            errors.append("Samaria 26 regression: 2025 alternate witness must remain non-authoritative")
    for song_no in ("467", "515"):
        record = next((record for record in records if str(record.get("identity", {}).get("songNo", "")).lower() == song_no), None)
        if not record:
            errors.append(f"SH2025 {song_no} regression: shared reconciliation record is missing")
            continue
        current_song = next((song for song in corpus.get("songs", []) if song.get("id") == record.get("identity", {}).get("songId")), None)
        if not current_song:
            errors.append(f"SH2025 {song_no} regression: current corpus song is missing")
            continue
        if (current_song.get("scoreByBook") or {}).get("sh2025"):
            errors.append(f"SH2025 {song_no} regression: alternate witness is counted as exact score")
        reference = (current_song.get("referenceScoreByBook") or {}).get("sh2025")
        reported_reference = (record.get("witnesses", {}).get("sh2025") or {}).get("referenceScoreByBook")
        if not reference or not reported_reference or reported_reference.get("role") != "alternate-reference":
            errors.append(f"SH2025 {song_no} regression: alternate reference witness is not preserved")
        if record.get("comparisons", {}).get("notation", {}).get("exactEditionWitnesses") is not False:
            errors.append(f"SH2025 {song_no} regression: notation must not claim exact edition witnesses")
    if errors:
        raise SystemExit("\n".join(errors))
    summary = report.get("summary", {})
    print(json.dumps({"sharedPairs": len(records), "safeToPromote": 0, "errors": []}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
