#!/usr/bin/env python3
"""Index public clean-source PDF candidates for missing 2025 records.

These files are acquisition candidates, not edition-verified scores.  A
composer's public PDF can be used to improve OMR and manual comparison, but it
must never be promoted as the Sacred Harp 2025 engraving without a note-for-
note comparison against the authorized 2025 source.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public" / "corpus.json"
DEFAULT_CROSSWALK = Path("/Users/jacquelinehenriksen/sh-corpus-scripts/modern_shape_note_duplicate_candidates.csv")
OUTPUT = ROOT / "work" / "source-transcriptions" / "2025" / "clean-source-candidates.json"
DOWNLOAD_ROOT = ROOT / "work" / "source-transcriptions" / "2025" / "clean-source-candidates"
USER_AGENT = "Shape-Note-Atlas/1.0 (source-candidate-index; local research)"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "untitled"


def fetch(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=12) as response:
        return response.read(), response.headers.get_content_type()


def pdf_links(page_url: str, payload: bytes) -> list[str]:
    text = payload.decode("utf-8", "ignore")
    links: list[str] = []
    for raw in re.findall(r"href\s*=\s*[\"']([^\"']+)[\"']", text, flags=re.I):
        value = html.unescape(raw)
        if ".pdf" not in value.lower():
            continue
        links.append(urllib.parse.urljoin(page_url, value))
    return list(dict.fromkeys(links))


def load_rows(path: Path, corpus: dict[str, Any], match_kind: str) -> list[dict[str, Any]]:
    current = {
        str(song.get("songNo", "")).lower(): song
        for song in corpus.get("songs", [])
        if "sh2025" in song.get("books", [])
    }
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row.get("matched_book_id") != "sh2025":
                continue
            if match_kind and row.get("match_kind") != match_kind:
                continue
            song_no = row.get("matched_song_no", "").lower()
            if song_no not in current:
                continue
            rows.append(row)
    # Multiple public compositions can match one page; retain every candidate
    # but keep output deterministic for review.
    return sorted(rows, key=lambda row: (row.get("matched_song_no", ""), row.get("source_url", "")))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--download", action="store_true", help="download discovered PDFs into work/ only")
    parser.add_argument("--match-kind", default="", help="only index one crosswalk match kind, such as same_title_and_text_key")
    args = parser.parse_args()
    if not args.crosswalk.exists():
        raise SystemExit(f"candidate crosswalk not found: {args.crosswalk}")

    socket.setdefaulttimeout(12)
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    rows = load_rows(args.crosswalk, corpus, args.match_kind)
    previous_by_identity: dict[tuple[str, str], dict[str, Any]] = {}
    if OUTPUT.exists():
        try:
            previous_payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
            previous_by_identity = {
                (str(item.get("songNo", "")).lower(), item.get("pdfUrl", "")): item
                for item in previous_payload.get("records", [])
            }
        except (OSError, json.JSONDecodeError):
            previous_by_identity = {}
    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for row in rows:
        page_url = row.get("source_url", "")
        target = {
            "bookId": "sh2025",
            "songNo": row.get("matched_song_no", ""),
            "title": row.get("matched_title", ""),
            "candidateTitle": row.get("source_title", ""),
            "candidatePageUrl": page_url,
            "matchKind": row.get("match_kind", ""),
            "status": "candidate-source-needs-edition-comparison",
            "editionVerified": False,
            "structuredScoreAdmissible": False,
            "policy": "Public candidate source only; compare against the authorized Sacred Harp 2025 engraving before promotion.",
            "pdfUrl": "",
            "localPdf": "",
            "sha256": "",
        }
        try:
            payload, content_type = fetch(page_url)
            if page_url.lower().endswith(".pdf") or content_type == "application/pdf":
                links = [page_url]
                pdf_payload = payload
            else:
                links = pdf_links(page_url, payload)
                if not links:
                    raise ValueError("public page exposes no PDF download link")
                # Prefer the site's explicit download asset over unrelated PDFs.
                links.sort(key=lambda value: ("media.sacredharptunes.com" not in value, len(value)))
                target["pdfUrl"] = links[0]
                pdf_payload, pdf_type = fetch(links[0])
                if pdf_type != "application/pdf" and not pdf_payload.startswith(b"%PDF"):
                    raise ValueError(f"download is not a PDF ({pdf_type})")
            target["pdfUrl"] = links[0]
            if not pdf_payload.startswith(b"%PDF"):
                raise ValueError("candidate payload does not begin with a PDF signature")
            target["sha256"] = hashlib.sha256(pdf_payload).hexdigest()
            target["candidateKey"] = f"sh2025/{target['songNo']}/{hashlib.sha256(target['sha256'].encode('utf-8')).hexdigest()[:10]}"
            previous = previous_by_identity.get((target["songNo"].lower(), target["pdfUrl"]))
            if previous and previous.get("sha256") == target["sha256"]:
                for field in ("compositePdf", "compositePdfSha256", "compositePdfPage", "omrInputPdf", "omrInputSha256", "omrInputPages", "omrInputStatus"):
                    if previous.get(field) is not None:
                        target[field] = previous[field]
            if args.download:
                source_suffix = hashlib.sha256(target["pdfUrl"].encode("utf-8")).hexdigest()[:10]
                directory = DOWNLOAD_ROOT / slug(f"{target['songNo']}-{target['title']}-{target['candidateTitle']}")
                directory = directory.with_name(f"{directory.name}-{source_suffix}")
                directory.mkdir(parents=True, exist_ok=True)
                path = directory / "source-candidate.pdf"
                if not path.exists() or path.read_bytes() != pdf_payload:
                    path.write_bytes(pdf_payload)
                target["localPdf"] = str(path.relative_to(ROOT))
        except (OSError, urllib.error.URLError, ValueError) as exc:
            target["status"] = "candidate-source-fetch-failed"
            errors.append({"songNo": target["songNo"], "title": target["title"], "url": page_url, "error": str(exc)})
        records.append(target)
        print(f"indexed {target['songNo']} {target['title']}: {target['status']}", flush=True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "policy": "Candidate PDFs are clean-source research aids. They are not Sacred Harp 2025 scores until edition comparison is complete.",
                "crosswalk": str(args.crosswalk),
                "downloaded": args.download,
                "summary": {
                    "candidates": len(records),
                    "pdfs": sum(bool(item.get("pdfUrl")) for item in records),
                    "downloadedPdfs": sum(bool(item.get("localPdf")) for item in records),
                    "fetchFailures": len(errors),
                    "sameTitleAndTextKey": sum(item.get("matchKind") == "same_title_and_text_key" for item in records),
                },
                "records": records,
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(OUTPUT), "summary": {"candidates": len(records), "pdfs": sum(bool(item.get("pdfUrl")) for item in records), "downloadedPdfs": sum(bool(item.get("localPdf")) for item in records), "fetchFailures": len(errors)}}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
