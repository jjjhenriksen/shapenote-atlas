#!/usr/bin/env python3
"""Fetch the public full-score MusicXML files listed by shapenote.net.

The dashboard's local corpus remains the metadata source of truth. This helper
only adds a score when the public index names the same book/page (or tune title)
and the downloaded file is a valid compressed MusicXML document. Raw downloads
live under work/ and are intentionally not needed by the browser at runtime.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATA = Path("/Users/jacquelinehenriksen/sh-corpus-scripts/dashboard/data.js")
INDEX_URL = "https://shapenote.net/music.htm"
INDEX_FILE = ROOT / "work" / "shapenote-music.htm"
LEGACY_INDEX_FILE = ROOT / "work-shapenote-music.htm"
RAW_DIR = ROOT / "work" / "shapenote-musicxml"
MANIFEST = ROOT / "public" / "shapenote-score-manifest.json"


def norm(value: str) -> str:
    value = value.lower().replace("’", "'")
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def norm_catalog_label(value: str) -> str:
    """Normalize a catalog label while retaining parenthesized identities."""
    value = value.lower().replace("’", "'")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def load_corpus() -> dict[str, Any]:
    text = SOURCE_DATA.read_text(encoding="utf-8")
    payload = text.split("window.SH_CORPUS_DATA = ", 1)[1].rsplit(";", 1)[0].strip()
    return json.loads(payload)


def fetch(url: str, destination: Path) -> None:
    if destination.exists() and destination.stat().st_size > 100:
        return
    request = urllib.request.Request(url, headers={"User-Agent": "Sacred-Harp-dashboard/1.0"})
    with urllib.request.urlopen(request, timeout=8) as response:
        data = response.read()
    destination.write_bytes(data)


def section_rows(soup: BeautifulSoup, heading: str) -> list[dict[str, Any]]:
    header = next((h for h in soup.find_all("h3") if heading in h.get_text(" ", strip=True)), None)
    if header is None:
        return []
    rows: list[dict[str, str]] = []
    node = header.find_next()
    while node and node.name != "h3":
        if node.name == "li":
            mxl = [a.get("href", "") for a in node.find_all("a", href=True) if a.get("href", "").lower().endswith(".mxl")]
            if mxl:
                rows.append({
                    "label": " ".join(node.get_text(" ", strip=True).split()),
                    "mxl": mxl[0],
                    # Russell is published twice in this catalog section:
                    # traditional and as-written. Preserve both links rather
                    # than silently dropping the second witness.
                    "mxlLinks": mxl,
                    "catalogSection": heading,
                })
        node = node.find_next()
    return rows


def choose_match(book_id: str, row: dict[str, str], songs: list[dict[str, Any]]) -> str | None:
    label = row["label"]
    if book_id == "sh2025":
        # Link annotations are not part of the identity. Keep the composer
        # text in parentheses, however: the 2025 catalog has two distinct
        # Lisbon entries that otherwise normalize to the same title.
        label_base = label.split("[", 1)[0].strip()
        label_key = norm_catalog_label(label_base)
        explicit = {
            "devotion daniel read": "50t",
            "lisbon daniel read": "467",
            "lisbon henry f chandler similar to sh1991 pg 51 my home first": "575",
        }
        if label_key in explicit:
            return explicit[label_key]
    else:
        label_base = label.split("[", 1)[0].strip()
    if book_id in {"sh1991", "shcooper2012", "southernharmony"}:
        match = re.match(r"^(\d+[a-z]?)\b", label.lower())
        if match:
            return match.group(1)
    title = norm(label_base)
    candidates = [song for song in songs if book_id in song.get("books", [])]
    exact = [song for song in candidates if norm(song.get("titlesByBook", {}).get(book_id, song.get("title", ""))) == title]
    if exact:
        return exact[0]["songNo"].lower()
    for song in candidates:
        candidate = norm(song.get("titlesByBook", {}).get(book_id, song.get("title", "")))
        if candidate and (candidate in title or title in candidate):
            return song["songNo"].lower()
    return None


def main() -> int:
    if not INDEX_FILE.exists() and LEGACY_INDEX_FILE.exists():
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        INDEX_FILE.write_bytes(LEGACY_INDEX_FILE.read_bytes())
    if not INDEX_FILE.exists():
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(INDEX_URL, headers={"User-Agent": "Sacred-Harp-dashboard/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            INDEX_FILE.write_bytes(response.read())
    soup = BeautifulSoup(INDEX_FILE.read_text(encoding="utf-8"), "html.parser")
    corpus = load_corpus()
    songs = corpus["songs"]
    sections = {
        "sh1991": "Sacred Harp (1991 Denson Revision)",
        "sh2025": "Sacred Harp (2025 Revision)",
        "shcooper2012": "Sacred Harp (Cooper Revision)",
        "southernharmony": "Southern Harmony",
    }
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict[str, str]] = {}
    unmatched: list[str] = []
    jobs: list[tuple[str, str, str, Path, str, str, str, str]] = []
    for book_id, heading in sections.items():
        for row in section_rows(soup, heading):
            song_no = choose_match(book_id, row, songs)
            if not song_no:
                unmatched.append(f"{book_id}: {row['label']}")
                continue
            # The 2025 section's Russell row is the only retained catalog row
            # whose second MXL is part of this audit. Keep the historical
            # one-link-per-row behavior for the other books so this provenance
            # correction does not widen the legacy manifest.
            links = row.get("mxlLinks", [row["mxl"]]) if book_id == "sh2025" else [row["mxl"]]
            for link_index, link in enumerate(links):
                url = link if link.startswith("http") else f"https://shapenote.net/{link}"
                url = urllib.parse.quote(url, safe=":/?&=%,")
                variant = ""
                if len(links) > 1:
                    stem = Path(urllib.parse.urlparse(url).path).stem.lower()
                    variant = "traditional" if stem.endswith("tr") else "as-written"
                key = f"{book_id}/{song_no}" if not variant or link_index == 0 else f"{book_id}/{song_no}-{variant}"
                destination = RAW_DIR / f"{hashlib.sha256(url.encode()).hexdigest()[:24]}.mxl"
                jobs.append((book_id, key, url, destination, row["label"], row["catalogSection"], song_no, variant))
    def download(job: tuple[str, str, str, Path, str, str, str, str]) -> tuple[str, dict[str, Any] | None, str | None]:
        _book_id, key, url, destination, label, catalog_section, source_record_key, variant = job
        try:
            fetch(url, destination)
            with zipfile.ZipFile(destination) as archive:
                if not any(name.endswith(".xml") and "container" not in name for name in archive.namelist()):
                    raise ValueError("missing MusicXML document")
        except Exception as exc:
            return key, None, str(exc)
        return key, {
            "sourceUrl": url,
            "rawPath": str(destination.relative_to(ROOT)),
            "sourceSha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "sourceBytes": destination.stat().st_size,
            "sourceEdition": _book_id,
            "sourceRecordKey": source_record_key,
            "catalogVariant": variant,
            "label": label,
            "catalogSection": catalog_section,
        }, None
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(download, job) for job in jobs]
        for future in as_completed(futures):
            key, entry, error = future.result()
            if entry:
                manifest[key] = entry
            elif error:
                print(f"skip {key}: {error}", file=sys.stderr)
    MANIFEST.write_text(json.dumps({"sourceUrl": INDEX_URL, "entries": manifest}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Fetched {len(manifest)} score mappings into {MANIFEST}")
    if unmatched:
        print(f"Unmatched source rows: {len(unmatched)}", file=sys.stderr)
        for item in unmatched[:20]:
            print(f"  {item}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
