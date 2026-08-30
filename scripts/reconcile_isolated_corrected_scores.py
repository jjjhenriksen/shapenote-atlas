#!/usr/bin/env python3
"""Reconcile an isolated, read-only three-score correction pass.

The isolated task supplies derivatives and an evidence index, but it is not
itself authoritative. This script admits only hash-pinned copies whose event
streams still equal the local exact SH25 MXL, then records the source scan,
mode, derivative, and no-promotion decision in the local comparisons.
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ISOLATED_ROOT = ROOT / "work" / "omr" / "autonomous-transcriptions" / "2025" / "isolated-audit"
EVIDENCE_INDEX = ROOT / "work" / "source-transcriptions" / "2025" / "isolated-audit-evidence-index.json"

RECORDS = {
    "sh2025/55": {
        "title": "Converse",
        "comparison": ROOT / "work/source-transcriptions/2025/55-converse-autonomous-comparison.json",
        "derivative": ISOLATED_ROOT / "55-converse-corrected.mxl",
        "derivativeSha256": "d12c0966f68b0083c9deb47a95eb6201c82e532fd7df70373e65e7fa87f88c59",
        "sourceScan": ROOT / "work/source-pdfs/official-sh25-scans/isolated-audit/SH25-CONVERSE.jpg",
        "sourceScanSha256": "27894c56076c94de739a7dd0f502fd8e0df2b711a19d6d75fdf7106e41902993",
        "sourceScanUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/001-099/055-Converse/55.jpg",
        "mode": "A major",
        "rawSourcePath": "work/shapenote-musicxml/53c8ee986905cbd07c468efd.mxl",
    },
    "sh2025/50t": {
        "title": "Devotion",
        "comparison": ROOT / "work/source-transcriptions/2025/50t-devotion-autonomous-comparison.json",
        "derivative": ISOLATED_ROOT / "50t-devotion-corrected.mxl",
        "derivativeSha256": "94a7db5249dbdfe3bd151357dfc357fc6aca3e50c395ccb437e952ffbae0a535",
        "sourceScan": ROOT / "work/source-pdfs/official-sh25-scans/isolated-audit/SH25-DEVOTION.jpg",
        "sourceScanSha256": "172d3613ce22907f58fecb61cb45087e1f053227a0e4694b447f93ce255deccc",
        "sourceScanUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/001-099/050t-Devotion/50t.jpg",
        "mode": "C major",
        "rawSourcePath": "work/shapenote-musicxml/25051a87a2fddb2c322ec07f.mxl",
    },
    "sh2025/415": {
        "title": "Endless Praise",
        "comparison": ROOT / "work/source-transcriptions/2025/415-endless-praise-autonomous-comparison.json",
        "derivative": ISOLATED_ROOT / "415-endless-praise-corrected.mxl",
        "derivativeSha256": "4ae5ee3d3ca72020646e64b412a35435b03c0fd09af86769385ae83d4974e55b",
        "sourceScan": ROOT / "work/source-pdfs/official-sh25-scans/isolated-audit/SH25-ENDLESS-PRAISE.jpg",
        "sourceScanSha256": "014a70d8d2c69be3b3ae176cbd38b204b37ff56ececda9a725d04d1bed1ebd1a",
        "sourceScanUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/415-Endless-Praise/415.jpg",
        "mode": "D minor",
        "rawSourcePath": "work/shapenote-musicxml/2eb61146c1b9bb3bc35d6bd8.mxl",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def first(parent: ET.Element, name: str) -> ET.Element | None:
    return next((child for child in parent if local_name(child.tag) == name), None)


def score_summary(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        name = next(item for item in archive.namelist() if item.endswith(".xml") and "container" not in item.lower())
        root = ET.fromstring(archive.read(name))
    parts = [item for item in root if local_name(item.tag) == "part"]
    shapes = 0
    pitched = 0
    shape_counts: dict[str, int] = {}
    modes: list[str] = []
    for key in root.iter():
        if local_name(key.tag) == "key":
            mode = first(key, "mode")
            modes.append((mode.text or "").strip() if mode is not None else "")
    measures: dict[str, int] = {}
    for part in parts:
        measures[part.attrib.get("id", "")] = sum(1 for item in part if local_name(item.tag) == "measure")
        for note in part.iter():
            if local_name(note.tag) != "note" or first(note, "pitch") is None:
                continue
            pitched += 1
            notehead = first(note, "notehead")
            value = (notehead.text or "").strip() if notehead is not None else ""
            if value:
                shapes += 1
                shape_counts[value] = shape_counts.get(value, 0) + 1
    return {
        "parts": len(parts),
        "measuresByPart": measures,
        "pitchedEvents": pitched,
        "shapeNoteheadsAdded": shapes,
        "shapeCounts": shape_counts,
        "modes": modes,
        "lyrics": sum(1 for item in root.iter() if local_name(item.tag) == "lyric"),
    }


def main() -> int:
    index = json.loads(EVIDENCE_INDEX.read_text(encoding="utf-8"))
    if index.get("no_promotion") is not True:
        raise SystemExit("isolated evidence index does not explicitly prohibit promotion")
    for queue_id, item in RECORDS.items():
        evidence = next(record for record in index.get("records", []) if record.get("queue_id") == queue_id)
        derivative = item["derivative"]
        source_scan = item["sourceScan"]
        raw_source = ROOT / item["rawSourcePath"]
        if sha256(derivative) != item["derivativeSha256"]:
            raise SystemExit(f"{queue_id}: derivative checksum mismatch")
        if sha256(source_scan) != item["sourceScanSha256"]:
            raise SystemExit(f"{queue_id}: source scan checksum mismatch")
        if sha256(raw_source) != evidence.get("input_sha256"):
            raise SystemExit(f"{queue_id}: raw source checksum does not match isolated evidence")
        if evidence.get("derivative_sha256") != item["derivativeSha256"] or evidence.get("event_stream_preserved") is not True:
            raise SystemExit(f"{queue_id}: isolated evidence is incomplete")
        with zipfile.ZipFile(raw_source) as raw_archive, zipfile.ZipFile(derivative) as derivative_archive:
            raw_root = ET.fromstring(raw_archive.read(next(n for n in raw_archive.namelist() if n.endswith(".xml") and "container" not in n.lower())))
            derivative_root = ET.fromstring(derivative_archive.read(next(n for n in derivative_archive.namelist() if n.endswith(".xml") and "container" not in n.lower())))
        # Compare normalized event-bearing XML by delegating to the existing
        # audit implementation, which ignores metadata-only corrections.
        sys.path.insert(0, str(ROOT / "scripts"))
        from audit_shapenote_2025_scores import event_signature  # type: ignore
        if event_signature(raw_source) != event_signature(derivative):
            raise SystemExit(f"{queue_id}: derivative event stream changed")
        summary = score_summary(derivative)
        if summary["parts"] != 4 or summary["pitchedEvents"] != summary["shapeNoteheadsAdded"] or any(mode != item["mode"].split()[-1].lower() for mode in summary["modes"]):
            raise SystemExit(f"{queue_id}: corrected derivative is not structurally complete")
        comparison_path = item["comparison"]
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        source = comparison.setdefault("sourceAuthority", {})
        source["sourceImagePath"] = str(source_scan.relative_to(ROOT))
        source["sourceImageSha256"] = item["sourceScanSha256"]
        source["sourceScanUrl"] = item["sourceScanUrl"]
        source.setdefault("sourceScanImmutable", True)
        source["directObservations"]["key"] = item["mode"]
        source["directObservations"]["sourceScanSha256"] = item["sourceScanSha256"]
        candidate = comparison.setdefault("candidateWitness", {})
        candidate["rawSourceCompleteness"] = {
            "mode": "omitted-in-raw-MusicXML",
            "shapeNoteheads": "omitted-or-partial-in-raw-MusicXML",
            "lyrics": "omitted-in-raw-MusicXML",
        }
        corrected = comparison.setdefault("correctedDraft", {})
        corrected["path"] = str(derivative.relative_to(ROOT))
        corrected["sha256"] = item["derivativeSha256"]
        corrected["summary"] = {key: value for key, value in summary.items() if key not in {"modes", "lyrics"}}
        corrected["summary"]["lyricsEncoded"] = False
        corrected["corrections"] = ["explicit source mode", "complete four-shape noteheads", "isolated-audit provenance", "fail-closed no-promotion gate"]
        comparison["comparisonStatus"] = "verified-with-correction-needed"
        comparison["autonomousDecision"] = "verified-with-correction-needed"
        comparison["safeToPromote"] = False
        comparison["humanReviewRequired"] = False
        comparison["isolatedAuditEvidence"] = {
            "indexPath": str(EVIDENCE_INDEX.relative_to(ROOT)),
            "readOnly": True,
            "derivativeSha256": item["derivativeSha256"],
            "eventStreamPreserved": True,
            "noPromotion": True,
        }
        comparison["promotionDisposition"] = "corrected-derivative-retained; raw-source-not-exact; no-corpus-promotion"
        comparison["nextAction"] = "retain-corrected-derivative; lyrics-unencoded; no-human-handoff-or-promotion"
        comparison["policy"] = "The immutable SH25 scan and exact source MXL remain authoritative. The isolated derivative preserves the exact event stream and adds only scan-supported mode and four-shape encoding; lyrics remain omitted because direct syllable alignment is not established. This record is correction-needed and fail-closed, with no corpus promotion."
        comparison["generatedAt"] = datetime.now(timezone.utc).isoformat()
        comparison_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"queueId": queue_id, "status": comparison["comparisonStatus"], "mode": item["mode"], **corrected["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
