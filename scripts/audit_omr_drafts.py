#!/usr/bin/env python3
"""Summarize local OMR drafts without promoting them into the corpus."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OMR_ROOT = ROOT / "work" / "omr"
OUTPUT = OMR_ROOT / "draft-index.json"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(element: ET.Element, name: str) -> str:
    for child in element:
        if local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def unpack_score(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = next(node for node in container.iter() if local_name(node.tag) == "rootfile")
        return ET.fromstring(archive.read(rootfile.attrib["full-path"]))


def main() -> int:
    records = []
    seen_hashes: set[str] = set()
    for path in sorted(OMR_ROOT.glob("*/*.mxl")):
        # The canonical queue is keyed by an edition page/song number. Keep
        # alternate reconciliation artifacts in their dedicated ledgers.
        if not re.match(r"^\d+[a-z]?(?:-|$)", path.parent.name.lower()):
            continue
        # Cleaned-input runs have their own ledger and must not silently
        # replace or duplicate the canonical review queue.
        if path.parent.name.startswith("cleaned-"):
            continue
        # Ignore the early scratch run kept under work/omr/259; the canonical
        # draft is stored under its edition slug below.
        if path.parent.name.isdigit():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        root = unpack_score(path)
        parts = []
        for part in root.findall("part"):
            measures = part.findall("measure")
            notes = sum(len(measure.findall("note")) for measure in measures)
            empty_measures = sum(not measure.findall("note") for measure in measures)
            parts.append(
                {
                    "id": part.attrib.get("id", ""),
                    "measures": len(measures),
                    "notes": notes,
                    "emptyMeasures": empty_measures,
                }
            )
        records.append(
            {
                "record": path.parent.name,
                "artifact": str(path.relative_to(ROOT)),
                "sha256": digest,
                "status": "omr-draft",
                "reviewRequired": True,
                "keyFifths": child_text(next(iter(root.findall(".//key")), ET.Element("key")), "fifths"),
                "timeSignature": "/".join(
                    filter(
                        None,
                        [
                            child_text(next(iter(root.findall(".//time")), ET.Element("time")), "beats"),
                            child_text(next(iter(root.findall(".//time")), ET.Element("time")), "beat-type"),
                        ],
                    )
                ),
                "parts": parts,
                "warnings": [
                    "OMR output must be compared against the source scan before admission.",
                    "Shape-note noteheads are not preserved by this standard MusicXML export.",
                ],
            }
        )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"status": "drafts-only", "records": records}, indent=2) + "\n", encoding="utf-8")
    print(f"Audited {len(records)} local OMR drafts; none were promoted to the corpus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
