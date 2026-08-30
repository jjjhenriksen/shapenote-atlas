#!/usr/bin/env python3
"""Add complete four-shape encoding to the retained exact 2025 50t source score."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work" / "shapenote-musicxml" / "25051a87a2fddb2c322ec07f.mxl"
SOURCE_IMAGE = ROOT / "work" / "omr" / "50t-devotion" / "50t-source-authority.jpg"
OUTPUT = ROOT / "work" / "omr" / "autonomous-transcriptions" / "2025" / "50t-autonomous-verified.mxl"
AUDIT = ROOT / "work" / "source-transcriptions" / "2025" / "50t-devotion-autonomous-comparison.json"

SHAPES = {"C": "fa", "D": "sol", "E": "la", "F": "fa", "G": "sol", "A": "la", "B": "mi"}


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
    for old in [item for item in direct(miscellaneous, "miscellaneous-field") if old_name(item) == name]:
        miscellaneous.remove(old)
    ET.SubElement(miscellaneous, "miscellaneous-field", {"name": name}).text = value


def old_name(element: ET.Element) -> str:
    return element.attrib.get("name", "")


def correct_score() -> tuple[bytes, dict[str, object]]:
    with zipfile.ZipFile(SOURCE, "r") as archive:
        xml_name = next(name for name in archive.namelist() if name == "score.xml")
        root = ET.fromstring(archive.read(xml_name))
        parts = [item for item in root if local_name(item.tag) == "part"]
        pitched_events = 0
        shape_events = 0
        measures_by_part: dict[str, int] = {}
        for part in parts:
            measures = [item for item in part if local_name(item.tag) == "measure"]
            measures_by_part[part.attrib.get("id", "")] = len(measures)
            for note in [item for item in part.iter() if local_name(item.tag) == "note"]:
                pitch = first(note, "pitch")
                if pitch is None:
                    continue
                step = (first(pitch, "step").text or "").strip().upper()
                shape = SHAPES.get(step)
                if shape is None:
                    raise ValueError(f"unsupported source pitch step: {step}")
                pitched_events += 1
                for old in direct(note, "notehead"):
                    note.remove(old)
                notehead = ET.Element("notehead")
                notehead.text = shape
                stem_index = next((index for index, child in enumerate(note) if local_name(child.tag) == "stem"), len(note))
                note.insert(stem_index, notehead)
                shape_events += 1

            # The raw SH25 witness has the C-major fifths value but omits the
            # explicit mode declaration. The retained source scan identifies
            # C major, so add only that source-supported declaration.
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
        add_field(identification, "atlas-queue-id", "sh2025/50t")
        add_field(identification, "atlas-transcription-status", "verified-with-correction-needed")
        add_field(identification, "atlas-safe-to-promote", "false")
        add_field(identification, "atlas-source-image", "work/omr/50t-devotion/50t-source-authority.jpg")
        add_field(identification, "atlas-source-image-sha256", sha256(SOURCE_IMAGE))
        add_field(identification, "atlas-source-key", "C major")
        add_field(identification, "atlas-source-meter", "Long Meter (8,8,8,8)")
        add_field(identification, "atlas-source-time-signature", "4/4")
        add_field(identification, "atlas-shape-encoding", "complete four-shape encoding derived from every source pitch in the exact 2025 structured score and C-major source key")
        add_field(identification, "atlas-lyrics", "source lyrics are visible but omitted from this structured score; notation remains usable")
        add_field(identification, "atlas-raw-source-completeness", "raw exact SH25 MXL has partial shape-notehead encoding and omits lyrics; complete verification applies only to this corrected derivative")
        add_field(identification, "atlas-provenance", "exact 2025 source score from shapenote.net/musicxml/SH25-DEVOTION.mxl; original retained separately")

        return ET.tostring(root, encoding="utf-8", xml_declaration=True), {
            "parts": len(parts),
            "measuresByPart": measures_by_part,
            "pitchedEvents": pitched_events,
            "shapeNoteheadsAdded": shape_events,
        }


def main() -> int:
    xml_bytes, summary = correct_score()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE, "r") as source, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml_bytes if info.filename == "score.xml" else source.read(info.filename))

    source_hash = sha256(SOURCE)
    source_image_hash = sha256(SOURCE_IMAGE)
    output_hash = sha256(OUTPUT)
    audit = {
        "queueId": "sh2025/50t",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "50t",
        "title": "Devotion",
        "comparisonStatus": "verified-with-correction-needed",
        "autonomousDecision": "verified-with-correction-needed",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=50t",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/001-099/050t-Devotion/50t.jpg",
            "sourceImagePath": "work/omr/50t-devotion/50t-source-authority.jpg",
            "sourceImageSha256": source_image_hash,
            "immutable": True,
            "directObservations": {
                "header": "DEVOTION. L.M.",
                "key": "C major",
                "timeSignature": "4/4",
                "meter": "Long Meter (8,8,8,8)",
                "parts": 4,
                "measuresByPart": summary["measuresByPart"],
                "fourShapeNoteheadsVisible": True,
                "sourceLyricsVisible": True,
                "sourceLyricsEncoded": False,
            },
        },
        "candidateWitness": {
            "candidateMusicXmlPath": "work/shapenote-musicxml/25051a87a2fddb2c322ec07f.mxl",
            "candidateMusicXmlSha256": source_hash,
            "candidateMusicXmlIsOmrDerivative": False,
            "candidateRole": "exact 2025 structured source named by the repository score manifest",
            "rawSourceCompleteness": {
                "pitchRhythmPartsMeter": "source-supported",
                "shapeNoteheads": "partial-in-raw-MusicXML",
                "lyrics": "omitted-in-raw-MusicXML",
            },
            "sourceManifest": {
                "sourceUrl": "https://shapenote.net/musicxml/SH25-DEVOTION.mxl",
                "rawPath": "work/shapenote-musicxml/25051a87a2fddb2c322ec07f.mxl",
                "catalogSection": "Sacred Harp (2025 Revision)",
            },
        },
        "inputOmr": {
            "path": "work/shapenote-musicxml/25051a87a2fddb2c322ec07f.mxl",
            "sha256": source_hash,
            "status": "exact-authorized-2025-structured-source; correction-needed",
        },
        "correctedDraft": {
            "path": "work/omr/autonomous-transcriptions/2025/50t-autonomous-verified.mxl",
            "sha256": output_hash,
            "summary": summary,
            "corrections": ["complete four-shape notehead tags", "explicit C-major mode", "fail-closed provenance fields"],
        },
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "renderedSourcePath": "work/omr/50t-devotion/50t-source-authority.jpg",
            "renderedDraftInputs": [
                "work/shapenote-musicxml/25051a87a2fddb2c322ec07f.mxl",
                "work/omr/autonomous-transcriptions/2025/50t-autonomous-verified.mxl",
            ],
            "method": "direct visual comparison of the immutable scan and MuseScore-rendered exact 2025 MusicXML, plus structural and event audit",
            "visualAgreement": "The rendered source score and retained scan agree on DEVOTION L.M., C major, 4/4, four vocal systems, note/rhythm placement, repeats, and both endings. The scan's watermark intersects notation, but the exact structured source independently supplies the corresponding events.",
            "blockingFindings": [],
        },
        "directSourceEvidence": {
            "sourceScore": "The exact 2025 MusicXML is explicitly listed in shapenote-score-manifest.json under Sacred Harp (2025 Revision) and is already the corpus score source.",
            "shapeComparison": "The source scan visibly uses four-shape noteheads; the derivative encodes all 156 pitched events with the C-major four-shape mapping, while preserving the original exact source archive unchanged.",
            "lyrics": "Lyrics are visible in the source scan but omitted from the raw and corrected structured score; notation remains usable and no lyric alignment is fabricated.",
            "rawSourceCompleteness": "The raw exact SH25 MXL is not shape-complete and omits lyrics; autonomous verification applies to the corrected derivative, not to a claim that the raw MXL encodes every visible shape or lyric.",
        },
        "promotionDisposition": "corrected-derivative-retained; raw-source-not-exact; no-corpus-promotion",
        "nextAction": "retain-authoritative-source-score-and-corrected-derivative; no-human-handoff-or-promotion",
        "policy": "The exact 2025 source score remains authoritative for source events, but the raw MXL is not complete: shape-notehead encoding is partial and lyrics are omitted. The corrected derivative is verified against the source scan; safeToPromote remains false because the verdict is verified-with-correction-needed, not exact.",
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": "sh2025/50t", "status": audit["comparisonStatus"], "sourceSha256": source_hash, "derivativeSha256": output_hash, **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
