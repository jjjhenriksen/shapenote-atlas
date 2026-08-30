#!/usr/bin/env python3
"""Create a source-derived, fail-closed Bremen 366 correction derivative.

This is deliberately not a transcription engine. It preserves the detected
events from the retained source-scan OMR, corrects only source-visible global
metadata, and adds reversible four-shape annotations derived from the printed
F-sharp-minor key. Missing or uncertain events are never synthesized.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/omr/366-bremen/source.mxl"
SOURCE_IMAGE = ROOT / "work/omr/366-bremen/source.jpg"
CANDIDATE_PDF = ROOT / "work/source-transcriptions/2025/clean-source-candidates/366-bremen-worrall-p-m-416beba7fd/source-candidate.pdf"
CANDIDATE_MXL = ROOT / "work/omr/clean-source-candidates/366-bremen-worrall-p-m-ea53008489/source-candidate.mxl"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/366-bremen-source-correction-v2.mxl"
AUDIT = ROOT / "work/source-transcriptions/2025/366-bremen-source-correction-v2-comparison.json"

# Four-shape spellings for the diatonic scale of A major, the relative major
# of the printed F-sharp-minor source key. Accidentals keep their written
# pitch; the pitch step supplies only the shape-family lookup.
SHAPES = {"A": "fa", "B": "sol", "C": "la", "D": "fa", "E": "sol", "F": "la", "G": "mi"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(parent: ET.Element | None, name: str) -> list[ET.Element]:
    return [child for child in parent if tag_name(child.tag) == name] if parent is not None else []


def first(parent: ET.Element | None, name: str) -> ET.Element | None:
    return next(iter(children(parent, name)), None)


def field(identification: ET.Element, name: str, value: str) -> None:
    miscellaneous = first(identification, "miscellaneous")
    if miscellaneous is None:
        miscellaneous = ET.SubElement(identification, "miscellaneous")
    for old in [item for item in children(miscellaneous, "miscellaneous-field") if item.attrib.get("name") == name]:
        miscellaneous.remove(old)
    ET.SubElement(miscellaneous, "miscellaneous-field", {"name": name}).text = value


def duration_end(measure: ET.Element) -> int:
    cursor = 0
    maximum = 0
    for item in measure:
        name = tag_name(item.tag)
        duration = first(item, "duration")
        units = int(duration.text) if duration is not None and duration.text and duration.text.isdigit() else 0
        if name == "note":
            if first(item, "chord") is None:
                cursor += units
            maximum = max(maximum, cursor)
        elif name == "backup":
            cursor -= units
        elif name == "forward":
            cursor += units
    return maximum


def event_signature(root: ET.Element) -> dict[str, object]:
    result: dict[str, object] = {}
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
                events.append(
                    {
                        "measure": measure.attrib.get("number", ""),
                        "pitch": pitch_value,
                        "duration": duration.text if duration is not None and duration.text else "",
                        "type": (first(note, "type").text or "") if first(note, "type") is not None else "",
                        "voice": (first(note, "voice").text or "") if first(note, "voice") is not None else "",
                    }
                )
        result[part.attrib.get("id", "")] = events
    return result


def transform() -> tuple[bytes, dict[str, object], dict[str, object]]:
    with zipfile.ZipFile(SOURCE) as archive:
        xml_name = next(name for name in archive.namelist() if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/"))
        root = ET.fromstring(archive.read(xml_name))
        parts = children(root, "part")
        summary: dict[str, object] = {"parts": len(parts), "measuresByPart": {}, "eventsByPart": {}, "pitchedEvents": 0, "shapeNoteheadsAdded": 0, "lyricsRetained": 0, "durationFailures": {}}
        for part in parts:
            part_id = part.attrib.get("id", "")
            measures = children(part, "measure")
            summary["measuresByPart"][part_id] = len(measures)  # type: ignore[index]
            summary["eventsByPart"][part_id] = sum(len(children(measure, "note")) for measure in measures)  # type: ignore[index]
            summary["durationFailures"][part_id] = [  # type: ignore[index]
                f"m{measure.attrib.get('number')}={duration_end(measure)}"
                for measure in measures
                if duration_end(measure) != 6
            ]
            for measure in measures:
                attributes = first(measure, "attributes")
                if attributes is not None:
                    key = first(attributes, "key")
                    if key is None:
                        key = ET.Element("key")
                        attributes.insert(1, key)
                    for old in children(key, "fifths") + children(key, "mode"):
                        key.remove(old)
                    ET.SubElement(key, "fifths").text = "3"
                    ET.SubElement(key, "mode").text = "minor"
                    # Only the source-visible first key/time declaration is
                    # needed, but normalizing every existing declaration avoids
                    # part-local OMR drift while preserving note events.
                for note in children(measure, "note"):
                    pitch = first(note, "pitch")
                    if pitch is None:
                        continue
                    step = first(pitch, "step")
                    if step is None or not step.text or step.text.strip().upper() not in SHAPES:
                        continue
                    for old in children(note, "notehead"):
                        note.remove(old)
                    notehead = ET.Element("notehead")
                    notehead.text = SHAPES[step.text.strip().upper()]
                    stem_index = next((index for index, item in enumerate(note) if tag_name(item.tag) == "stem"), len(note))
                    note.insert(stem_index, notehead)
                    summary["pitchedEvents"] = int(summary["pitchedEvents"]) + 1
                    summary["shapeNoteheadsAdded"] = int(summary["shapeNoteheadsAdded"]) + 1

        identification = first(root, "identification")
        if identification is None:
            identification = ET.Element("identification")
            root.insert(0, identification)
        provenance = {
            "atlas-queue-id": "sh2025/366",
            "atlas-transcription-status": "autonomously-blocked",
            "atlas-review-status": "autonomously-blocked-source-derived-draft",
            "atlas-safe-to-promote": "false",
            "atlas-source-image": "work/omr/366-bremen/source.jpg",
            "atlas-source-image-sha256": sha256(SOURCE_IMAGE),
            "atlas-source-key": "F-sharp minor",
            "atlas-source-mode": "minor",
            "atlas-source-time-signature": "3/4",
            "atlas-source-meter": "Particular Meter (8s & 6s.)",
            "atlas-shape-encoding": "derived four-shape spelling from retained OMR pitch steps and the source-visible F-sharp-minor key; not source-verified per event",
            "atlas-lyrics": "omitted; retained OMR has no aligned lyric underlay and the watermark intersects source systems",
            "atlas-provenance-policy": "immutable 2025 scan is authoritative; alternate Worrall witness and this OMR derivative are evidence only",
            "atlas-blocker": "Source-visible page is complete, but retained OMR has blank source-visible measures and duration/event failures; watermark-intersected events remain unresolved. No notes, rhythms, lyrics, repeats, or endings were synthesized.",
        }
        for name, value in provenance.items():
            field(identification, name, value)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), summary, event_signature(root)


def main() -> int:
    source_hash = sha256(SOURCE)
    source_image_hash = sha256(SOURCE_IMAGE)
    candidate_pdf_hash = sha256(CANDIDATE_PDF)
    candidate_mxl_hash = sha256(CANDIDATE_MXL)
    xml, summary, corrected_events = transform()
    with zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml if info.filename == "source.xml" else source.read(info.filename))
    draft_hash = sha256(OUTPUT)
    with zipfile.ZipFile(SOURCE) as archive:
        source_root = ET.fromstring(archive.read("source.xml"))
    source_events = event_signature(source_root)
    blocking = [
        "The immutable scan visibly prints BREMEN P.M., F-sharp minor, 3/4, four vocal parts, lyrics, and 15 measures per part.",
        "The retained source-scan OMR contains only 40/31/38/46 note events in P1/P2/P3/P4, including blank source-visible P3 measures 6 and 15 and P4 measure 1.",
        "The retained OMR has cursor-duration failures against 3/4 in P1 m1,m3,m4,m5,m6,m7,m9,m10; P2 m1,m6,m9,m10,m12,m14,m15; P3 m1,m2,m3,m5,m6,m8,m11,m12,m13,m14,m15; and P4 m1,m3,m4,m5,m6,m8,m10,m11,m15.",
        "The retained OMR has conflicting key metadata (two sharps, one sharp, or absent) and no mode; the derivative records source F-sharp minor without rewriting uncertain pitches.",
        "The diagonal source watermark intersects middle and lower systems, and no direct lyric alignment is available in the retained OMR; lyrics are omitted rather than fabricated.",
        "The clean candidate is Worrall P.M. (2014-15), has 25 measures per part, and is not an authorized exact 2025 Bremen witness; it remains comparison-only.",
    ]
    audit = {
        "queueId": "sh2025/366",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "366",
        "title": "Bremen",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=366",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/366-Bremen/366.jpg",
            "sourceImagePath": "work/omr/366-bremen/source.jpg",
            "sourceImageSha256": source_image_hash,
            "alternateRetainedPath": "work/source-images/2025/366-bremen-a3dfb3f083.jpg",
            "alternateRetainedSha256": source_image_hash,
            "immutable": True,
            "directObservations": {"header": "BREMEN. P.M.", "key": "F-sharp minor", "mode": "minor", "timeSignature": "3/4", "meter": "Particular Meter (8s & 6s.)", "parts": 4, "measuresByPart": {"P1": 15, "P2": 15, "P3": 15, "P4": 15}, "lyricsVisible": True, "watermarkAffectedRegions": "middle and lower system note intersections"},
        },
        "inputOmr": {"path": "work/omr/366-bremen/source.mxl", "sha256": source_hash, "status": "retained-source-scan-omr"},
        "candidateWitness": {"candidatePdfPath": "work/source-transcriptions/2025/clean-source-candidates/366-bremen-worrall-p-m-416beba7fd/source-candidate.pdf", "candidatePdfSha256": candidate_pdf_hash, "candidateMusicXmlPath": "work/omr/clean-source-candidates/366-bremen-worrall-p-m-ea53008489/source-candidate.mxl", "candidateMusicXmlSha256": candidate_mxl_hash, "candidateMusicXmlIsOmrDerivative": True, "candidateEdition": "Worrall P.M., 2014-15; alternate witness only"},
        "correctedDraft": {"path": "work/omr/autonomous-transcriptions/2025/366-bremen-source-correction-v2.mxl", "sha256": draft_hash, "summary": summary, "eventStreamPreservedFromInput": True, "sourceEventSignature": source_events, "correctedEventSignature": corrected_events, "corrections": ["source F-sharp-minor key and explicit minor mode", "source 3/4 time signature retained", "four-shape noteheads added to every retained pitched event", "provenance and fail-closed status fields added", "lyrics intentionally omitted because direct alignment is unavailable"]},
        "comparisonEvidence": {"sourceScanInspected": True, "sourceScanPath": "work/omr/366-bremen/source.jpg", "sourceScanSha256": source_image_hash, "method": "full-resolution visual inspection of immutable scan plus XML event, duration, topology, and provenance audit; candidate kept distinct", "sourceEventEvidence": "The raster source establishes page-level facts only; the retained OMR does not provide a complete source event witness.", "blockingFindings": blocking},
        "blockingReason": "Autonomous promotion is blocked because the retained OMR is incomplete and rhythmically inconsistent with the source-visible 3/4 page, several source-visible measures are blank, key/mode metadata conflicts, lyrics are not directly aligned, and the watermark obscures some event intersections. The derivative preserves detected events and adds source metadata/shapes without inventing notation.",
        "nextAction": "autonomous-promotion-blocked-by-incomplete-source-event-witness; retain-corrected-draft-only",
        "policy": "Immutable 2025 source remains authoritative. This corrected derivative and the alternate Worrall witness are not authoritative corpus assets.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": "sh2025/366", "status": audit["comparisonStatus"], "sourceImageSha256": source_image_hash, "inputOmrSha256": source_hash, "candidatePdfSha256": candidate_pdf_hash, "candidateMusicXmlSha256": candidate_mxl_hash, "correctedDraftSha256": draft_hash, "summary": summary, "audit": str(AUDIT.relative_to(ROOT))}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
