#!/usr/bin/env python3
"""Inventory and health-check every external source used by the atlas.

Online mode checks status, redirects, and content type. Offline mode reuses
the previous network result while rechecking every retained local checksum.
Neither mode rewrites or replaces source material.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "source-health.json"
USER_AGENT = "Shape-Note-Atlas-source-health/1.1"
JSON_SOURCES = [
    ROOT / "public" / "corpus.json",
    ROOT / "public" / "shapenote-score-manifest.json",
    ROOT / "public" / "source-image-manifest.json",
    ROOT / "public" / "candidate-reconciliation.json",
    ROOT / "public" / "shapenote-2025-score-audit.json",
    ROOT / "work" / "source-images" / "manifest.json",
    ROOT / "work" / "source-transcriptions" / "2025" / "recording-index.json",
    ROOT / "work" / "source-transcriptions" / "2025" / "debut-recording-index.json",
    ROOT / "work" / "source-transcriptions" / "2025" / "clean-source-candidates.json",
    ROOT / "work" / "luna-program-20260904" / "source_only" / "retention-manifest.json",
    ROOT / "work" / "luna-program-20260904" / "existing_books" / "christian-harmony-batch-01.json",
]

# The collector is intentionally explicit about which manifests contributed to
# the report. A missing or unreadable manifest must not silently look like an
# empty manifest in a health result.
LOAD_DIAGNOSTICS: dict[str, dict[str, Any]] = {}
MANIFEST_READ_TIMEOUT = 4.0
# macOS marks iCloud/CloudDocs placeholders as dataless in st_flags. Avoid a
# blocking read and preserve that state as unavailable retention evidence.
CLOUD_PLACEHOLDER_FLAG = 0x40000000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    if not path.is_file():
        LOAD_DIAGNOSTICS[key] = {"status": "missing"}
        return {}
    try:
        # Read each manifest in a child process so a cloud-backed placeholder
        # cannot wedge the whole offline report. This is deliberately bounded;
        # the report records timeout/unreadable state instead of guessing that
        # an inaccessible manifest is empty.
        probe = subprocess.run(
            [sys.executable, "-c", "import json,sys; print(json.dumps(json.load(open(sys.argv[1], encoding='utf-8')), ensure_ascii=False))", str(path)],
            capture_output=True,
            text=True,
            timeout=MANIFEST_READ_TIMEOUT,
            check=False,
        )
        if probe.returncode != 0:
            raise OSError(probe.stderr.strip() or f"manifest probe exited {probe.returncode}")
        value = json.loads(probe.stdout)
    except json.JSONDecodeError as exc:
        LOAD_DIAGNOSTICS[key] = {"status": "invalid", "error": str(exc)}
        return {}
    except subprocess.TimeoutExpired as exc:
        LOAD_DIAGNOSTICS[key] = {"status": "timeout", "timeoutSeconds": MANIFEST_READ_TIMEOUT, "error": str(exc)}
        return {}
    except OSError as exc:
        LOAD_DIAGNOSTICS[key] = {"status": "unreadable", "error": str(exc)}
        return {}
    if not isinstance(value, dict):
        LOAD_DIAGNOSTICS[key] = {"status": "unexpected-shape", "type": type(value).__name__}
        return {}
    LOAD_DIAGNOSTICS[key] = {"status": "loaded"}
    return value


def is_http_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def source_role(path: str, url: str) -> str:
    lower_path = path.lower()
    lower_url = url.lower()
    if any(token in lower_path for token in ("recording", "tracks", "audio")) or re.search(r"\.(?:mp3|wav|ogg)(?:$|\?)", lower_url):
        return "recording"
    if "sourceimage" in lower_path or re.search(r"\.(?:jpg|jpeg|png|webp)(?:$|\?)", lower_url):
        return "source-scan"
    if "musicxml" in lower_path or "shapenote.net/musicxml" in lower_url or re.search(r"\.(?:mxl|musicxml)(?:$|\?)", lower_url):
        return "structured-score-witness"
    if "pdf" in lower_path or lower_url.endswith(".pdf") or "media.sacredharptunes.com" in lower_url:
        return "candidate-score-witness"
    if "editionevidence" in lower_path or "publisher" in lower_url or "sacredharp.com" in lower_url:
        return "edition-metadata"
    if "fasola.org/indexes" in lower_url or any(token in lower_path for token in ("sourcepage", "sourceurl", "sourceurls", "index")):
        return "source-index-page"
    return "source-reference"


def empty_item(url: str) -> dict[str, Any]:
    return {"url": url, "roles": set(), "references": set(), "books": set(), "localEvidence": []}


def add_url(inventory: dict[str, dict[str, Any]], url: str, role: str, reference: str, books: tuple[str, ...] = ()) -> None:
    if not is_http_url(url):
        return
    item = inventory.setdefault(url, empty_item(url))
    item["roles"].add(role)
    item["references"].add(reference)
    item["books"].update(book for book in books if isinstance(book, str) and book)


def walk_urls(value: Any, path: str, reference: str, inventory: dict[str, dict[str, Any]], books: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}"
            if is_http_url(child):
                add_url(inventory, child, source_role(child_path, child), f"{reference}:{key}", books)
            else:
                walk_urls(child, child_path, reference, inventory, books)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_urls(child, f"{path}/{index}", reference, inventory, books)
    elif is_http_url(value):
        # Lists may contain URL strings directly, including nested source/recording lists.
        add_url(inventory, value, source_role(path, value), f"{reference}:{path}", books)


def add_local_evidence(item: dict[str, Any], *, kind: str, path: str, expected_sha256: str = "", expected_bytes: Any = None, immutable: bool = False) -> None:
    if not path:
        return
    evidence = {
        "kind": kind,
        "path": path,
        "expectedSha256": expected_sha256,
        "expectedBytes": expected_bytes,
        "immutable": immutable,
    }
    if evidence not in item["localEvidence"]:
        item["localEvidence"].append(evidence)


def inventory_sources() -> dict[str, dict[str, Any]]:
    LOAD_DIAGNOSTICS.clear()
    inventory: dict[str, dict[str, Any]] = {}
    for path in JSON_SOURCES:
        payload = load_json(path)
        if not payload:
            continue
        reference = str(path.relative_to(ROOT))
        if path.name == "corpus.json":
            # Song records are the corpus-only inventory used by the audit.
            for song in payload.get("songs", []):
                if isinstance(song, dict):
                    song_books = tuple(song.get("books", ())) if isinstance(song.get("books"), list) else ()
                    walk_urls(song, "/songs", f"corpus:{song.get('id', song.get('songNo', 'unknown'))}", inventory, song_books)
            # Book covers and landing pages are external source assets too, but
            # are tagged separately so the 7,590 song-record count remains
            # visible and is never conflated with the full report inventory.
            for book_key, book in payload.get("books", {}).items():
                if isinstance(book, dict):
                    walk_urls(book, f"/books/{book_key}", f"corpus:book:{book_key}", inventory, (str(book_key),))
        else:
            walk_urls(payload, "", reference, inventory)

    score_manifest = load_json(ROOT / "public" / "shapenote-score-manifest.json")
    for record_key, entry in score_manifest.get("entries", {}).items():
        if not isinstance(entry, dict) or not is_http_url(entry.get("sourceUrl")):
            continue
        item = inventory.setdefault(entry["sourceUrl"], empty_item(entry["sourceUrl"]))
        item["roles"].add("structured-score-witness")
        item["references"].add(f"score-manifest:{record_key}")
        add_local_evidence(item, kind="retained-structured-source", path=str(entry.get("rawPath", "")), expected_sha256=str(entry.get("sourceSha256", "")), expected_bytes=entry.get("sourceBytes"))

    image_manifest = load_json(ROOT / "work" / "source-images" / "manifest.json")
    for entry in image_manifest.get("records", []):
        if not isinstance(entry, dict) or not is_http_url(entry.get("sourceImageUrl")):
            continue
        item = inventory.setdefault(entry["sourceImageUrl"], empty_item(entry["sourceImageUrl"]))
        item["roles"].add("source-scan")
        item["references"].add(f"source-image:{entry.get('queueId', entry.get('songNo', 'unknown'))}")
        add_local_evidence(item, kind="immutable-source-scan", path=str(entry.get("localPath", "")), expected_sha256=str(entry.get("sha256", "")), expected_bytes=entry.get("bytes"), immutable=entry.get("immutable") is True)

    candidates = load_json(ROOT / "work" / "source-transcriptions" / "2025" / "clean-source-candidates.json")
    for entry in candidates.get("records", []):
        if not isinstance(entry, dict) or not is_http_url(entry.get("pdfUrl")):
            continue
        item = inventory.setdefault(entry["pdfUrl"], empty_item(entry["pdfUrl"]))
        item["roles"].add("candidate-score-witness")
        item["references"].add(f"candidate:{entry.get('candidateKey', entry.get('songNo', 'unknown'))}")
        add_local_evidence(item, kind="retained-candidate-pdf", path=str(entry.get("localPdf", "")), expected_sha256=str(entry.get("sha256", "")))

    # Consume lane-owned retention manifests without copying or promoting the
    # retained bodies. If a record has a derived retained URL, bind the local
    # hash to that URL—not to the page/index URL that led to it.
    lane_retention = load_json(ROOT / "work" / "luna-program-20260904" / "source_only" / "retention-manifest.json")
    for entry in lane_retention.get("records", []):
        if not isinstance(entry, dict):
            continue
        record_id = str(entry.get("record_id", entry.get("recordId", "unknown")))
        source_url = entry.get("source_url", entry.get("sourceUrl"))
        retained_url = entry.get("retained_source_url", entry.get("retainedSourceUrl"))
        local_path = str(entry.get("local_path", entry.get("localPath", "")))
        sha256 = str(entry.get("sha256", ""))
        byte_count = entry.get("bytes")
        target_url = retained_url if is_http_url(retained_url) else source_url
        if not is_http_url(target_url):
            continue
        item = inventory.setdefault(target_url, empty_item(target_url))
        item["roles"].add(source_role(f"source-only-retention/{local_path}", target_url))
        item["references"].add(f"source-only-retention:{record_id}")
        add_local_evidence(item, kind="lane-retained-source", path=local_path, expected_sha256=sha256, expected_bytes=byte_count, immutable=True)
        if is_http_url(source_url):
            source_item = inventory.setdefault(source_url, empty_item(source_url))
            source_item["references"].add(f"source-only-retention-lead:{record_id}")

    # Existing-books lane handoff: page URLs and explicitly linked scan URLs
    # remain distinct. The local image hash is bound only to the linked image
    # body, never to the page that returned it.
    christian_batch_path = ROOT / "work" / "luna-program-20260904" / "existing_books" / "christian-harmony-batch-01.json"
    christian_batch = load_json(christian_batch_path)
    for entry in christian_batch.get("batch", []):
        if not isinstance(entry, dict):
            continue
        queue_id = str(entry.get("queueId", "unknown"))
        browser_check = entry.get("browserCheck") if isinstance(entry.get("browserCheck"), dict) else {}
        linked_image = browser_check.get("linkedImage")
        scan = entry.get("scan") if isinstance(entry.get("scan"), dict) else {}
        local_path = str(scan.get("local", ""))
        if not is_http_url(linked_image) or not local_path:
            continue
        local_absolute = (christian_batch_path.parent / local_path).resolve()
        try:
            local_relative = str(local_absolute.relative_to(ROOT.resolve()))
        except ValueError:
            continue
        item = inventory.setdefault(linked_image, empty_item(linked_image))
        item["roles"].add("source-scan")
        item["books"].add("ch7")
        item["references"].add(f"existing-books-retention:{queue_id}")
        add_local_evidence(item, kind="retained-exact-edition-scan", path=local_relative, expected_sha256=str(scan.get("sha256", "")), immutable=True)
    return inventory


def inventory_declarations(inventory: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return the canonical counts derived from the exact collected inventory."""
    books = sorted({book for item in inventory.values() for book in item["books"]})
    return {
        "corpusSongUrls": sum(
            1 for item in inventory.values()
            if any(reference.startswith("corpus:") and ":book:" not in reference for reference in item["references"])
        ),
        "fullManifestUrls": len(inventory),
        "bookCount": len(books),
        "bookUrlCounts": {book: sum(book in item["books"] for item in inventory.values()) for book in books},
    }


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
    response: Any = None
    try:
        response = opener.open(Request(url, method="HEAD", headers={"User-Agent": USER_AGENT, "Accept": "*/*"}), timeout=timeout)
    except HTTPError as exc:
        response = exc
        if exc.code in {403, 405, 501}:
            method = "GET-range-fallback"
            try:
                response = opener.open(Request(url, method="GET", headers={"User-Agent": USER_AGENT, "Accept": "*/*", "Range": "bytes=0-0"}), timeout=timeout)
                response.read(1)
            except Exception as fallback_exc:  # pragma: no cover - network dependent
                return {"status": "network-error", "httpStatus": None, "finalUrl": url, "contentType": "", "method": method, "redirects": recorder.redirects, "error": str(fallback_exc)}
    except (URLError, TimeoutError, socket.timeout, OSError) as exc:
        return {"status": "network-error", "httpStatus": None, "finalUrl": url, "contentType": "", "method": method, "redirects": recorder.redirects, "error": str(exc)}

    if isinstance(response, HTTPError):
        return {"status": "unreachable", "httpStatus": response.code, "finalUrl": url, "contentType": str(response.headers.get("Content-Type", "")), "method": method, "redirects": recorder.redirects, "error": str(response)}
    try:
        status_code = int(response.status)
        final_url = str(response.geturl())
        content_type = str(response.headers.get("Content-Type", ""))
        response.close()
    except Exception as exc:  # pragma: no cover - defensive network cleanup
        return {"status": "network-error", "httpStatus": None, "finalUrl": url, "contentType": "", "method": method, "redirects": recorder.redirects, "error": str(exc)}
    state = "redirected" if recorder.redirects or final_url != url else "reachable"
    if status_code >= 400:
        state = "unreachable"
    return {"status": state, "httpStatus": status_code, "finalUrl": final_url, "contentType": content_type, "method": method, "redirects": recorder.redirects}


def local_evidence_status(evidence: dict[str, Any]) -> dict[str, Any]:
    result = dict(evidence)
    path_text = str(evidence.get("path", ""))
    path = ROOT / path_text
    try:
        stat_result = path.stat()
    except OSError:
        stat_result = None
    result["exists"] = bool(stat_result and path.is_file())
    result["actualSha256"] = ""
    result["actualBytes"] = None
    if not stat_result or not path.is_file():
        result["status"] = "missing"
        return result
    if getattr(stat_result, "st_flags", 0) & CLOUD_PLACEHOLDER_FLAG:
        result["status"] = "unavailable"
        result["availability"] = "cloud-placeholder"
        return result
    data = path.read_bytes()
    result["actualSha256"] = hashlib.sha256(data).hexdigest()
    result["actualBytes"] = len(data)
    expected_hash = str(evidence.get("expectedSha256", ""))
    expected_bytes = evidence.get("expectedBytes")
    result["status"] = "exact" if (not expected_hash or result["actualSha256"] == expected_hash) and (expected_bytes in (None, "", result["actualBytes"])) else "drifted"
    return result


def retention_status(evidence: list[dict[str, Any]]) -> str:
    """Return retention state without treating remote health as retention proof."""
    if not evidence:
        return "missing-retention"
    states = {str(item.get("status")) for item in evidence}
    if "unavailable" in states:
        return "retention-unavailable"
    if "drifted" in states:
        return "local-drift"
    if "exact" in states:
        return "retained-exact"
    return "missing-retention"


def previous_by_url() -> dict[str, dict[str, Any]]:
    payload = load_json(OUTPUT)
    return {str(item.get("url")): item for item in payload.get("records", []) if isinstance(item, dict) and item.get("url")}


def previous_network(item: dict[str, Any] | None) -> dict[str, Any]:
    if not item:
        return {"status": "not-checked-offline", "httpStatus": None, "finalUrl": "", "contentType": "", "method": "offline", "redirects": [], "networkCheckedAt": None, "remoteBodyStatus": "unknown"}
    prior_status = item.get("status")
    if prior_status == "not-checked-budget":
        return {
            "status": "not-checked-budget",
            "httpStatus": None,
            "finalUrl": item.get("finalUrl", ""),
            "contentType": "",
            "method": "budget-cached",
            "redirects": [],
            "networkCheckedAt": None,
            "remoteBodyStatus": "not-checked-budget",
        }
    if prior_status == "not-checked-offline":
        return {
            "status": "not-checked-offline",
            "httpStatus": item.get("httpStatus"),
            "finalUrl": item.get("finalUrl", ""),
            "contentType": item.get("contentType", ""),
            "method": "offline-cached",
            "redirects": item.get("redirects", []),
            "networkCheckedAt": None,
            "remoteBodyStatus": item.get("remoteBodyStatus", "unknown"),
        }
    actual_statuses = {"reachable", "redirected", "unreachable", "network-error"}
    cached_status = item.get("networkStatus", item.get("cachedStatus", item.get("status")))
    has_actual_network_evidence = prior_status in actual_statuses or cached_status in actual_statuses
    return {
        "status": "cached",
        "cachedStatus": cached_status,
        "httpStatus": item.get("httpStatus"),
        "finalUrl": item.get("finalUrl", ""),
        "contentType": item.get("contentType", ""),
        "method": "cached",
        "redirects": item.get("redirects", []),
        "networkCheckedAt": item.get("networkCheckedAt") or (item.get("checkedAt") if has_actual_network_evidence else None),
        "remoteBodyStatus": item.get("remoteBodyStatus", "unknown"),
    }


def host_name(url: str) -> str:
    return (urlsplit(url).hostname or "").lower() or "<invalid-host>"


def check_network_urls(urls: list[str], timeout: float, workers: int, per_host: int, max_seconds: float) -> tuple[dict[str, dict[str, Any]], set[str], dict[str, int]]:
    """Check a bounded URL set with a per-host semaphore and total deadline."""
    import threading

    host_locks: dict[str, threading.BoundedSemaphore] = {}
    lock = threading.Lock()
    def check_one(url: str) -> dict[str, Any]:
        host = host_name(url)
        with lock:
            semaphore = host_locks.setdefault(host, threading.BoundedSemaphore(max(1, per_host)))
        with semaphore:
            result = request_url(url, timeout)
            result["host"] = host
            return result

    results: dict[str, dict[str, Any]] = {}
    started = time.monotonic()
    futures: dict[concurrent.futures.Future[dict[str, Any]], str] = {}
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers))
    try:
        for url in urls:
            futures[executor.submit(check_one, url)] = url
        try:
            remaining = None if max_seconds <= 0 else max(0.0, max_seconds - (time.monotonic() - started))
            for future in concurrent.futures.as_completed(futures, timeout=remaining):
                url = futures[future]
                try:
                    results[url] = future.result()
                except Exception as exc:  # pragma: no cover - defensive worker isolation
                    results[url] = {"status": "network-error", "httpStatus": None, "finalUrl": url, "contentType": "", "method": "unknown", "redirects": [], "error": str(exc), "host": host_name(url)}
        except concurrent.futures.TimeoutError:
            pass
        for future, url in futures.items():
            if url not in results:
                future.cancel()
    finally:
        # Do not make a bounded run wait for a slow host after the deadline.
        executor.shutdown(wait=False, cancel_futures=True)
    checked_hosts = {}
    for url, result in results.items():
        host = result.get("host", host_name(url))
        checked_hosts[host] = checked_hosts.get(host, 0) + 1
    return results, set(futures_by_url for futures_by_url in results), checked_hosts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="reuse the previous network result and only recheck local retained files")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--per-host-concurrency", type=int, default=2, help="maximum simultaneous requests to one host")
    parser.add_argument("--max-seconds", type=float, default=0.0, help="total live-check budget; 0 means no additional deadline")
    parser.add_argument("--max-urls", type=int, default=0, help="optional bounded online check; remaining URLs are not-checked-budget")
    parser.add_argument("--resume", action="store_true", help="reuse prior current network results and retry only prior budget/offline/error records")
    args = parser.parse_args()

    checked_at = utc_now()
    inventory = inventory_sources()
    previous = previous_by_url()
    urls = sorted(inventory)
    online_urls = [] if args.offline else ([(url) for url in urls if not args.resume or previous.get(url, {}).get("status") in {"not-checked-budget", "not-checked-offline", "network-error"}])
    if args.max_urls > 0:
        online_urls = online_urls[: args.max_urls]
    network_results: dict[str, dict[str, Any]] = {}
    checked_urls: set[str] = set()
    checked_hosts: dict[str, int] = {}
    if online_urls:
        network_results, checked_urls, checked_hosts = check_network_urls(
            online_urls,
            timeout=max(0.1, args.timeout),
            workers=max(1, args.workers),
            per_host=max(1, args.per_host_concurrency),
            max_seconds=max(0.0, args.max_seconds),
        )

    records = []
    for url in urls:
        item = inventory[url]
        local_evidence = [local_evidence_status(evidence) for evidence in item["localEvidence"]]
        if args.offline:
            network = previous_network(previous.get(url))
            if not previous.get(url):
                network["finalUrl"] = url
            evidence_scope = "cached network result plus retained-local checksum; no network request"
        elif url in network_results:
            network = dict(network_results[url])
            network["networkCheckedAt"] = checked_at
            network["remoteBodyStatus"] = "unknown"
            evidence_scope = "current bounded network status/redirect/content-type plus retained-local checksum; remote body hash not fetched"
        elif args.resume and previous.get(url):
            network = previous_network(previous[url])
            evidence_scope = "cached prior network result plus retained-local checksum; omitted by resumable selection"
        else:
            network = {"status": "not-checked-budget", "httpStatus": None, "finalUrl": url, "contentType": "", "method": "budget", "redirects": [], "networkCheckedAt": None, "remoteBodyStatus": "not-checked-budget"}
            evidence_scope = "not checked within explicit live URL/time budget; retained-local checksum only"
        network_status = network.get("status")
        record_status = network_status
        # Preserve the public status vocabulary while exposing the underlying
        # current/cached network result separately for consumers that need it.
        if network_status == "cached" and network.get("cachedStatus"):
            network["networkStatus"] = network["cachedStatus"]
        elif network_status not in {"cached", "not-checked-offline", "not-checked-budget"}:
            network["networkStatus"] = network_status
        records.append({
            "url": url,
            "books": sorted(item["books"]),
            "roles": sorted(item["roles"]),
            "references": sorted(item["references"]),
            "checkedAt": checked_at,
            "networkCheckedAt": network.get("networkCheckedAt"),
            "evidenceAge": "current" if url in checked_urls else ("cached" if network_status == "cached" else "not-checked"),
            "evidenceScope": evidence_scope,
            "retentionStatus": retention_status(local_evidence),
            "remoteBodyStatus": network.get("remoteBodyStatus", "unknown"),
            **network,
            "status": record_status,
            "localEvidence": local_evidence,
        })

    statuses = sorted({record["status"] for record in records})
    retention_states = sorted({record["retentionStatus"] for record in records})
    books = sorted({book for item in inventory.values() for book in item["books"]})
    by_book = {}
    for book in books:
        book_records = [record for record in records if book in record.get("books", [])]
        by_book[book] = {
            "totalUrls": len(book_records),
            "byStatus": {status: sum(record["status"] == status for record in book_records) for status in sorted({record["status"] for record in book_records})},
            "byRetention": {status: sum(record["retentionStatus"] == status for record in book_records) for status in retention_states if any(record["retentionStatus"] == status for record in book_records)},
        }
    manifest_states = {path: details.get("status") for path, details in sorted(LOAD_DIAGNOSTICS.items()) if path != str(OUTPUT.relative_to(ROOT))}
    manifest_issues = {path: status for path, status in manifest_states.items() if status != "loaded"}
    declarations = inventory_declarations(inventory)
    summary = {
        "totalUrls": len(records),
        "byStatus": {status: sum(record["status"] == status for record in records) for status in statuses},
        "byRetention": {status: sum(record["retentionStatus"] == status for record in records) for status in retention_states},
        "withLocalEvidence": sum(bool(record["localEvidence"]) for record in records),
        "localExact": sum(evidence["status"] == "exact" for record in records for evidence in record["localEvidence"]),
        "localDrifted": sum(evidence["status"] == "drifted" for record in records for evidence in record["localEvidence"]),
        "localMissing": sum(evidence["status"] == "missing" for record in records for evidence in record["localEvidence"]),
        "missingRetention": sum(record["retentionStatus"] == "missing-retention" for record in records),
        "remoteBodyDriftUnknown": sum(record["remoteBodyStatus"] == "unknown" for record in records),
        "checkedCurrent": len(checked_urls),
        "budgetExcluded": sum(record["status"] == "not-checked-budget" for record in records),
        "networkFailures": sum(record["status"] == "network-error" for record in records),
        "corpusSongUrls": declarations["corpusSongUrls"],
        "manifestReadIssues": len(manifest_issues),
    }
    output = {
        "generatedAt": utc_now(),
        "version": "source-health-v2",
        "checkMode": "offline" if args.offline else "live-bounded",
        "parameters": {
            "timeoutSeconds": args.timeout,
            "workers": max(1, args.workers),
            "perHostConcurrency": max(1, args.per_host_concurrency),
            "maxSeconds": args.max_seconds,
            "maxUrls": args.max_urls,
            "resumed": args.resume,
        },
        "policy": "Remote source changes are reported only. Retained source files are immutable and are never overwritten or replaced automatically. HEAD/range checks do not establish remote body-hash equality; remote body drift remains unknown unless a future body-hash check is recorded.",
        "inventory": {
            "corpusSongUrls": declarations["corpusSongUrls"],
            "fullManifestUrls": declarations["fullManifestUrls"],
            "bookCount": declarations["bookCount"],
            "books": by_book,
            "manifestReads": manifest_states,
            "manifestReadIssues": manifest_issues,
        },
        "summary": summary,
        "checkedHosts": checked_hosts,
        "records": records,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "checkMode": output["checkMode"], **summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
