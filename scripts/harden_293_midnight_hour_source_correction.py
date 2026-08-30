#!/usr/bin/env python3
"""Add source-supported standard MusicXML metadata to the existing 293 draft."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "work/omr/autonomous-transcriptions/2025/293-autonomous-blocked.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/293-midnight-hour-autonomous-comparison.json"


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


def event_signature(root: ET.Element) -> list[list[tuple[str, str, str, str, str]]]:
    result = []
    for part in children(root, "part"):
        events = []
        for measure in children(part, "measure"):
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                value = "rest" if first(note, "rest") is not None else "unknown"
                if pitch is not None:
                    value = ":".join([first(pitch, "step").text, (first(pitch, "alter").text if first(pitch, "alter") is not None else "0"), first(pitch, "octave").text])
                events.append((measure.attrib.get("number", ""), value, first(note, "duration").text if first(note, "duration") is not None else "", first(note, "type").text if first(note, "type") is not None else "", first(note, "voice").text if first(note, "voice") is not None else ""))
        result.append(events)
    return result


def ensure_child(parent: ET.Element, tag: str, index: int | None = None) -> ET.Element:
    existing = first(parent, tag)
    if existing is not None:
        return existing
    child = ET.Element(tag)
    if index is None:
        parent.append(child)
    else:
        parent.insert(index, child)
    return child


def main() -> int:
    with zipfile.ZipFile(DRAFT) as archive:
        xml_name = next(item for item in archive.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        before = ET.fromstring(archive.read(xml_name))
        original_members = [(info, archive.read(info.filename)) for info in archive.infolist()]
    before_events = event_signature(before)
    measures_changed = 0
    for part in children(before, "part"):
        for measure in children(part, "measure"):
            attributes = first(measure, "attributes")
            if attributes is None:
                attributes = ET.Element("attributes")
                measure.insert(0, attributes)
            key = ensure_child(attributes, "key", 1)
            fifths = ensure_child(key, "fifths")
            fifths.text = "1"
            mode = ensure_child(key, "mode")
            mode.text = "minor"
            time = ensure_child(attributes, "time", 2)
            beats = ensure_child(time, "beats")
            beats.text = "4"
            beat_type = ensure_child(time, "beat-type")
            beat_type.text = "4"
            measures_changed += 1
    after_events = event_signature(before)
    if before_events != after_events:
        raise RuntimeError("standard metadata repair changed the event stream")
    xml = ET.tostring(before, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(DRAFT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for info, data in original_members:
            archive.writestr(info, xml if info.filename == xml_name else data)
    draft_hash = sha256(DRAFT)
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    corrected = audit.get("correctedDraft", {})
    corrected["sha256"] = draft_hash
    corrections = corrected.setdefault("corrections", [])
    note = "standard MusicXML key/mode and 4/4 attributes added from source-visible E-minor header without changing events"
    if note not in corrections:
        corrections.append(note)
    audit["correctedDraft"] = corrected
    audit["comparisonEvidence"]["blockingFindings"].append("The repair adds only standard E-minor and 4/4 MusicXML attributes; it does not resolve the retained OMR's missing events, duration failures, lyrics, or watermark-obscured notation.")
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/293", "measuresChanged": measures_changed, "eventStreamPreserved": True, "draftSha256": draft_hash, "audit": str(AUDIT.relative_to(ROOT))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
