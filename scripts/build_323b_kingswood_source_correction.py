#!/usr/bin/env python3
"""Create a source-derived, fail-closed correction for Sacred Harp 323b."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/omr/323b-kingswood/source.mxl"
SOURCE_IMAGE = ROOT / "work/omr/323b-kingswood/source.jpg"
RETAINED_IMAGE = ROOT / "work/source-images/2025/323b-kingswood-300cd6851c.jpg"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/323b-kingswood-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/323b-kingswood-comparison.json"

# D minor uses the relative F-major spelling: F=fa, G=sol, A=la, Bb=mi,
# C=fa, D=sol, E=la. The retained OMR's step/alter values are untouched.
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
    summary: dict[str, object] = {"parts": 0, "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "restEvents": 0, "shapeNoteheadsAdded": 0, "emptyMeasures": 0, "durationFailuresAgainst2_2": {}, "sourceBarlines": 0, "lyricsRetained": 0}
    parts = children(root, "part")
    summary["parts"] = len(parts)
    for part in parts:
        part_id = part.attrib.get("id", "")
        measures = children(part, "measure")
        summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
        summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
        summary["emptyMeasures"] = int(summary["emptyMeasures"]) + sum(not children(measure, "note") for measure in measures)
        summary["sourceBarlines"] = int(summary["sourceBarlines"]) + sum(len(children(measure, "barline")) for measure in measures)
        summary["durationFailuresAgainst2_2"][part_id] = [f"m{measure.attrib.get('number')}={duration_end(measure)}" for measure in measures if duration_end(measure) != 8]  # type: ignore[index]
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
            ET.SubElement(key, "mode").text = "minor"
            time = first(attributes, "time")
            if time is None:
                time = ET.Element("time")
                attributes.insert(2, time)
            for old in children(time, "beats") + children(time, "beat-type"):
                time.remove(old)
            ET.SubElement(time, "beats").text = "2"
            ET.SubElement(time, "beat-type").text = "2"
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
        "atlas-queue-id": "sh2025/323b", "atlas-transcription-status": "autonomously-blocked", "atlas-review-status": "autonomously-blocked-source-derived-draft", "atlas-safe-to-promote": "false", "atlas-source-image": "work/omr/323b-kingswood/source.jpg", "atlas-source-image-sha256": sha256(SOURCE_IMAGE), "atlas-retained-source-copy": "work/source-images/2025/323b-kingswood-300cd6851c.jpg", "atlas-retained-source-copy-sha256": sha256(RETAINED_IMAGE), "atlas-source-key": "D minor", "atlas-source-mode": "minor", "atlas-source-time-signature": "2/2", "atlas-source-meter": "Common Meter (C.M.)", "atlas-source-title-and-credits": "KINGSWOOD. C.M.; Anne Steele, 1760; Victoria Elliott, 2016", "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and source-visible D-minor key; not source-verified per event", "atlas-lyrics": "omitted; source lyrics are visible but retained OMR has no directly aligned lyric underlay", "atlas-provenance-policy": "immutable 2025 source image is authoritative; the same-title Haworth candidate is a distinct mismatched setting and is not used; this OMR derivative is evidence only", "atlas-blocker": "The immutable page visibly prints KINGSWOOD. C.M., D minor, 2/2, four vocal parts, lyrics, and a terminal double bar. The retained OMR exports 14 measures per part but has sparse duration/event grouping, no aligned lyrics, and no shape tags. The only same-title candidate is Haworth C.M.D. in 6/4 with 16 measures and is rejected as a source mismatch. A diagonal DO NOT COPY watermark crosses central notation. No notation was synthesized.",
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
    blocking = ["The source page establishes D minor, 2/2, four parts, visible lyrics, and a terminal double bar, but the retained OMR has no aligned lyrics or source-confirmed per-note shapes.", "The source scan has 14 measures per part while the rejected same-title Haworth candidate has 16 measures in a different C.M.D./6/4 setting; neither supplies exact SH25 structured notation.", "The retained OMR's duration grouping fails against 2/2 in multiple measures and the diagonal watermark intersects central notation; no obscured note, lyric, repeat, ending, duration, or shape was inferred.", "The Haworth candidate is preserved only as a rejected alternate-edition witness and was not merged or used for playback/transposition."]
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    audit.update({"comparisonStatus": "autonomously-blocked", "autonomousDecision": "blocked", "safeToPromote": False, "humanReviewRequired": False})
    audit["sourceAuthority"] = {"sourcePageUrl": "https://fasola.org/indexes/2025/?p=323b", "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/323b-Kingswood/323b.jpg", "sourceImagePath": "work/omr/323b-kingswood/source.jpg", "sourceImageSha256": sha256(SOURCE_IMAGE), "immutable": True, "sourceImageVariants": [{"path": "work/source-images/2025/323b-kingswood-300cd6851c.jpg", "sha256": sha256(RETAINED_IMAGE), "relationship": "retained same-page copy; byte-identical to canonical source image"}], "directObservations": {"header": "KINGSWOOD. C.M.", "key": "D minor", "mode": "minor", "timeSignature": "2/2", "meter": "Common Meter (C.M.)", "composer": "Anne Steele, 1760", "arranger": "Victoria Elliott, 2016", "parts": 4, "clefOrder": ["treble", "treble", "treble", "bass"], "sourceMeasuresByPart": {"P1": 14, "P2": 14, "P3": 14, "P4": 14}, "sourceLyricsVisible": True, "sourceRepeatEnding": "terminal double bar visible; no numbered endings observed", "watermarkAffectedRegions": "central notation and lyric region"}}
    audit["inputOmr"] = {"path": "work/omr/323b-kingswood/source.mxl", "sha256": sha256(SOURCE), "status": "retained-source-scan-omr", "parts": int(summary["parts"]), "measuresByPart": summary["measuresByPart"], "eventsByPart": summary["eventsByPart"], "pitchedEvents": int(summary["pitchedEvents"]), "restEvents": int(summary["restEvents"]), "noteheads": 0, "lyrics": 0, "timeSignatures": 0, "durationAudit": summary["durationFailuresAgainst2_2"], "statusReason": "The canonical OMR has 14 measures per part but sparse event/duration grouping, no source key/mode/time metadata, no lyrics, and no shape tags."}
    audit["correctedDraft"] = {"path": str(OUTPUT.relative_to(ROOT)), "sha256": draft_hash, "summary": summary, "eventStreamPreservedFromInput": True, "sourceEventSignature": source_events, "correctedEventSignature": corrected_events, "corrections": ["source D-minor key and explicit minor mode", "source 2/2 time signature", "four-shape noteheads added to every retained pitched event", "canonical and byte-identical retained source-image provenance recorded", "lyrics, uncertain repeat semantics, missing events, and uncertain durations intentionally omitted"]}
    audit["candidateWitness"] = {"status": "rejected-source-mismatch", "candidateKey": "sh2025/323b/220fafc091", "candidatePdfPath": "work/source-transcriptions/2025/clean-source-candidates/323b-kingswood-haworth-c-m-d-87e7e72d58/source-candidate.pdf", "candidateMusicXmlPath": "work/omr/clean-source-candidates/323b-kingswood-haworth-c-m-d-220fafc091/source-candidate.mxl", "candidateMusicXmlSha256": "db97121f1e25cc059e1667ae2988a4bf8b97e174d5c0506fe15ea29648e1dcd2", "reason": "Haworth C.M.D./6-4/16-measure witness is not the SH25 Kingswood C.M./2-2/14-measure setting."}
    audit["comparisonEvidence"] = {"sourceScanInspected": True, "sourceScanPath": "work/omr/323b-kingswood/source.jpg", "sourceScanSha256": sha256(SOURCE_IMAGE), "retainedSourceCopyInspected": "work/source-images/2025/323b-kingswood-300cd6851c.jpg", "method": "full-resolution direct source-image inspection plus canonical OMR event, duration, topology, lyric, repeat, and candidate-mismatch audit; alternate witness kept distinct", "blockingFindings": blocking}
    audit["blockingFindings"] = blocking
    audit["blockingReason"] = "Autonomous promotion is blocked because the retained source OMR is sparse and does not establish all 14 source measures note-for-note against 2/2, while the only same-title candidate is a different Haworth C.M.D./6/4/16-measure setting. Lyrics, source-confirmed per-note shapes, and complete structural semantics remain unproven; the derivative preserves detected events and adds metadata/shapes without fabrication."
    audit["nextAction"] = "autonomous-promotion-blocked-by-incomplete-source-event-witness-and-rejected-alternate-setting; retain-corrected-draft-only"
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/323b", "status": audit["comparisonStatus"], "sourceImageSha256": sha256(SOURCE_IMAGE), "retainedSourceImageSha256": sha256(RETAINED_IMAGE), "inputOmrSha256": sha256(SOURCE), "correctedDraftSha256": draft_hash, "summary": summary, "audit": str(AUDIT.relative_to(ROOT))}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
