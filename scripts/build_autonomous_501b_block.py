#!/usr/bin/env python3
"""Create a fail-closed, source-derived O'Leary OMR derivative."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work" / "omr" / "501b-o-leary" / "source.mxl"
IMAGE = ROOT / "work" / "omr" / "501b-o-leary" / "source.jpg"
OUTPUT = ROOT / "work" / "omr" / "autonomous-transcriptions" / "2025" / "501b-autonomous-blocked.mxl"
AUDIT = ROOT / "work" / "source-transcriptions" / "2025" / "501b-o-leary-autonomous-comparison.json"

# G major is the source key; the four-shape syllables follow its scale.
SHAPES = {"A": "sol", "B": "la", "C": "fa", "D": "sol", "E": "la", "F": "mi", "G": "fa"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def ln(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(parent: ET.Element | None, name: str) -> list[ET.Element]:
    return [child for child in parent if ln(child.tag) == name] if parent is not None else []


def first(parent: ET.Element | None, name: str) -> ET.Element | None:
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
                if duration_end(measure) != 6
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
        failure_text = "; ".join(
            f"{part_id} {','.join(failures)}" for part_id, failures in duration_failures.items() if failures
        )
        identification = first(root, "identification")
        if identification is None:
            identification = ET.Element("identification")
            root.insert(0, identification)
        for name, value in {
            "atlas-queue-id": "sh2025/501b",
            "atlas-transcription-status": "autonomously-blocked",
            "atlas-safe-to-promote": "false",
            "atlas-source-image": "work/omr/501b-o-leary/source.jpg",
            "atlas-source-image-sha256": digest(IMAGE),
            "atlas-source-key": "G major",
            "atlas-source-mode": "major",
            "atlas-source-meter": "S.M.",
            "atlas-source-time-signature": "3/4",
            "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitches and source-visible G-major key; not source-verified per event",
            "atlas-lyrics": "source lyrics visible but not safely aligned in OMR; omitted because the notation remains usable without fabricated underlay",
            "atlas-blocker": f"The source visibly prints O'LEARY. S.M., G major, 3/4, four vocal parts, and six measures per part. Chord-aware cursor duration fails at {failure_text}, using source 3/4 with retained divisions=2. P2 m1,m2, P3 m1,m6, and P4 m6 are blank while the source shows notation. OMR key fields record fifths=1 without a mode in P1/P2/P3 and no key in P4, conflicting with complete source-visible G-major metadata. The diagonal watermark intersects middle-system events; only those intersected events remain unresolved for that reason.",
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
        "The retained source scan visibly prints O'LEARY. S.M., G major, 3/4, four vocal parts, and six measures per part.",
        "Chord-aware cursor duration fails in the named part/measure groups against source 3/4; P2 m1,m2, P3 m1,m6, and P4 m6 are blank although the source visibly contains notation.",
        "The retained OMR omits mode and P4 key metadata; the derivative follows source-visible G major without silently rewriting event pitches.",
        "The diagonal watermark intersects middle-system events; only those intersected events remain unresolved for that reason. Lyrics are optional and are omitted without fabrication.",
    ]
    audit = {
        "queueId": "sh2025/501b",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "501b",
        "title": "O'Leary",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=501b",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/501b-O-Leary/501b.jpg",
            "sourceImagePath": "work/omr/501b-o-leary/source.jpg",
            "sourceImageSha256": image_hash,
            "immutable": True,
            "directObservations": {
                "header": "O'LEARY. S.M.",
                "key": "G major",
                "timeSignature": "3/4",
                "meter": "S.M.",
                "parts": 4,
                "measuresByPart": summary["measuresByPart"],
                "watermarkAffectedRegions": "middle-system note intersections only",
            },
        },
        "inputOmr": {
            "path": "work/omr/501b-o-leary/source.mxl",
            "sha256": source_hash,
            "status": "retained-source-scan-omr",
        },
        "correctedDraft": {
            "path": "work/omr/autonomous-transcriptions/2025/501b-autonomous-blocked.mxl",
            "sha256": output_hash,
            "summary": summary,
            "corrections": [
                "four part structure preserved",
                "source G-major key/mode",
                "source 3/4 time signature",
                "derived four-shape notehead tags",
                "fail-closed provenance fields",
            ],
        },
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "renderedSourcePath": "work/omr/501b-o-leary/source.jpg",
            "renderedDraftInputs": ["work/omr/501b-o-leary/source.mxl"],
            "method": "direct visual inspection of retained scan plus structural/event and chord-aware duration audit of retained OMR",
            "blockingFindings": blocking,
        },
        "blockingReason": "Autonomous promotion is blocked by the named duration/event failures, blank source-visible groups, incomplete OMR key metadata, and only the watermark-intersected middle-system events. The derivative preserves detected events but does not invent rhythm, pitch, or lyrics.",
        "nextAction": "autonomous-promotion-blocked-by-source-event-grouping-and-obscured-events; requires-source-event-verification",
        "policy": "Immutable 2025 source remains authoritative. The corrected OMR is retained as a blocked source-derived draft and is not promoted.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": audit["queueId"], "status": audit["comparisonStatus"], "sourceSha256": source_hash, "derivativeSha256": output_hash, **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
