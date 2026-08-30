#!/usr/bin/env python3
"""Index confirmed Sacred Harp 2025 page-scan image URLs.

The Bremen mirror uses stable image paths, but not every title slug follows
the same capitalization or punctuation rules. Probe a small, deterministic
set of candidates and record only URLs that respond as images. These scans
remain source notation, never transposable score data.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public/corpus.json"
OUTPUT = ROOT / "public/source-image-manifest.json"
HOST = "https://sacredharpbremen.org/wp-content/uploads/songs"

# A few current-edition pages use a title/number alias that cannot be derived
# from the normalized corpus title. These URLs were confirmed from the
# authoritative Bremen page HTML and are still source scans, never scores.
KNOWN_IMAGE_URLS = {
    "312b": f"{HOST}/300-399/312b-Restoration-First/312b.jpg",
    "461": f"{HOST}/400-499/461-John-337/461.jpg",
    "501b": f"{HOST}/500-599/501b-O-Leary/501b.jpg",
    "565b": f"{HOST}/500-599/565b-The-Hill-of-Zion/565b.jpg",
    "565t": f"{HOST}/500-599/565t-Hebron/565t.jpg",
}


def title_slug(title: str) -> str:
    return re.sub(r"^-|-$", "", re.sub(r"[^A-Za-z0-9]+", "-", title.replace("’", "").replace("'", "")))


def range_folder(number: int) -> str:
    if number < 100:
        return "001-099"
    lower = (number // 100) * 100
    return f"{lower}-{lower + 99}"


def candidates(song: dict) -> list[str]:
    song_no = str(song.get("songNo", "")).lower()
    match = re.match(r"(\d+)([tb])?$", song_no)
    if not match:
        return []
    number = int(match.group(1))
    suffix = match.group(2) or ""
    slug = title_slug(str(song.get("title", "")))
    page_slugs = []
    for url in song.get("urls", []):
        parsed = urlparse(url)
        if parsed.netloc != "sacredharpbremen.org":
            continue
        value = parsed.path.strip("/").split("/")[-1]
        if value and value not in page_slugs:
            page_slugs.append(value)
    folder_stems = [f"{song_no}-{slug}", f"{number:03d}{suffix}-{slug}"] + [
        f"{song_no}-{page_slug.split('-', 1)[-1]}" for page_slug in page_slugs if "-" in page_slug
    ]
    file_stems = [song_no, str(number), f"{song_no}-{slug}"]
    urls = []
    for folder in dict.fromkeys(folder_stems):
        for filename in dict.fromkeys(file_stems):
            urls.append(f"{HOST}/{range_folder(number)}/{folder}/{filename}.jpg")
    if song_no in KNOWN_IMAGE_URLS:
        urls.insert(0, KNOWN_IMAGE_URLS[song_no])
    return urls


def probe(url: str) -> bool:
    try:
        request = Request(url, method="HEAD", headers={"User-Agent": "Shape-Note-Atlas-source-index/1.0"})
        with urlopen(request, timeout=5) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            return 200 <= response.status < 300 and content_type.startswith("image/")
    except Exception:
        return False


def main() -> int:
    payload = json.loads(CORPUS.read_text(encoding="utf-8"))
    songs = [
        song
        for song in payload["songs"]
        if "sh2025" in song.get("books", [])
        and not song.get("scoreByBook", {}).get("sh2025")
        and not song.get("referenceScoreByBook", {}).get("sh2025")
    ]
    records: dict[str, dict[str, str]] = {}
    jobs = [
        (f"sh2025/{song['songNo'].lower()}", song, url)
        for song in songs
        for url in candidates(song)
    ]
    with ThreadPoolExecutor(max_workers=32) as executor:
        futures = {executor.submit(probe, url): (key, song, url) for key, song, url in jobs}
        for future in as_completed(futures):
            key, song, url = futures[future]
            if key in records:
                continue
            try:
                found = future.result()
            except Exception:
                found = False
            if found:
                records[key] = {
                    "songNo": str(song["songNo"]),
                    "title": str(song.get("title", "")),
                    "sourceImageUrl": url,
                }
    output = {
        "policy": "Confirmed remote page-scan URLs only; scans are authoritative source notation and are never promoted to transposable score data.",
        "records": dict(sorted(records.items())),
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed {len(records)} confirmed Sacred Harp 2025 source scans out of {len(songs)} current records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
