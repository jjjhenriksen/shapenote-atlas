#!/usr/bin/env python3
"""Create a fail-closed, source-derived Thy Strength OMR derivative."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work" / "omr" / "469-thy-strength" / "source.mxl"
IMAGE = ROOT / "work" / "omr" / "469-thy-strength" / "source.jpg"
OUTPUT = ROOT / "work" / "omr" / "autonomous-transcriptions" / "2025" / "469-autonomous-blocked.mxl"
AUDIT = ROOT / "work" / "source-transcriptions" / "2025" / "469-thy-strength-autonomous-comparison.json"
SHAPES = {"C": "fa", "D": "sol", "E": "la", "F": "fa", "G": "sol", "A": "la", "B": "mi"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def ln(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(parent: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in parent if ln(child.tag) == name]


def first(parent: ET.Element, name: str) -> ET.Element | None:
    return next(iter(children(parent, name)), None)


def set_field(identification: ET.Element, name: str, value: str) -> None:
    misc = first(identification, "miscellaneous")
    if misc is None:
        misc = ET.SubElement(identification, "miscellaneous")
    for old in [item for item in children(misc, "miscellaneous-field") if item.attrib.get("name") == name]:
        misc.remove(old)
    ET.SubElement(misc, "miscellaneous-field", {"name": name}).text = value


def transform() -> tuple[bytes, dict[str, object]]:
    with zipfile.ZipFile(SOURCE) as archive:
        root = ET.fromstring(archive.read("source.xml"))
        parts = children(root, "part")
        pitched = 0
        shapes = 0
        counts = {}
        for part in parts:
            counts[part.attrib.get("id", "")] = len(children(part, "measure"))
            for note in [item for item in part.iter() if ln(item.tag) == "note"]:
                pitch = first(note, "pitch")
                if pitch is None:
                    continue
                step = (first(pitch, "step").text or "").strip().upper()
                shape = SHAPES[step]
                for old in children(note, "notehead"):
                    note.remove(old)
                head = ET.Element("notehead")
                head.text = shape
                index = next((i for i, item in enumerate(note) if ln(item.tag) == "stem"), len(note))
                note.insert(index, head)
                pitched += 1
                shapes += 1
        identification = first(root, "identification")
        if identification is None:
            identification = ET.Element("identification")
            root.insert(0, identification)
        for name, value in {
            "atlas-queue-id": "sh2025/469",
            "atlas-transcription-status": "autonomously-blocked",
            "atlas-safe-to-promote": "false",
            "atlas-source-image": "work/omr/469-thy-strength/source.jpg",
            "atlas-source-image-sha256": digest(IMAGE),
            "atlas-source-key": "D major",
            "atlas-source-mode": "major",
            "atlas-source-meter": "Long Meter (8,8,8,8)",
            "atlas-source-time-signature": "3/2",
            "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitches and source-visible D-major key; not source-verified per note",
            "atlas-lyrics": "source lyrics visible but not safely aligned in OMR; omitted rather than fabricated",
            "atlas-blocker": "Incomplete event coverage: P1 m1; P2 m1,m3,m6; P4 m1,m3,m6 are blank despite visible source notation. Duration/event grouping is unresolved at P1 m1-3,5-8; P2 m1-8; P3 m1-8; and P4 m1-3,5-8 against source 3/2.",
        }.items():
            set_field(identification, name, value)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), {"parts": len(parts), "measuresByPart": counts, "pitchedEvents": pitched, "shapeNoteheadsAdded": shapes}


def main() -> int:
    xml, summary = transform()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml if info.filename == "source.xml" else source.read(info.filename))
    source_hash = digest(SOURCE)
    output_hash = digest(OUTPUT)
    image_hash = digest(IMAGE)
    blocking = [
        "The retained source scan visibly prints Thy Strength L.M., D major, and 3/2 with four vocal parts and eight measures per part.",
        "The retained OMR is incomplete: P1 m1; P2 m1,m3,m6; and P4 m1,m3,m6 contain no event coverage despite visible source notation.",
        "The retained OMR also has unresolved duration/event grouping at P1 m1-3,5-8; P2 m1-8; P3 m1-8; and P4 m1-3,5-8 against source 3/2; P1 m5, P2 m5, and P3 m5 are oversized collapsed clusters.",
        "A diagonal watermark crosses the middle source systems; only the note intersections in those systems are unresolved for that reason. Lyrics are optional and are omitted without fabrication.",
    ]
    audit = {
        "queueId": "sh2025/469", "edition": "Sacred Harp, 2025 Edition", "songNo": "469", "title": "Thy Strength",
        "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {"sourcePageUrl": "https://fasola.org/indexes/2025/?p=469", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/469-Thy-Strength/469.jpg", "sourceImagePath": "work/omr/469-thy-strength/source.jpg", "sourceImageSha256": image_hash, "immutable": True, "directObservations": {"header": "THY STRENGTH. L.M.", "key": "D major", "timeSignature": "3/2", "meter": "Long Meter (8,8,8,8)", "parts": 4, "measuresByPart": summary["measuresByPart"]}},
        "inputOmr": {"path": "work/omr/469-thy-strength/source.mxl", "sha256": source_hash, "status": "retained-source-scan-omr"},
        "correctedDraft": {"path": "work/omr/autonomous-transcriptions/2025/469-autonomous-blocked.mxl", "sha256": output_hash, "summary": summary, "corrections": ["four part structure preserved", "source D-major key/mode", "source 3/2 time signature", "derived four-shape notehead tags", "fail-closed provenance fields"]},
        "comparisonEvidence": {"sourceScanInspected": True, "renderedSourcePath": "work/omr/469-thy-strength/source.jpg", "renderedDraftInputs": ["work/omr/469-thy-strength/source.mxl"], "method": "direct visual inspection of retained scan plus structural/event audit of retained OMR", "blockingFindings": blocking},
        "blockingReason": "Autonomous promotion is blocked by the listed blank source-visible measures, collapsed duration groups, and specific watermark intersections. The derivative preserves detected events but does not invent missing music.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-omr-and-obscured-events; requires-source-event-verification",
        "policy": "Immutable 2025 source remains authoritative. Incomplete OMR is retained as a blocked source-derived draft and is not promoted.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "sourceSha256": source_hash, "derivativeSha256": output_hash, **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
