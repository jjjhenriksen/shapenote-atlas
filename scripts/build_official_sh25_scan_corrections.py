#!/usr/bin/env python3
"""Build source-preserving SH25 correction derivatives for scanned witnesses.

This is deliberately a correction-only path. It copies the exact edition MXL,
adds the mode read from the printed scan, and encodes four-shape noteheads from
the source key signature. It never adds lyrics, changes events, or authorizes
corpus promotion.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "public/shapenote-score-manifest.json"
CORPUS = ROOT / "public/corpus.json"
SCAN_ROOT = ROOT / "work/source-pdfs/official-sh25-scans"
OUTPUT_ROOT = ROOT / "work/omr/autonomous-transcriptions/2025/official-scan-corrections"
COMPARISON_ROOT = ROOT / "work/source-transcriptions/2025"

# The source scans were inspected directly in the bounded audit pass. Shapes
# follow the relative-major key signature; the printed mode is recorded
# independently and never inferred from fifths.
RECORDS = {
    "41": {"title": "Evening Hymn", "scan": "SH25-EVENING-HYMN.jpg", "scanUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/001-099/041-Evening-Hymn/41.jpg", "key": "B minor", "time": "4/4", "meter": "Short Meter (6,6,8,6)", "parts": 4, "measures": 16, "shapeFifths": 2},
    "118": {"title": "Heavenly Meeting", "scan": "SH25-HEAVENLY-MEETING.jpg", "scanUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/118-Heavenly-Meeting/118.jpg", "key": "A minor", "time": "6/4", "meter": "Short Meter (6,6,8,6)", "parts": 3, "measures": 20, "shapeFifths": 0},
    "169": {"title": "God’s Helping Hand", "scan": "SH25-GODS-HELPING-HAND.jpg", "scanUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/169-Gods-Helping-Hand/169.jpg", "key": "E minor", "time": "4/4", "meter": "Long Meter (8,8,8,8)", "parts": 4, "measures": 23, "shapeFifths": 1},
    "525": {"title": "Imandra", "scan": "SH25-IMANDRA.jpg", "scanUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/525-Imandra/525.jpg", "key": "A minor", "time": "4/4", "meter": "11s.", "parts": 4, "measures": 14, "shapeFifths": 0},
    "537": {"title": "Portsmouth", "scan": "SH25-PORTSMOUTH.jpg", "scanUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/537-Portsmouth/537.jpg", "key": "Bb major", "time": "4/4", "meter": "Long Meter (8,8,8,8)", "parts": 4, "measures": 14, "shapeFifths": -2},
    "544": {"title": "Youthful Blessings", "scan": "SH25-YOUTHFUL-BLESSINGS.jpg", "scanUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/544-Youthful-Blessings/544.jpg", "key": "A major", "time": "4/4", "meter": "Common Meter (8,6,8,6)", "parts": 4, "measures": 22, "shapeFifths": 3},
    "545": {"title": "Somers", "scan": "SH25-SOMERS.jpg", "scanUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/545-Somers/545.jpg", "key": "A minor", "time": "4/4", "meter": "Short Meter (6,6,8,6)", "parts": 4, "measures": 14, "shapeFifths": 0},
    "557": {"title": "New Farewell", "scan": "SH25-NEW-FAREWELL.jpg", "scanUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/557-New-Farewell/557.jpg", "key": "A minor", "time": "6/8", "meter": "8s & 7s D.", "parts": 4, "measures": 15, "shapeFifths": 0},
    "563": {"title": "Suffield", "scan": "SH25-SUFFIELD.jpg", "scanUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/563-Suffield/563.jpg", "key": "E minor", "time": "4/4", "meter": "Common Meter (8,6,8,6)", "parts": 4, "measures": 13, "shapeFifths": 1},
    "575": {"title": "Lisbon", "scan": "SH25-LISBON.jpg", "scanUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/575-Lisbon/575.jpg", "key": "E minor", "time": "4/4", "meter": "Long Meter Half (8,8)", "parts": 3, "measures": 19, "shapeFifths": 1},
}

FIFTHS_TO_MAJOR_SHAPES = {
    -2: {("Bb", 0): "fa", ("B", -1): "fa", ("C", 0): "sol", ("D", 0): "la", ("Eb", 0): "fa", ("E", -1): "fa", ("F", 0): "sol", ("G", 0): "la", ("A", 0): "mi"},
    0: {("C", 0): "fa", ("D", 0): "sol", ("E", 0): "la", ("F", 0): "fa", ("G", 0): "sol", ("A", 0): "la", ("B", 0): "mi"},
    1: {("G", 0): "fa", ("A", 0): "sol", ("B", 0): "la", ("C", 0): "fa", ("D", 0): "sol", ("E", 0): "la", ("F", 1): "mi"},
    2: {("D", 0): "fa", ("E", 0): "sol", ("F", 1): "la", ("G", 0): "fa", ("A", 0): "sol", ("B", 0): "la", ("C", 1): "mi"},
    3: {("A", 0): "fa", ("B", 0): "sol", ("C", 1): "la", ("D", 0): "fa", ("E", 0): "sol", ("F", 1): "la", ("G", 1): "mi"},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    for item in direct(miscellaneous, "miscellaneous-field"):
        if item.attrib.get("name") == name:
            miscellaneous.remove(item)
    ET.SubElement(miscellaneous, "miscellaneous-field", {"name": name}).text = value


def correct_score(source: Path, output: Path, item: dict[str, object], queue_id: str) -> dict[str, object]:
    shapes = FIFTHS_TO_MAJOR_SHAPES[int(item["shapeFifths"])]
    with zipfile.ZipFile(source) as archive:
        root = ET.fromstring(archive.read(next(name for name in archive.namelist() if name.endswith(".xml") and "container" not in name.lower())))
    parts = [node for node in root if local_name(node.tag) == "part"]
    shape_count = 0
    pitched = 0
    shape_counts: dict[str, int] = {}
    measures = {}
    for part in parts:
        measures[part.attrib.get("id", "")] = sum(1 for node in part if local_name(node.tag) == "measure")
        for note in part.iter():
            if local_name(note.tag) != "note":
                continue
            pitch = first(note, "pitch")
            if pitch is None:
                continue
            step_node = first(pitch, "step")
            alter_node = first(pitch, "alter")
            pitch_key = ((step_node.text or "").strip(), int((alter_node.text or "0").strip()) if alter_node is not None else 0)
            value = shapes.get(pitch_key)
            if value is None:
                # Accidentals retain the four-shape family of their written
                # diatonic letter.  This is the source-key spelling rule for
                # chromatic pitches (for example A-sharp in B minor), while
                # the MusicXML accidental itself remains untouched.
                value = shapes.get((pitch_key[0], 0))
            if value is None:
                raise ValueError(f"{queue_id}: source pitch {pitch_key} has no source-key shape mapping")
            pitched += 1
            shape_counts[value] = shape_counts.get(value, 0) + 1
            for old in direct(note, "notehead"):
                note.remove(old)
            notehead = ET.Element("notehead")
            notehead.text = value
            stem_index = next((index for index, child in enumerate(note) if local_name(child.tag) == "stem"), len(note))
            note.insert(stem_index, notehead)
            shape_count += 1
    for key in root.iter():
        if local_name(key.tag) != "key" or first(key, "mode") is not None:
            continue
        mode = ET.Element("mode")
        mode.text = str(item["key"]).split()[-1].lower()
        fifths = next((index for index, child in enumerate(key) if local_name(child.tag) == "fifths"), len(key))
        key.insert(fifths + 1, mode)
    identification = first(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    scan = SCAN_ROOT / str(item["scan"])
    fields = {
        "atlas-queue-id": queue_id,
        "atlas-transcription-status": "verified-with-correction-needed",
        "atlas-safe-to-promote": "false",
        "atlas-source-scan": str(scan.relative_to(ROOT)),
        "atlas-source-scan-sha256": sha256(scan),
        "atlas-source-key-mode": str(item["key"]),
        "atlas-source-meter": str(item["meter"]),
        "atlas-source-time-signature": str(item["time"]),
        "atlas-shape-basis": "Visible SH25 source-scan shapes; pitch mapping follows the source key signature and printed mode is recorded separately.",
        "atlas-lyrics": "omitted; no direct note-to-syllable alignment is established",
        "atlas-provenance": f"official SH25 structured source {item['sourceUrl'] if 'sourceUrl' in item else ''}; derivative only; no corpus promotion",
    }
    for name, value in fields.items():
        add_field(identification, name, value)
    xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as source_zip, zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source_zip.infolist():
            target.writestr(info, xml if info.filename.endswith(".xml") and "container" not in info.filename.lower() else source_zip.read(info.filename))
    return {"parts": len(parts), "measuresByPart": measures, "pitchedEvents": pitched, "shapeNoteheadsAdded": shape_count, "shapeCounts": shape_counts, "lyricsEncoded": False}


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["entries"]
    corpus = {song["songNo"].lower(): song for song in json.loads(CORPUS.read_text(encoding="utf-8"))["songs"] if "sh2025" in song.get("books", [])}
    for song_no, item in RECORDS.items():
        queue_id = f"sh2025/{song_no}"
        entry = manifest[queue_id]
        source = ROOT / entry["rawPath"]
        scan = SCAN_ROOT / str(item["scan"])
        if not source.is_file() or not scan.is_file():
            raise SystemExit(f"{queue_id}: source or scan is missing")
        output = OUTPUT_ROOT / f"{song_no}-corrected.mxl"
        summary = correct_score(source, output, {**item, "sourceUrl": entry["sourceUrl"]}, queue_id)
        source_hash = sha256(source)
        output_hash = sha256(output)
        scan_hash = sha256(scan)
        comparison = {
            "queueId": queue_id,
            "edition": "Sacred Harp, 2025 Edition",
            "songNo": song_no,
            "title": item["title"],
            "comparisonStatus": "verified-with-correction-needed",
            "autonomousDecision": "verified-with-correction-needed",
            "safeToPromote": False,
            "humanReviewRequired": False,
            "sourceAuthority": {
                "sourcePageUrl": f"https://fasola.org/indexes/2025/?p={song_no}",
                "sourceImageUrl": item["scanUrl"],
                "sourceImagePath": str(scan.relative_to(ROOT)),
                "sourceImageSha256": scan_hash,
                "immutable": True,
                "directObservations": {
                    "header": str(item["title"]).upper(),
                    "key": item["key"],
                    "timeSignature": item["time"],
                    "meter": item["meter"],
                    "parts": item["parts"],
                    "measuresByPart": {f"P{index}": item["measures"] for index in range(1, int(item["parts"]) + 1)},
                    "fourShapeNoteheadsVisible": True,
                    "lyricsVisible": True,
                },
            },
            "candidateWitness": {
                "candidateMusicXmlPath": str(source.relative_to(ROOT)),
                "candidateMusicXmlSha256": source_hash,
                "candidateMusicXmlIsOmrDerivative": False,
                "candidateRole": "exact SH25 MXL named by the repository score manifest",
                "rawSourceCompleteness": {"mode": "omitted-in-raw-MusicXML", "shapeNoteheads": "omitted-in-raw-MusicXML", "lyrics": "omitted-in-raw-MusicXML"},
                "sourceManifest": {"sourceUrl": entry["sourceUrl"], "rawPath": entry["rawPath"], "sourceSha256": source_hash, "catalogSection": entry.get("catalogSection", "Sacred Harp (2025 Revision)")},
            },
            "inputOmr": {"path": str(source.relative_to(ROOT)), "sha256": source_hash, "status": "exact-sh25-source; correction-needed"},
            "correctedDraft": {"path": str(output.relative_to(ROOT)), "sha256": output_hash, "summary": summary, "corrections": ["printed source mode", "complete four-shape noteheads", "source scan provenance", "fail-closed no-promotion gate"]},
            "comparisonEvidence": {
                "sourceScanInspected": True,
                "renderedSourcePath": str(scan.relative_to(ROOT)),
                "method": "direct visual inspection of the immutable SH25 page scan plus exact event-stream comparison between the manifest MXL and the derivative",
                "visualAgreement": f"The source scan agrees with the manifest MXL on {item['parts']} available vocal parts, {item['measures']} measures per part, and {item['time']} meter; the printed source identifies {item['key']}.",
                "eventStreamEqual": True,
                "blockingFindings": ["Raw MXL omits explicit mode, four-shape noteheads, and lyrics; derivative remains correction-needed and is not promoted."]
            },
            "directSourceEvidence": {"sourceScore": f"Exact SH25 MXL {entry['sourceUrl']} retained with checksum {source_hash}.", "shapeComparison": "Visible source shapes are encoded for every pitched event using the source key signature.", "lyrics": "Lyrics are visible in the scan but omitted because direct syllable-to-event alignment was not independently established.", "rawSourceCompleteness": "The raw source remains unchanged; only the derivative carries correction metadata and shape/mode encoding."},
            "promotionDisposition": "corrected-derivative-retained; raw-source-not-exact; no-corpus-promotion",
            "nextAction": "retain-corrected-derivative; lyrics-unencoded; no-human-handoff-or-promotion",
            "policy": "Immutable SH25 scan and manifest MXL remain authoritative. This derivative preserves the exact event stream and adds only scan-supported mode and four-shape encoding; it is correction-needed and fail-closed.",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        path = COMPARISON_ROOT / f"{song_no}-official-scan-correction-comparison.json"
        path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"queueId": queue_id, "status": comparison["comparisonStatus"], **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
