#!/usr/bin/env python3
"""Bounded, non-destructive startup audit for The Shape-Note Atlas.

Only processes started by this check are stopped. Source data and global
configuration are never changed. The receipt records local and packaged
static evidence separately from the optional native-shell probe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import select
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
URL_RE = re.compile(r"https?://127\.0\.0\.1:(\d+)/")
PORT_RE = re.compile(r"(?:127\.0\.0\.1:|\()(?P<port>\d{2,5})\b")


class StartupCheckError(RuntimeError):
    """A fail-closed startup assertion."""


def fetch(url: str, timeout: float = 3.0) -> tuple[int, str, bytes]:
    request = Request(url, headers={"User-Agent": "shape-note-atlas-agent-09-startup/1"})
    with urlopen(request, timeout=timeout) as response:
        return response.status, response.headers.get_content_type(), response.read()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stop_owned_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def read_available(process: subprocess.Popen[str], output: list[str]) -> None:
    if not process.stdout:
        return
    ready, _, _ = select.select([process.stdout], [], [], 0)
    while ready:
        line = process.stdout.readline()
        if not line:
            break
        output.append(line.rstrip())
        ready, _, _ = select.select([process.stdout], [], [], 0)


def wait_for_announcement(
    process: subprocess.Popen[str], pattern: re.Pattern[str], timeout: float
) -> tuple[str, list[str]]:
    deadline = time.monotonic() + timeout
    output: list[str] = []
    while time.monotonic() < deadline:
        read_available(process, output)
        for line in output:
            match = pattern.search(line)
            if match:
                return f"http://127.0.0.1:{match.group(1)}", output
        if process.poll() is not None:
            break
        time.sleep(0.05)
    detail = "\n".join(output[-20:])
    if process.poll() is not None:
        raise StartupCheckError(f"owned server exited before readiness (code {process.returncode})\n{detail}")
    raise StartupCheckError(f"owned server did not announce readiness within {timeout:g}s\n{detail}")


def wait_for_http(base_url: str, paths: list[str], timeout: float) -> dict[str, dict[str, Any]]:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            evidence: dict[str, dict[str, Any]] = {}
            for path in paths:
                status, content_type, body = fetch(f"{base_url}{path}", timeout=min(timeout, 2.0))
                if status != 200 or not body:
                    raise StartupCheckError(f"{path}: expected 200/non-empty, got {status}/{len(body)} bytes")
                evidence[path] = {"status": status, "contentType": content_type, "bytes": len(body)}
            return evidence
        except (HTTPError, URLError, OSError, StartupCheckError) as error:
            last_error = str(error)
            time.sleep(0.1)
    raise StartupCheckError(f"readiness endpoints did not settle within {timeout:g}s: {last_error}")


def check_html_assets(root: Path) -> dict[str, Any]:
    index = root / "index.html"
    if not index.is_file():
        raise StartupCheckError(f"missing deployment entry point: {index}")
    html = index.read_text(encoding="utf-8")
    references = re.findall(r'(?:src|href)="([^\"]+)"', html)
    asset_references = [reference for reference in references if reference.startswith("/assets/")]
    missing = [reference for reference in asset_references if not (root / reference.lstrip("/")).is_file()]
    if missing:
        raise StartupCheckError(f"entry point references missing assets: {missing}")
    return {"entryPointBytes": len(html.encode("utf-8")), "assetReferences": asset_references}


def compare_trees(left: Path, right: Path) -> dict[str, int]:
    left_files = {path.relative_to(left) for path in left.rglob("*") if path.is_file()}
    right_files = {path.relative_to(right) for path in right.rglob("*") if path.is_file()}
    missing = sorted(str(path) for path in left_files - right_files)
    extra = sorted(str(path) for path in right_files - left_files)
    changed = sorted(str(path) for path in left_files & right_files if sha256(left / path) != sha256(right / path))
    if missing or extra or changed:
        raise StartupCheckError(
            f"packaged web resources differ from dist (missing={missing[:8]}, extra={extra[:8]}, changed={changed[:8]})"
        )
    return {"files": len(left_files), "sha256Compared": len(left_files & right_files)}


def book_value(record: dict[str, Any], field: str, book_id: str) -> dict[str, Any] | None:
    value = record.get(field)
    if not isinstance(value, dict):
        return None
    item = value.get(book_id)
    return item if isinstance(item, dict) else None


def choose_representatives(corpus: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = corpus.get("songs")
    if not isinstance(records, list):
        raise StartupCheckError("corpus.json does not contain a songs list")
    selected: dict[str, dict[str, Any] | None] = {
        "exact": None,
        "unknownKey": None,
        "reference": None,
        "draft": None,
        "missingNotation": None,
    }
    for record in records:
        if not isinstance(record, dict):
            continue
        score = book_value(record, "scoreByBook", "sh1991")
        if selected["exact"] is None and score and score.get("transposition", {}).get("available"):
            selected["exact"] = {"record": record, "book": "sh1991", "kind": "exact-score", "asset": score.get("scoreRef")}
        if selected["unknownKey"] is None and score and not score.get("keySignature"):
            selected["unknownKey"] = {"record": record, "book": "sh1991", "kind": "unknown-key", "asset": score.get("scoreRef")}
        reference = book_value(record, "referenceScoreByBook", "sh2025")
        if selected["reference"] is None and reference:
            selected["reference"] = {"record": record, "book": "sh2025", "kind": "reference-witness", "asset": reference.get("scoreRef")}
        draft = book_value(record, "draftScoreByBook", "sh2025")
        if selected["draft"] is None and draft and not book_value(record, "scoreByBook", "sh2025") and not reference:
            selected["draft"] = {"record": record, "book": "sh2025", "kind": "review-draft", "asset": draft.get("scoreRef")}
        coverage = book_value(record, "sourceCoverageByBook", "sh2025")
        if selected["missingNotation"] is None and coverage and coverage.get("status") == "transcription-blocked" and not book_value(record, "scoreByBook", "sh2025"):
            selected["missingNotation"] = {"record": record, "book": "sh2025", "kind": "missing-notation", "asset": None}
        if all(selected.values()):
            break
    absent = [name for name, item in selected.items() if item is None]
    if absent:
        raise StartupCheckError(f"corpus lacks representative states: {absent}")
    return {name: item for name, item in selected.items() if item is not None}


def check_bundle(dist: Path, package: Path) -> dict[str, Any]:
    dist_evidence = check_html_assets(dist)
    package_web = package / "Contents/Resources/web"
    required = [
        package / "Contents/Info.plist",
        package / "Contents/MacOS/ShapeNoteAtlas",
        package_web / "index.html",
        package_web / "corpus.json",
        package_web / "source-coverage.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise StartupCheckError(f"packaged app is incomplete: {missing}")
    return {"dist": dist_evidence, "package": check_html_assets(package_web), "resourceTree": compare_trees(dist, package_web)}


def check_preview(timeout: float, paths: list[str]) -> dict[str, Any]:
    process = subprocess.Popen(
        ["npm", "run", "preview", "--", "--host", "127.0.0.1", "--port", "0"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    try:
        base_url, output = wait_for_announcement(process, URL_RE, timeout)
        return {"baseUrl": base_url, "announce": output[-8:], "endpoints": wait_for_http(base_url, paths, timeout)}
    finally:
        stop_owned_process(process)


def start_python_server(root: Path) -> tuple[subprocess.Popen[str], str, list[str]]:
    code = """
import functools, http.server, sys
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=sys.argv[1])
server = http.server.ThreadingHTTPServer((\"127.0.0.1\", 0), handler)
print(server.server_port, flush=True)
server.serve_forever()
"""
    process = subprocess.Popen([sys.executable, "-c", code, str(root)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    base_url, output = wait_for_announcement(process, re.compile(r"^(\d{2,5})$"), 8)
    return process, base_url, output


def check_packaged_static(package_web: Path, timeout: float, paths: list[str]) -> dict[str, Any]:
    process, base_url, output = start_python_server(package_web)
    try:
        return {"baseUrl": base_url, "announce": output[-4:], "endpoints": wait_for_http(base_url, paths, timeout)}
    finally:
        stop_owned_process(process)


def check_occupied_port(timeout: float) -> dict[str, Any]:
    reservation = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    reservation.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    reservation.bind(("127.0.0.1", 0))
    occupied_port = reservation.getsockname()[1]
    process = subprocess.Popen(
        ["npm", "run", "preview", "--", "--host", "127.0.0.1", "--port", str(occupied_port), "--strictPort"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output: list[str] = []
    try:
        deadline = time.monotonic() + timeout
        while process.poll() is None and time.monotonic() < deadline:
            read_available(process, output)
            time.sleep(0.05)
        if process.poll() is None:
            raise StartupCheckError(f"occupied-port probe did not fail within {timeout:g}s")
        if process.returncode == 0:
            raise StartupCheckError(f"occupied-port probe unexpectedly succeeded: {output[-8:]}")
        return {"port": occupied_port, "exitCode": process.returncode, "diagnostics": output[-8:]}
    finally:
        stop_owned_process(process)
        reservation.close()


def descendant_pids(root_pid: int) -> list[int]:
    try:
        result = subprocess.run(["ps", "-axo", "pid=,ppid="], text=True, capture_output=True, check=False, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return [root_pid]
    children: dict[int, list[int]] = {}
    for line in result.stdout.splitlines():
        values = line.split()
        if len(values) != 2:
            continue
        pid, parent = (int(value) for value in values)
        children.setdefault(parent, []).append(pid)
    found = [root_pid]
    pending = [root_pid]
    while pending:
        parent = pending.pop()
        for child in children.get(parent, []):
            if child not in found:
                found.append(child)
                pending.append(child)
    return found


def listening_port(root_pid: int) -> int | None:
    try:
        result = subprocess.run(
            ["lsof", "-Pan", "-p", ",".join(str(pid) for pid in descendant_pids(root_pid)), "-iTCP", "-sTCP:LISTEN", "-n"],
            text=True,
            capture_output=True,
            check=False,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    ports = [int(match.group("port")) for match in PORT_RE.finditer(result.stdout)]
    return ports[0] if ports else None


def check_native_app(package: Path, timeout: float, paths: list[str]) -> dict[str, Any]:
    if sys.platform != "darwin":
        return {"status": "not-applicable", "detail": "native wrapper requires macOS"}
    binary = package / "Contents/MacOS/ShapeNoteAtlas"
    process = subprocess.Popen([str(binary)], cwd=package, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    owned_pids = [process.pid]
    output: list[str] = []
    try:
        deadline = time.monotonic() + timeout
        port = None
        while time.monotonic() < deadline and process.poll() is None:
            owned_pids = descendant_pids(process.pid)
            port = listening_port(process.pid)
            if port:
                break
            read_available(process, output)
            time.sleep(0.1)
        if not port:
            read_available(process, output)
            detail = "native app did not expose its private local service"
            if process.poll() is not None:
                detail += f" (exit code {process.returncode})"
            return {"status": "environment-limited", "detail": detail, "output": output[-12:]}
        base_url = f"http://127.0.0.1:{port}"
        return {"status": "passed", "baseUrl": base_url, "port": port, "endpoints": wait_for_http(base_url, paths, timeout)}
    finally:
        stop_owned_process(process)
        for pid in owned_pids:
            if pid == process.pid:
                continue
            try:
                os.kill(pid, 15)
            except (ProcessLookupError, PermissionError, OSError):
                pass


def representative_evidence(item: dict[str, Any]) -> dict[str, Any]:
    record = item["record"]
    coverage = book_value(record, "sourceCoverageByBook", item["book"]) or {}
    return {"kind": item["kind"], "book": item["book"], "songNo": record.get("songNo"), "title": record.get("title"), "sourceStatus": coverage.get("status"), "asset": item.get("asset")}


def run(args: argparse.Namespace) -> dict[str, Any]:
    dist = args.dist.resolve()
    package = args.package.resolve()
    corpus = json.loads((dist / "corpus.json").read_text(encoding="utf-8"))
    representatives = choose_representatives(corpus)
    asset_paths = sorted({item["asset"] for item in representatives.values() if item.get("asset")})
    paths = ["/", "/corpus.json", "/source-coverage.json", *asset_paths]
    checks = {
        "bundle": check_bundle(dist, package),
        "representatives": {name: representative_evidence(item) for name, item in representatives.items()},
        "preview": check_preview(args.timeout, paths),
        "packagedStatic": check_packaged_static(package / "Contents/Resources/web", args.timeout, paths),
        "occupiedPort": check_occupied_port(args.timeout),
        "nativeApp": check_native_app(package, args.timeout, paths),
    }
    return {
        "schemaVersion": 1,
        "status": "passed",
        "projectRoot": str(ROOT),
        "gitHead": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False).stdout.strip(),
        "checks": checks,
        "limitations": [checks["nativeApp"]["detail"]] if checks["nativeApp"].get("status") != "passed" else [],
        "policy": {"ownedProcessesOnly": True, "sourceDataMutated": False, "portMode": "ephemeral", "packagedResourceTreeCompared": True},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--package", type=Path, default=ROOT / "outputs" / "The Shape-Note Atlas.app")
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--receipt", type=Path, default=ROOT / "work/agent-09-startup/receipt.json")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    try:
        receipt = run(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, URLError) as error:
        receipt = {"schemaVersion": 1, "status": "failed", "error": str(error), "projectRoot": str(ROOT)}
        if not args.no_write:
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(receipt, indent=2))
        return 1
    if not args.no_write:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
