#!/usr/bin/env python3
"""Extract authoritative recording URLs from retained source-page witnesses."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "work" / "source-transcriptions" / "2025"
OUTPUT = SOURCE_ROOT / "recording-index.json"
SOURCE_RE = re.compile(r'data-title="([^"]+)".*?data-src="(https?://[^" ]+\.mp3)"', re.S | re.I)


def main() -> int:
    records = {}
    for page in sorted(SOURCE_ROOT.glob("*.html")):
        if page.name.endswith(".fasola.html"):
            continue
        record = page.name.split("-", 1)[0]
        tracks = []
        for title, url in SOURCE_RE.findall(page.read_text(encoding="utf-8")):
            track = {"title": title.strip(), "url": url}
            if track not in tracks:
                tracks.append(track)
        if tracks:
            records[f"sh2025/{record}"] = {
                "sourcePage": f"work/source-transcriptions/2025/{page.name}",
                "tracks": tracks,
            }
    OUTPUT.write_text(json.dumps({"status": "source-witness", "records": records}, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed source recordings for {len(records)} edition records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
