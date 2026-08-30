#!/usr/bin/env python3
"""Create a source-derived, fail-closed Africa derivative."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/omr/178t-africa/source.mxl"
SOURCE_IMAGE = ROOT / "work/omr/178t-africa/source.jpg"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/178t-africa-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/178t-africa-source-correction-v2-comparison.json"

# E-flat major: Eb=fa, F=sol, G=la, Ab=fa, Bb=sol, C=la, D=mi.
# Tags are derived from retained OMR pitch steps and are not proof that the
# OMR pitch stream itself is source-correct.
SHAPES = {"A": "fa", "B": "sol", "C": "la", "D": "mi", "E": "fa", "F": "sol", "G": "la"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(parent: ET.Element | None, wanted: str) -> list[ET.Element]:
    return [child for child in parent if local_name(child.tag) == wanted] if parent is not None else []


def first(parent: ET.Element | None, wanted: str) -> ET.Element | None:
    return next(iter(children(parent, wanted)), None)


def text(parent: ET.Element | None, wanted: str, default: str = "") -> str:
    item = first(parent, wanted)
    return item.text.strip() if item is not None and item.text else default


def put_field(identification: ET.Element, key: str, value: str) -> None:
    miscellaneous = first(identification, "miscellaneous")
    if miscellaneous is None:
        miscellaneous = ET.SubElement(identification, "miscellaneous")
    for old in [item for item in children(miscellaneous, "miscellaneous-field") if item.attrib.get("name") == key]:
        miscellaneous.remove(old)
    ET.SubElement(miscellaneous, "miscellaneous-field", {"name": key}).text = value


def duration_end(measure: ET.Element) -> int:
    cursor = 0
    maximum = 0
    for item in measure:
        item_name = local_name(item.tag)
        duration = first(item, "duration")
        units = int(duration.text) if duration is not None and duration.text and duration.text.isdigit() else 0
        if item_name == "note":
            if first(item, "chord") is None:
                cursor += units
            maximum = max(maximum, cursor)
        elif item_name == "backup":
            cursor -= units
        elif item_name == "forward":
            cursor += units
    return maximum


def event_signature(root: ET.Element) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for part in children(root, "part"):
        rows: list[dict[str, str]] = []
        for measure in children(part, "measure"):
            for note in children(measure, "note"):
                pitch = first(note, "pitch")
                pitch_value = "rest" if first(note, "rest") is not None else "unknown"
                if pitch is not None:
                    pitch_value = ":".join([text(pitch, "step"), text(pitch, "alter", "0"), text(pitch, "octave")])
                rows.append({
                    "measure": measure.attrib.get("number", ""),
                    "pitch": pitch_value,
                    "duration": text(note, "duration"),
                    "type": text(note, "type"),
                    "voice": text(note, "voice"),
                })
        result[part.attrib.get("id", "")] = rows
    return result


def barline_signature(root: ET.Element) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for part in children(root, "part"):
        rows: list[dict[str, str]] = []
        for measure in children(part, "measure"):
            for bar in children(measure, "barline"):
                repeat = first(bar, "repeat")
                ending = first(bar, "ending")
                rows.append({
                    "measure": measure.attrib.get("number", ""),
                    "location": bar.attrib.get("location", ""),
                    "style": text(bar, "bar-style"),
                    "repeat": repeat.attrib.get("direction", "") if repeat is not None else "",
                    "ending": ending.attrib.get("number", "") if ending is not None else "",
                })
        result[part.attrib.get("id", "")] = rows
    return result


def read_xml(path: Path) -> tuple[str, ET.Element]:
    with zipfile.ZipFile(path) as archive:
        xml_name = next(item for item in archive.namelist() if item.lower().endswith(".xml") and not item.lower().startswith("meta-inf/"))
        return xml_name, ET.fromstring(archive.read(xml_name))


def transform() -> tuple[str, bytes, dict[str, object], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    xml_name, root = read_xml(SOURCE)
    source_events = event_signature(root)
    source_barlines = barline_signature(root)
    parts = children(root, "part")
    summary: dict[str, object] = {
        "parts": len(parts),
        "measuresByPart": {},
        "eventsByPart": {},
        "pitchedEvents": 0,
        "restEvents": 0,
        "shapeNoteheadsAdded": 0,
        "lyricsRetained": 0,
        "emptyMeasures": 0,
        "durationEndByPart": {},
        "durationValidationStatus": "blocked-missing-or-empty-divisions-in-retained-OMR",
        "sourceBarlines": source_barlines,
    }
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = children(part, "measure")
        summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
        summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
        summary["emptyMeasures"] = int(summary["emptyMeasures"]) + sum(not children(measure, "note") for measure in measures)
        summary["durationEndByPart"][part_id] = {  # type: ignore[index]
            measure.attrib.get("number", ""): duration_end(measure) for measure in measures
        }
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
            clock = first(attributes, "time")
            if clock is None:
                clock = ET.Element("time")
                key_index = next((i for i, item in enumerate(attributes) if local_name(item.tag) == "key"), 1)
                attributes.insert(key_index + 1, clock)
            for old in children(clock, "beats") + children(clock, "beat-type"):
                clock.remove(old)
            ET.SubElement(clock, "beats").text = "3"
            ET.SubElement(clock, "beat-type").text = "2"
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
                stem_index = next((i for i, item in enumerate(note) if local_name(item.tag) == "stem"), len(note))
                note.insert(stem_index, notehead)
                summary["pitchedEvents"] = int(summary["pitchedEvents"]) + 1
                summary["shapeNoteheadsAdded"] = int(summary["shapeNoteheadsAdded"]) + 1
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    fields = {
        "atlas-queue-id": "sh2025/178t",
        "atlas-transcription-status": "autonomously-blocked",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-image": str(SOURCE_IMAGE.relative_to(ROOT)),
        "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
        "atlas-source-key": "E-flat major",
        "atlas-source-mode": "major",
        "atlas-source-time-signature": "3/2",
        "atlas-source-meter": "Common Meter (8,6,8,6)",
        "atlas-source-repeat-ending": "Terminal double bar is visible on the immutable page; no repeat or numbered ending was encoded because none is source-proven in the retained OMR",
        "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible E-flat-major key; not source-verified per event",
        "atlas-lyrics": "omitted; retained OMR contains no directly aligned lyric underlay",
        "atlas-provenance-policy": "immutable 2025 scan is authoritative; no same-title structured candidate is authorized; this OMR derivative is evidence only",
        "atlas-blocker": "The source page visibly prints AFRICA. C.M., E-flat Major, Isaac Watts 1707, four vocal parts, three lyric stanzas, and a terminal double bar. Retained OMR exports 11 measures per part while Audiveris logged 12 raw measures; it has sparse events, no usable divisions, no lyrics, no shapes, and no complete source structure. Its one-flat key and 3/4 meter conflict with the source-visible E-flat major and 3/2. No notation was synthesized.",
    }
    for key, value in fields.items():
        put_field(identification, key, value)
    return xml_name, ET.tostring(root, encoding="utf-8", xml_declaration=True), summary, source_events, source_barlines


def main() -> int:
    source_hash = sha256(SOURCE)
    image_hash = sha256(SOURCE_IMAGE)
    xml_name, xml, summary, source_events, source_barlines = transform()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml if info.filename == xml_name else source.read(info.filename))
    draft_hash = sha256(OUTPUT)
    _, corrected_root = read_xml(OUTPUT)
    corrected_events = event_signature(corrected_root)
    corrected_barlines = barline_signature(corrected_root)
    blocking = [
        "The immutable scan visibly prints AFRICA. C.M., E-flat Major, Isaac Watts 1707, William Billings 1770, four vocal parts, three lyric stanzas, and a terminal double bar.",
        "The retained source OMR exports 11 measure elements per part with event counts P1=23, P2=20, P3=24, P4=12 and 11 empty measures; Audiveris reports 12 raw measures, so complete source topology and event coverage are not established.",
        "The retained OMR has empty or unusable divisions and cannot provide a reliable 3/2 duration audit; its per-measure duration ends are retained in durationEndByPart.",
        "The retained OMR has no lyrics, four-shape tags, or complete structural semantics. Its one-flat key and 3/4 time signature conflict with the source-visible E-flat-major and 3/2 header; the derivative records the scan and does not trust the stale OMR metadata.",
        "No authorized same-title structured candidate exists, so no alternate tune or edition was used to fill missing notation.",
        "No separate retained work/source-images/2025 duplicate matching 178t Africa exists; the immutable work/omr/178t-africa/source.jpg is the canonical local visual witness.",
    ]
    audit = {
        "queueId": "sh2025/178t",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "178t",
        "title": "Africa",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=178t",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/178t-Africa/178t.jpg",
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)),
            "sourceImageSha256": image_hash,
            "immutable": True,
            "directObservations": {
                "header": "AFRICA. C.M.",
                "composer": "Isaac Watts, 1707",
                "arranger": "William Billings, 1770",
                "key": "E-flat major",
                "mode": "major",
                "timeSignature": "3/2",
                "meter": "Common Meter (8,6,8,6)",
                "parts": 4,
                "systems": 1,
                "lyricsVisible": True,
                "stanzaLinesVisible": 3,
                "repeatBarsVisible": False,
                "endingsVisible": False,
                "terminalDoubleBarVisible": True,
                "sourceMeasureCountStatus": "Audiveris direct page analysis reports 12 raw measures; exported OMR contains 11 per part and does not establish complete source topology",
            },
            "retainedSourceImageMissing": {"expectedGlob": "work/source-images/2025/*178t*africa*.jpg", "status": "not-found"},
        },
        "inputOmr": {"path": "work/omr/178t-africa/source.mxl", "sha256": source_hash, "status": "retained-source-scan-omr"},
        "candidateWitness": {"status": "none-authorized", "sameTitleStructuredCandidate": False},
        "correctedDraft": {
            "path": "work/omr/autonomous-transcriptions/2025/178t-africa-source-correction-v2.mxl",
            "sha256": draft_hash,
            "summary": summary,
            "eventStreamPreservedFromInput": True,
            "sourceEventSignature": source_events,
            "correctedEventSignature": corrected_events,
            "sourceBarlines": source_barlines,
            "correctedBarlines": corrected_barlines,
            "corrections": [
                "source E-flat-major key and explicit major mode",
                "source 3/2 time signature",
                "four-shape noteheads derived for every retained pitched event",
                "source lyric and terminal-bar visibility recorded in provenance",
                "lyrics and uncertain structural details intentionally omitted",
            ],
        },
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)),
            "sourceScanSha256": image_hash,
            "method": "full-resolution visual inspection of immutable source scan plus XML event/duration/topology/barline audit; no alternate witness used",
            "blockingFindings": blocking,
        },
        "blockingReason": "Autonomous promotion is blocked by incomplete event coverage, unresolved source topology, unusable OMR divisions/duration proof, absent direct lyrics/shapes/structural evidence, stale conflicting key/meter metadata, and no authorized structured witness. The derivative preserves detected events and adds source metadata/derived shapes without fabrication.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-no-authorized-candidate; retain-corrected-draft-only",
        "policy": "Immutable 2025 source remains authoritative. This corrected derivative is not an authoritative corpus asset.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/178t", "status": audit["comparisonStatus"], "sourceImageSha256": image_hash, "inputOmrSha256": source_hash, "correctedDraftSha256": draft_hash, "summary": summary, "audit": str(AUDIT.relative_to(ROOT))}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
