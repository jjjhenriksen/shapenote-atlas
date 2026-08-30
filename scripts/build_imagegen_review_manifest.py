#!/usr/bin/env python3
"""Index imagegen-derived review artifacts without treating them as notation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "work" / "source-images" / "manifest.json"
BATCH_ROOT = ROOT / "work" / "transcription-images" / "working" / "imagegen-batches"
PILOT_ROOT = ROOT / "work" / "transcription-images" / "working" / "imagegen-pilot"
OUTPUT = BATCH_ROOT / "manifest.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_number(path: Path) -> str:
    suffix = "-imagegen-v1.png"
    return path.name[: -len(suffix)]


def audit_for(image: Path, song_no: str) -> Path | None:
    candidates = [
        image.with_name(image.name + ".audit.json"),
        image.with_name(f"{song_no}-imagegen-v1.audit.json"),
        image.with_name(f"{song_no}-audit.json"),
    ]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    source_manifest = load_json(SOURCE_MANIFEST)
    source_by_queue = {item.get("queueId", ""): item for item in source_manifest.get("records", [])}
    source_by_song = {f"sh2025/{item.get('songNo', '')}": item for item in source_manifest.get("records", [])}

    images: list[tuple[str, str, Path]] = []
    for batch_dir in sorted(BATCH_ROOT.glob("batch-*")):
        if batch_dir.is_dir():
            images.extend((batch_dir.name, f"sh2025/{record_number(path)}", path) for path in sorted(batch_dir.glob("*-imagegen-v1.png")))

    pilot_manifest = load_json(PILOT_ROOT / "manifest.json")
    pilot_by_path = {item.get("workingPath", ""): item for item in pilot_manifest.get("records", [])}
    for pilot_record in pilot_manifest.get("records", []):
        pilot_path = ROOT / pilot_record.get("workingPath", "")
        if pilot_path.exists():
            images.append(("pilot", pilot_record.get("queueId", ""), pilot_path))

    records = []
    for batch, queue_id, image in images:
        song_no = queue_id.removeprefix("sh2025/")
        source = source_by_queue.get(queue_id) or source_by_song.get(queue_id) or {}
        source_path = ROOT / source.get("localPath", "") if source.get("localPath") else None
        audit_path = audit_for(image, song_no)
        audit = load_json(audit_path) if audit_path else {}
        pilot_record = pilot_by_path.get(relative(image), {})
        manifest_audit = bool(pilot_record)
        source_exists = bool(source_path and source_path.exists())
        source_hash = sha256(source_path) if source_exists else ""
        source_hash_matches = bool(source.get("sha256") and source_hash == source.get("sha256"))
        status = audit.get("status") or audit.get("disposition") or audit.get("reviewStatus") or pilot_record.get("status") or "audit-missing"
        records.append(
            {
                "artifactId": f"{batch}/{song_no}",
                "batch": batch,
                "queueId": queue_id,
                "songNo": song_no,
                "title": source.get("title", ""),
                "source": {
                    "path": relative(source_path) if source_exists else source.get("localPath", ""),
                    "manifestSha256": source.get("sha256", ""),
                    "observedSha256": source_hash,
                    "exists": source_exists,
                    "immutable": source.get("immutable") is True,
                    "sha256Matches": source_hash_matches,
                },
                "working": {
                    "path": relative(image),
                    "sha256": sha256(image),
                    "tool": "built-in imagegen",
                },
                "audit": {
                    "path": relative(audit_path) if audit_path else (relative(PILOT_ROOT / "manifest.json") if manifest_audit else ""),
                    "present": audit_path is not None or manifest_audit,
                    "status": status,
                    "notes": audit.get("notes") or audit.get("reason") or audit.get("reviewNote") or pilot_record.get("promptPolicy", ""),
                },
                "safeToPromote": False,
                "policy": "Derived imagegen output is a review-only visual aid. Immutable source scans remain authoritative; no generated pixels may be used for automatic OMR or notation promotion.",
            }
        )

    records.sort(key=lambda item: (item["queueId"], item["batch"]))
    queue_counts: dict[str, int] = {}
    for item in records:
        queue_counts[item["queueId"]] = queue_counts.get(item["queueId"], 0) + 1
    duplicate_queue_ids = sorted(queue_id for queue_id, count in queue_counts.items() if count > 1)
    summary = {
        "artifacts": len(records),
        "uniqueSourceRecords": len(queue_counts),
        "duplicateQueueIds": duplicate_queue_ids,
        "audited": sum(item["audit"]["present"] for item in records),
        "auditMissing": sum(not item["audit"]["present"] for item in records),
        "rejectedForNotation": sum(item["audit"]["status"] == "rejected-for-notation" for item in records),
        "sourceHashMismatches": sum(not item["source"]["sha256Matches"] for item in records),
        "immutableSources": sum(item["source"]["immutable"] for item in records),
        "safeToPromote": 0,
    }
    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "version": "imagegen-review-manifest-v1",
        "policy": "Imagegen artifacts are derived review aids only. Original source scans remain immutable and authoritative. Every artifact is fail-closed for automatic OMR and notation promotion.",
        "summary": summary,
        "records": records,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": relative(OUTPUT), **summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
