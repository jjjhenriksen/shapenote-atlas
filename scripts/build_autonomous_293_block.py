#!/usr/bin/env python3
"""Create a fail-closed, source-derived Midnight Hour OMR derivative."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work" / "omr" / "293-midnight-hour" / "source.mxl"
IMAGE = ROOT / "work" / "omr" / "293-midnight-hour" / "source.jpg"
OUTPUT = ROOT / "work" / "omr" / "autonomous-transcriptions" / "2025" / "293-autonomous-blocked.mxl"
AUDIT = ROOT / "work" / "source-transcriptions" / "2025" / "293-midnight-hour-autonomous-comparison.json"

# E minor is relative to G major for four-shape spelling.
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
                if duration_total(measure) != 8
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
            "atlas-queue-id": "sh2025/293",
            "atlas-transcription-status": "autonomously-blocked",
            "atlas-safe-to-promote": "false",
            "atlas-source-image": "work/omr/293-midnight-hour/source.jpg",
            "atlas-source-image-sha256": digest(IMAGE),
            "atlas-source-key": "E minor",
            "atlas-source-mode": "minor",
            "atlas-source-meter": "Common Meter (8s, 6s, 8s, 6s.)",
            "atlas-source-time-signature": "4/4",
            "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitches and source-visible E-minor key; not source-verified per event",
            "atlas-lyrics": "source lyrics visible but not safely aligned in OMR; omitted because the notation remains usable without fabricated underlay",
            "atlas-blocker": "The source visibly prints MIDNIGHT HOUR. C.M., E minor, 4/4, and four vocal parts with 12 measures per part. Retained OMR duration/event grouping fails at P1 m1=6,m2=4,m3=6,m5=4,m6=0,m7=12,m8=28,m10=12,m12=6; P2 m1=2,m2=6,m3=2,m4=2,m5=12,m6=0,m8=2,m9=6,m10=4,m11=4,m12=0; P3 m2=10,m5=6,m6=4,m7=6,m8=6,m10=6,m11=4,m12=0; and P4 m2=20,m3=22,m4=22,m5=14,m6=4,m7=2,m8=6,m9=6,m10=2,m11=4,m12=4, using source 4/4 with retained divisions=2. P1 m6, P2 m6,m12, and P3 m12 are blank while the source shows notation. OMR key fields record fifths=1 without a mode in P1/P3 and no key in P2/P4, conflicting with source-visible E minor. Watermark intersections are separately unresolved only in the affected middle/bottom systems.",
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
        "The retained source scan visibly prints MIDNIGHT HOUR. C.M., E minor, 4/4, and four vocal parts with 12 measures per part.",
        "The retained OMR duration/event grouping fails in the named part/measure groups against source 4/4; P1 m6, P2 m6,m12, and P3 m12 are blank although the source visibly contains notation.",
        "The retained OMR key fields conflict with source-visible E minor: P1/P3 record fifths=1 without a mode and P2/P4 have no key; the derivative corrects source metadata without silently rewriting event pitches.",
        "Watermark intersections remain unresolved only for the note events in the affected middle/bottom systems. Lyrics are optional and are omitted without fabrication.",
    ]
    audit = {
        "queueId": "sh2025/293",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "293",
        "title": "Midnight Hour",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=293",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/293-Midnight-Hour/293.jpg",
            "sourceImagePath": "work/omr/293-midnight-hour/source.jpg",
            "sourceImageSha256": image_hash,
            "immutable": True,
            "directObservations": {
                "header": "MIDNIGHT HOUR. C.M.",
                "key": "E minor",
                "timeSignature": "4/4",
                "meter": "Common Meter (8s, 6s, 8s, 6s.)",
                "parts": 4,
                "measuresByPart": summary["measuresByPart"],
                "watermarkAffectedRegions": "affected middle/bottom system note intersections only",
            },
        },
        "inputOmr": {
            "path": "work/omr/293-midnight-hour/source.mxl",
            "sha256": source_hash,
            "status": "retained-source-scan-omr",
        },
        "correctedDraft": {
            "path": "work/omr/autonomous-transcriptions/2025/293-autonomous-blocked.mxl",
            "sha256": output_hash,
            "summary": summary,
            "corrections": [
                "four part structure preserved",
                "source E-minor key/mode",
                "source 4/4 time signature",
                "derived four-shape notehead tags",
                "fail-closed provenance fields",
            ],
        },
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "renderedSourcePath": "work/omr/293-midnight-hour/source.jpg",
            "renderedDraftInputs": ["work/omr/293-midnight-hour/source.mxl"],
            "method": "direct visual inspection of retained scan plus structural/event and duration audit of retained OMR",
            "blockingFindings": blocking,
        },
        "blockingReason": "Autonomous promotion is blocked by the named duration/event failures, blank source-visible measures, conflicting OMR key fields, and only watermark-intersected events. The derivative preserves detected events but does not invent rhythm, pitch, or lyrics.",
        "nextAction": "autonomous-promotion-blocked-by-source-event-grouping-and-obscured-events; requires-source-event-verification",
        "policy": "Immutable 2025 source remains authoritative. The corrected OMR is retained as a blocked source-derived draft and is not promoted.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "sourceSha256": source_hash, "derivativeSha256": output_hash, **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
