#!/usr/bin/env python3
"""Bounded, non-destructive startup and static-bundle smoke test.

The verifier owns the preview process it starts and only terminates that
process. It never kills by name, changes ports globally, or mutates the
packaged application bundle.
"""

from __future__ import annotations

import argparse
import json
import re
import select
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
URL_RE = re.compile(r"https?://127\.0\.0\.1:(\d+)/")


def fetch(url: str, timeout: float) -> tuple[int, str, bytes]:
    request = Request(url, headers={"User-Agent": "shape-note-atlas-startup-smoke/1"})
    with urlopen(request, timeout=timeout) as response:
        return response.status, response.headers.get_content_type(), response.read()


def wait_for_preview(process: subprocess.Popen[str], timeout: float) -> str:
    deadline = time.monotonic() + timeout
    output: list[str] = []
    while time.monotonic() < deadline:
        line = ""
        if process.stdout:
            ready, _, _ = select.select([process.stdout], [], [], 0.1)
            if ready:
                line = process.stdout.readline()
        if line:
            output.append(line.rstrip())
            match = URL_RE.search(line)
            if match:
                return f"http://127.0.0.1:{match.group(1)}"
        elif process.poll() is not None:
            break
        else:
            time.sleep(0.05)
    detail = "\n".join(output[-12:])
    raise RuntimeError(f"preview did not announce a ready URL before timeout\n{detail}")


def stop_owned_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def check_static_bundle(dist: Path, package: Path) -> dict[str, object]:
    index = dist / "index.html"
    if not index.is_file():
        raise RuntimeError(f"missing build output: {index}")
    html = index.read_text(encoding="utf-8")
    asset_paths = re.findall(r'(?:src|href)="([^\"]+)', html)
    assets = [dist / path.lstrip("/") for path in asset_paths if path.startswith("/assets/")]
    missing = [str(path.relative_to(dist)) for path in assets if not path.is_file()]
    if missing:
        raise RuntimeError(f"index references missing assets: {missing}")

    required_package_files = [
        package / "Contents/Info.plist",
        package / "Contents/MacOS/ShapeNoteAtlas",
        package / "Contents/Resources/web/index.html",
        package / "Contents/Resources/web/corpus.json",
        package / "Contents/Resources/web/source-coverage.json",
    ]
    missing_package = [str(path) for path in required_package_files if not path.is_file()]
    if missing_package:
        raise RuntimeError(f"packaged app is incomplete: {missing_package}")

    corpus = json.loads((dist / "corpus.json").read_text(encoding="utf-8"))
    songs = corpus.get("songs") if isinstance(corpus, dict) else corpus
    if not isinstance(songs, list) or not songs:
        raise RuntimeError("dist/corpus.json is not a non-empty record collection")
    return {
        "distAssets": len(assets),
        "corpusRecords": len(songs),
        "package": str(package),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument(
        "--package",
        type=Path,
        default=ROOT / "outputs" / "The Shape-Note Atlas.app",
    )
    args = parser.parse_args()

    try:
        static_evidence = check_static_bundle(args.dist, args.package)
        process = subprocess.Popen(
            ["npm", "run", "preview", "--", "--host", "127.0.0.1", "--port", "0"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        try:
            base_url = wait_for_preview(process, args.timeout)
            checks = {
                "/": "text/html",
                "/corpus.json": "application/json",
                "/source-coverage.json": "application/json",
            }
            endpoint_evidence: dict[str, object] = {}
            for path, expected_type in checks.items():
                status, content_type, body = fetch(f"{base_url}{path}", args.timeout)
                if status != 200 or content_type != expected_type or not body:
                    raise RuntimeError(
                        f"{path}: expected 200/non-empty/{expected_type}, "
                        f"got {status}/{content_type}/{len(body)} bytes"
                    )
                endpoint_evidence[path] = {
                    "status": status,
                    "contentType": content_type,
                    "bytes": len(body),
                }
        finally:
            stop_owned_process(process)
        print(json.dumps({"status": "passed", "static": static_evidence, "preview": endpoint_evidence}, indent=2))
        return 0
    except (OSError, RuntimeError, URLError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
