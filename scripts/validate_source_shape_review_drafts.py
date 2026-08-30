#!/usr/bin/env python3
"""Validate source-scan shape review derivatives and their public copies."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from build_shape_review_drafts import local_path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "work" / "omr" / "source-shape-review-drafts" / "2025" / "manifest.json"
CORPUS = ROOT / "public" / "corpus.json"
ALLOWED_SHAPES = {"fa", "sol", "la", "mi"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def validate_mxl(path: Path) -> tuple[int, int]:
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"corrupt archive: {path}")
        xml_name = next((name for name in archive.namelist() if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/")), None)
        if xml_name is None:
            raise ValueError(f"no score XML member: {path}")
        root = ET.fromstring(archive.read(xml_name))
    if clean_tag(root.tag) != "score-partwise":
        raise ValueError(f"not score-partwise: {path}")
    notes = [element for element in root.iter() if clean_tag(element.tag) == "note"]
    pitched = [note for note in notes if any(clean_tag(child.tag) == "pitch" for child in note)]
    noteheads = [child for note in notes for child in note if clean_tag(child.tag) == "notehead"]
    if len(noteheads) != len(pitched):
        raise ValueError(f"pitched notes without direct noteheads: {path} ({len(pitched)} vs {len(noteheads)})")
    if any((notehead.text or "").strip() not in ALLOWED_SHAPES for notehead in noteheads):
        raise ValueError(f"unsupported four-shape value: {path}")
    fields = {
        child.attrib.get("name"): child.text
        for child in root.iter()
        if clean_tag(child.tag) == "miscellaneous-field"
    }
    required = {"atlas-review-status", "atlas-safe-to-promote", "atlas-source-key", "atlas-source-mode", "atlas-source-image-sha256", "atlas-source-omr-sha256"}
    if not required <= fields.keys():
        raise ValueError(f"missing provenance fields: {path}")
    if fields.get("atlas-safe-to-promote") != "false":
        raise ValueError(f"review draft is not fail-closed: {path}")
    return len(pitched), len(noteheads)


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = manifest.get("records", [])
    summary = manifest.get("summary", {})
    if summary.get("sourceRecords") != len(records) or summary.get("expectedSourceRecords") != 90:
        raise SystemExit("source shape review record count is stale")
    if summary.get("safeToPromote") != 0 or manifest.get("errors"):
        raise SystemExit("source shape review manifest is not clean and fail-closed")
    corpus_text = CORPUS.read_text(encoding="utf-8")
    queue_ids = set()
    pitched_total = 0
    notehead_total = 0
    for record in records:
        queue_id = record.get("queueId", "")
        if queue_id in queue_ids:
            raise SystemExit(f"duplicate source record: {queue_id}")
        queue_ids.add(queue_id)
        source = record.get("sourceAuthority", {})
        image = local_path(source.get("sourceImagePath", ""))
        if not image.is_file() or sha256(image) != source.get("sourceImageSha256"):
            raise SystemExit(f"source image checksum mismatch for {queue_id}")
        source_omr = local_path(record.get("sourceScanOmr", {}).get("path", ""))
        if not source_omr.is_file() or sha256(source_omr) != record.get("sourceScanOmr", {}).get("sha256"):
            raise SystemExit(f"source OMR checksum mismatch for {queue_id}")
        draft = record.get("reviewDraft", {})
        local = local_path(draft.get("path", ""))
        public = ROOT / "public" / draft.get("publicPath", "")
        if not local.is_file() or not public.is_file():
            raise SystemExit(f"missing review artifact for {queue_id}")
        if sha256(local) != draft.get("sha256") or sha256(public) != draft.get("publicSha256") or sha256(local) != sha256(public):
            raise SystemExit(f"review artifact checksum mismatch for {queue_id}")
        if draft.get("publicPath", "") in corpus_text:
            raise SystemExit(f"source review artifact is referenced by authoritative corpus: {queue_id}")
        pitched, noteheads = validate_mxl(local)
        if pitched != draft.get("pitchedEventsRetained") or noteheads != draft.get("shapeNoteheadsAdded"):
            raise SystemExit(f"event counts stale for {queue_id}")
        pitched_total += pitched
        notehead_total += noteheads
    if pitched_total != summary.get("pitchedEventsRetained") or notehead_total != summary.get("shapeNoteheadsAdded"):
        raise SystemExit("source shape review summary counts are stale")
    print(json.dumps({"records": len(records), "pitchedEvents": pitched_total, "shapeNoteheads": notehead_total, "safeToPromote": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
