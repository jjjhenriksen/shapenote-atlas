#!/usr/bin/env python3
"""Create a fail-closed, source-derived Troubles Over OMR derivative."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work" / "omr" / "80t-troubles-over" / "source.mxl"
IMAGE = ROOT / "work" / "omr" / "80t-troubles-over" / "source.jpg"
OUTPUT = ROOT / "work" / "omr" / "autonomous-transcriptions" / "2025" / "80t-autonomous-blocked.mxl"
AUDIT = ROOT / "work" / "source-transcriptions" / "2025" / "80t-troubles-over-autonomous-comparison.json"
STEPS = ["C", "D", "E", "F", "G", "A", "B"]
SHAPES = ["fa", "sol", "la", "fa", "sol", "la", "mi"]


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
                degree = (STEPS.index(step) - STEPS.index("B")) % 7
                for old in children(note, "notehead"):
                    note.remove(old)
                head = ET.Element("notehead")
                head.text = SHAPES[degree]
                index = next((i for i, item in enumerate(note) if ln(item.tag) == "stem"), len(note))
                note.insert(index, head)
                pitched += 1
                shapes += 1
        identification = first(root, "identification")
        if identification is None:
            identification = ET.Element("identification")
            root.insert(0, identification)
        for name, value in {
            "atlas-queue-id": "sh2025/80t",
            "atlas-transcription-status": "autonomously-blocked",
            "atlas-safe-to-promote": "false",
            "atlas-source-image": "work/omr/80t-troubles-over/source.jpg",
            "atlas-source-image-sha256": digest(IMAGE),
            "atlas-source-key": "G minor",
            "atlas-source-mode": "minor",
            "atlas-source-meter": "Long Meter Half (8,8)",
            "atlas-source-time-signature": "2/4",
            "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitches and source-visible G-minor key; not source-verified per note",
            "atlas-lyrics": "source lyrics visible but not safely aligned in OMR; omitted rather than fabricated",
            "atlas-blocker": "Incomplete event coverage: P1 m2; P2 m3; P3 m2,m3,m8,m10,m12,m13; and P4 m2,m8 are blank despite visible source notation. Duration/event grouping is unresolved at P1 m1-13; P2 m1-13; P3 m1-13; and P4 m1-13 against source 2/4, including oversized clusters at P1 m7-8, P2 m5-8, and P3 m6-7.",
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
        "The retained source scan visibly prints Troubles Over L.M.H., G minor, and 2/4 with four vocal parts and thirteen measures per part.",
        "The retained OMR is incomplete: P1 m2; P2 m3; P3 m2,m3,m8,m10,m12,m13; and P4 m2,m8 contain no event coverage despite visible source notation.",
        "The retained OMR also has unresolved duration/event grouping at P1 m1-13, P2 m1-13, P3 m1-13, and P4 m1-13 against source 2/4, including oversized clusters at P1 m7-8, P2 m5-8, and P3 m6-7.",
        "A diagonal watermark crosses the middle source systems; only the note intersections in those systems are unresolved for that reason. Lyrics are optional and are omitted without fabrication.",
    ]
    audit = {
        "queueId": "sh2025/80t", "edition": "Sacred Harp, 2025 Edition", "songNo": "80t", "title": "Troubles Over",
        "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {"sourcePageUrl": "https://fasola.org/indexes/2025/?p=80t", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/001-099/080t-Troubles-Over/80t.jpg", "sourceImagePath": "work/omr/80t-troubles-over/source.jpg", "sourceImageSha256": image_hash, "immutable": True, "directObservations": {"header": "TROUBLES OVER. L.M.H.", "key": "G minor", "timeSignature": "2/4", "meter": "Long Meter Half (8,8)", "parts": 4, "measuresByPart": summary["measuresByPart"]}},
        "inputOmr": {"path": "work/omr/80t-troubles-over/source.mxl", "sha256": source_hash, "status": "retained-source-scan-omr"},
        "correctedDraft": {"path": "work/omr/autonomous-transcriptions/2025/80t-autonomous-blocked.mxl", "sha256": output_hash, "summary": summary, "corrections": ["four part structure preserved", "source G-minor key/mode", "source 2/4 time signature", "derived four-shape notehead tags", "fail-closed provenance fields"]},
        "comparisonEvidence": {"sourceScanInspected": True, "renderedSourcePath": "work/omr/80t-troubles-over/source.jpg", "renderedDraftInputs": ["work/omr/80t-troubles-over/source.mxl"], "method": "direct visual inspection of retained scan plus structural/event audit of retained OMR", "blockingFindings": blocking},
        "blockingReason": "Autonomous promotion is blocked by the listed blank source-visible measures, pervasive duration uncertainty, collapsed clusters, and specific watermark intersections. The derivative preserves detected events but does not invent missing music.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-omr-and-obscured-events; requires-source-event-verification",
        "policy": "Immutable 2025 source remains authoritative. Incomplete OMR is retained as a blocked source-derived draft and is not promoted.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "sourceSha256": source_hash, "derivativeSha256": output_hash, **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
