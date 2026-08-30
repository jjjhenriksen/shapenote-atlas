#!/usr/bin/env python3
"""Materialize a fail-closed exact-notation backlog for every book.

This report is intentionally separate from the generated public ledgers. It
joins the current edition coverage and transcription queue with the exact
structured-score manifest, then gives every queued record an explicit
autonomous disposition. A source URL, image URL, OMR draft, or other-edition
witness is retained as evidence but never treated as note-level MusicXML
authority by this script.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
OUTPUT_DIR = ROOT / "work" / "agent-01-notation"
OUTPUT_JSON = OUTPUT_DIR / "all-book-notation-backlog.json"
OUTPUT_MD = OUTPUT_DIR / "all-book-notation-backlog.md"

PROTECTED_RECORDS = {
    "sh2025/115": "Active first-batch record 115 is outside agent-01 ownership; existing work is untouched.",
    "sh2025/116": "Active first-batch record 116 is outside agent-01 ownership; existing work is untouched.",
}

INPUTS = (
    PUBLIC / "source-coverage.json",
    PUBLIC / "transcription-queue.json",
    PUBLIC / "shapenote-score-manifest.json",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hosts(urls: list[str]) -> list[str]:
    return sorted({parsed.netloc for parsed in (urlparse(url) for url in urls) if parsed.netloc})


def source_reason(record: dict[str, Any], protected: str | None) -> tuple[str, str]:
    queue_id = str(record.get("queueId", ""))
    if protected:
        return "protected-active-first-batch", protected

    if record.get("status") == "transcription-blocked":
        existing = str(record.get("blockedReason", "")).strip()
        if existing:
            return "autonomously-blocked", f"Existing source-acquisition block retained: {existing}"
        return (
            "autonomously-blocked",
            "The edition record is already marked transcription-blocked and has no exact structured score.",
        )

    if record.get("sourceImageUrl"):
        return (
            "autonomously-blocked",
            "The queue retains a source-image URL, but no exact structured witness or note-level comparison is recorded for "
            f"{queue_id}; the image/reference cannot support every encoded note in an autonomous MusicXML result.",
        )

    return (
        "autonomously-blocked",
        "The queue contains source reference URL(s) but no retained source image/PDF, exact structured witness, or "
        f"note-level comparison for {queue_id}; every encoded note would be unsupported.",
    )


def build_report() -> dict[str, Any]:
    coverage_payload = read_json(PUBLIC / "source-coverage.json")
    queue_payload = read_json(PUBLIC / "transcription-queue.json")
    score_payload = read_json(PUBLIC / "shapenote-score-manifest.json")

    coverage_records = coverage_payload.get("records", [])
    queue_records = queue_payload.get("records", [])
    coverage_by_id = {
        f"{item.get('bookId', '')}/{item.get('songNo', '')}".lower(): item
        for item in coverage_records
        if item.get("bookId") and item.get("songNo")
    }
    queue_by_id = {
        str(item.get("queueId", "")).lower(): item
        for item in queue_records
        if item.get("queueId")
    }
    expected_queue = {
        key
        for key, item in coverage_by_id.items()
        if item.get("status") != "structured-score" and item.get("sourceUrls")
    }
    actual_queue = set(queue_by_id)
    if actual_queue != expected_queue:
        raise ValueError(
            "queue does not exactly cover non-structured source-reference records: "
            f"missing={sorted(expected_queue - actual_queue)[:10]}, "
            f"extra={sorted(actual_queue - expected_queue)[:10]}"
        )

    score_entries = score_payload.get("entries", {})
    if not isinstance(score_entries, dict):
        raise ValueError("structured-score manifest entries must be an object")
    leaked_score_ids = sorted(actual_queue & {str(key).lower() for key in score_entries})
    if leaked_score_ids:
        raise ValueError(f"queued records have structured-score manifest entries: {leaked_score_ids[:10]}")

    records: list[dict[str, Any]] = []
    for queue_id in sorted(actual_queue):
        record = queue_by_id[queue_id]
        coverage = coverage_by_id[queue_id]
        state, reason = source_reason(record, PROTECTED_RECORDS.get(queue_id))
        source_urls = [str(url) for url in record.get("sourceUrls", []) if str(url)]
        coverage_urls = [str(url) for url in coverage.get("sourceUrls", []) if str(url)]
        if source_urls != coverage_urls:
            raise ValueError(f"source URL drift between queue and coverage for {queue_id}")
        records.append(
            {
                "canonicalRecordId": queue_id,
                "bookId": record.get("bookId", ""),
                "songNo": record.get("songNo", ""),
                "title": record.get("title", ""),
                "sourceStatus": record.get("status", ""),
                "nextSafeAction": (
                    "leave-protected-existing-work"
                    if state == "protected-active-first-batch"
                    else "acquire-authorized-structured-source-or-retained-readable-page"
                ),
                "sourceEvidence": {
                    "sourceUrls": source_urls,
                    "sourceHosts": hosts(source_urls),
                    "sourceImageUrl": record.get("sourceImageUrl", ""),
                    "sourceImageReferencePresent": bool(record.get("sourceImageUrl")),
                    "manifestExactScoreEntry": False,
                    "noteLevelComparisonRecorded": False,
                    "musicXmlProduced": False,
                },
                "disposition": {
                    "state": state,
                    "safeToPromote": False,
                    "humanReviewRequired": False,
                    "reason": reason,
                },
            }
        )

    by_book: dict[str, dict[str, Any]] = {}
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["bookId"]].append(record)
    for book_id in sorted(grouped):
        book_records = grouped[book_id]
        by_book[book_id] = {
            "recordCount": len(book_records),
            "recordIds": [item["canonicalRecordId"] for item in book_records],
            "sourceReferenceCount": sum(item["sourceStatus"] == "source-reference" for item in book_records),
            "transcriptionBlockedCount": sum(item["sourceStatus"] == "transcription-blocked" for item in book_records),
            "autonomouslyBlockedCount": sum(item["disposition"]["state"] == "autonomously-blocked" for item in book_records),
            "protectedCount": sum(item["disposition"]["state"] == "protected-active-first-batch" for item in book_records),
            "sourceHosts": sorted({host for item in book_records for host in item["sourceEvidence"]["sourceHosts"]}),
        }

    disposition_counts = Counter(item["disposition"]["state"] for item in records)
    source_status_counts = Counter(item["sourceStatus"] for item in records)
    report = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "scope": "all-books-with-source-references",
        "policy": {
            "exactNotationGate": "No structured MusicXML is admitted unless direct source evidence supports every encoded note, duration, rest, tie, repeat, lyric, and shape claim.",
            "sourceReferenceIsNotProof": "A source URL or source image reference is an acquisition lead, not note-level proof.",
            "reviewOnlyEvidence": "OMR, imagegen, cross-edition, and other review witnesses are not promoted by this report.",
            "publicLedgersModified": False,
        },
        "inputs": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "generatedAt": read_json(path).get("generatedAt", ""),
            }
            for path in INPUTS
        ],
        "summary": {
            "books": len(by_book),
            "records": len(records),
            "sourceReferenceRecords": source_status_counts.get("source-reference", 0),
            "transcriptionBlockedRecords": source_status_counts.get("transcription-blocked", 0),
            "autonomouslyBlockedRecords": disposition_counts.get("autonomously-blocked", 0),
            "protectedActiveFirstBatchRecords": disposition_counts.get("protected-active-first-batch", 0),
            "rejectedRecords": disposition_counts.get("rejected", 0),
            "musicXmlProduced": sum(item["sourceEvidence"]["musicXmlProduced"] for item in records),
            "safeToPromote": sum(item["disposition"]["safeToPromote"] for item in records),
            "structuredManifestEntries": len(score_entries),
        },
        "protectedRecords": PROTECTED_RECORDS,
        "byBook": by_book,
        "records": records,
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Agent-01 all-book exact-notation backlog",
        "",
        "This bounded report extends the exact-notation queue from Sacred Harp 2025 to every book represented by a current source reference. It is generated from the three input manifests named below and does not modify public ledgers.",
        "",
        "## Disposition",
        "",
        f"- {summary['records']} non-structured records across {summary['books']} books are covered: {summary['sourceReferenceRecords']} source-reference records and {summary['transcriptionBlockedRecords']} existing transcription blocks.",
        f"- {summary['autonomouslyBlockedRecords']} records are explicitly autonomously blocked because the current evidence does not prove every encoded note; {summary['protectedActiveFirstBatchRecords']} active first-batch records are explicitly protected.",
        f"- MusicXML produced: {summary['musicXmlProduced']}. Safe to promote: {summary['safeToPromote']}. Rejected: {summary['rejectedRecords']}.",
        "- Exact record IDs, source URLs, hosts, and per-record reasons are in `all-book-notation-backlog.json`.",
        "",
        "## Per-book coverage",
        "",
        "| Book | Records | Source refs | Existing blocks | Autonomous blocks | Protected | Source hosts |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for book_id, book in report["byBook"].items():
        lines.append(
            f"| `{book_id}` | {book['recordCount']} | {book['sourceReferenceCount']} | {book['transcriptionBlockedCount']} | {book['autonomouslyBlockedCount']} | {book['protectedCount']} | {', '.join(book['sourceHosts'])} |"
        )
    lines.extend(
        [
            "",
            "## Protected records",
            "",
            "- `sh2025/115` — active first-batch record; left untouched.",
            "- `sh2025/116` — active first-batch record; left untouched.",
            "",
            "## Evidence rule for the next bounded batch",
            "",
            "A record can leave this backlog only after an authorized exact-edition source is retained and compared note-for-note, including rhythm, rests, ties, repeats/endings, lyrics, and shape identity. URL-only references and review-only OMR remain blocked.",
            "",
            "## Input manifests",
            "",
        ]
    )
    for item in report["inputs"]:
        lines.append(f"- `{item['path']}` — SHA-256 `{item['sha256']}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    report = build_report()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(
        f"Built {OUTPUT_JSON.relative_to(ROOT)}: "
        f"{report['summary']['records']} records, "
        f"{report['summary']['books']} books, "
        f"{report['summary']['musicXmlProduced']} MusicXML outputs."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
