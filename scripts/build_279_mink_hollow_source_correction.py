#!/usr/bin/env python3
"""Create a source-derived, fail-closed correction for Sacred Harp 279."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/omr/279-mink-hollow/source.mxl"
SOURCE_IMAGE = ROOT / "work/omr/279-mink-hollow/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/279-mink-hollow-fb325f175f.jpg"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/279-mink-hollow-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/279-source-shape-autonomous-blocked-comparison.json"

# Four-shape spelling for F major. This is derived from the source-page key;
# it does not claim that each retained OMR pitch was source-verified.
SHAPES = {"A": "la", "B": "fa", "C": "sol", "D": "la", "E": "mi", "F": "fa", "G": "sol"}


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


def set_field(identification: ET.Element, key: str, value: str) -> None:
    misc = first(identification, "miscellaneous")
    if misc is None:
        misc = ET.SubElement(identification, "miscellaneous")
    for old in [item for item in children(misc, "miscellaneous-field") if item.attrib.get("name") == key]:
        misc.remove(old)
    ET.SubElement(misc, "miscellaneous-field", {"name": key}).text = value


def duration_end(measure: ET.Element) -> int:
    cursor = maximum = 0
    for item in measure:
        duration = first(item, "duration")
        units = int(duration.text) if duration is not None and duration.text and duration.text.lstrip("-").isdigit() else 0
        if local(item.tag) == "note":
            if first(item, "chord") is None:
                cursor += units
            maximum = max(maximum, cursor)
        elif local(item.tag) == "backup":
            cursor -= units
        elif local(item.tag) == "forward":
            cursor += units
    return maximum


def source_xml() -> ET.Element:
    with zipfile.ZipFile(SOURCE) as archive:
        name = next(item for item in archive.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        return ET.fromstring(archive.read(name))


def event_signature(root: ET.Element) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for part in children(root, "part"):
        events: list[dict[str, str]] = []
        for measure in children(part, "measure"):
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                pitch_value = "rest" if first(note, "rest") is not None else "unknown"
                if pitch is not None:
                    pitch_value = ":".join([text(pitch, "step"), text(pitch, "alter", "0"), text(pitch, "octave")])
                events.append({
                    "measure": measure.attrib.get("number", ""),
                    "pitch": pitch_value,
                    "duration": text(note, "duration"),
                    "type": text(note, "type"),
                    "voice": text(note, "voice"),
                })
        result[part.attrib.get("id", "")] = events
    return result


def transform() -> tuple[bytes, dict[str, object], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    root = source_xml()
    source_events = event_signature(root)
    summary: dict[str, object] = {
        "parts": 0,
        "measuresByPart": {},
        "eventsByPart": {},
        "pitchedEvents": 0,
        "restEvents": 0,
        "shapeNoteheadsAdded": 0,
        "emptyMeasures": 0,
        "durationFailuresAgainst4_4": {},
        "sourceBarlines": 0,
        "lyricsRetained": 0,
    }
    parts = children(root, "part")
    summary["parts"] = len(parts)
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = children(part, "measure")
        summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
        summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
        summary["emptyMeasures"] = int(summary["emptyMeasures"]) + sum(not children(measure, "note") for measure in measures)
        summary["sourceBarlines"] = int(summary["sourceBarlines"]) + sum(len(children(measure, "barline")) for measure in measures)
        summary["durationFailuresAgainst4_4"][part_id] = [  # type: ignore[index]
            f"m{measure.attrib.get('number')}={duration_end(measure)}" for measure in measures if duration_end(measure) != 8
        ]
        for measure in measures:
            attributes = first(measure, "attributes")
            if attributes is None:
                attributes = ET.Element("attributes")
                measure.insert(0, attributes)
            key = first(attributes, "key")
            if key is None:
                key = ET.Element("key")
                attributes.insert(1, key)
            for old in children(key, "fifths") + children(key, "mode"):
                key.remove(old)
            ET.SubElement(key, "fifths").text = "-1"
            ET.SubElement(key, "mode").text = "major"
            time = first(attributes, "time")
            if time is None:
                time = ET.Element("time")
                attributes.insert(2, time)
            for old in children(time, "beats") + children(time, "beat-type"):
                time.remove(old)
            ET.SubElement(time, "beats").text = "4"
            ET.SubElement(time, "beat-type").text = "4"
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                if pitch is None:
                    if first(note, "rest") is not None:
                        summary["restEvents"] = int(summary["restEvents"]) + 1
                    continue
                step = text(pitch, "step").upper()
                if step not in SHAPES:
                    continue
                for old in children(note, "notehead"):
                    note.remove(old)
                notehead = ET.Element("notehead")
                notehead.text = SHAPES[step]
                stem_index = next((index for index, item in enumerate(note) if local(item.tag) == "stem"), len(note))
                note.insert(stem_index, notehead)
                summary["pitchedEvents"] = int(summary["pitchedEvents"]) + 1
                summary["shapeNoteheadsAdded"] = int(summary["shapeNoteheadsAdded"]) + 1
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    provenance = {
        "atlas-queue-id": "sh2025/279",
        "atlas-transcription-status": "autonomously-blocked",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-image": "work/omr/279-mink-hollow/source.jpg",
        "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
        "atlas-retained-source-copy": "work/source-images/2025/279-mink-hollow-fb325f175f.jpg",
        "atlas-retained-source-copy-sha256": sha256(RETAINED_IMAGE),
        "atlas-source-key": "F major",
        "atlas-source-mode": "major",
        "atlas-source-time-signature": "4/4",
        "atlas-source-meter": "Common Meter Double (8,6,8,6,8,6,8,6)",
        "atlas-source-title-and-credits": "MINK HOLLOW. C.M.D.; William Bengo Collyer, 1812; Isaac Watts, 1707; Benjamin Beddome, 1794; Keillor Mose, 2023",
        "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible F-major key; not source-verified per event",
        "atlas-lyrics": "omitted; source lyrics are visible but retained OMR has no directly aligned lyric underlay",
        "atlas-provenance-policy": "immutable 2025 source image is authoritative; no authorized same-title structured candidate exists; this OMR derivative is evidence only",
        "atlas-blocker": "The immutable page visibly prints MINK HOLLOW. C.M.D., F major, 4/4, four vocal parts, lyrics, repeated sections with first/second endings, and a terminal double bar. The retained OMR contains 23 measures per part but no key, mode, meter, lyrics, or shape tags; its duration grouping is sparse and not source-proven. A diagonal DO NOT COPY watermark intersects the lower systems, lyric lines, and ending region. No notation was synthesized.",
    }
    for key, value in provenance.items():
        set_field(identification, key, value)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), summary, source_events, event_signature(root)


def main() -> int:
    source_hash = sha256(SOURCE)
    source_image_hash = sha256(SOURCE_IMAGE)
    retained_hash = sha256(RETAINED_IMAGE)
    xml, summary, source_events, corrected_events = transform()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        xml_name = next(item for item in source.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        for info in source.infolist():
            target.writestr(info, xml if info.filename == xml_name else source.read(info.filename))
    draft_hash = sha256(OUTPUT)
    blocking = [
        "The source page establishes F major, 4/4, four parts, visible lyrics, repeated sections with first/second endings, and a terminal double bar, but the OMR does not encode aligned lyrics or source-confirmed per-note shapes.",
        "The source has 23 measures per part while the retained OMR exports 23 measures per part with sparse event grouping; no direct note-for-note source mapping proves every duration, rest, repeat, or ending event.",
        "The retained OMR contains 223 note elements (222 pitches and 1 rest) and duration failures against 4/4; the source-visible lower systems and ending area are crossed by a diagonal watermark.",
        "No obscured note, lyric, repeat, ending, duration, or shape was inferred, and no authorized same-title structured candidate was available.",
    ]
    audit = {
        "queueId": "sh2025/279",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "279",
        "title": "Mink Hollow",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=279",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/279-Mink-Hollow/279.jpg",
            "sourceImagePath": "work/omr/279-mink-hollow/source.jpg",
            "sourceImageSha256": source_image_hash,
            "immutable": True,
            "sourceImageVariants": [{"path": "work/source-images/2025/279-mink-hollow-fb325f175f.jpg", "sha256": retained_hash, "relationship": "retained same-page copy; byte-identical to canonical source image"}],
            "directObservations": {
                "header": "MINK HOLLOW. C.M.D.",
                "key": "F major",
                "mode": "major",
                "timeSignature": "4/4",
                "meter": "Common Meter Double (8,6,8,6,8,6,8,6)",
                "composer": "William Bengo Collyer, 1812",
                "lyricist": "Isaac Watts, 1707; Benjamin Beddome, 1794",
                "arranger": "Keillor Mose, 2023",
                "parts": 4,
                "clefOrder": ["treble", "treble", "treble", "bass"],
                "sourceMeasuresByPart": {"P1": 23, "P2": 23, "P3": 23, "P4": 23},
                "sourceLyricsVisible": True,
                "sourceRepeatEnding": "repeated sections with first/second endings and terminal double bar visible",
                "watermarkAffectedRegions": "lower systems, lyric lines, and ending region",
            },
        },
        "inputOmr": {
            "path": "work/omr/279-mink-hollow/source.mxl",
            "sha256": source_hash,
            "status": "retained-source-scan-omr",
            "parts": int(summary["parts"]),
            "measuresByPart": summary["measuresByPart"],
            "eventsByPart": summary["eventsByPart"],
            "pitchedEvents": sum(len(events) for events in source_events.values()) - int(summary["restEvents"]),
            "restEvents": int(summary["restEvents"]),
            "noteheads": 0,
            "lyrics": 0,
            "timeSignatures": 0,
            "durationAudit": summary["durationFailuresAgainst4_4"],
            "statusReason": "The canonical OMR matches the source measure count but has sparse duration grouping and no source-confirmed lyric, meter, repeat/ending, or shape encoding.",
        },
        "candidateWitness": {"status": "none-authorized", "sameTitleStructuredCandidate": False},
        "correctedDraft": {
            "path": "work/omr/autonomous-transcriptions/2025/279-mink-hollow-source-correction-v2.mxl",
            "sha256": draft_hash,
            "summary": summary,
            "eventStreamPreservedFromInput": source_events == corrected_events,
            "sourceEventSignature": source_events,
            "correctedEventSignature": corrected_events,
            "corrections": ["source F-major key and explicit major mode", "source 4/4 time signature", "four-shape noteheads added to every retained pitched event", "canonical and byte-identical retained source-image provenance recorded", "lyrics, repeats, endings, missing events, and uncertain durations intentionally omitted"],
        },
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "sourceScanPath": "work/omr/279-mink-hollow/source.jpg",
            "sourceScanSha256": source_image_hash,
            "retainedSourceCopyInspected": "work/source-images/2025/279-mink-hollow-fb325f175f.jpg",
            "method": "full-resolution direct source-image inspection plus canonical OMR event, duration, topology, lyric, repeat, ending, and provenance audit; no alternate witness used",
            "blockingFindings": blocking,
        },
        "blockingFindings": blocking,
        "blockingReason": "Autonomous promotion is blocked because the OMR is not proven note-for-note against the 23-measure source, its durations are not validated against 4/4, and it omits lyrics, complete repeat/ending semantics, and source-confirmed per-note shapes. The diagonal watermark intersects the lower notation and lyric/ending region. The derivative preserves detected events and adds source metadata/shapes without fabrication.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-watermark-obscured-structure; retain-corrected-draft-only",
        "autonomousDisposition": "Blocked autonomously; no generic human handoff and no authoritative corpus promotion.",
        "policy": "Immutable 2025 source remains authoritative. OMR and derived shape tags are review work product only and cannot authorize promotion without direct event-level, lyric, repeat/ending, and shape evidence.",
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/279", "status": audit["comparisonStatus"], "sourceImageSha256": source_image_hash, "retainedSourceImageSha256": retained_hash, "inputOmrSha256": source_hash, "correctedDraftSha256": draft_hash, "summary": summary, "audit": str(AUDIT.relative_to(ROOT))}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
