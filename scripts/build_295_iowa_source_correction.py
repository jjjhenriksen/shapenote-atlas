#!/usr/bin/env python3
"""Create a source-derived, fail-closed correction for Sacred Harp 295."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/omr/295-iowa/source.mxl"
SOURCE_IMAGE = ROOT / "work/omr/295-iowa/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/295-iowa-e64f240632.jpg"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/295-iowa-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/295-iowa-autonomous-comparison.json"

# E minor uses the relative G-major four-shape spelling in the source system:
# G=fa, A=sol, B=la, C=fa, D=sol, E=la, F-sharp=mi.
SHAPES = {"A": "sol", "B": "la", "C": "fa", "D": "sol", "E": "la", "F": "mi", "G": "fa"}


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


def transform() -> tuple[bytes, dict[str, object], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    root = source_xml()
    source_events = event_signature(root)
    summary: dict[str, object] = {"parts": 0, "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "restEvents": 0, "shapeNoteheadsAdded": 0, "emptyMeasures": 0, "durationFailuresAgainst6_4": {}, "sourceBarlines": 0, "lyricsRetained": 0}
    parts = children(root, "part")
    summary["parts"] = len(parts)
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = children(part, "measure")
        summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
        summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
        summary["emptyMeasures"] = int(summary["emptyMeasures"]) + sum(not children(measure, "note") for measure in measures)
        summary["sourceBarlines"] = int(summary["sourceBarlines"]) + sum(len(children(measure, "barline")) for measure in measures)
        summary["durationFailuresAgainst6_4"][part_id] = [f"m{measure.attrib.get('number')}={duration_end(measure)}" for measure in measures if duration_end(measure) != 12]  # type: ignore[index]
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
            ET.SubElement(key, "fifths").text = "1"
            ET.SubElement(key, "mode").text = "minor"
            time = first(attributes, "time")
            if time is None:
                time = ET.Element("time")
                attributes.insert(2, time)
            for old in children(time, "beats") + children(time, "beat-type"):
                time.remove(old)
            ET.SubElement(time, "beats").text = "6"
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
        "atlas-queue-id": "sh2025/295",
        "atlas-transcription-status": "autonomously-blocked",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-image": "work/omr/295-iowa/source.jpg",
        "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
        "atlas-retained-source-copy": "work/source-images/2025/295-iowa-e64f240632.jpg",
        "atlas-retained-source-copy-sha256": sha256(RETAINED_IMAGE),
        "atlas-source-key": "E minor",
        "atlas-source-mode": "minor",
        "atlas-source-time-signature": "6/4",
        "atlas-source-meter": "8s, 7s & 4s.",
        "atlas-source-title-and-credits": "IOWA. 8s, 7s & 4s.; John Newton, 1774; P. Dan Brittain, 2002",
        "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible E-minor key; not source-verified per event",
        "atlas-lyrics": "omitted; source lyrics are visible but retained OMR has no directly aligned lyric underlay",
        "atlas-provenance-policy": "immutable 2025 source image is authoritative; no authorized same-title structured candidate exists; this OMR derivative is evidence only",
        "atlas-blocker": "The immutable page visibly prints IOWA. 8s, 7s & 4s., E minor, 6/4, four vocal parts, lyrics, sectional bars, and terminal repeat-style bars. The retained OMR has six measures per part but sparse duration/event grouping, no aligned lyrics, and no shape tags. A diagonal DO NOT COPY watermark crosses the middle systems. No notation was synthesized.",
    }
    for key, value in provenance.items():
        set_field(identification, key, value)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), summary, source_events, event_signature(root)


def main() -> int:
    source_hash = sha256(SOURCE)
    image_hash = sha256(SOURCE_IMAGE)
    retained_hash = sha256(RETAINED_IMAGE)
    xml, summary, source_events, corrected_events = transform()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        xml_name = next(item for item in source.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        for info in source.infolist():
            target.writestr(info, xml if info.filename == xml_name else source.read(info.filename))
    draft_hash = sha256(OUTPUT)
    blocking = [
        "The source page establishes E minor, 6/4, four parts, visible lyrics, sectional bars, and terminal repeat-style bars, but the retained OMR has no directly aligned lyrics or source-confirmed per-note shapes.",
        "The retained OMR matches the six-measure-per-part nominal topology but its duration/event grouping fails against 6/4 in every part; no direct note-for-note source mapping proves all rhythm and rest placement.",
        "The source-visible middle systems are crossed by a diagonal watermark; no obscured note, lyric, repeat, ending, duration, or shape was inferred.",
        "The OMR records G-major-compatible key data while the page visibly prints E minor; the derivative corrects metadata without silently rewriting pitch events.",
        "No authorized same-title structured candidate was available, so no alternate tune or edition was used.",
    ]
    audit = {
        "queueId": "sh2025/295", "edition": "Sacred Harp, 2025 Edition", "songNo": "295", "title": "Iowa", "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {"sourcePageUrl": "https://fasola.org/indexes/2025/?p=295", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/295-Iowa/295.jpg", "sourceImagePath": "work/omr/295-iowa/source.jpg", "sourceImageSha256": image_hash, "immutable": True, "sourceImageVariants": [{"path": "work/source-images/2025/295-iowa-e64f240632.jpg", "sha256": retained_hash, "relationship": "retained same-page copy; distinct JPEG bytes"}], "directObservations": {"header": "IOWA. 8s, 7s & 4s.", "key": "E minor", "mode": "minor", "timeSignature": "6/4", "meter": "8s, 7s & 4s.", "composer": "P. Dan Brittain, 2002", "lyricist": "John Newton, 1774", "parts": 4, "clefOrder": ["treble", "treble", "treble", "bass"], "sourceMeasuresByPart": {"P1": 6, "P2": 6, "P3": 6, "P4": 6}, "sourceLyricsVisible": True, "sourceRepeatEnding": "sectional bars and terminal repeat-style bars visible", "watermarkAffectedRegions": "middle systems and lyric-adjacent notation"}},
        "inputOmr": {"path": "work/omr/295-iowa/source.mxl", "sha256": source_hash, "status": "retained-source-scan-omr", "parts": int(summary["parts"]), "measuresByPart": summary["measuresByPart"], "eventsByPart": summary["eventsByPart"], "pitchedEvents": int(summary["pitchedEvents"]), "restEvents": int(summary["restEvents"]), "noteheads": 0, "lyrics": 0, "timeSignatures": 0, "durationAudit": summary["durationFailuresAgainst6_4"], "statusReason": "The canonical OMR has six measures per part but sparse duration/event grouping, conflicting key metadata, no aligned lyrics, and no shape tags."},
        "candidateWitness": {"status": "none-authorized", "sameTitleStructuredCandidate": False},
        "correctedDraft": {"path": "work/omr/autonomous-transcriptions/2025/295-iowa-source-correction-v2.mxl", "sha256": draft_hash, "summary": summary, "eventStreamPreservedFromInput": source_events == corrected_events, "sourceEventSignature": source_events, "correctedEventSignature": corrected_events, "corrections": ["source E-minor key and explicit minor mode", "source 6/4 time signature", "four-shape noteheads added to every retained pitched event", "canonical and distinct retained source-image provenance recorded", "lyrics, repeat semantics, missing events, and uncertain durations intentionally omitted"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": "work/omr/295-iowa/source.jpg", "sourceScanSha256": image_hash, "retainedSourceCopyInspected": "work/source-images/2025/295-iowa-e64f240632.jpg", "method": "full-resolution direct source-image inspection plus canonical OMR event, duration, topology, lyric, repeat, and provenance audit; no alternate witness used", "blockingFindings": blocking},
        "blockingFindings": blocking, "blockingReason": "Autonomous promotion is blocked because the OMR is not proven note-for-note against the source, duration grouping fails against 6/4 in every part, and lyrics, complete repeat structure, and per-note shapes are not source-proven. The watermark intersects middle notation. The derivative preserves detected events and adds source metadata/shapes without fabrication.", "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-watermark-obscured-structure; retain-corrected-draft-only", "autonomousDisposition": "Blocked autonomously; no generic human handoff and no authoritative corpus promotion.", "policy": "Immutable 2025 source remains authoritative. OMR and derived shape tags are review work product only and cannot authorize promotion without direct event-level, lyric, repeat, and shape evidence.",
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/295", "status": audit["comparisonStatus"], "sourceImageSha256": image_hash, "retainedSourceImageSha256": retained_hash, "inputOmrSha256": source_hash, "correctedDraftSha256": draft_hash, "summary": summary, "audit": str(AUDIT.relative_to(ROOT))}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
