#!/usr/bin/env python3
"""Create a source-derived, fail-closed correction for Sacred Harp 330b."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/omr/330b-chandesse/source.mxl"
SOURCE_IMAGE = ROOT / "work/omr/330b-chandesse/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/330b-chandesse-9e7b3999c8.jpg"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/330b-chandesse-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/330b-source-shape-autonomous-blocked-comparison.json"

# A minor follows the relative C-major four-shape spelling: A=la, B=mi,
# C=fa, D=sol, E=la, F=fa, G=sol.
SHAPES = {"A": "la", "B": "mi", "C": "fa", "D": "sol", "E": "la", "F": "fa", "G": "sol"}


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
                value = "rest" if first(note, "rest") is not None else "unknown"
                if pitch is not None:
                    value = ":".join([text(pitch, "step"), text(pitch, "alter", "0"), text(pitch, "octave")])
                events.append({"measure": measure.attrib.get("number", ""), "pitch": value, "duration": text(note, "duration"), "type": text(note, "type"), "voice": text(note, "voice")})
        result[part.attrib.get("id", "")] = events
    return result


def main() -> int:
    root = source_xml()
    source_events = event_signature(root)
    summary: dict[str, object] = {"parts": 0, "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "restEvents": 0, "shapeNoteheadsAdded": 0, "emptyMeasures": 0, "durationFailuresAgainst4_4": {}, "sourceBarlines": 0, "lyricsRetained": 0}
    parts = children(root, "part")
    summary["parts"] = len(parts)
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = children(part, "measure")
        summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
        summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
        summary["emptyMeasures"] = int(summary["emptyMeasures"]) + sum(not children(measure, "note") for measure in measures)
        summary["sourceBarlines"] = int(summary["sourceBarlines"]) + sum(len(children(measure, "barline")) for measure in measures)
        summary["durationFailuresAgainst4_4"][part_id] = [f"m{measure.attrib.get('number')}={duration_end(measure)}" for measure in measures if duration_end(measure) != 8]  # type: ignore[index]
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
            ET.SubElement(key, "fifths").text = "0"
            ET.SubElement(key, "mode").text = "minor"
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
                shape = SHAPES.get(text(pitch, "step").upper())
                if shape is None:
                    continue
                for old in children(note, "notehead"):
                    note.remove(old)
                notehead = ET.Element("notehead")
                notehead.text = shape
                stem_index = next((index for index, item in enumerate(note) if local(item.tag) == "stem"), len(note))
                note.insert(stem_index, notehead)
                summary["pitchedEvents"] = int(summary["pitchedEvents"]) + 1
                summary["shapeNoteheadsAdded"] = int(summary["shapeNoteheadsAdded"]) + 1
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    fields = {
        "atlas-queue-id": "sh2025/330b", "atlas-transcription-status": "autonomously-blocked", "atlas-review-status": "autonomously-blocked-source-derived-draft", "atlas-safe-to-promote": "false", "atlas-source-image": "work/omr/330b-chandesse/source.jpg", "atlas-source-image-sha256": sha256(SOURCE_IMAGE), "atlas-retained-source-copy": "work/source-images/2025/330b-chandesse-9e7b3999c8.jpg", "atlas-retained-source-copy-sha256": sha256(RETAINED_IMAGE), "atlas-source-key": "A minor", "atlas-source-mode": "minor", "atlas-source-time-signature": "4/4", "atlas-source-meter": "Common Meter Double (8,6,8,6,8,6,8,6)", "atlas-source-title-and-credits": "CHANDESSE. C.M.D.; Isaac Watts, 1719; Frédéric Eymard, 2020", "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible A-minor key; not source-verified per event", "atlas-lyrics": "omitted; source lyrics are visible but retained OMR has no directly aligned lyric underlay", "atlas-provenance-policy": "immutable 2025 source image is authoritative; no authorized same-title structured candidate exists; this OMR derivative is evidence only", "atlas-blocker": "The immutable page visibly prints CHANDESSE. C.M.D., A minor, 4/4, four vocal parts, lyrics, sectional repeat, and first/second endings. The retained OMR has 23 measures per part but sparse duration/event grouping, no aligned lyrics, and no shape tags. A diagonal DO NOT COPY watermark intersects the second-system notation and lyrics. No notation was synthesized.",
    }
    for key, value in fields.items():
        set_field(identification, key, value)
    corrected_events = event_signature(root)
    if corrected_events != source_events:
        raise RuntimeError("metadata/shape correction changed the source OMR event stream")
    xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        xml_name = next(item for item in source.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        for info in source.infolist():
            target.writestr(info, xml if info.filename == xml_name else source.read(info.filename))
    draft_hash = sha256(OUTPUT)
    blocking = ["The source page establishes A minor, 4/4, four parts, visible lyrics, sectional repeat, and first/second endings, but the retained OMR has no aligned lyrics or source-confirmed per-note shapes.", "The source has 23 measures per part while the retained OMR has sparse event/duration grouping; no direct note-for-note source mapping proves every rhythm, repeat, or ending event.", "The diagonal watermark intersects second-system notation and lyric regions; no obscured note, lyric, repeat, ending, duration, or shape was inferred.", "No authorized same-title structured candidate was available, so no alternate tune or edition was used."]
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    audit.update({"comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False})
    audit["sourceAuthority"] = {"sourcePageUrl": "https://fasola.org/indexes/2025/?p=330b", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/330b-Chandesse/330b.jpg", "sourceImagePath": "work/omr/330b-chandesse/source.jpg", "sourceImageSha256": sha256(SOURCE_IMAGE), "immutable": True, "sourceImageVariants": [{"path": "work/source-images/2025/330b-chandesse-9e7b3999c8.jpg", "sha256": sha256(RETAINED_IMAGE), "relationship": "retained same-page copy; byte-identical to canonical source image"}], "directObservations": {"header": "CHANDESSE. C.M.D.", "key": "A minor", "mode": "minor", "timeSignature": "4/4", "meter": "Common Meter Double (8,6,8,6,8,6,8,6)", "composer": "Isaac Watts, 1719", "arranger": "Frédéric Eymard, 2020", "parts": 4, "clefOrder": ["treble", "treble", "treble", "bass"], "sourceMeasuresByPart": {"P1": 23, "P2": 23, "P3": 23, "P4": 23}, "sourceLyricsVisible": True, "sourceRepeatEnding": "sectional repeat with first/second endings visible", "watermarkAffectedRegions": "second-system notation and lyric region"}}
    audit["inputOmr"] = {"path": "work/omr/330b-chandesse/source.mxl", "sha256": sha256(SOURCE), "status": "retained-source-scan-omr", "parts": int(summary["parts"]), "measuresByPart": summary["measuresByPart"], "eventsByPart": summary["eventsByPart"], "pitchedEvents": int(summary["pitchedEvents"]), "restEvents": int(summary["restEvents"]), "noteheads": 0, "lyrics": 0, "timeSignatures": 0, "durationAudit": summary["durationFailuresAgainst4_4"], "statusReason": "The canonical OMR has 23 measures per part but sparse duration/event grouping, no aligned lyrics, and no shape tags."}
    audit["candidateWitness"] = {"status": "none-authorized", "sameTitleStructuredCandidate": False}
    audit["correctedDraft"] = {"path": str(OUTPUT.relative_to(ROOT)), "sha256": draft_hash, "summary": summary, "eventStreamPreservedFromInput": True, "sourceEventSignature": source_events, "correctedEventSignature": corrected_events, "corrections": ["source A-minor key and explicit minor mode", "source 4/4 time signature", "four-shape noteheads added to every retained pitched event", "canonical and byte-identical retained source-image provenance recorded", "lyrics, repeats, endings, missing events, and uncertain durations intentionally omitted"]}
    audit["comparisonEvidence"] = {"sourceScanInspected": True, "sourceScanPath": "work/omr/330b-chandesse/source.jpg", "sourceScanSha256": sha256(SOURCE_IMAGE), "retainedSourceCopyInspected": "work/source-images/2025/330b-chandesse-9e7b3999c8.jpg", "method": "full-resolution direct source-image inspection plus canonical OMR event, duration, topology, lyric, repeat/ending, and provenance audit; no alternate witness used", "blockingFindings": blocking}
    audit["blockingFindings"] = blocking
    audit["blockingReason"] = "Autonomous promotion is blocked because the retained OMR is not proven note-for-note against the 23-measure source, duration grouping is unresolved against 4/4, and lyrics, complete repeat/endings, and per-note shapes are not source-proven. The watermark intersects the second system. The derivative preserves detected events and adds source metadata/shapes without fabrication."
    audit["nextAction"] = "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-watermark-obscured-structure; retain-corrected-draft-only"
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/330b", "status": audit["comparisonStatus"], "sourceImageSha256": sha256(SOURCE_IMAGE), "retainedSourceImageSha256": sha256(RETAINED_IMAGE), "inputOmrSha256": sha256(SOURCE), "correctedDraftSha256": draft_hash, "summary": summary, "audit": str(AUDIT.relative_to(ROOT))}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
