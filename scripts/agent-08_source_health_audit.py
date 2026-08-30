#!/usr/bin/env python3
"""Build a read-only, provenance-aware source-health audit.

The existing public source-health file is a shared generated artifact.  This
audit never writes there: it inventories the current corpus and retention
manifests into ``work/agent-08-source-health``.  Offline mode reuses that
report as a cache; live mode performs bounded HEAD/range checks and still
never downloads replacements.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import socket
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "work" / "agent-08-source-health" / "agent-08-source-health.json"
CACHE_REPORT = ROOT / "public" / "source-health.json"
USER_AGENT = "Shape-Note-Atlas-agent-08-source-health/1.0"
KNOWN_BOOKS = {
    "sh1991",
    "sh2025",
    "shcooper2012",
    "ch7",
    "shenandoah",
    "southernharmony",
    "kentucky",
    "socialharp",
    "mnharmony",
    "sacredharptunes",
    "trumpet",
}

JSON_INPUTS = [
    ROOT / "public" / "corpus.json",
    ROOT / "public" / "shapenote-score-manifest.json",
    ROOT / "public" / "source-image-manifest.json",
    ROOT / "public" / "candidate-reconciliation.json",
    ROOT / "public" / "shapenote-2025-score-audit.json",
    ROOT / "public" / "edition-2025-additions.json",
    ROOT / "public" / "key-mode-reconciliation.json",
    ROOT / "public" / "sacred-harp-2025-autonomous-reconciliation.json",
    ROOT / "public" / "image-review-queue.json",
    ROOT / "public" / "human-review-queue.json",
    ROOT / "work" / "source-images" / "manifest.json",
    ROOT / "work" / "source-transcriptions" / "2025" / "recording-index.json",
    ROOT / "work" / "source-transcriptions" / "2025" / "debut-recording-index.json",
    ROOT / "work" / "source-transcriptions" / "2025" / "clean-source-candidates.json",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def is_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def source_role(location: str, url: str) -> str:
    path = location.lower()
    lower_url = url.lower()
    if any(token in path for token in ("recording", "tracks", "audio")) or re.search(r"\.(?:mp3|wav|ogg)(?:$|\?)", lower_url):
        return "recording"
    if any(token in path for token in ("sourceimage", "source-image", "coverimage")) or re.search(r"\.(?:jpg|jpeg|png|webp)(?:$|\?)", lower_url):
        return "source-scan"
    if "musicxml" in path or "shapenote.net/musicxml" in lower_url or re.search(r"\.(?:mxl|musicxml)(?:$|\?)", lower_url):
        return "structured-score-witness"
    if any(token in path for token in ("pdf", "candidate")) or lower_url.endswith(".pdf") or "media.sacredharptunes.com" in lower_url:
        return "candidate-score-witness"
    if any(token in path for token in ("editionevidence", "edition-evidence", "publisher")) or "sacredharp.com" in lower_url:
        return "edition-metadata"
    if "fasola.org/indexes" in lower_url or any(token in path for token in ("sourcepage", "source-page", "sourceurl", "sourceurls", "sourceindex", "source-index")):
        return "source-index-page"
    return "source-reference"


def add_url(inventory: dict[str, dict[str, Any]], url: str, *, books: Iterable[str], role: str, reference: str) -> None:
    if not is_url(url):
        return
    item = inventory.setdefault(url, {"url": url, "books": set(), "roles": set(), "references": set(), "localEvidence": []})
    item["books"].update(str(book) for book in books if book)
    item["roles"].add(role)
    item["references"].add(reference)


def walk_urls(value: Any, location: str, *, books: Iterable[str], reference: str, inventory: dict[str, dict[str, Any]]) -> None:
    """Walk dictionaries, lists, and scalar leaves, including URL arrays."""
    if is_url(value):
        add_url(inventory, value, books=books, role=source_role(location, value), reference=reference)
        return
    if isinstance(value, dict):
        for key, child in value.items():
            walk_urls(child, f"{location}/{key}", books=books, reference=reference, inventory=inventory)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_urls(child, f"{location}/{index}", books=books, reference=reference, inventory=inventory)


def add_evidence(item: dict[str, Any], *, kind: str, path: str, expected_sha256: str = "", expected_bytes: Any = None, immutable_declared: bool = False, authority: str) -> None:
    evidence = {
        "kind": kind,
        "path": path,
        "expectedSha256": expected_sha256,
        "expectedBytes": expected_bytes,
        "immutableDeclared": bool(immutable_declared),
        "authority": authority,
    }
    if evidence not in item["localEvidence"]:
        item["localEvidence"].append(evidence)


def corpus_inventory(inventory: dict[str, dict[str, Any]]) -> set[str]:
    corpus = load_json(ROOT / "public" / "corpus.json")
    books = corpus.get("books", {})
    book_ids = set(books) if isinstance(books, dict) else set()
    if isinstance(books, dict):
        for book_id, book in books.items():
            if isinstance(book, dict):
                walk_urls(book.get("coverImage"), f"/books/{book_id}/coverImage", books=[book_id], reference=f"corpus:book:{book_id}", inventory=inventory)

    if not isinstance(corpus.get("songs"), list):
        return book_ids
    for song in corpus["songs"]:
        if not isinstance(song, dict):
            continue
        song_id = str(song.get("id", song.get("songNo", "unknown")))
        song_books = [str(book) for book in song.get("books", []) if book]
        for url in song.get("urls", []):
            if is_url(url):
                add_url(inventory, url, books=song_books, role=source_role("song/urls", url), reference=f"corpus:{song_id}:urls")
        coverage = song.get("sourceCoverageByBook", {})
        if isinstance(coverage, dict):
            for book_id, details in coverage.items():
                if isinstance(details, dict):
                    walk_urls(details, f"/songs/{song_id}/sourceCoverageByBook/{book_id}", books=[str(book_id)], reference=f"corpus:{song_id}:{book_id}", inventory=inventory)
        walk_urls(song, f"/songs/{song_id}", books=song_books, reference=f"corpus:{song_id}", inventory=inventory)
    return book_ids


def record_book_context(key: str, record: dict[str, Any], default: str = "") -> set[str]:
    books: set[str] = set()
    for field in ("bookId", "book", "sourceEdition", "edition"):
        value = record.get(field)
        if isinstance(value, str):
            if value in KNOWN_BOOKS:
                books.add(value)
            elif value in {"Sacred Harp 2025", "Sacred Harp, 2025 Edition"}:
                books.add("sh2025")
    if key.startswith(("sh1991/", "sh2025/", "shcooper2012/", "ch7/", "shenandoah/", "southernharmony/", "kentucky/", "socialharp/", "mnharmony/", "sacredharptunes/", "trumpet/")):
        books.add(key.split("/", 1)[0])
    if default in KNOWN_BOOKS:
        books.add(default)
    elif default in {"Sacred Harp 2025", "Sacred Harp, 2025 Edition"}:
        books.add("sh2025")
    return books


def manifest_inventory(inventory: dict[str, dict[str, Any]]) -> dict[str, int]:
    book_ids: set[str] = set()
    for path in JSON_INPUTS:
        payload = load_json(path)
        if not payload or path.name == "corpus.json":
            continue
        reference = str(path.relative_to(ROOT))
        top_default = str(payload.get("edition", "")) if isinstance(payload.get("edition"), str) else ""
        if isinstance(payload.get("entries"), dict):
            iterable = payload["entries"].items()
        elif isinstance(payload.get("records"), list):
            iterable = ((str(index), record) for index, record in enumerate(payload["records"]))
        elif isinstance(payload.get("records"), dict):
            iterable = payload["records"].items()
        else:
            iterable = []
        for key, record in iterable:
            if not isinstance(record, dict):
                continue
            books = record_book_context(str(key), record, top_default)
            book_ids.update(books)
            walk_urls(record, f"/{reference}/{key}", books=books, reference=f"{reference}:{key}", inventory=inventory)

        if path.name == "shapenote-score-manifest.json":
            for key, record in payload.get("entries", {}).items():
                if not isinstance(record, dict):
                    continue
                books = record_book_context(str(key), record)
                book_ids.update(books)
                add_evidence(
                    inventory.setdefault(record.get("sourceUrl", ""), {"url": record.get("sourceUrl", ""), "books": set(books), "roles": {"structured-score-witness"}, "references": set(), "localEvidence": []}),
                    kind="retained-structured-original",
                    path=str(record.get("rawPath", "")),
                    expected_sha256=str(record.get("sourceSha256", "")),
                    expected_bytes=record.get("sourceBytes"),
                    immutable_declared=False,
                    authority="source-authority",
                ) if is_url(record.get("sourceUrl")) else None

        if path.name == "manifest.json" and "source-images" in str(path):
            for record in payload.get("records", []):
                if not isinstance(record, dict):
                    continue
                url = record.get("sourceImageUrl")
                if not is_url(url):
                    continue
                books = record_book_context(str(record.get("queueId", "")), record, "sh2025")
                add_evidence(inventory[url], kind="immutable-source-scan", path=str(record.get("localPath", "")), expected_sha256=str(record.get("sha256", "")), expected_bytes=record.get("bytes"), immutable_declared=record.get("immutable") is True, authority="source-authority")

        if path.name == "clean-source-candidates.json":
            for record in payload.get("records", []):
                if not isinstance(record, dict):
                    continue
                url = record.get("pdfUrl")
                if not is_url(url):
                    continue
                books = record_book_context(str(record.get("candidateKey", "")), record, "sh2025")
                add_evidence(inventory[url], kind="review-working-copy", path=str(record.get("localPdf", "")), expected_sha256=str(record.get("sha256", "")), immutable_declared=False, authority="generated-review-only")

    return {"manifestContextBooks": len(book_ids)}


def add_missing_retention_annotations(inventory: dict[str, dict[str, Any]]) -> None:
    for item in inventory.values():
        if item["localEvidence"]:
            item["retentionDisposition"] = "retained-copy-present"
        elif "recording" in item["roles"]:
            item["retentionDisposition"] = "not-retained-recording"
        else:
            item["retentionDisposition"] = "no-manifest-bound-retention"


def hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def local_evidence_status(evidence: dict[str, Any]) -> dict[str, Any]:
    result = dict(evidence)
    path_text = str(evidence.get("path", ""))
    path = (ROOT / path_text).resolve() if path_text else ROOT / "__missing_agent_08_path__"
    result["exists"] = path.is_file()
    result["actualSha256"] = ""
    result["actualBytes"] = None
    if not path.is_file():
        result["status"] = "missing"
        return result
    actual_hash, actual_bytes = hash_file(path)
    result["actualSha256"] = actual_hash
    result["actualBytes"] = actual_bytes
    expected_hash = str(evidence.get("expectedSha256", ""))
    expected_bytes = evidence.get("expectedBytes")
    result["status"] = "exact" if (not expected_hash or expected_hash == actual_hash) and expected_bytes in (None, "", actual_bytes) else "drifted"
    return result


class RedirectRecorder(HTTPRedirectHandler):
    def __init__(self) -> None:
        super().__init__()
        self.redirects: list[dict[str, Any]] = []

    def redirect_request(self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Request | None:
        self.redirects.append({"status": code, "from": req.full_url, "to": newurl})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def request_url(url: str, timeout: float) -> dict[str, Any]:
    recorder = RedirectRecorder()
    opener = build_opener(recorder)
    method = "HEAD"
    try:
        response: Any = opener.open(Request(url, method="HEAD", headers={"User-Agent": USER_AGENT, "Accept": "*/*"}), timeout=timeout)
    except HTTPError as exc:
        if exc.code not in {403, 405, 501}:
            return {"status": "unreachable", "httpStatus": exc.code, "finalUrl": url, "contentType": str(exc.headers.get("Content-Type", "")), "method": method, "redirects": recorder.redirects, "error": str(exc)}
        method = "GET-range-fallback"
        try:
            response = opener.open(Request(url, method="GET", headers={"User-Agent": USER_AGENT, "Accept": "*/*", "Range": "bytes=0-0"}), timeout=timeout)
            response.read(1)
        except Exception as fallback_exc:  # pragma: no cover - network-dependent
            return {"status": "network-error", "httpStatus": None, "finalUrl": url, "contentType": "", "method": method, "redirects": recorder.redirects, "error": str(fallback_exc)}
    except (URLError, TimeoutError, socket.timeout, OSError) as exc:
        return {"status": "network-error", "httpStatus": None, "finalUrl": url, "contentType": "", "method": method, "redirects": recorder.redirects, "error": str(exc)}
    try:
        status_code = int(response.status)
        final_url = str(response.geturl())
        content_type = str(response.headers.get("Content-Type", ""))
        response.close()
    except Exception as exc:  # pragma: no cover - defensive cleanup
        return {"status": "network-error", "httpStatus": None, "finalUrl": url, "contentType": "", "method": method, "redirects": recorder.redirects, "error": str(exc)}
    status = "redirected" if recorder.redirects or final_url != url else "reachable"
    if status_code >= 400:
        status = "unreachable"
    return {"status": status, "httpStatus": status_code, "finalUrl": final_url, "contentType": content_type, "method": method, "redirects": recorder.redirects}


def cached_result(url: str, cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
    prior = cache.get(url)
    if not prior:
        return {"status": "not-checked-offline", "healthMode": "offline-no-cache", "httpStatus": None, "finalUrl": url, "contentType": "", "method": "offline", "redirects": []}
    return {"status": "cached", "healthMode": "cached-offline", "httpStatus": prior.get("httpStatus"), "finalUrl": prior.get("finalUrl", url), "contentType": prior.get("contentType", ""), "method": "cached", "redirects": prior.get("redirects", []), "cachedCheckedAt": prior.get("checkedAt", "")}


def cache_records() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    payload = load_json(CACHE_REPORT)
    records = {str(item.get("url")): item for item in payload.get("records", []) if isinstance(item, dict) and is_url(item.get("url"))}
    return records, {"path": str(CACHE_REPORT.relative_to(ROOT)), "generatedAt": payload.get("generatedAt", ""), "checkMode": payload.get("checkMode", ""), "recordCount": len(records)}


def duplicate_81b_report() -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    files: list[Path] = []
    for path in (ROOT / "work").rglob("*"):
        if path.is_file() and "81b" in str(path.relative_to(ROOT / "work")).lower():
            files.append(path)
            digest, size = hash_file(path)
            groups[digest].append({"path": str(path.relative_to(ROOT)), "bytes": size})
    duplicate_groups = [{"sha256": digest, "bytes": items[0]["bytes"], "files": sorted(items, key=lambda item: item["path"])} for digest, items in sorted(groups.items()) if len(items) > 1]
    return {"fileCount": len(files), "hashGroupCount": len(groups), "duplicateGroupCount": len(duplicate_groups), "duplicateGroups": duplicate_groups, "policy": "All 81b originals and duplicate artifacts are retained; this audit performs no deletion or replacement."}


def derivative_inventory() -> dict[str, Any]:
    roots = {
        "public-score-working-copies": ROOT / "public" / "scores",
        "public-draft-working-copies": ROOT / "public" / "draft-scores",
        "public-review-working-copies": ROOT / "public" / "review-drafts",
        "omr-and-correction-working-copies": ROOT / "work" / "omr",
        "working-image-derivatives": ROOT / "work" / "transcription-images" / "working",
        "source-transcription-audit-copies": ROOT / "work" / "source-transcriptions" / "2025",
    }
    result: dict[str, Any] = {}
    for label, path in roots.items():
        files = [candidate for candidate in path.rglob("*") if candidate.is_file()] if path.is_dir() else []
        result[label] = {"root": str(path.relative_to(ROOT)), "fileCount": len(files), "exists": path.is_dir(), "classification": "generated-working-copy-or-review-evidence"}
    result["source-authority-retention"] = {"classification": "retained-source-authority", "roots": ["work/shapenote-musicxml", "work/source-images/2025"]}
    return result


def classify_retention(item: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    if any(e.get("authority") == "source-authority" and e.get("status") == "drifted" for e in evidence):
        return "retained-source-drifted"
    if any(e.get("authority") == "source-authority" and e.get("status") == "missing" for e in evidence):
        return "retained-source-missing"
    if any(e.get("authority") == "source-authority" and e.get("status") == "exact" for e in evidence):
        return "retained-source-exact"
    if any(e.get("authority") == "generated-review-only" for e in evidence):
        return "generated-working-copy-exact-or-missing"
    return str(item.get("retentionDisposition", "no-manifest-bound-retention"))


def build_report(*, offline: bool, timeout: float, workers: int, max_urls: int) -> dict[str, Any]:
    inventory: dict[str, dict[str, Any]] = {}
    book_ids = corpus_inventory(inventory)
    manifest_inventory(inventory)
    add_missing_retention_annotations(inventory)
    cache, cache_meta = cache_records()
    urls = sorted(inventory)
    cache_only_urls = sorted(set(cache) - set(urls))
    live_urls = [] if offline else (urls if max_urls <= 0 else urls[:max_urls])
    live_results: dict[str, dict[str, Any]] = {}
    if live_urls:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = {executor.submit(request_url, url, timeout): url for url in live_urls}
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    live_results[url] = future.result()
                except Exception as exc:  # pragma: no cover - worker isolation
                    live_results[url] = {"status": "network-error", "httpStatus": None, "finalUrl": url, "contentType": "", "method": "worker", "redirects": [], "error": str(exc)}

    records: list[dict[str, Any]] = []
    checked_at = now_utc()
    for url in urls:
        item = inventory[url]
        if offline:
            network = cached_result(url, cache)
        elif url in live_results:
            network = dict(live_results[url])
            network["healthMode"] = "live"
        else:
            network = {"status": "not-checked-budget", "healthMode": "live-budget-excluded", "httpStatus": None, "finalUrl": url, "contentType": "", "method": "budget", "redirects": []}
        evidence = [local_evidence_status(entry) for entry in item["localEvidence"]]
        remote_hash_scope = "not-probed-by-HEAD-or-range-check"
        if evidence and any(entry.get("status") == "drifted" for entry in evidence):
            drift = "retained-local-copy-drift"
        elif evidence and any(entry.get("authority") == "source-authority" for entry in evidence):
            drift = "retained-local-copy-exact; remote-content-drift-unknown"
        else:
            drift = "remote-content-drift-unknown; no-retained-source-hash"
        records.append({
            "url": url,
            "books": sorted(item["books"]),
            "roles": sorted(item["roles"]),
            "references": sorted(item["references"]),
            "checkedAt": checked_at,
            "evidenceScope": "URL status, redirect chain, and content type; retained-local SHA-256/bytes where manifest-bound; no replacement download",
            **network,
            "retentionDisposition": classify_retention(item, evidence),
            "localEvidence": evidence,
            "driftDisposition": drift,
            "remoteHashScope": remote_hash_scope,
        })

    by_book: dict[str, dict[str, Any]] = {}
    for book in sorted(book_ids | {book for record in records for book in record["books"]}):
        rows = [record for record in records if book in record["books"]]
        by_book[book] = {
            "uniqueUrls": len(rows),
            "byHealthStatus": dict(sorted(Counter(row["status"] for row in rows).items())),
            "byRole": dict(sorted(Counter(role for row in rows for role in row["roles"]).items())),
            "byRetention": dict(sorted(Counter(row["retentionDisposition"] for row in rows).items())),
            "sourceAuthorityEvidence": sum(any(e.get("authority") == "source-authority" for e in row["localEvidence"]) for row in rows),
            "missingLocalRetention": sum(not row["localEvidence"] for row in rows),
            "driftedLocalEvidence": sum(row["driftDisposition"] == "retained-local-copy-drift" for row in rows),
        }

    return {
        "generatedAt": now_utc(),
        "version": "agent-08-source-health-v1",
        "checkMode": "offline" if offline else "live",
        "policy": "Read-only audit. Shared public manifests and ledgers are inputs only. Retained originals and duplicate 81b artifacts are never overwritten, replaced, or deleted.",
        "inventory": {"urlCount": len(records), "bookCount": len(by_book), "books": sorted(by_book), "cache": {**cache_meta, "cacheOnlyUrlCount": len(cache_only_urls), "cacheOnlyUrls": cache_only_urls}, "inputFiles": [str(path.relative_to(ROOT)) for path in JSON_INPUTS]},
        "summary": {
            "totalUrls": len(records),
            "byHealthStatus": dict(sorted(Counter(record["status"] for record in records).items())),
            "byRole": dict(sorted(Counter(role for record in records for role in record["roles"]).items())),
            "withAnyLocalEvidence": sum(bool(record["localEvidence"]) for record in records),
            "withSourceAuthorityEvidence": sum(any(e.get("authority") == "source-authority" for e in record["localEvidence"]) for record in records),
            "localExact": sum(e.get("status") == "exact" for record in records for e in record["localEvidence"]),
            "localDrifted": sum(e.get("status") == "drifted" for record in records for e in record["localEvidence"]),
            "localMissing": sum(e.get("status") == "missing" for record in records for e in record["localEvidence"]),
            "urlsWithoutLocalRetention": sum(not record["localEvidence"] for record in records),
            "remoteContentDriftUnknown": sum(record["remoteHashScope"] == "not-probed-by-HEAD-or-range-check" for record in records),
        },
        "books": by_book,
        "derivativeInventory": derivative_inventory(),
        "duplicate81b": duplicate_81b_report(),
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="perform live HEAD/range checks; without this flag use cached/offline evidence")
    parser.add_argument("--timeout", type=float, default=6.0)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--max-urls", type=int, default=0, help="bound live checks; excluded URLs remain explicitly not-checked-budget")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(offline=not args.live, timeout=args.timeout, workers=args.workers, max_urls=args.max_urls)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "checkMode": report["checkMode"], "inventory": report["inventory"], "summary": report["summary"], "duplicate81b": report["duplicate81b"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
