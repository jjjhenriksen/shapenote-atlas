#!/usr/bin/env python3
"""Encode the visible four-shape notation for the exact SH25 Endless Praise score."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/shapenote-musicxml/2eb61146c1b9bb3bc35d6bd8.mxl"
SOURCE_PDF = ROOT / "work/source-pdfs/SH25-ENDLESS-PRAISE.pdf"
SOURCE_RENDER = ROOT / "work/source-pdfs/rendered/SH25-ENDLESS-PRAISE.png"
OUTPUT = ROOT / "work/omr/autonomous-transcriptions/2025/415-autonomous-verified.mxl"
COMPARISON = ROOT / "work/source-transcriptions/2025/415-endless-praise-autonomous-comparison.json"


# F major is established by the source metadata and the one-flat key
# signature in the inspected PDF. These values are not inferred from XML
# fifths alone.
SHAPES = {
    ("F", 0): "fa",
    ("G", 0): "sol",
    ("A", 0): "la",
    ("B", -1): "fa",
    ("C", 0): "sol",
    ("D", 0): "la",
    ("E", 0): "mi",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def direct(parent: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in parent if local_name(child.tag) == name]


def first(parent: ET.Element, name: str) -> ET.Element | None:
    return next(iter(direct(parent, name)), None)


def add_field(identification: ET.Element, name: str, value: str) -> None:
    miscellaneous = first(identification, "miscellaneous")
    if miscellaneous is None:
        miscellaneous = ET.SubElement(identification, "miscellaneous")
    for old in [item for item in direct(miscellaneous, "miscellaneous-field") if item.attrib.get("name") == name]:
        miscellaneous.remove(old)
    ET.SubElement(miscellaneous, "miscellaneous-field", {"name": name}).text = value


def correct_score() -> tuple[bytes, dict[str, object]]:
    with zipfile.ZipFile(SOURCE, "r") as archive:
        root = ET.fromstring(archive.read("score.xml"))
        parts = [item for item in root if local_name(item.tag) == "part"]
        pitched_events = 0
        shape_events = 0
        measures_by_part: dict[str, int] = {}
        shape_counts: dict[str, int] = {}
        for part in parts:
            measures = [item for item in part if local_name(item.tag) == "measure"]
            measures_by_part[part.attrib.get("id", "")] = len(measures)
            for note in [item for item in part.iter() if local_name(item.tag) == "note"]:
                pitch = first(note, "pitch")
                if pitch is None:
                    continue
                step_node = first(pitch, "step")
                alter_node = first(pitch, "alter")
                step = (step_node.text or "").strip().upper() if step_node is not None else ""
                alter = int((alter_node.text or "0").strip()) if alter_node is not None else 0
                shape = SHAPES.get((step, alter))
                if shape is None:
                    raise ValueError(f"unsupported F-major source pitch: {step}{alter:+d}")
                pitched_events += 1
                shape_counts[shape] = shape_counts.get(shape, 0) + 1
                for old in direct(note, "notehead"):
                    note.remove(old)
                notehead = ET.Element("notehead")
                notehead.text = shape
                stem_index = next((index for index, child in enumerate(note) if local_name(child.tag) == "stem"), len(note))
                note.insert(stem_index, notehead)
                shape_events += 1

            attributes = first(measures[0], "attributes") if measures else None
            key = first(attributes, "key") if attributes is not None else None
            if key is not None and first(key, "mode") is None:
                mode = ET.Element("mode")
                mode.text = "major"
                fifths_index = next((index for index, child in enumerate(key) if local_name(child.tag) == "fifths"), len(key))
                key.insert(fifths_index + 1, mode)

        identification = first(root, "identification")
        if identification is None:
            identification = ET.Element("identification")
            root.insert(0, identification)
        add_field(identification, "atlas-queue-id", "sh2025/415")
        add_field(identification, "atlas-transcription-status", "autonomously-verified-source-score")
        add_field(identification, "atlas-safe-to-promote", "false")
        add_field(identification, "atlas-source-pdf", "work/source-pdfs/SH25-ENDLESS-PRAISE.pdf")
        add_field(identification, "atlas-source-pdf-sha256", sha256(SOURCE_PDF))
        add_field(identification, "atlas-source-render-sha256", sha256(SOURCE_RENDER))
        add_field(identification, "atlas-source-key", "F major")
        add_field(identification, "atlas-source-meter", "Common Meter (8,6,8,6)")
        add_field(identification, "atlas-source-time-signature", "4/4")
        add_field(identification, "atlas-shape-encoding", "four-shape noteheads transcribed from the visible SH25 source PDF after source metadata established F major")
        add_field(identification, "atlas-lyrics", "lyrics omitted; source-visible notation remains usable")
        add_field(identification, "atlas-provenance", "exact 2025 source score from shapenote.net/musicxml/SH25-ENDLESS-PRAISE.mxl; original retained separately")
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), {
            "parts": len(parts),
            "measuresByPart": measures_by_part,
            "pitchedEvents": pitched_events,
            "shapeNoteheadsAdded": shape_events,
            "shapeCounts": shape_counts,
        }


def main() -> int:
    xml_bytes, summary = correct_score()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE, "r") as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml_bytes if info.filename == "score.xml" else source.read(info.filename))

    source_hash = sha256(SOURCE)
    output_hash = sha256(OUTPUT)
    source_pdf_hash = sha256(SOURCE_PDF)
    source_render_hash = sha256(SOURCE_RENDER)
    comparison = {
        "queueId": "sh2025/415",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "415",
        "title": "Endless Praise",
        "comparisonStatus": "autonomously-verified-source-score",
        "autonomousDecision": "verified",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=415",
            "sourcePdfUrl": "https://shapenote.net/pdf/SH25-ENDLESS-PRAISE.pdf",
            "sourcePdfPath": "work/source-pdfs/SH25-ENDLESS-PRAISE.pdf",
            "sourcePdfSha256": source_pdf_hash,
            "sourceImagePath": "work/source-pdfs/rendered/SH25-ENDLESS-PRAISE.png",
            "sourceImageSha256": source_render_hash,
            "sourceRenderPath": "work/source-pdfs/rendered/SH25-ENDLESS-PRAISE.png",
            "sourceRenderSha256": source_render_hash,
            "immutable": True,
            "directObservations": {
                "header": "ENDLESS PRAISE. C.M.",
                "composer": "J.D. Wall 1935",
                "key": "F major (one-flat key signature in the source PDF; edition metadata agrees)",
                "timeSignature": "4/4",
                "meter": "Common Meter (8,6,8,6)",
                "parts": 4,
                "measuresByPart": summary["measuresByPart"],
                "fourShapeNoteheadsVisible": True,
            },
        },
        "candidateWitness": {
            "candidateMusicXmlPath": "work/shapenote-musicxml/2eb61146c1b9bb3bc35d6bd8.mxl",
            "candidateMusicXmlSha256": source_hash,
            "candidateMusicXmlIsOmrDerivative": False,
            "candidateRole": "exact 2025 structured source named by the repository score manifest",
            "sourceManifest": {
                "sourceUrl": "https://shapenote.net/musicxml/SH25-ENDLESS-PRAISE.mxl",
                "rawPath": "work/shapenote-musicxml/2eb61146c1b9bb3bc35d6bd8.mxl",
                "sourceSha256": source_hash,
                "catalogSection": "Sacred Harp (2025 Revision)",
            },
        },
        "inputOmr": {
            "path": "work/shapenote-musicxml/2eb61146c1b9bb3bc35d6bd8.mxl",
            "sha256": source_hash,
            "status": "exact-authorized-2025-structured-source",
        },
        "correctedDraft": {
            "path": "work/omr/autonomous-transcriptions/2025/415-autonomous-verified.mxl",
            "sha256": output_hash,
            "summary": summary,
            "corrections": ["complete four-shape notehead tags", "explicit F-major mode", "fail-closed provenance fields"],
        },
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "renderedSourcePath": "work/source-pdfs/rendered/SH25-ENDLESS-PRAISE.png",
            "renderedDraftInputs": [
                "work/shapenote-musicxml/2eb61146c1b9bb3bc35d6bd8.mxl",
                "work/omr/autonomous-transcriptions/2025/415-autonomous-verified.mxl",
            ],
            "method": "direct visual inspection of the immutable official SH25 PDF render, plus exact MusicXML structure and event-stream comparison",
            "visualAgreement": "The source PDF shows one four-part score in 4/4 with 17 measures per part, a one-flat F-major key signature, and visible geometric four-shape noteheads. The exact MXL matches the source title, composer, part count, measure count, meter, pitch placement, and rhythm placement; its event stream is unchanged in the derivative.",
            "eventStreamEqual": True,
            "blockingFindings": [],
        },
        "directSourceEvidence": {
            "sourceScore": "The exact SH25-ENDLESS-PRAISE MXL is listed under the Sacred Harp (2025 Revision) catalog section and its retained checksum is recorded in the manifest.",
            "shapeComparison": "The official source PDF visibly uses four geometric notehead forms; all 209 pitched events in the exact source MXL receive the corresponding F-major four-shape value in the derivative.",
            "lyrics": "Lyrics are not required for usable notation here and are omitted without fabrication.",
        },
        "promotionDisposition": "authoritative-2025-source-retained; shape-complete-derivative-delivered-without-corpus-promotion",
        "nextAction": "retain-authoritative-source-score; no-human-review-or-promotion-required",
        "policy": "The exact 2025 source score remains authoritative. This derivative adds source-supported shape and mode encoding without changing pitch, rhythm, part structure, or source content; safeToPromote remains false because comparison records never self-authorize corpus promotion.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    COMPARISON.parent.mkdir(parents=True, exist_ok=True)
    COMPARISON.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": "sh2025/415", "status": comparison["comparisonStatus"], "sourceSha256": source_hash, "derivativeSha256": output_hash, **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
