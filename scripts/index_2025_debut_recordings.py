#!/usr/bin/env python3
"""Index the official 2025 Sacred Harp debut-singing recordings.

The recording titles carry the edition page number.  This script only accepts
that explicit page-number evidence and refuses to create a fuzzy title match.
The resulting index is source audio, not notation and never promotes a song
into the transposable-score path.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METADATA_URL = "https://archive.org/metadata/sacredharp2025edition"
DEFAULT_OUTPUT = ROOT / "work/source-transcriptions/2025/debut-recording-index.json"
SOURCE_PAGE = "https://sacredharp.com/museum/debut-singing-sacred-harp-2025-edition/"
COLLECTION_URL = "https://archive.org/details/sacredharp2025edition"
DOWNLOAD_ROOT = "https://archive.org/download/sacredharp2025edition"


def load_metadata(path: Path | None, url: str) -> dict:
    if path:
        return json.loads(path.read_text(encoding="utf-8"))
    with urlopen(url, timeout=30) as response:
        return json.load(response)


def parse_source_title(title: str) -> tuple[str, str] | None:
    match = re.match(r"^(\d+\s*[tb]?)\s*[-–]\s*(.+)$", title.strip(), re.IGNORECASE)
    if not match:
        return None
    page = re.sub(r"\s+", "", match.group(1)).lower()
    return page, match.group(2).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-path", type=Path, help="Use a downloaded Internet Archive metadata JSON")
    parser.add_argument("--metadata-url", default=DEFAULT_METADATA_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = load_metadata(args.metadata_path, args.metadata_url)
    mp3_files = [file for file in payload.get("files", []) if str(file.get("name", "")).lower().endswith(".mp3")]
    if len(mp3_files) != 88:
        raise SystemExit(f"Expected 88 official debut recordings, found {len(mp3_files)}")

    records: dict[str, dict] = {}
    for file in sorted(mp3_files, key=lambda item: item.get("name", "")):
        parsed = parse_source_title(str(file.get("title", "")))
        if not parsed:
            raise SystemExit(f"Recording title has no explicit page number: {file.get('name')!r}")
        page, song_title = parsed
        key = f"sh2025/{page}"
        if key in records:
            raise SystemExit(f"Duplicate debut recording page: {page}")
        filename = str(file["name"])
        records[key] = {
            "sourcePage": SOURCE_PAGE,
            "sourceCollectionUrl": COLLECTION_URL,
            "tracks": [{
                "title": f"{page} · 2025 debut singing",
                "url": f"{DOWNLOAD_ROOT}/{filename}",
                "kind": "full-song-source-witness",
                "isFullSong": True,
                "sourceFile": filename,
                "sourceTitle": str(file.get("title", "")),
                "sourceSongTitle": song_title,
                "md5": str(file.get("md5", "")),
                "sha1": str(file.get("sha1", "")),
                "durationSeconds": float(file["length"]) if file.get("length") else None,
            }],
        }

    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "status": "source-witness",
        "edition": "sh2025",
        "recordCount": len(records),
        "sourcePage": SOURCE_PAGE,
        "sourceCollectionUrl": COLLECTION_URL,
        "sourceDescription": "Official recordings from the Sacred Harp 2025 Edition debut singing; audio only, not transposable notation.",
        "records": dict(sorted(records.items())),
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed {len(records)} official Sacred Harp 2025 debut recordings into {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
