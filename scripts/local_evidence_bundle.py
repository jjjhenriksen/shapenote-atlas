#!/usr/bin/env python3
"""Export, verify, and restore an explicit retained-evidence bundle.

The dependency manifest is the allow-list.  Export copies only records that
are explicitly marked ``tracked: false`` and ``status: present``.  Verification
checks the embedded manifest and every file hash.  Restore is fail-closed: it
rejects unsafe paths, symlinks, and conflicting existing bytes, and writes only
files that are absent from a separate destination checkout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "work" / "luna-program-20260904" / "data" / "retained-source-dependency-manifest.json"
DEFAULT_BUNDLE = ROOT / "work" / "luna-program-20260904" / "data" / "evidence-bundles" / "retained-source-evidence-v2"
BUNDLE_VERSION = 1


class BundleError(RuntimeError):
    """A bundle is invalid or cannot be safely processed."""


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def bytes_and_digest(path: Path) -> tuple[int, str]:
    return path.stat().st_size, digest(path)


def safe_relative_path(value: Any) -> str:
    """Return a normalized repo-relative path or reject traversal/absolute paths."""
    if not isinstance(value, str) or not value or "\\" in value:
        raise BundleError(f"unsafe relative path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise BundleError(f"unsafe relative path: {value!r}")
    normalized = path.as_posix()
    if normalized != value:
        raise BundleError(f"non-normalized relative path: {value!r}")
    return normalized


def resolve_repo_path(root: Path, relative: str) -> Path:
    safe = safe_relative_path(relative)
    candidate = root / safe
    try:
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise BundleError(f"path escapes repository root: {relative}") from error
    return candidate


def reject_symlink_path(path: Path, *, stop: Path) -> None:
    """Reject a symlink in path or any existing ancestor through stop."""
    current = path
    stop_resolved = stop.resolve(strict=False)
    while True:
        if current.is_symlink():
            raise BundleError(f"symlink path is not allowed: {current}")
        if current == stop or current.resolve(strict=False) == stop_resolved:
            break
        parent = current.parent
        if parent == current:
            break
        current = parent


def load_json(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BundleError(f"invalid JSON file {path}: {error}") from error
    if not isinstance(value, dict):
        raise BundleError(f"JSON object required: {path}")
    return value, raw


def selected_records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records = manifest.get("records")
    if not isinstance(records, list):
        raise BundleError("dependency manifest records must be a list")
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise BundleError("dependency manifest contains a non-object record")
        if "path" not in record:
            raise BundleError("dependency manifest record has no path")
        safe_relative_path(record.get("path"))
        if record.get("tracked") is not False or record.get("status") != "present":
            continue
        relative = record["path"]
        if relative in seen:
            raise BundleError(f"duplicate selected dependency path: {relative}")
        seen.add(relative)
        selected.append(record)
    return sorted(selected, key=lambda item: item["path"])


def selection_summary(manifest: dict[str, Any], selected: list[dict[str, Any]]) -> dict[str, Any]:
    records = manifest.get("records")
    assert isinstance(records, list)
    selected_paths = {record["path"] for record in selected}
    excluded = []
    for record in records:
        if record["path"] in selected_paths:
            continue
        excluded.append(
            {
                "path": record["path"],
                "tracked": record.get("tracked"),
                "status": record.get("status"),
                "reason": "tracked dependency excluded from local evidence bundle" if record.get("tracked") is True else "not explicitly present and untracked; excluded fail-closed",
            }
        )
    missing_or_unavailable = [
        item for item in excluded if item["status"] != "present"
    ]
    return {
        "manifestRecords": len(records),
        "selectedPresentUntracked": len(selected),
        "excludedRecords": len(excluded),
        "excludedTracked": sum(item["tracked"] is True for item in excluded),
        "excludedMissingOrUnavailable": len(missing_or_unavailable),
        "completeForSelectedPresentUntracked": not missing_or_unavailable,
        "completeForAllManifestDependencies": not excluded,
        "excluded": excluded,
    }


def source_manifest_record(record: dict[str, Any]) -> dict[str, Any]:
    """Keep provenance and expected values needed to verify a restored file."""
    fields = (
        "path",
        "artifactClasses",
        "status",
        "bytes",
        "sha256",
        "expectedSha256",
        "expectedBytes",
        "sourceUrls",
        "consumers",
        "gates",
        "references",
        "tracked",
        "immutable",
        "derived",
        "acquisitionRequirement",
    )
    return {field: record.get(field) for field in fields}


def bundle_file_records(bundle_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    files = bundle_manifest.get("files")
    if not isinstance(files, list):
        raise BundleError("bundle files must be a list")
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in files:
        if not isinstance(item, dict):
            raise BundleError("bundle contains a non-object file record")
        relative = safe_relative_path(item.get("path"))
        if relative in seen:
            raise BundleError(f"duplicate bundle file path: {relative}")
        seen.add(relative)
        if item.get("tracked") is not False or item.get("status") != "present":
            raise BundleError(f"bundle file is not an explicitly listed present untracked dependency: {relative}")
        if not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64:
            raise BundleError(f"bundle file has invalid hash: {relative}")
        if not isinstance(item.get("bytes"), int) or item["bytes"] < 0:
            raise BundleError(f"bundle file has invalid byte count: {relative}")
        result.append(item)
    return sorted(result, key=lambda item: item["path"])


def validate_bundle(bundle: Path) -> dict[str, Any]:
    if not bundle.is_dir() or bundle.is_symlink():
        raise BundleError(f"bundle directory is missing or unsafe: {bundle}")
    bundle_manifest_path = bundle / "bundle-manifest.json"
    source_manifest_path = bundle / "source-manifest.json"
    files_root = bundle / "files"
    if bundle_manifest_path.is_symlink() or not bundle_manifest_path.is_file():
        raise BundleError("bundle does not contain a safe bundle-manifest.json")
    bundle_manifest, _ = load_json(bundle_manifest_path)
    if bundle_manifest.get("schemaVersion") != BUNDLE_VERSION:
        raise BundleError("unsupported bundle schema version")
    if not source_manifest_path.is_file() or source_manifest_path.is_symlink():
        raise BundleError("bundle does not contain a safe source-manifest.json")
    source_manifest, source_raw = load_json(source_manifest_path)
    expected_source_hash = bundle_manifest.get("sourceManifestSha256")
    if expected_source_hash != hashlib.sha256(source_raw).hexdigest():
        raise BundleError("embedded source manifest hash mismatch")
    if bundle_manifest.get("sourceManifestBytes") != len(source_raw):
        raise BundleError("embedded source manifest byte count mismatch")
    files = bundle_file_records(bundle_manifest)
    if bundle_manifest.get("fileCount") != len(files):
        raise BundleError("bundle file count metadata is stale")
    if bundle_manifest.get("totalBytes") != sum(item["bytes"] for item in files):
        raise BundleError("bundle byte-count metadata is stale")
    source_selected = selected_records(source_manifest)
    source_by_path = {record["path"]: record for record in source_selected}
    if set(item["path"] for item in files) != set(source_by_path):
        raise BundleError("bundle file allow-list differs from embedded dependency manifest")
    if not files_root.is_dir() or files_root.is_symlink():
        raise BundleError("bundle files directory is missing or unsafe")

    actual_files: set[str] = set()
    for path in files_root.rglob("*"):
        if path.is_symlink():
            raise BundleError(f"bundle contains a symlink: {path}")
        if path.is_file():
            relative = path.relative_to(files_root).as_posix()
            safe_relative_path(relative)
            actual_files.add(relative)
    if actual_files != set(source_by_path):
        raise BundleError("bundle contains extra or missing unlisted files")

    for item in files:
        relative = item["path"]
        source_record = source_by_path[relative]
        if item.get("sha256") != source_record.get("sha256") or item.get("bytes") != source_record.get("bytes"):
            raise BundleError(f"bundle metadata disagrees with source manifest: {relative}")
        path = files_root / relative
        reject_symlink_path(path, stop=files_root)
        actual_bytes, actual_hash = bytes_and_digest(path)
        if actual_bytes != item["bytes"] or actual_hash != item["sha256"]:
            raise BundleError(f"bundle file hash/size mismatch: {relative}")
    selection = bundle_manifest.get("selectionSummary")
    if not isinstance(selection, dict):
        raise BundleError("bundle selection summary is missing")
    if selection.get("selectedPresentUntracked") != len(files):
        raise BundleError("bundle selection summary is stale")
    receipt_selection = {key: value for key, value in selection.items() if key != "excluded"}
    return {
        "bundle": str(bundle),
        "files": len(files),
        "bytes": sum(item["bytes"] for item in files),
        "sourceManifestSha256": expected_source_hash,
        "selectionSummary": receipt_selection,
    }


def export_bundle(source_root: Path, manifest_path: Path, output: Path) -> dict[str, Any]:
    source_root = source_root.resolve()
    manifest_path = manifest_path.resolve()
    manifest, manifest_raw = load_json(manifest_path)
    selected = selected_records(manifest)
    prepared: list[dict[str, Any]] = []
    for record in selected:
        relative = record["path"]
        source = resolve_repo_path(source_root, relative)
        reject_symlink_path(source, stop=source_root)
        if not source.is_file():
            raise BundleError(f"selected dependency is not a regular file: {relative}")
        actual_bytes, actual_hash = bytes_and_digest(source)
        if actual_bytes != record.get("bytes") or actual_hash != record.get("sha256"):
            raise BundleError(f"source changed or disagrees with dependency manifest: {relative}")
        prepared.append(source_manifest_record(record))

    if output.exists() or output.is_symlink():
        raise BundleError(f"refusing to overwrite existing bundle: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}-staging-", dir=output.parent))
    try:
        (staging / "files").mkdir()
        (staging / "source-manifest.json").write_bytes(manifest_raw)
        for record in prepared:
            relative = record["path"]
            source = resolve_repo_path(source_root, relative)
            target = staging / "files" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        bundle_manifest = {
            "schemaVersion": BUNDLE_VERSION,
            "selection": "records where tracked=false and status=present",
            "selectionSummary": selection_summary(manifest, selected),
            "sourceManifestPath": manifest_path.relative_to(source_root).as_posix() if manifest_path.is_relative_to(source_root) else str(manifest_path),
            "sourceManifestBytes": len(manifest_raw),
            "sourceManifestSha256": hashlib.sha256(manifest_raw).hexdigest(),
            "fileCount": len(prepared),
            "totalBytes": sum(int(record["bytes"]) for record in prepared),
            "files": prepared,
        }
        (staging / "bundle-manifest.json").write_text(json.dumps(bundle_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        validate_bundle(staging)
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return validate_bundle(output)


def destination_is_separate(destination: Path, source_root: Path) -> None:
    current = destination
    while True:
        if current.is_symlink():
            raise BundleError(f"restore destination path contains a symlink: {current}")
        parent = current.parent
        if parent == current:
            break
        current = parent
    destination_resolved = destination.resolve(strict=False)
    source_resolved = source_root.resolve()
    if destination_resolved == source_resolved or source_resolved in destination_resolved.parents or destination_resolved in source_resolved.parents:
        raise BundleError("restore destination must be separate from the source checkout")
    if destination.exists() and destination.is_symlink():
        raise BundleError("restore destination cannot be a symlink")


def target_state(destination: Path, relative: str, expected_bytes: int, expected_hash: str) -> str:
    target = destination / relative
    parent = target.parent
    current = parent
    while current != destination and current != current.parent:
        if current.is_symlink():
            raise BundleError(f"restore parent is a symlink: {current}")
        if current.exists() and not current.is_dir():
            raise BundleError(f"restore parent is not a directory: {current}")
        current = current.parent
    if target.is_symlink():
        raise BundleError(f"restore target is a symlink: {target}")
    if not target.exists():
        return "missing"
    if not target.is_file():
        raise BundleError(f"restore target is not a regular file: {target}")
    actual_bytes, actual_hash = bytes_and_digest(target)
    if actual_bytes != expected_bytes or actual_hash != expected_hash:
        raise BundleError(f"conflicting existing bytes at restore target: {relative}")
    return "already-present"


def restore_bundle(bundle: Path, destination: Path, source_root: Path = ROOT) -> dict[str, Any]:
    validation = validate_bundle(bundle)
    destination_is_separate(destination, source_root.resolve())
    destination = destination.resolve(strict=False)
    bundle_manifest, _ = load_json(bundle / "bundle-manifest.json")
    files = bundle_file_records(bundle_manifest)
    states = {item["path"]: target_state(destination, item["path"], item["bytes"], item["sha256"]) for item in files}
    missing = [item for item in files if states[item["path"]] == "missing"]

    if missing:
        destination.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink() or not destination.is_dir():
            raise BundleError("restore destination became unsafe")
    restored = 0
    for item in missing:
        relative = item["path"]
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            raise BundleError(f"restore target appeared during restore: {relative}")
        source = bundle / "files" / relative
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        try:
            with os.fdopen(fd, "wb") as destination_file, source.open("rb") as source_file:
                shutil.copyfileobj(source_file, destination_file, length=1024 * 1024)
                destination_file.flush()
                os.fsync(destination_file.fileno())
        except Exception:
            try:
                target.unlink()
            except OSError:
                pass
            raise
        actual_bytes, actual_hash = bytes_and_digest(target)
        if actual_bytes != item["bytes"] or actual_hash != item["sha256"]:
            target.unlink(missing_ok=True)
            raise BundleError(f"restored bytes failed verification: {relative}")
        restored += 1
    return {**validation, "destination": str(destination), "restored": restored, "alreadyPresent": len(files) - restored}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="export explicitly listed present untracked dependencies")
    export_parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    export_parser.add_argument("--output", default=str(DEFAULT_BUNDLE))

    verify_parser = subparsers.add_parser("verify", help="verify an evidence bundle without mutation")
    verify_parser.add_argument("--bundle", required=True)

    restore_parser = subparsers.add_parser("restore", help="restore missing files into a separate checkout")
    restore_parser.add_argument("--bundle", required=True)
    restore_parser.add_argument("--destination", required=True)

    args = parser.parse_args()
    try:
        if args.command == "export":
            result = export_bundle(ROOT, Path(args.manifest), Path(args.output))
        elif args.command == "verify":
            result = validate_bundle(Path(args.bundle))
        else:
            result = restore_bundle(Path(args.bundle), Path(args.destination), ROOT)
    except BundleError as error:
        print(f"evidence bundle failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
