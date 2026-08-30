#!/usr/bin/env python3
"""Extract unambiguous score pages from multi-page candidate PDFs.

The extracted pages remain alternate-source review aids. The composite PDF and
its checksum stay attached to each candidate, and no extracted page is treated
as an edition-verified Sacred Harp score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "work" / "source-transcriptions" / "2025" / "clean-source-candidates.json"
EXTRACT_ROOT = ROOT / "work" / "source-transcriptions" / "2025" / "clean-source-candidates" / "extracted"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pdf_pages(path: Path) -> int:
    result = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=False)
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    return 0


def page_text(path: Path, page: int) -> str:
    result = subprocess.run(
        ["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(path), "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


def score_page(path: Path, title: str) -> int:
    marker = re.compile(rf"\b{re.escape(title.upper())}\s*\.")
    matches = [page for page in range(1, pdf_pages(path) + 1) if marker.search(page_text(path, page).upper())]
    if len(matches) != 1:
        raise ValueError(f"expected one score page for {title!r}, found {matches}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="append", default=[])
    args = parser.parse_args()
    payload = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    requested = {value.lower() for value in args.record}
    changed = 0
    for item in payload.get("records", []):
        song_no = str(item.get("songNo", "")).lower()
        if requested and song_no not in requested:
            continue
        source_relative = item.get("localPdf", "")
        source = ROOT / source_relative
        if not source.is_file() or pdf_pages(source) <= 2:
            continue
        page = score_page(source, str(item.get("candidateTitle") or item.get("title") or song_no))
        suffix = hashlib.sha256(str(item.get("pdfUrl", "")).encode("utf-8")).hexdigest()[:10]
        folder = EXTRACT_ROOT / f"{song_no}-{suffix}"
        extracted = folder / f"page-{page}.pdf"
        folder.mkdir(parents=True, exist_ok=True)
        if not extracted.exists():
            subprocess.run(
                ["pdfseparate", "-f", str(page), "-l", str(page), str(source), str(extracted)],
                check=True,
                capture_output=True,
                text=True,
            )
        item["compositePdf"] = source_relative
        item["compositePdfSha256"] = item.get("sha256", "")
        item["compositePdfPage"] = page
        item["omrInputPdf"] = str(extracted.relative_to(ROOT))
        item["omrInputSha256"] = digest(extracted)
        item["omrInputPages"] = 1
        item["omrInputStatus"] = "extracted-page-review-aid"
        changed += 1
        print(f"extracted {song_no} {item.get('candidateTitle', '')}: page {page}", flush=True)
    payload["generatedAt"] = datetime.now(timezone.utc).isoformat()
    payload["policy"] = "Candidate PDFs and extracted pages are alternate-source review aids. They are not Sacred Harp 2025 scores until edition comparison is complete."
    payload.setdefault("summary", {})["extractedCompositePages"] = sum(bool(item.get("omrInputPdf")) for item in payload.get("records", []))
    CANDIDATES.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"changed": changed, "extractedCompositePages": payload["summary"]["extractedCompositePages"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
