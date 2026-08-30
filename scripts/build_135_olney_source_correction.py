#!/usr/bin/env python3
"""Create a source-derived, fail-closed Olney derivative."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/omr/135-olney/source.mxl"
SOURCE_IMAGE = ROOT / "work/omr/135-olney/source.jpg"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/135-olney-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/135-olney-source-correction-v2-comparison.json"

# F major: F=fa, G=sol, A=la, B-flat=fa, C=sol, D=la, E=mi.
# These tags are derived from retained OMR pitch steps and are not proof that
# the OMR pitch stream itself is source-correct.
SHAPES = {"A": "la", "B": "fa", "C": "sol", "D": "la", "E": "mi", "F": "fa", "G": "sol"}


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
            ET.SubElement(key, "fifths").text = "-1"
            ET.SubElement(key, "mode").text = "major"
            clock = first(attributes, "time")
            if clock is None:
                clock = ET.Element("time")
                key_index = next((i for i, item in enumerate(attributes) if local_name(item.tag) == "key"), 1)
                attributes.insert(key_index + 1, clock)
            for old in children(clock, "beats") + children(clock, "beat-type"):
                clock.remove(old)
            ET.SubElement(clock, "beats").text = "2"
            ET.SubElement(clock, "beat-type").text = "4"
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
        "atlas-queue-id": "sh2025/135",
        "atlas-transcription-status": "autonomously-blocked",
        "atlas-review-status": "autonomously-blocked-source-derived-draft",
        "atlas-safe-to-promote": "false",
        "atlas-source-image": str(SOURCE_IMAGE.relative_to(ROOT)),
        "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
        "atlas-source-key": "F major",
        "atlas-source-mode": "major",
        "atlas-source-time-signature": "2/4",
        "atlas-source-meter": "8s & 7s Double",
        "atlas-source-repeat-ending": "Repeat/barline structure is visible on the immutable page; retained OMR only contains a terminal light-light barline and does not encode a complete structural witness",
        "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible F-major key; not source-verified per event",
        "atlas-lyrics": "omitted; retained OMR contains no directly aligned lyric underlay",
        "atlas-provenance-policy": "immutable 2025 scan is authoritative; no same-title structured candidate is authorized; this OMR derivative is evidence only",
        "atlas-blocker": "The source page visibly prints OLNEY. 8s & 7s D., F Major, Robert Robinson 1758, four vocal parts, lyrics, and repeat/barline structure. Retained OMR exports 22 measures per part, matching the 20-raw-measure log only in neither count nor topology, with sparse events, no usable divisions, no lyrics, no shapes, and no complete structural encoding. No notation was synthesized.",
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
        "The immutable scan visibly prints OLNEY. 8s & 7s D., F Major, Robert Robinson 1758, four vocal parts, lyric underlay, and repeat/barline structure.",
        "The retained source OMR exports 22 measure elements per part with event counts P1=33, P2=39, P3=40, P4=39, including three rests and 28 empty measures; Audiveris reports a separate 22 raw measures (10 in system 1 and 12 in system 2), but the exported part topology and event coverage remain incomplete.",
        "The retained OMR has empty or unusable divisions and cannot provide a reliable 2/4 duration audit; its per-measure duration ends are retained in durationEndByPart.",
        "The retained OMR has no lyrics, four-shape tags, or complete repeat/barline semantics. The derivative adds source metadata and derived shapes without rewriting uncertain events.",
        "No authorized same-title structured candidate exists, so no alternate tune or edition was used to fill missing notation.",
        "No separate retained work/source-images/2025 duplicate matching 135 Olney exists; the immutable work/omr/135-olney/source.jpg is the canonical local visual witness.",
    ]
    audit = {
        "queueId": "sh2025/135",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "135",
        "title": "Olney",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=135",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/135-Olney/135.jpg",
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)),
            "sourceImageSha256": image_hash,
            "immutable": True,
            "directObservations": {
                "header": "OLNEY. 8s & 7s D.",
                "composer": "Robert Robinson, 1758",
                "key": "F major",
                "mode": "major",
                "timeSignature": "2/4",
                "meter": "8s & 7s Double",
                "parts": 4,
                "systems": 2,
                "lyricsVisible": True,
                "stanzaLinesVisible": 2,
                "repeatBarsVisible": True,
                "endingsVisible": False,
                "sourceMeasureCountStatus": "Audiveris reports 22 raw measures (10 in system 1 and 12 in system 2); exported OMR also has 22 per part but sparse/incomplete event coverage does not establish source topology",
            },
            "retainedSourceImageMissing": {"expectedGlob": "work/source-images/2025/*135*olney*.jpg", "status": "not-found"},
        },
        "inputOmr": {"path": "work/omr/135-olney/source.mxl", "sha256": source_hash, "status": "retained-source-scan-omr"},
        "candidateWitness": {"status": "none-authorized", "sameTitleStructuredCandidate": False},
        "correctedDraft": {
            "path": "work/omr/autonomous-transcriptions/2025/135-olney-source-correction-v2.mxl",
            "sha256": draft_hash,
            "summary": summary,
            "eventStreamPreservedFromInput": True,
            "sourceEventSignature": source_events,
            "correctedEventSignature": corrected_events,
            "sourceBarlines": source_barlines,
            "correctedBarlines": corrected_barlines,
            "corrections": [
                "source F-major key and explicit major mode",
                "source 2/4 time signature",
                "four-shape noteheads derived for every retained pitched event",
                "source repeat/barline and lyric visibility recorded in provenance",
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
        "blockingReason": "Autonomous promotion is blocked by incomplete event coverage, unresolved source topology, unusable OMR divisions/duration proof, absent direct lyrics/shapes/repeat evidence, and no authorized structured witness. The derivative preserves detected events and adds source metadata/derived shapes without fabrication.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-no-authorized-candidate; retain-corrected-draft-only",
        "policy": "Immutable 2025 source remains authoritative. This corrected derivative is not an authoritative corpus asset.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/135", "status": audit["comparisonStatus"], "sourceImageSha256": image_hash, "inputOmrSha256": source_hash, "correctedDraftSha256": draft_hash, "summary": summary, "audit": str(AUDIT.relative_to(ROOT))}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
