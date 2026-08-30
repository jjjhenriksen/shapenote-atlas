#!/usr/bin/env python3
"""Validate review-only shape MusicXML derivatives and their public copies."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "work" / "omr" / "review-shape-drafts" / "2025" / "manifest.json"
CORPUS = ROOT / "public" / "corpus.json"
ALLOWED_SHAPES = {"fa", "sol", "la", "mi"}
REQUIRED_FIELDS = {
    "atlas-review-status",
    "atlas-safe-to-promote",
    "atlas-source-key",
    "atlas-source-mode",
    "atlas-shape-encoding",
}


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
        xml_name = next(
            (name for name in archive.namelist() if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/")),
            None,
        )
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
    if not REQUIRED_FIELDS <= fields.keys():
        raise ValueError(f"missing provenance fields: {path}")
    if fields.get("atlas-safe-to-promote") != "false":
        raise ValueError(f"review draft is not fail-closed: {path}")
    return len(pitched), len(noteheads)


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = manifest.get("records", [])
    summary = manifest.get("summary", {})
    if summary.get("selectedStrongMatches") != len(records):
        raise SystemExit("shape review record count is stale")
    if summary.get("safeToPromote") != 0:
        raise SystemExit("shape review manifest is not fail-closed")

    corpus_text = CORPUS.read_text(encoding="utf-8")
    pitched_total = 0
    notehead_total = 0
    for record in records:
        draft = record.get("reviewDraft", {})
        local = ROOT / draft.get("path", "")
        public_path = ROOT / "public" / draft.get("publicPath", "")
        if not local.is_file() or not public_path.is_file():
            raise SystemExit(f"missing review artifact for {record.get('queueId')}")
        if sha256(local) != draft.get("sha256") or sha256(public_path) != draft.get("publicSha256"):
            raise SystemExit(f"review artifact checksum mismatch for {record.get('queueId')}")
        if sha256(local) != sha256(public_path):
            raise SystemExit(f"local/public review artifact diverged for {record.get('queueId')}")
        if draft.get("publicPath", "") in corpus_text:
            raise SystemExit(f"review artifact is referenced by authoritative corpus: {record.get('queueId')}")
        pitched, noteheads = validate_mxl(local)
        if pitched != draft.get("pitchedEventsRetained") or noteheads != draft.get("shapeNoteheadsAdded"):
            raise SystemExit(f"event counts stale for {record.get('queueId')}")
        pitched_total += pitched
        notehead_total += noteheads

    if pitched_total != summary.get("pitchedEventsRetained") or notehead_total != summary.get("shapeNoteheadsAdded"):
        raise SystemExit("shape review summary counts are stale")
    print(json.dumps({"records": len(records), "pitchedEvents": pitched_total, "shapeNoteheads": notehead_total, "safeToPromote": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
