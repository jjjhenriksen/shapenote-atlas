#!/usr/bin/env python3
"""Preserve a source-derived Humility draft while recording precise OMR gaps."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work" / "omr" / "347b-humility" / "source.mxl"
SOURCE_IMAGE = ROOT / "work" / "omr" / "347b-humility" / "source.jpg"
OUTPUT = ROOT / "work" / "omr" / "autonomous-transcriptions" / "2025" / "347b-autonomous-blocked.mxl"
AUDIT = ROOT / "work" / "source-transcriptions" / "2025" / "347b-humility-autonomous-comparison.json"

SHAPES = {"C": "fa", "D": "sol", "E": "la", "F": "fa", "G": "sol", "A": "la", "B": "mi"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def direct(parent: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in parent if local_name(child.tag) == name]


def first(parent: ET.Element, name: str) -> ET.Element | None:
    return next(iter(direct(parent, name)), None)


def field(identification: ET.Element, name: str, value: str) -> None:
    misc = first(identification, "miscellaneous")
    if misc is None:
        misc = ET.SubElement(identification, "miscellaneous")
    for old in [child for child in direct(misc, "miscellaneous-field") if child.attrib.get("name") == name]:
        misc.remove(old)
    ET.SubElement(misc, "miscellaneous-field", {"name": name}).text = value


def build() -> tuple[bytes, dict[str, object]]:
    with zipfile.ZipFile(SOURCE) as archive:
        xml_name = "source.xml"
        root = ET.fromstring(archive.read(xml_name))
        parts = [child for child in root if local_name(child.tag) == "part"]
        pitched = 0
        shapes = 0
        counts: dict[str, int] = {}
        for part in parts:
            counts[part.attrib.get("id", "")] = len(direct(part, "measure"))
            for measure in direct(part, "measure"):
                attributes = first(measure, "attributes")
                if attributes is None:
                    attributes = ET.Element("attributes")
                    measure.insert(0, attributes)
                key = first(attributes, "key")
                if key is None:
                    key = ET.Element("key")
                    attributes.insert(1, key)
                for old in direct(key, "fifths") + direct(key, "mode"):
                    key.remove(old)
                ET.SubElement(key, "fifths").text = "-1"
                ET.SubElement(key, "mode").text = "major"
            for note in [child for child in part.iter() if local_name(child.tag) == "note"]:
                pitch = first(note, "pitch")
                if pitch is None:
                    continue
                step = (first(pitch, "step").text or "").strip().upper()
                if step not in SHAPES:
                    raise ValueError(step)
                for old in direct(note, "notehead"):
                    note.remove(old)
                notehead = ET.Element("notehead")
                notehead.text = SHAPES[step]
                index = next((i for i, child in enumerate(note) if local_name(child.tag) == "stem"), len(note))
                note.insert(index, notehead)
                pitched += 1
                shapes += 1
        identification = first(root, "identification")
        if identification is None:
            identification = ET.Element("identification")
            root.insert(0, identification)
        values = {
            "atlas-queue-id": "sh2025/347b",
            "atlas-transcription-status": "autonomously-blocked",
            "atlas-safe-to-promote": "false",
            "atlas-source-image": "work/omr/347b-humility/source.jpg",
            "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
            "atlas-source-key": "B-flat major",
            "atlas-source-mode": "major",
            "atlas-source-meter": "Common Meter (8,6,8,6)",
            "atlas-source-time-signature": "3/2",
            "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitches and source-visible B-flat major key; not source-verified per note",
            "atlas-lyrics": "source lyrics visible but not safely aligned in OMR; omitted rather than fabricated",
            "atlas-blocker": "Incomplete event coverage: P1 m4,m6; P2 m1,m5,m6; P3 m4; P4 m0,m1,m5,m6 are blank in the retained OMR despite visible source notation. Duration/event grouping is also unresolved at P1 m0-3,5,7; P2 m0,m2-4,m7; P3 m0-3,5-7; and P4 m2-4,7 against source 3/2.",
        }
        for name, value in values.items():
            field(identification, name, value)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), {
            "parts": len(parts),
            "measuresByPart": counts,
            "pitchedEvents": pitched,
            "shapeNoteheadsAdded": shapes,
        }


def main() -> int:
    xml, summary = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml if info.filename == "source.xml" else source.read(info.filename))
    source_hash = sha256(SOURCE)
    output_hash = sha256(OUTPUT)
    image_hash = sha256(SOURCE_IMAGE)
    blocking = [
        "The retained source scan visibly prints Humility C.M., B-flat major, and 3/2 with four vocal parts and eight measures per part.",
        "The retained OMR is incomplete: P1 m4,m6; P2 m1,m5,m6; P3 m4; and P4 m0,m1,m5,m6 contain no event coverage despite visible source notation.",
        "The retained OMR also has unresolved duration/event grouping at P1 m0-3,5,7; P2 m0,m2-4,m7; P3 m0-3,5-7; and P4 m2-4,7 against the source-visible 3/2 meter.",
        "A diagonal watermark crosses the middle source systems; only the note intersections in those systems are unresolved for that reason. Lyrics are optional and are omitted without fabrication.",
    ]
    audit = {
        "queueId": "sh2025/347b",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "347b",
        "title": "Humility",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=347b",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/347b-Humility/347b.jpg",
            "sourceImagePath": "work/omr/347b-humility/source.jpg",
            "sourceImageSha256": image_hash,
            "immutable": True,
            "directObservations": {"header": "HUMILITY. C.M.", "key": "B-flat major", "timeSignature": "3/2", "meter": "Common Meter (8,6,8,6)", "parts": 4, "measuresByPart": summary["measuresByPart"]},
        },
        "inputOmr": {"path": "work/omr/347b-humility/source.mxl", "sha256": source_hash, "status": "retained-source-scan-omr"},
        "correctedDraft": {"path": "work/omr/autonomous-transcriptions/2025/347b-autonomous-blocked.mxl", "sha256": output_hash, "summary": summary, "corrections": ["four part structure preserved", "source B-flat-major key/mode", "source 3/2 time signature", "derived four-shape notehead tags", "fail-closed provenance fields"]},
        "comparisonEvidence": {"sourceScanInspected": True, "renderedSourcePath": "work/omr/347b-humility/source.jpg", "renderedDraftInputs": ["work/omr/347b-humility/source.mxl"], "method": "direct visual inspection of retained scan plus structural/event audit of retained OMR", "blockingFindings": blocking},
        "blockingReason": "Autonomous promotion is blocked by the listed blank source-visible measures, unresolved duration/event groups, and specific watermark intersections. The derivative preserves the usable detected events but does not invent missing music.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-omr-and-obscured-events; requires-clean-source-event-verification",
        "policy": "Immutable 2025 source remains authoritative. Incomplete OMR is retained as a blocked source-derived draft and is not promoted.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "sourceSha256": source_hash, "derivativeSha256": output_hash, **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
