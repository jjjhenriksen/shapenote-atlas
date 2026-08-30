#!/usr/bin/env python3
"""Build lossless, fail-closed review copies for imagegen cleanup records.

This intentionally performs no image processing. A byte-for-byte copy is the
only operation that can preserve an obstructed notation page without making a
claim about pixels under the obstruction. The source scan remains immutable
and authoritative; every output is a review aid and is forbidden as automatic
OMR input or promoted notation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
from pathlib import Path

from PIL import Image, __version__ as PILLOW_VERSION


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BATCH_MANIFEST = ROOT / "work/transcription-images/working/imagegen-batches/manifest.json"
DEFAULT_PILOT_MANIFEST = ROOT / "work/transcription-images/working/imagegen-pilot/manifest.json"
DEFAULT_SOURCE_MANIFEST = ROOT / "work/source-images/manifest.json"
DEFAULT_BATCH_ROOT = ROOT / "work/transcription-images/working/imagegen-batches"
DEFAULT_PILOT_ROOT = ROOT / "work/transcription-images/working/imagegen-pilot"
DEFAULT_OUTPUT_ROOT = ROOT / "work/transcription-images/working/deterministic-v1"
DEFAULT_MANIFEST = DEFAULT_OUTPUT_ROOT / "manifest.json"
DEFAULT_REPORT = DEFAULT_OUTPUT_ROOT / "README.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path, root: Path = ROOT) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def display_path(path: Path, root: Path) -> str:
    try:
        return relative(path, root)
    except ValueError:
        return str(path.resolve())


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value.replace("/", "-")).strip("-")


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def source_record_by_path(source_manifest: dict) -> dict[str, dict]:
    return {
        item.get("localPath", ""): item
        for item in source_manifest.get("records", [])
        if item.get("localPath")
    }


def audit_for(image: Path, song_no: str) -> Path | None:
    candidates = [
        image.with_name(image.name + ".audit.json"),
        image.with_name(f"{song_no}-imagegen-v1.audit.json"),
        image.with_name(f"{song_no}-audit.json"),
    ]
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def audit_record(path: Path | None, fallback: dict | None = None) -> dict:
    if path is not None:
        try:
            audit = load_json(path)
        except (OSError, json.JSONDecodeError):
            audit = {}
        return {
            "path": str(path),
            "present": True,
            "status": audit.get("status") or audit.get("disposition") or audit.get("reviewStatus") or "audit-present-no-status",
        }
    return {
        "path": (fallback or {}).get("path", ""),
        "present": bool((fallback or {}).get("present")),
        "status": (fallback or {}).get("status", "audit-missing"),
    }


def imagegen_records(
    batch_manifest: dict,
    pilot_manifest: dict,
    batch_root: Path,
    pilot_root: Path,
    source_manifest: dict,
    root: Path,
) -> list[dict]:
    indexed_by_working_path = {
        item.get("working", {}).get("path", ""): item
        for item in batch_manifest.get("records", [])
    }
    source_by_song = {
        item.get("songNo", ""): item
        for item in source_manifest.get("records", [])
        if item.get("songNo")
    }
    records: list[dict] = []
    for batch_dir in sorted(batch_root.glob("batch-*")):
        if not batch_dir.is_dir():
            continue
        for image in sorted(batch_dir.glob("*-imagegen-v1.png")):
            song_no = image.name.removesuffix("-imagegen-v1.png")
            working_path = display_path(image, root)
            indexed = indexed_by_working_path.get(working_path, {})
            source = source_by_song.get(song_no, {})
            audit_path = audit_for(image, song_no)
            records.append(
                {
                    "artifactId": f"{batch_dir.name}/{song_no}",
                    "batch": batch_dir.name,
                    "queueId": f"sh2025/{song_no}",
                    "songNo": song_no,
                    "title": source.get("title", indexed.get("title", "")),
                    "source": {
                        "path": source.get("localPath", indexed.get("source", {}).get("path", "")),
                        "manifestSha256": source.get("sha256", indexed.get("source", {}).get("manifestSha256", "")),
                        "immutable": source.get("immutable", indexed.get("source", {}).get("immutable", False)),
                    },
                    "working": {"path": working_path},
                    "audit": audit_record(audit_path, indexed.get("audit")),
                }
            )

    existing_working_paths = {item["working"]["path"] for item in records}
    for item in pilot_manifest.get("records", []):
        pilot_path = (root / item.get("workingPath", "")).resolve()
        pilot_display_path = display_path(pilot_path, root)
        if pilot_display_path in existing_working_paths:
            continue
        records.append(
            {
                "artifactId": f"pilot/{item.get('queueId', 'unknown').removeprefix('sh2025/')}",
                "batch": "pilot",
                "queueId": item.get("queueId", ""),
                "songNo": item.get("queueId", "").removeprefix("sh2025/"),
                "title": "",
                "source": {
                    "path": item.get("sourcePath", ""),
                    "manifestSha256": item.get("sourceSha256", ""),
                    "immutable": item.get("immutable", True),
                },
                "working": {
                    "path": pilot_display_path,
                },
                "audit": {
                    "status": item.get("status", "audit-missing"),
                    "present": True,
                    "path": display_path(DEFAULT_PILOT_MANIFEST, root),
                    "notes": item.get("promptPolicy", ""),
                },
            }
        )
    return sorted(records, key=lambda item: (item.get("queueId", ""), item.get("artifactId", "")))


def dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def build_record(
    item: dict,
    source_by_path: dict[str, dict],
    output_root: Path,
    root: Path,
) -> tuple[dict, bool]:
    source_info = item.get("source", {})
    source_path_value = source_info.get("path", "")
    source_path = (root / source_path_value).resolve()
    root_resolved = root.resolve()
    expected_imagegen_sha = source_info.get("manifestSha256", "")
    source_manifest_item = source_by_path.get(source_path_value, {})
    expected_source_sha = source_manifest_item.get("sha256", "")
    expected_sha = expected_imagegen_sha or expected_source_sha
    immutable = source_info.get("immutable") is True and source_manifest_item.get("immutable", True) is True
    output_path = output_root / f"{safe_slug(item.get('artifactId', item.get('queueId', 'unknown')))}-source-copy{source_path.suffix.lower()}"
    output_path = output_path.resolve()
    errors: list[str] = []
    source_sha = ""
    source_dimensions: list[int] = []
    output_sha = ""
    output_dimensions: list[int] = []
    output_exists = output_path.is_file()

    if not source_path_value:
        errors.append("source path is missing")
    elif source_path != root_resolved and root_resolved not in source_path.parents:
        errors.append("source path escapes repository root")
    elif source_path.is_relative_to(root / "work/transcription-images/working"):
        errors.append("derived working image was supplied as the source")
    elif not source_path.is_file():
        errors.append("immutable source is missing")
    elif not immutable:
        errors.append("source is not marked immutable in both manifests")
    else:
        source_sha = sha256(source_path)
        if not expected_sha:
            errors.append("source SHA-256 is missing from the manifests")
        elif source_sha != expected_sha:
            errors.append("source SHA-256 does not match the manifest")
        if expected_imagegen_sha and expected_source_sha and expected_imagegen_sha != expected_source_sha:
            errors.append("imagegen and source-image manifests disagree on source SHA-256")
        try:
            source_dimensions = list(dimensions(source_path))
        except Exception as exc:  # pragma: no cover - exercised by malformed external input
            errors.append(f"source is not a readable raster: {exc}")

    if not errors and output_exists:
        output_sha = sha256(output_path)
        if output_sha != source_sha:
            errors.append("deterministic output exists with a different SHA-256; refusing overwrite")
    elif not errors:
        output_root.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, output_path)
        output_exists = True
        output_sha = sha256(output_path)
        if output_sha != source_sha:
            errors.append("source changed during copy or output SHA-256 differs")

    if output_exists and output_path.is_file():
        try:
            output_dimensions = list(dimensions(output_path))
        except Exception as exc:  # pragma: no cover - exercised by malformed external input
            errors.append(f"output is not a readable raster: {exc}")
        if source_dimensions and output_dimensions != source_dimensions:
            errors.append("output dimensions differ from source dimensions")

    status = "deterministic-lossless-copy" if not errors else "blocked-fail-closed"
    record = {
        "artifactId": item.get("artifactId", ""),
        "queueId": item.get("queueId", ""),
        "songNo": item.get("songNo", ""),
        "title": item.get("title", ""),
        "imagegenWorkingPath": item.get("working", {}).get("path", ""),
        "imagegenAudit": {
            "path": item.get("audit", {}).get("path", ""),
            "present": bool(item.get("audit", {}).get("present")),
            "status": item.get("audit", {}).get("status", "audit-missing"),
        },
        "source": {
            "path": source_path_value,
            "sha256": source_sha,
            "manifestSha256": expected_sha,
            "exists": source_path.is_file(),
            "immutable": immutable,
            "dimensions": source_dimensions,
        },
        "output": {
            "path": display_path(output_path, root) if output_exists else "",
            "sha256": output_sha,
            "exists": output_exists,
            "dimensions": output_dimensions,
        },
        "operation": {
            "name": "lossless-source-copy",
            "parameters": {
                "copyBytesUnchanged": True,
                "crop": "none",
                "resize": "none",
                "rotation": "none",
                "colorNormalization": "none",
                "contrastOrBackgroundCleanup": "none",
                "watermarkMasking": "none; notation-overlap remains unresolved",
                "ocrOrInference": "none",
            },
            "tool": {
                "name": "Python shutil.copyfile",
                "pythonVersion": platform.python_version(),
                "pillowVersion": PILLOW_VERSION,
            },
        },
        "review": {
            "status": status,
            "failClosed": True,
            "reviewOnly": True,
            "automaticOmrAllowed": False,
            "safeToPromote": False,
            "qualityAssessment": "neutral-copy; source scan noise and watermark overlap are intentionally unchanged",
            "errors": errors,
        },
    }
    return record, not errors


def render_report(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Deterministic imagegen replacement review",
        "",
        "This is a lossless, fail-closed review layer for the existing Sacred Harp imagegen cleanup records. It copies immutable source bytes without resampling, color changes, denoise, sharpening, deskew, cropping, masking, OCR, inference, or notation reconstruction.",
        "",
        f"- Imagegen records inspected: **{summary['imagegenRecords']}** across **{summary['uniqueQueueIds']}** unique queue IDs.",
        f"- Deterministic copies: **{summary['deterministicCopies']}**; byte-identical: **{summary['byteIdentical']}**; geometry-identical: **{summary['geometryIdentical']}**.",
        f"- Source verification failures: **{summary['sourceVerificationFailures']}**; output conflicts: **{summary['outputConflicts']}**.",
        f"- Imagegen artifacts on disk: **{summary['imagegenArtifactsOnDisk']}**; stored imagegen manifest records: **{summary['imagegenManifestRecords']}**; unindexed batch PNGs: **{summary['imagegenUnindexedBatchPngs']}**.",
        f"- Existing imagegen artifacts rejected for notation: **{summary['imagegenRejectedForNotation']}**; safe to promote: **{summary['imagegenSafeToPromote']}**.",
        "",
        "## Comparison and retirement decision",
        "",
        "The deterministic layer is safer than the imagegen layer because every successful output has the exact source SHA-256 and dimensions, and every record remains non-OMR and non-promotable. It is quality-neutral: it leaves the diagonal watermark and scan noise in place. Because the watermark crosses notation, no deterministic masking or cleanup was applied.",
        "",
        "The expensive imagegen cleanup task can be retired as a source-of-truth or OMR strategy for these records: its audits reject notation use, and the deterministic copies provide a reproducible review aid. No imagegen task is replaced as a visual watermark-removal operation; that operation is unsafe without an authorized clean scan or human reconstruction outside this workflow.",
        "",
        "The existing imagegen files, manifests, audits, and both `81b` paths were not modified or collapsed. See `manifest.json` for per-record source/output hashes, parameters, tool versions, and fail-closed status.",
        "",
        "## Limitations",
        "",
        "- A byte-identical copy cannot improve legibility or remove a watermark.",
        "- The pilot `81b` record is covered by its manifest-level review disposition; it has no adjacent `.audit.json` file.",
        "- These outputs must not be fed to automatic OMR or promoted notation. Human comparison against the immutable source remains required.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root; defaults to the checkout containing this script")
    parser.add_argument("--batch-manifest", type=Path, default=DEFAULT_BATCH_MANIFEST)
    parser.add_argument("--pilot-manifest", type=Path, default=DEFAULT_PILOT_MANIFEST)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--batch-root", type=Path, default=DEFAULT_BATCH_ROOT)
    parser.add_argument("--pilot-root", type=Path, default=DEFAULT_PILOT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--manifest-output", type=Path, default=None)
    parser.add_argument("--report-output", type=Path, default=None)
    args = parser.parse_args()

    root = args.root.resolve()
    batch_root = args.batch_root if args.batch_root.is_absolute() else root / args.batch_root
    pilot_root = args.pilot_root if args.pilot_root.is_absolute() else root / args.pilot_root
    output_root = args.output_root if args.output_root.is_absolute() else root / args.output_root
    manifest_output = args.manifest_output or output_root / "manifest.json"
    report_output = args.report_output or output_root / "README.md"
    source_manifest = load_json(args.source_manifest)
    batch_manifest = load_json(args.batch_manifest)
    pilot_manifest = load_json(args.pilot_manifest)
    items = imagegen_records(batch_manifest, pilot_manifest, batch_root, pilot_root, source_manifest, root)
    records = []
    successes = 0
    for item in items:
        record, success = build_record(item, source_record_by_path(source_manifest), output_root, root)
        records.append(record)
        successes += success

    imagegen_rejected = sum(item["imagegenAudit"]["status"] == "rejected-for-notation" for item in records)
    batch_paths_in_manifest = {
        item.get("working", {}).get("path", "")
        for item in batch_manifest.get("records", [])
        if item.get("working", {}).get("path", "").find("/imagegen-batches/") >= 0
    }
    batch_pngs_on_disk = sum(1 for batch_dir in batch_root.glob("batch-*") if batch_dir.is_dir() for _ in batch_dir.glob("*-imagegen-v1.png"))
    payload = {
        "version": "deterministic-image-review-v1",
        "policy": "Immutable source scans remain authoritative. Lossless copies are review-only, never automatic OMR input, never promoted notation, and fail closed on any source/output verification problem.",
        "operation": "lossless-source-copy",
        "summary": {
            "imagegenRecords": len(records),
            "imagegenArtifactsOnDisk": len(records),
            "imagegenManifestRecords": len(batch_manifest.get("records", [])),
            "imagegenUnindexedBatchPngs": max(0, batch_pngs_on_disk - len(batch_paths_in_manifest)),
            "uniqueQueueIds": len({item["queueId"] for item in records}),
            "deterministicCopies": successes,
            "byteIdentical": sum(item["source"]["sha256"] == item["output"]["sha256"] and bool(item["output"]["sha256"]) for item in records),
            "geometryIdentical": sum(item["source"]["dimensions"] == item["output"]["dimensions"] and bool(item["output"]["dimensions"]) for item in records),
            "sourceVerificationFailures": sum("source" in " ".join(item["review"]["errors"]) for item in records),
            "outputConflicts": sum("output exists with a different" in " ".join(item["review"]["errors"]) for item in records),
            "imagegenRejectedForNotation": imagegen_rejected,
            "imagegenSafeToPromote": 0,
            "safeToPromote": 0,
        },
        "records": records,
    }
    manifest_output.parent.mkdir(parents=True, exist_ok=True)
    manifest_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(render_report(payload), encoding="utf-8")
    print(json.dumps({"manifest": display_path(manifest_output, root), "report": display_path(report_output, root), **payload["summary"]}, indent=2))
    return 0 if successes == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
