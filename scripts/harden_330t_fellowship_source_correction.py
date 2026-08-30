#!/usr/bin/env python3
"""Repair metadata/shape omissions in the existing 330t blocked draft."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "work/omr/autonomous-transcriptions/2025/330t-fellowship-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/330t-fellowship-source-correction-v2-comparison.json"

# E minor uses the relative G-major spelling: G=fa, A=sol, B=la,
# C=fa, D=sol, E=la, F-sharp=mi.
SHAPES = {"A": "sol", "B": "la", "C": "fa", "D": "sol", "E": "la", "F": "mi", "G": "fa"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(parent: ET.Element | None, tag: str) -> list[ET.Element]:
    return [item for item in parent if local(item.tag) == tag] if parent is not None else []


def first(parent: ET.Element | None, tag: str) -> ET.Element | None:
    return next(iter(children(parent, tag)), None)


def text(parent: ET.Element | None, tag: str, default: str = "") -> str:
    item = first(parent, tag)
    return item.text.strip() if item is not None and item.text else default


def ensure(parent: ET.Element, tag: str, index: int | None = None) -> ET.Element:
    existing = first(parent, tag)
    if existing is not None:
        return existing
    item = ET.Element(tag)
    parent.insert(index, item) if index is not None else parent.append(item)
    return item


def event_signature(root: ET.Element) -> list[list[tuple[str, str, str, str, str]]]:
    result = []
    for part in children(root, "part"):
        events = []
        for measure in children(part, "measure"):
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                value = "rest" if first(note, "rest") is not None else "unknown"
                if pitch is not None:
                    value = ":".join([text(pitch, "step"), text(pitch, "alter", "0"), text(pitch, "octave")])
                events.append((measure.attrib.get("number", ""), value, text(note, "duration"), text(note, "type"), text(note, "voice")))
        result.append(events)
    return result


def main() -> int:
    with zipfile.ZipFile(DRAFT) as archive:
        xml_name = next(item for item in archive.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        root = ET.fromstring(archive.read(xml_name))
        members = [(info, archive.read(info.filename)) for info in archive.infolist()]
    before = event_signature(root)
    measures_changed = 0
    shapes_added = 0
    for part in children(root, "part"):
        for measure in children(part, "measure"):
            attributes = first(measure, "attributes")
            if attributes is None:
                attributes = ET.Element("attributes")
                measure.insert(0, attributes)
            key = ensure(attributes, "key", 1)
            fifths = ensure(key, "fifths")
            fifths.text = "1"
            mode = ensure(key, "mode")
            mode.text = "minor"
            time = ensure(attributes, "time", 2)
            ensure(time, "beats").text = "3"
            ensure(time, "beat-type").text = "4"
            measures_changed += 1
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                if pitch is None:
                    continue
                shape = SHAPES.get(text(pitch, "step").upper())
                if shape is None:
                    continue
                for old in children(note, "notehead"):
                    note.remove(old)
                notehead = ET.Element("notehead")
                notehead.text = shape
                stem_index = next((index for index, item in enumerate(note) if local(item.tag) == "stem"), len(note))
                note.insert(stem_index, notehead)
                shapes_added += 1
    after = event_signature(root)
    if before != after:
        raise RuntimeError("metadata/shape repair changed the event stream")
    xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(DRAFT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for info, data in members:
            archive.writestr(info, xml if info.filename == xml_name else data)
    draft_hash = sha256(DRAFT)
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    corrected = audit.get("correctedDraft", {})
    corrected["sha256"] = draft_hash
    corrected.setdefault("summary", {})["shapeNoteheadsAdded"] = shapes_added
    corrections = corrected.setdefault("corrections", [])
    note = "standard MusicXML E-minor and 3/4 attributes plus derived four-shape noteheads added without changing events"
    if note not in corrections:
        corrections.append(note)
    audit["correctedDraft"] = corrected
    audit["comparisonEvidence"]["blockingFindings"].append("The repair adds standard E-minor/3/4 attributes and derived shape tags only; it does not resolve the retained OMR's missing source events, lyric underlay, or complete ending semantics.")
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/330t", "measuresChanged": measures_changed, "shapeNoteheadsAdded": shapes_added, "eventStreamPreserved": True, "draftSha256": draft_hash}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
