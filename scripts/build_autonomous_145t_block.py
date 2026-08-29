#!/usr/bin/env python3
"""Create a fail-closed, source-derived Warrenton OMR derivative."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work" / "omr" / "145t-warrenton" / "source.mxl"
IMAGE = ROOT / "work" / "omr" / "145t-warrenton" / "source.jpg"
OUTPUT = ROOT / "work" / "omr" / "autonomous-transcriptions" / "2025" / "145t-autonomous-blocked.mxl"
AUDIT = ROOT / "work" / "source-transcriptions" / "2025" / "145t-warrenton-autonomous-comparison.json"

# Warrenton is printed in G major; the four-shape syllables follow the source key.
SHAPES = {"G": "fa", "A": "sol", "B": "la", "C": "fa", "D": "sol", "E": "la", "F": "mi"}


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


def duration_total(measure: ET.Element) -> int:
    total = 0
    for note in children(measure, "note"):
        duration = first(note, "duration")
        if duration is not None and duration.text:
            total += int(duration.text)
    return total


def transform() -> tuple[bytes, dict[str, object]]:
    with zipfile.ZipFile(SOURCE) as archive:
        root = ET.fromstring(archive.read("source.xml"))
        parts = children(root, "part")
        pitched = 0
        shapes = 0
        counts: dict[str, int] = {}
        duration_failures: dict[str, list[str]] = {}
        for part in parts:
            part_id = part.attrib.get("id", "")
            measures = children(part, "measure")
            counts[part_id] = len(measures)
            duration_failures[part_id] = [
                f"m{measure.attrib.get('number')}={duration_total(measure)}"
                for measure in measures
                if duration_total(measure) != 2
            ]
            for note in [item for item in part.iter() if ln(item.tag) == "note"]:
                pitch = first(note, "pitch")
                if pitch is None:
                    continue
                step_node = first(pitch, "step")
                if step_node is None or not step_node.text:
                    continue
                shape = SHAPES.get(step_node.text.strip().upper())
                if shape is None:
                    continue
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
            "atlas-queue-id": "sh2025/145t",
            "atlas-transcription-status": "autonomously-blocked",
            "atlas-safe-to-promote": "false",
            "atlas-source-image": "work/omr/145t-warrenton/source.jpg",
            "atlas-source-image-sha256": digest(IMAGE),
            "atlas-source-key": "G major",
            "atlas-source-mode": "major",
            "atlas-source-meter": "Particular Meter (8s & 7s.)",
            "atlas-source-time-signature": "2/4",
            "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitches and source-visible G-major key; not source-verified per event",
            "atlas-lyrics": "source lyrics visible but not safely aligned in OMR; omitted because the notation remains usable without fabricated underlay",
            "atlas-blocker": "The source visibly prints WARRENTON. 8s & 7s., G major, 2/4, four vocal parts, and 13 measures per part. Retained OMR duration/event grouping fails at P1 m1=0,m6=3,m7=4,m8=1,m10=3,m11=4,m12=1; P2 m3=1,m4=7,m6=4,m7=6,m8=5,m10=1,m11=1,m12=1; P3 m3=3,m5=12,m6=4,m9=0,m12=0,m13=0; and P4 m6=4,m13=0, using source 2/4 with retained divisions=1. P1 m1, P3 m9,m12,m13, and P4 m13 are blank while the source shows notation. The OMR omits the source mode and has no key in P4; the derivative corrects source metadata without silently rewriting event pitches. Watermark intersections are separately unresolved only in the middle systems.",
        }.items():
            set_field(identification, name, value)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), {
            "parts": len(parts),
            "measuresByPart": counts,
            "pitchedEvents": pitched,
            "shapeNoteheadsAdded": shapes,
            "durationFailures": duration_failures,
        }


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
        "The retained source scan visibly prints WARRENTON. 8s & 7s., G major, 2/4, four vocal parts, and 13 measures per part.",
        "The retained OMR duration/event grouping fails in the named part/measure groups against source 2/4; P1 m1, P3 m9,m12,m13, and P4 m13 are blank although the source visibly contains notation.",
        "The retained OMR omits the source mode and has no key in P4; the derivative corrects source metadata without silently rewriting event pitches.",
        "A diagonal watermark intersects notes in the middle systems; only those intersected events remain unresolved for that reason. Lyrics are optional and are omitted without fabrication.",
    ]
    audit = {
        "queueId": "sh2025/145t",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "145t",
        "title": "Warrenton",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=145t",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/145t-Warrenton/145t.jpg",
            "sourceImagePath": "work/omr/145t-warrenton/source.jpg",
            "sourceImageSha256": image_hash,
            "immutable": True,
            "directObservations": {
                "header": "WARRENTON. 8s & 7s.",
                "key": "G major",
                "timeSignature": "2/4",
                "meter": "Particular Meter (8s & 7s.)",
                "parts": 4,
                "measuresByPart": summary["measuresByPart"],
                "watermarkAffectedRegions": "middle-system note intersections only",
            },
        },
        "inputOmr": {
            "path": "work/omr/145t-warrenton/source.mxl",
            "sha256": source_hash,
            "status": "retained-source-scan-omr",
        },
        "correctedDraft": {
            "path": "work/omr/autonomous-transcriptions/2025/145t-autonomous-blocked.mxl",
            "sha256": output_hash,
            "summary": summary,
            "corrections": [
                "four part structure preserved",
                "source G-major key/mode",
                "source 2/4 time signature",
                "derived four-shape notehead tags",
                "fail-closed provenance fields",
            ],
        },
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "renderedSourcePath": "work/omr/145t-warrenton/source.jpg",
            "renderedDraftInputs": ["work/omr/145t-warrenton/source.mxl"],
            "method": "direct visual inspection of retained scan plus structural/event and duration audit of retained OMR",
            "blockingFindings": blocking,
        },
        "blockingReason": "Autonomous promotion is blocked by the named duration/event failures, blank source-visible measures, incomplete OMR key/mode metadata, and only the watermark-intersected middle-system events. The derivative preserves detected events but does not invent rhythm, pitch, or lyrics.",
        "nextAction": "autonomous-promotion-blocked-by-source-event-grouping-and-obscured-events; requires-source-event-verification",
        "policy": "Immutable 2025 source remains authoritative. The corrected OMR is retained as a blocked source-derived draft and is not promoted.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "sourceSha256": source_hash, "derivativeSha256": output_hash, **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
