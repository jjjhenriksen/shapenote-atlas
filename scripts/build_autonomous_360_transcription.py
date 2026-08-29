#!/usr/bin/env python3
"""Build the autonomous, fail-closed MusicXML transcription for SH2025/360.

The retained 2025 scan is the authority for the printed header.  The retained
Audiveris file supplies the structured event stream, but its few over/underfull
measures are preserved and reported rather than silently repaired.  This makes
the result useful for playback and editing while keeping promotion closed.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "work/omr/360-the-royal-band/source.mxl"
SOURCE_IMAGE = ROOT / "work/omr/360-the-royal-band/source.jpg"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/360-autonomous-provisional.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/360-the-royal-band-autonomous-comparison.json"

STEPS = ("C", "D", "E", "F", "G", "A", "B")
SHAPES = ("fa", "sol", "la", "fa", "sol", "la", "mi")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def first(parent: ET.Element, name: str) -> ET.Element | None:
    return next((child for child in parent if local_name(child.tag) == name), None)


def text(parent: ET.Element, name: str) -> str:
    child = first(parent, name)
    return (child.text or "").strip() if child is not None else ""


def ensure(parent: ET.Element, name: str) -> ET.Element:
    child = first(parent, name)
    return child if child is not None else ET.SubElement(parent, name)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_xml(path: Path) -> tuple[bytes, str]:
    with zipfile.ZipFile(path) as archive:
        member = next(
            name
            for name in archive.namelist()
            if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/")
        )
        return archive.read(member), member


def add_misc(identification: ET.Element, name: str, value: str) -> None:
    miscellaneous = first(identification, "miscellaneous")
    if miscellaneous is None:
        miscellaneous = ET.SubElement(identification, "miscellaneous")
    for old in [item for item in miscellaneous if item.attrib.get("name") == name]:
        miscellaneous.remove(old)
    field = ET.SubElement(miscellaneous, "miscellaneous-field", {"name": name})
    field.text = value


def shape_for(step: str) -> str | None:
    """Map E-minor scale steps through its relative major, G major."""
    if step not in STEPS:
        return None
    relative_major = STEPS[(STEPS.index("E") + 2) % 7]
    return SHAPES[(STEPS.index(step) - STEPS.index(relative_major)) % 7]


def measure_duration(measure: ET.Element, divisions: float) -> float:
    cursor = 0.0
    maximum = 0.0
    for item in measure:
        name = local_name(item.tag)
        if name == "note":
            duration = float(text(item, "duration") or "0") / divisions
            if first(item, "chord") is None:
                cursor += duration
            maximum = max(maximum, cursor)
        elif name == "backup":
            cursor -= float(text(item, "duration") or "0") / divisions
        elif name == "forward":
            cursor += float(text(item, "duration") or "0") / divisions
    return round(maximum, 3)


def transform(xml_bytes: bytes, source_hash: str, omr_hash: str) -> tuple[bytes, dict[str, object]]:
    root = ET.fromstring(xml_bytes)
    if local_name(root.tag) != "score-partwise":
        raise ValueError("expected score-partwise MusicXML")

    work = first(root, "work")
    if work is None:
        work = ET.Element("work")
        root.insert(0, work)
    ensure(work, "work-title").text = "The Royal Band, 360 — autonomous provisional transcription"

    part_names = {"P1": "Soprano", "P2": "Alto", "P3": "Tenor", "P4": "Bass"}
    for score_part in root.iter():
        if local_name(score_part.tag) != "score-part":
            continue
        part_name = part_names.get(score_part.attrib.get("id", ""))
        if part_name:
            ensure(score_part, "part-name").text = part_name
            ensure(score_part, "part-abbreviation").text = part_name[:2]

    counts: dict[str, object] = {"parts": 0, "measuresByPart": {}, "pitchedEvents": 0, "shapeNoteheadsAdded": 0, "measureDurations": {}}
    for part in [item for item in root if local_name(item.tag) == "part"]:
        part_id = part.attrib.get("id", "")
        counts["parts"] = int(counts["parts"]) + 1
        durations: list[float] = []
        divisions = 4.0
        for measure in [item for item in part if local_name(item.tag) == "measure"]:
            attributes = first(measure, "attributes")
            if attributes is None:
                attributes = ET.Element("attributes")
                measure.insert(0, attributes)
            if text(attributes, "divisions"):
                divisions = float(text(attributes, "divisions"))
            key = ensure(attributes, "key")
            ensure(key, "fifths").text = "1"
            ensure(key, "mode").text = "minor"
            time = ensure(attributes, "time")
            ensure(time, "beats").text = "6"
            ensure(time, "beat-type").text = "8"
            durations.append(measure_duration(measure, divisions))
            for note in [item for item in measure if local_name(item.tag) == "note"]:
                pitch = first(note, "pitch")
                if pitch is None:
                    continue
                counts["pitchedEvents"] = int(counts["pitchedEvents"]) + 1
                shape = shape_for(text(pitch, "step").upper())
                if shape is None:
                    continue
                for old in [item for item in note if local_name(item.tag) == "notehead"]:
                    note.remove(old)
                notehead = ET.Element("notehead")
                notehead.text = shape
                stem_index = next((index for index, item in enumerate(note) if local_name(item.tag) == "stem"), len(note))
                note.insert(stem_index, notehead)
                counts["shapeNoteheadsAdded"] = int(counts["shapeNoteheadsAdded"]) + 1
        counts["measuresByPart"][part_id] = len(durations)  # type: ignore[index]
        counts["measureDurations"][part_id] = durations  # type: ignore[index]

    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(1, identification)
    fields = {
        "atlas-queue-id": "sh2025/360",
        "atlas-transcription-status": "autonomously-blocked",
        "atlas-safe-to-promote": "false",
        "atlas-source-image": "work/omr/360-the-royal-band/source.jpg",
        "atlas-source-image-sha256": source_hash,
        "atlas-source-omr": "work/omr/360-the-royal-band/source.mxl",
        "atlas-source-omr-sha256": omr_hash,
        "atlas-source-key": "E minor",
        "atlas-source-mode": "minor",
        "atlas-source-meter": "12s & 11s D.",
        "atlas-source-time-signature": "6/8",
        "atlas-shape-encoding": "derived from the visibly printed E-minor source key; every pitched event has an explicit four-shape notehead",
        "atlas-lyrics": "source text is visible but not yet aligned event-by-event; omitted because the notation remains usable without fabricated underlay",
        "atlas-structural-discrepancies": "OMR durations outside the 6/8 bar are preserved for autonomous audit: P1 m6=3.5,m11=3.5,m12=2.5,m14=1.5; P2 m3=3.5,m4=3.25,m7=3.5,m10=2.5,m14=1.5; P3 m3=3.5,m4=3.25,m10=2.5,m13=3.25; P4 m3=3.5,m6=3.5,m8=3.5,m10=2.5,m12=2.5.",
        "atlas-metadata-conflict": "legacy corpus metadata says G major; retained 2025 scan visibly prints E Minor; this derivative follows the scan and remains unpromoted",
    }
    for name, value in fields.items():
        add_misc(identification, name, value)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), counts


def write_mxl(xml_bytes: bytes, member: str) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(INPUT) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml_bytes if info.filename == member else source.read(info.filename))


def main() -> int:
    source_hash = sha256(SOURCE_IMAGE)
    omr_hash = sha256(INPUT)
    xml_bytes, member = read_xml(INPUT)
    corrected, summary = transform(xml_bytes, source_hash, omr_hash)
    write_mxl(corrected, member)
    audit = {
        "queueId": "sh2025/360",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "360",
        "title": "The Royal Band",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=360",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/360-The-Royal-Band/360-The-Royal-Band.jpg",
            "sourceImagePath": "work/omr/360-the-royal-band/source.jpg",
            "sourceImageSha256": source_hash,
            "immutable": True,
            "directObservations": {
                "header": "360 THE ROYAL BAND. 12s & 11s.",
                "key": "E minor",
                "meter": "12s & 11s D.",
                "timeSignature": "6/8",
                "composer": "W. T. Power, 1850",
                "lyricist": "Mercer's Cluster, 1829",
                "parts": 4,
                "measuresByPart": {"P1": 14, "P2": 14, "P3": 14, "P4": 14},
                "fourShapeNoteheadsVisible": True,
            },
        },
        "inputOmr": {
            "path": "work/omr/360-the-royal-band/source.mxl",
            "sha256": omr_hash,
            "status": "retained-source-scan-omr",
        },
        "correctedDraft": {
            "path": str(OUTPUT.relative_to(ROOT)),
            "sha256": sha256(OUTPUT),
            "summary": summary,
            "corrections": ["four part names", "scan-visible E-minor key/mode", "scan-visible 6/8 meter", "explicit derived four-shape noteheads", "provenance fields"],
        },
        "autonomousEvidence": {
            "sourceScanInspected": True,
            "sourceImageIsUnwatermarked": True,
            "method": "direct inspection of the retained scan plus deterministic transformation of the retained OMR; no image generation and no human sign-off dependency",
            "usableNow": ["editable four-part MusicXML", "playable pitch/rhythm event stream", "explicit notehead shape tags", "source key/mode and meter metadata"],
            "notClaimed": ["event-by-event source proof for preserved OMR duration anomalies", "event-aligned lyrics", "promotion into the authoritative corpus"],
        },
        "blockingFindings": [
            "The retained OMR has 14 measures per part and 242 pitched events, but 18 named measures are over/underfull relative to 6/8: P1 m6,m11,m12,m14; P2 m3,m4,m7,m10,m14; P3 m3,m4,m10,m13; P4 m3,m6,m8,m10,m12. Those event durations are preserved rather than guessed at.",
            "The 2025 scan visibly prints E minor while legacy corpus metadata says G major; this derivative follows the immutable scan and remains outside the authoritative corpus.",
            "The source scan is unwatermarked and the displayed notation remains usable without lyric underlay; lyrics are omitted without fabrication and are not an independent blocker.",
        ],
        "nextAction": "autonomous-promotion-blocked-by-listed-omr-duration-anomalies; requires-source-event-verification",
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)), "audit": str(AUDIT.relative_to(ROOT)), "pitchedEvents": summary["pitchedEvents"], "shapeNoteheadsAdded": summary["shapeNoteheadsAdded"], "safeToPromote": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
