#!/usr/bin/env python3
"""Create a source-derived, fail-closed correction for Sacred Harp 508."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/omr/508-sermon-on-the-mount/source.mxl"
SOURCE_IMAGE = ROOT / "work/omr/508-sermon-on-the-mount/source.jpg"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/508-sermon-on-the-mount-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/508-sermon-on-the-mount-source-correction-v2-comparison.json"

# Four-shape spelling for the source-visible E-flat-major key. This annotates
# only OMR-retained pitches and does not assert their note-level accuracy.
SHAPES = {"C": "la", "D": "mi", "E": "fa", "F": "sol", "G": "la", "A": "fa", "B": "sol"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(parent: ET.Element | None, wanted: str) -> list[ET.Element]:
    return [item for item in parent if name(item.tag) == wanted] if parent is not None else []


def first(parent: ET.Element | None, wanted: str) -> ET.Element | None:
    return next(iter(children(parent, wanted)), None)


def field(identification: ET.Element, key: str, value: str) -> None:
    misc = first(identification, "miscellaneous")
    if misc is None:
        misc = ET.SubElement(identification, "miscellaneous")
    for old in [item for item in children(misc, "miscellaneous-field") if item.attrib.get("name") == key]:
        misc.remove(old)
    ET.SubElement(misc, "miscellaneous-field", {"name": key}).text = value


def event_signature(root: ET.Element) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for part in children(root, "part"):
        events: list[dict[str, str]] = []
        for measure in children(part, "measure"):
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                if pitch is None:
                    pitch_value = "rest" if first(note, "rest") is not None else "unknown"
                else:
                    pitch_value = ":".join(
                        [
                            (first(pitch, "step").text or "") if first(pitch, "step") is not None else "",
                            (first(pitch, "alter").text or "0") if first(pitch, "alter") is not None else "0",
                            (first(pitch, "octave").text or "") if first(pitch, "octave") is not None else "",
                        ]
                    )
                duration = first(note, "duration")
                note_type = first(note, "type")
                voice = first(note, "voice")
                events.append({"measure": measure.attrib.get("number", ""), "pitch": pitch_value, "duration": duration.text if duration is not None and duration.text else "", "type": note_type.text if note_type is not None and note_type.text else "", "voice": voice.text if voice is not None and voice.text else ""})
        result[part.attrib.get("id", "")] = events
    return result


def transform() -> tuple[bytes, dict[str, object], dict[str, list[dict[str, str]]]]:
    with zipfile.ZipFile(SOURCE) as archive:
        xml_name = next(item for item in archive.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        root = ET.fromstring(archive.read(xml_name))
    parts = children(root, "part")
    summary: dict[str, object] = {"parts": len(parts), "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "restEvents": 0, "shapeNoteheadsAdded": 0, "emptyMeasures": 0, "sourceBarlines": 0, "lyricsRetained": 0, "inputTimeSignatures": {}, "inputKeySignatures": {}}
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = children(part, "measure")
        summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
        summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
        summary["emptyMeasures"] = int(summary["emptyMeasures"]) + sum(not children(measure, "note") for measure in measures)
        summary["sourceBarlines"] = int(summary["sourceBarlines"]) + sum(len(children(measure, "barline")) for measure in measures)
        summary["inputTimeSignatures"][part_id] = [(m.findtext("attributes/time/beats"), m.findtext("attributes/time/beat-type")) for m in measures if first(m.find("attributes"), "time") is not None]  # type: ignore[index]
        summary["inputKeySignatures"][part_id] = [m.findtext("attributes/key/fifths") for m in measures if first(m.find("attributes"), "key") is not None]  # type: ignore[index]
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
            ET.SubElement(key, "fifths").text = "-3"
            ET.SubElement(key, "mode").text = "major"
            # The source visibly changes meter across sections. Exact change
            # positions are not recoverable from this OMR, so retain its time
            # elements and record the authoritative source sequence in the
            # provenance fields below instead of inventing a global meter.
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                if pitch is None:
                    if first(note, "rest") is not None:
                        summary["restEvents"] = int(summary["restEvents"]) + 1
                    continue
                step = first(pitch, "step")
                if step is None or not step.text or step.text.strip().upper() not in SHAPES:
                    continue
                for old in children(note, "notehead"):
                    note.remove(old)
                notehead = ET.Element("notehead")
                notehead.text = SHAPES[step.text.strip().upper()]
                stem_index = next((index for index, item in enumerate(note) if name(item.tag) == "stem"), len(note))
                note.insert(stem_index, notehead)
                summary["pitchedEvents"] = int(summary["pitchedEvents"]) + 1
                summary["shapeNoteheadsAdded"] = int(summary["shapeNoteheadsAdded"]) + 1
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    provenance = {
        "atlas-queue-id": "sh2025/508",
        "atlas-transcription-status": "autonomously-blocked",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-image": "work/omr/508-sermon-on-the-mount/source.jpg",
        "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
        "atlas-source-key": "E-flat major",
        "atlas-source-mode": "major",
        "atlas-source-time-signatures": "Source visibly uses changing sections: 2/2, 2/4, 6/8, 3/4, and 4/4; exact per-measure change positions are not established by the retained OMR",
        "atlas-source-meter": "Irregular/prose text setting; do not collapse to one global meter",
        "atlas-source-title-and-credits": "SERMON ON THE MOUNT.; Matthew 5:1-3, 5, 8.; A. M. Cagle, 1959",
        "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible E-flat-major key; not source-verified per event",
        "atlas-lyrics": "omitted; source lyrics are visible but retained OMR has no directly aligned lyric underlay",
        "atlas-provenance-policy": "immutable 2025 scan is authoritative; no same-title structured candidate is authorized; this OMR derivative is evidence only",
        "atlas-blocker": "The immutable page visibly prints SERMON ON THE MOUNT., E-flat major, changing 2/2, 2/4, 6/8, 3/4, and 4/4 sections, four vocal parts, lyrics, first/second endings, and a terminal double bar. The retained OMR exports 42 measures per part versus 43 raw source measures (14+8+12+9), has sparse events and 47 empty measures, conflicting key data, only partial 3/4 time metadata, no lyrics, no complete barlines/repeat semantics, and watermark-obscured middle notation. No notation was synthesized.",
    }
    for key, value in provenance.items():
        field(identification, key, value)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), summary, event_signature(root)


def main() -> int:
    source_hash = sha256(SOURCE)
    source_image_hash = sha256(SOURCE_IMAGE)
    xml, summary, corrected_events = transform()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml if info.filename == "source.xml" else source.read(info.filename))
    draft_hash = sha256(OUTPUT)
    with zipfile.ZipFile(SOURCE) as archive:
        source_root = ET.fromstring(archive.read("source.xml"))
    source_events = event_signature(source_root)
    blocking = [
        "The immutable scan establishes E-flat major, four parts, lyrics, first/second endings, terminal double bar, and changing 2/2, 2/4, 6/8, 3/4, and 4/4 sections; the retained OMR has only partial 3/4 metadata and no aligned lyrics or complete repeat semantics.",
        "Audiveris reports 43 raw measures across four systems (14+8+12+9), while the exported MusicXML contains 42 measures per part, so the event topology is not source-complete.",
        "The retained OMR contains 336 note elements, 332 pitched events, 4 rests, and 47 empty measures, with conflicting key signatures and rhythm failures logged at measures 23, 24, 27, 29, 35-42; no single duration target is safe because the source changes meter.",
        "The watermark intersects middle notation and lyric areas; no hidden note, lyric, repeat, ending, or meter change was inferred.",
        "No authorized exact-edition structured candidate is present for this record; alternate-edition notation was not borrowed.",
    ]
    audit = {
        "queueId": "sh2025/508", "edition": "Sacred Harp, 2025 Edition", "songNo": "508", "title": "Sermon on the Mount", "comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False,
        "sourceAuthority": {"sourcePageUrl": "https://fasola.org/indexes/2025/?p=508", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/508-Sermon-on-the-Mount/508.jpg", "sourceImagePath": "work/omr/508-sermon-on-the-mount/source.jpg", "sourceImageSha256": source_image_hash, "immutable": True, "directObservations": {"header": "SERMON ON THE MOUNT.", "key": "E-flat major", "mode": "major", "timeSignatures": ["2/2", "2/4", "6/8", "3/4", "4/4"], "meter": "Irregular/prose text setting", "parts": 4, "audiverisRawMeasures": 43, "sourceMeasuresBySystem": [14, 8, 12, 9], "sourceLyricsVisible": True, "sourceRepeatEnding": "first/second endings and terminal double bar visible", "watermarkAffectedRegions": "middle notation and lyric areas"}},
        "inputOmr": {"path": "work/omr/508-sermon-on-the-mount/source.mxl", "sha256": source_hash, "status": "retained-source-scan-omr"},
        "correctedDraft": {"path": "work/omr/autonomous-transcriptions/2025/508-sermon-on-the-mount-source-correction-v2.mxl", "sha256": draft_hash, "summary": summary, "eventStreamPreservedFromInput": True, "sourceEventSignature": source_events, "correctedEventSignature": corrected_events, "corrections": ["source E-flat-major key and explicit major mode", "source meter sequence recorded without inventing per-measure changes", "four-shape noteheads added to every retained pitched event", "provenance and fail-closed status fields added", "lyrics, repeats, endings, missing events, and meter changes intentionally omitted"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": "work/omr/508-sermon-on-the-mount/source.jpg", "sourceScanSha256": source_image_hash, "method": "full-resolution visual inspection of immutable scan plus XML event, duration, topology, and provenance audit", "blockingFindings": blocking},
        "blockingReason": "Autonomous promotion is blocked because the retained OMR is one measure short of the source topology, sparse across 47 measures, rhythmically unresolved across changing meter sections, and missing source lyrics/repeat semantics. The derivative preserves detected events and adds source key/mode/shapes without inventing notation.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness; retain-corrected-draft-only",
        "policy": "Immutable 2025 source remains authoritative. This corrected derivative is not an authoritative corpus asset.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/508", "status": audit["comparisonStatus"], "sourceImageSha256": source_image_hash, "inputOmrSha256": source_hash, "correctedDraftSha256": draft_hash, "summary": summary, "audit": str(AUDIT.relative_to(ROOT))}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
