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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "source-health.json"
USER_AGENT = "Shape-Note-Atlas-source-health/1.0"
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
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


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
    return {"url": url, "roles": set(), "references": set(), "localEvidence": []}


def add_url(inventory: dict[str, dict[str, Any]], url: str, role: str, reference: str) -> None:
    if not is_http_url(url):
        return
    item = inventory.setdefault(url, empty_item(url))
    item["roles"].add(role)
    item["references"].add(reference)


def walk_urls(value: Any, path: str, reference: str, inventory: dict[str, dict[str, Any]]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}"
            if is_http_url(child):
                add_url(inventory, child, source_role(child_path, child), f"{reference}:{key}")
            else:
                walk_urls(child, child_path, reference, inventory)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_urls(child, f"{path}/{index}", reference, inventory)


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
    inventory: dict[str, dict[str, Any]] = {}
    for path in JSON_SOURCES:
        payload = load_json(path)
        if not payload:
            continue
        reference = str(path.relative_to(ROOT))
        if path.name == "corpus.json":
            for song in payload.get("songs", []):
                if isinstance(song, dict):
                    walk_urls(song, "/songs", f"corpus:{song.get('id', song.get('songNo', 'unknown'))}", inventory)
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
    return inventory


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
    result["exists"] = path.is_file()
    result["actualSha256"] = ""
    result["actualBytes"] = None
    if not path.is_file():
        result["status"] = "missing"
        return result
    data = path.read_bytes()
    result["actualSha256"] = hashlib.sha256(data).hexdigest()
    result["actualBytes"] = len(data)
    expected_hash = str(evidence.get("expectedSha256", ""))
    expected_bytes = evidence.get("expectedBytes")
    result["status"] = "exact" if (not expected_hash or result["actualSha256"] == expected_hash) and (expected_bytes in (None, "", result["actualBytes"])) else "drifted"
    return result


def previous_by_url() -> dict[str, dict[str, Any]]:
    payload = load_json(OUTPUT)
    return {str(item.get("url")): item for item in payload.get("records", []) if isinstance(item, dict) and item.get("url")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="reuse the previous network result and only recheck local retained files")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--max-urls", type=int, default=0, help="optional bounded online check; remaining URLs are not-checked-budget")
    args = parser.parse_args()

    checked_at = utc_now()
    inventory = inventory_sources()
    previous = previous_by_url()
    urls = sorted(inventory)
    online_urls = [] if args.offline else urls
    if args.max_urls > 0:
        online_urls = online_urls[: args.max_urls]
    network_results: dict[str, dict[str, Any]] = {}
    if online_urls:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {executor.submit(request_url, url, args.timeout): url for url in online_urls}
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    network_results[url] = future.result()
                except Exception as exc:  # pragma: no cover - defensive worker isolation
                    network_results[url] = {"status": "network-error", "httpStatus": None, "finalUrl": url, "contentType": "", "method": "unknown", "redirects": [], "error": str(exc)}

    records = []
    for url in urls:
        item = inventory[url]
        if args.offline:
            prior = previous.get(url)
            network = {"status": "cached" if prior else "not-checked-offline", "httpStatus": prior.get("httpStatus") if prior else None, "finalUrl": prior.get("finalUrl", url) if prior else url, "contentType": prior.get("contentType", "") if prior else "", "method": "cached" if prior else "offline", "redirects": prior.get("redirects", []) if prior else []}
        else:
            network = network_results.get(url, {"status": "not-checked-budget", "httpStatus": None, "finalUrl": url, "contentType": "", "method": "budget", "redirects": []})
        records.append({"url": url, "roles": sorted(item["roles"]), "references": sorted(item["references"]), "checkedAt": checked_at, "evidenceScope": "network status/redirect/content-type plus retained-local checksum where available" if not args.offline else "cached network result plus retained-local checksum; no network request", **network, "localEvidence": [local_evidence_status(evidence) for evidence in item["localEvidence"]]})

    statuses = sorted({record["status"] for record in records})
    summary = {
        "totalUrls": len(records),
        "byStatus": {status: sum(record["status"] == status for record in records) for status in statuses},
        "withLocalEvidence": sum(bool(record["localEvidence"]) for record in records),
        "localExact": sum(evidence["status"] == "exact" for record in records for evidence in record["localEvidence"]),
        "localDrifted": sum(evidence["status"] == "drifted" for record in records for evidence in record["localEvidence"]),
        "localMissing": sum(evidence["status"] == "missing" for record in records for evidence in record["localEvidence"]),
    }
    output = {"generatedAt": utc_now(), "version": "source-health-v1", "checkMode": "offline" if args.offline else "online", "policy": "Remote source changes are reported only. Retained source files are immutable and are never overwritten or replaced automatically.", "summary": summary, "records": records}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "checkMode": output["checkMode"], **summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
