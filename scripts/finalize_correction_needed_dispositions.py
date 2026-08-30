#!/usr/bin/env python3
"""Finalize the bounded SH25 correction-needed batch fail-closed.

This script owns only the thirteen direct comparison artifacts that were
already inspected against exact SH25 source scans. It does not touch the
public ledger, corpus, UI, source images, or MusicXML derivatives. The
shared queue/ledger worker can consume these explicit dispositions after
checking its own concurrent changes.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
COMPARISON_ROOT = ROOT / "work" / "source-transcriptions" / "2025"
OUTPUT = COMPARISON_ROOT / "correction-needed-autonomous-dispositions.json"

EXPECTED = {
    "sh2025/41": "41-official-scan-correction-comparison.json",
    "sh2025/50t": "50t-devotion-autonomous-comparison.json",
    "sh2025/55": "55-converse-autonomous-comparison.json",
    "sh2025/118": "118-official-scan-correction-comparison.json",
    "sh2025/169": "169-official-scan-correction-comparison.json",
    "sh2025/415": "415-endless-praise-autonomous-comparison.json",
    "sh2025/525": "525-official-scan-correction-comparison.json",
    "sh2025/537": "537-official-scan-correction-comparison.json",
    "sh2025/544": "544-official-scan-correction-comparison.json",
    "sh2025/545": "545-official-scan-correction-comparison.json",
    "sh2025/557": "557-official-scan-correction-comparison.json",
    "sh2025/563": "563-official-scan-correction-comparison.json",
    "sh2025/575": "575-official-scan-correction-comparison.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def score_summary(path: Path) -> dict[str, int | bool]:
    with zipfile.ZipFile(path) as archive:
        xml_name = next(
            name
            for name in archive.namelist()
            if name.endswith(".xml") and "container" not in name.lower()
        )
        root = ET.fromstring(archive.read(xml_name))
    parts = [node for node in root if local_name(node.tag) == "part"]
    pitched = sum(
        1
        for node in root.iter()
        if local_name(node.tag) == "note"
        and any(local_name(child.tag) == "pitch" for child in node)
    )
    lyrics = sum(1 for node in root.iter() if local_name(node.tag) == "lyric")
    shapes = sum(
        1
        for node in root.iter()
        if local_name(node.tag) == "notehead"
        and (node.text or "").strip().lower() in {"fa", "sol", "la", "mi"}
    )
    return {
        "parts": len(parts),
        "pitchedEvents": pitched,
        "shapeNoteheads": shapes,
        "lyricsEncoded": lyrics > 0,
    }


def main() -> int:
    records: list[dict[str, object]] = []
    errors: list[str] = []
    for queue_id, filename in EXPECTED.items():
        path = COMPARISON_ROOT / filename
        if not path.exists():
            errors.append(f"{queue_id}: missing comparison artifact {path}")
            continue
        comparison = json.loads(path.read_text(encoding="utf-8"))
        if comparison.get("queueId") != queue_id:
            errors.append(f"{queue_id}: artifact queueId mismatch")
        if comparison.get("comparisonStatus") != "verified-with-correction-needed":
            errors.append(f"{queue_id}: unexpected source comparison status")
        source = comparison.get("sourceAuthority", {})
        candidate = comparison.get("candidateWitness", {})
        corrected = comparison.get("correctedDraft", {})
        source_path = ROOT / str(source.get("sourceImagePath", ""))
        candidate_path = ROOT / str(candidate.get("candidateMusicXmlPath", ""))
        corrected_path = ROOT / str(corrected.get("path", ""))
        for label, path in (("source scan", source_path), ("candidate", candidate_path), ("corrected", corrected_path)):
            if not path.is_file():
                errors.append(f"{queue_id}: missing {label} {path}")
        if not (source_path.is_file() and candidate_path.is_file() and corrected_path.is_file()):
            continue
        if sha256(source_path) != source.get("sourceImageSha256"):
            errors.append(f"{queue_id}: source scan checksum mismatch")
        if sha256(candidate_path) != candidate.get("candidateMusicXmlSha256"):
            errors.append(f"{queue_id}: candidate checksum mismatch")
        if sha256(corrected_path) != corrected.get("sha256"):
            errors.append(f"{queue_id}: corrected derivative checksum mismatch")
        summary = score_summary(corrected_path)
        expected = corrected.get("summary", {})
        if summary["parts"] != expected.get("parts"):
            errors.append(f"{queue_id}: corrected part count mismatch")
        if summary["pitchedEvents"] != expected.get("pitchedEvents"):
            errors.append(f"{queue_id}: corrected pitched-event count mismatch")
        if summary["shapeNoteheads"] != expected.get("shapeNoteheadsAdded"):
            errors.append(f"{queue_id}: corrected shape count mismatch")
        if summary["lyricsEncoded"] is not False:
            errors.append(f"{queue_id}: lyrics unexpectedly encoded")
        blocking_reason = str(comparison.get("blockingReason", ""))
        if "lyrics" not in blocking_reason.lower() or "alignment" not in blocking_reason.lower():
            errors.append(f"{queue_id}: blocking reason does not name lyric alignment")
        records.append(
            {
                "queueId": queue_id,
                "title": comparison.get("title", ""),
                "status": "autonomously-blocked",
                "humanReviewRequired": False,
                "safeToPromote": False,
                "blockerCode": "unencoded-lyrics-alignment",
                "blockingReason": blocking_reason,
                "sourceScan": {
                    "path": str(source_path.relative_to(ROOT)),
                    "sha256": sha256(source_path),
                    "immutable": source.get("immutable") is True,
                },
                "candidateMusicXml": {
                    "path": str(candidate_path.relative_to(ROOT)),
                    "sha256": sha256(candidate_path),
                },
                "correctedDerivative": {
                    "path": str(corrected_path.relative_to(ROOT)),
                    "sha256": sha256(corrected_path),
                    "summary": summary,
                },
                "evidence": {
                    "eventStreamEqual": comparison.get("comparisonEvidence", {}).get("eventStreamEqual"),
                    "sourceScanInspected": comparison.get("comparisonEvidence", {}).get("sourceScanInspected") is True,
                    "lyricsVisibleInSource": source.get("directObservations", {}).get("lyricsVisible") is True,
                    "lyricsAlignedInStructuredSource": False,
                    "notesOrLyricsFabricated": False,
                },
            }
        )
    if len(records) != len(EXPECTED):
        errors.append(f"expected {len(EXPECTED)} records, validated {len(records)}")
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "kind": "sacred-harp-2025-correction-needed-autonomous-dispositions",
        "version": 1,
        "status": "valid" if not errors else "invalid",
        "policy": "These exact SH25 source comparisons are autonomously blocked by unencoded lyrics whose note-to-syllable alignment is not established. No human handoff, promotion, or notation fabrication is authorized.",
        "summary": {
            "records": len(records),
            "autonomouslyBlocked": sum(record["status"] == "autonomously-blocked" for record in records),
            "safeToPromote": 0,
            "humanReviewRequired": 0,
            "errors": len(errors),
        },
        "errors": errors,
        "records": sorted(records, key=lambda record: str(record["queueId"])),
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
