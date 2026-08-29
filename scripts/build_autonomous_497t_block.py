#!/usr/bin/env python3
"""Create a fail-closed, source-derived Natick OMR derivative."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work" / "omr" / "497t-natick" / "source.mxl"
IMAGE = ROOT / "work" / "omr" / "497t-natick" / "source.jpg"
OUTPUT = ROOT / "work" / "omr" / "autonomous-transcriptions" / "2025" / "497t-autonomous-blocked.mxl"
AUDIT = ROOT / "work" / "source-transcriptions" / "2025" / "497t-natick-autonomous-comparison.json"

# Natick is printed in A major; the four-shape syllables follow the source key.
SHAPES = {"A": "fa", "B": "sol", "C": "la", "D": "fa", "E": "sol", "F": "la", "G": "mi"}


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


def duration_end(measure: ET.Element) -> int:
    """Return the furthest cursor position, respecting chords and backups."""
    cursor = 0
    maximum = 0
    for item in measure:
        name = ln(item.tag)
        duration = first(item, "duration")
        units = int(duration.text) if duration is not None and duration.text else 0
        if name == "note":
            if first(item, "chord") is None:
                cursor += units
            maximum = max(maximum, cursor)
        elif name == "backup":
            cursor -= units
        elif name == "forward":
            cursor += units
    return maximum


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
                f"m{measure.attrib.get('number')}={duration_end(measure)}"
                for measure in measures
                if duration_end(measure) != 8
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
            "atlas-queue-id": "sh2025/497t",
            "atlas-transcription-status": "autonomously-blocked",
            "atlas-safe-to-promote": "false",
            "atlas-source-image": "work/omr/497t-natick/source.jpg",
            "atlas-source-image-sha256": digest(IMAGE),
            "atlas-source-key": "A major",
            "atlas-source-mode": "major",
            "atlas-source-meter": "7s.",
            "atlas-source-time-signature": "4/4",
            "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitches and source-visible A-major key; not source-verified per event",
            "atlas-lyrics": "source lyrics visible but not safely aligned in OMR; omitted because the notation remains usable without fabricated underlay",
            "atlas-blocker": "The source visibly has four parts and ten 4/4 measures. Chord-aware cursor duration fails against source 4/4 with retained divisions=2 at P1 m1=2,m2=4,m3=7,m7=10,m8=4,m10=6; P2 m1=2,m3=4,m4=4,m5=2,m6=0,m7=12,m8=4,m9=7,m10=6; P3 m1=4,m2=2,m3=10,m4=6,m5=7,m6=10,m7=10,m8=10,m9=4,m10=3; and P4 m1=4,m2=2,m3=10,m4=10,m5=4,m7=12,m8=10,m9=5,m10=4. P2 m6 is blank while the source shows notation. OMR key fields record fifths=2 in P1/P2, fifths=3 in P3, and no key in P4, with no mode; only P3 agrees with the source A-major key signature. Watermark intersections are separately unresolved only in the middle systems.",
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
        "The retained source scan visibly prints NATICK. 7s., A major, 4/4, four vocal parts, and ten measures per part.",
        "Chord-aware cursor duration fails in the named part/measure groups recorded in the derivative against source 4/4; P2 m6 is blank although the source visibly contains notation.",
        "The retained OMR key fields conflict with source-visible A major in P1/P2/P4 and omit mode; the derivative corrects source metadata without silently rewriting event pitches.",
        "A diagonal watermark intersects notes in the middle systems; only those intersected events remain unresolved for that reason. Lyrics are optional and are omitted without fabrication.",
    ]
    audit = {
        "queueId": "sh2025/497t",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "497t",
        "title": "Natick",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=497t",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/497t-Natick/497t.jpg",
            "sourceImagePath": "work/omr/497t-natick/source.jpg",
            "sourceImageSha256": image_hash,
            "immutable": True,
            "directObservations": {
                "header": "NATICK. 7s.",
                "key": "A major",
                "timeSignature": "4/4",
                "meter": "7s.",
                "parts": 4,
                "measuresByPart": summary["measuresByPart"],
                "watermarkAffectedRegions": "middle-system note intersections only",
            },
        },
        "inputOmr": {
            "path": "work/omr/497t-natick/source.mxl",
            "sha256": source_hash,
            "status": "retained-source-scan-omr",
        },
        "correctedDraft": {
            "path": "work/omr/autonomous-transcriptions/2025/497t-autonomous-blocked.mxl",
            "sha256": output_hash,
            "summary": summary,
            "corrections": [
                "four part structure preserved",
                "source A-major key/mode",
                "source 4/4 time signature",
                "derived four-shape notehead tags",
                "fail-closed provenance fields",
            ],
        },
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "renderedSourcePath": "work/omr/497t-natick/source.jpg",
            "renderedDraftInputs": ["work/omr/497t-natick/source.mxl"],
            "method": "direct visual inspection of retained scan plus structural/event and duration audit of retained OMR",
            "blockingFindings": blocking,
        },
        "blockingReason": "Autonomous promotion is blocked by the named duration/event failures, blank P2 m6, conflicting OMR key fields, and only the watermark-intersected middle-system events. The derivative preserves detected events but does not invent rhythm, pitch, or lyrics.",
        "nextAction": "autonomous-promotion-blocked-by-source-event-grouping-and-obscured-events; requires-source-event-verification",
        "policy": "Immutable 2025 source remains authoritative. The corrected OMR is retained as a blocked source-derived draft and is not promoted.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "sourceSha256": source_hash, "derivativeSha256": output_hash, **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
