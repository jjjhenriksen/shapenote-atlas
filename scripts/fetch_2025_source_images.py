#!/usr/bin/env python3
"""Retain current 2025 source scans locally without changing the originals.

The public source-image index is an inventory of confirmed remote page scans.
This helper turns the 2025 records that still need transcription into local,
immutable source inputs. Existing retained originals are reused; new downloads
are written once to a URL-addressed path and recorded with a checksum.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public" / "corpus.json"
SOURCE_INDEX = ROOT / "public" / "source-image-manifest.json"
OUTPUT_ROOT = ROOT / "work" / "source-images" / "2025"
MANIFEST = ROOT / "work" / "source-images" / "manifest.json"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "untitled"


def current_missing_records(corpus: dict, source_index: dict) -> list[dict]:
    indexed = source_index.get("records", {})
    records = []
    for song in corpus.get("songs", []):
        if "sh2025" not in song.get("books", []):
            continue
        if song.get("scoreByBook", {}).get("sh2025") or song.get("referenceScoreByBook", {}).get("sh2025"):
            continue
        song_no = str(song.get("songNo", ""))
        key = f"sh2025/{song_no.lower()}"
        metadata = song.get("metadataByBook", {}).get("sh2025", {})
        indexed_record = indexed.get(key, {})
        source_url = indexed_record.get("sourceImageUrl") or metadata.get("sourceImageUrl", "")
        records.append({
            "queueId": key,
            "songNo": song_no,
            "title": song.get("titlesByBook", {}).get("sh2025", song.get("title", "")),
            "sourceImageUrl": source_url,
            "sourceIndexKey": key if indexed_record else "",
        })
    return sorted(records, key=lambda item: (int(re.match(r"\d+", item["songNo"]).group()), item["songNo"]))


def existing_local_source(song_no: str) -> Path | None:
    base = ROOT / "work" / "source-transcriptions" / "2025"
    if not base.exists():
        return None
    candidates = [
        path for path in base.rglob("*")
        if path.is_file()
        and path.suffix.lower() in IMAGE_SUFFIXES
        and (path.stem.lower() == song_no.lower() or path.stem.lower().startswith(f"{song_no.lower()}-"))
    ]
    return sorted(candidates)[0] if candidates else None


def is_image(data: bytes, content_type: str) -> bool:
    return (
        content_type.lower().startswith("image/")
        or data.startswith(b"\xff\xd8\xff")
        or data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith((b"II*\x00", b"MM\x00*", b"RIFF"))
    )


def download(url: str) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": "Shape-Note-Atlas-source-image-retainer/1.0"})
    with urlopen(request, timeout=45) as response:
        data = response.read()
        content_type = response.headers.get("Content-Type", "")
    if len(data) < 1000:
        raise ValueError(f"source image was unexpectedly small ({len(data)} bytes)")
    if not is_image(data, content_type):
        raise ValueError(f"source response is not an image ({content_type or 'unknown content type'})")
    return data, content_type


def retain(item: dict) -> dict:
    source_url = item["sourceImageUrl"]
    local = existing_local_source(item["songNo"])
    if local is not None:
        return {
            **item,
            "localPath": str(local.relative_to(ROOT)),
            "sha256": sha256_file(local),
            "bytes": local.stat().st_size,
            "contentType": "image/local-retained",
            "acquisition": "existing-local-source",
            "immutable": True,
            "status": "ready",
        }
    if not source_url:
        return {
            **item,
            "localPath": "",
            "sha256": "",
            "bytes": 0,
            "contentType": "",
            "acquisition": "source-url-missing",
            "immutable": True,
            "status": "source-url-missing",
        }
    url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:10]
    destination = OUTPUT_ROOT / f"{item['songNo'].lower()}-{slug(item['title'])}-{url_hash}.jpg"
    if destination.exists():
        return {
            **item,
            "localPath": str(destination.relative_to(ROOT)),
            "sha256": sha256_file(destination),
            "bytes": destination.stat().st_size,
            "contentType": "image/jpeg",
            "acquisition": "previously-retained-download",
            "immutable": True,
            "status": "ready",
        }
    data, content_type = download(source_url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{destination.name}.", dir=destination.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(data)
    try:
        temp_path.replace(destination)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return {
        **item,
        "localPath": str(destination.relative_to(ROOT)),
        "sha256": sha256_bytes(data),
        "bytes": len(data),
        "contentType": content_type,
        "acquisition": "remote-source-download",
        "immutable": True,
        "status": "ready",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="retain at most N records; zero means all")
    args = parser.parse_args()
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    source_index = json.loads(SOURCE_INDEX.read_text(encoding="utf-8"))
    records = current_missing_records(corpus, source_index)
    requested = records[: args.limit] if args.limit else records
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(retain, item): item["queueId"] for item in requested}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                item = next(record for record in requested if record["queueId"] == key)
                results[key] = {**item, "localPath": "", "sha256": "", "bytes": 0, "contentType": "", "acquisition": "download-failed", "immutable": True, "status": "download-failed", "error": str(exc)}
    prior = {}
    if MANIFEST.exists():
        try:
            prior = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prior = {}
    merged = {item["queueId"]: item for item in prior.get("records", [])}
    merged.update(results)
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "version": "2025-source-images-v1",
        "policy": "Retained source scans are immutable originals. Downloads are checksum-tracked and never overwritten by working-image transforms or promoted as notation.",
        "sourceIndex": str(SOURCE_INDEX.relative_to(ROOT)),
        "recordCount": len(merged),
        "ready": sum(item.get("status") == "ready" for item in merged.values()),
        "failed": sum(item.get("status") == "download-failed" for item in merged.values()),
        "records": [merged[key] for key in sorted(merged)],
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(payload["records"]), "processedThisRun": len(requested), "ready": payload["ready"], "failed": payload["failed"], "output": str(MANIFEST)}, indent=2))
    return 1 if payload["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
