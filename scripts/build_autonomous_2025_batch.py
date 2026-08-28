#!/usr/bin/env python3
"""Build corrected, fail-closed MusicXML derivatives for the 115/116 batch.

The normalized OMR files are retained as inputs. This script corrects only
facts directly visible in the retained source pages: part labels, printed
key/mode, printed meter, and the four-shape notehead spelling derived from
the source key. It never claims that OMR pitches, rhythms, lyrics, or
obscured note intersections are source-verified.
"""

from __future__ import annotations

import hashlib
import argparse
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "work" / "omr" / "autonomous-transcriptions" / "2025"
SOURCE_META = ROOT / "public" / "source-metadata-observations.json"

SHAPES = ["fa", "sol", "la", "fa", "sol", "la", "mi"]
STEPS = ["C", "D", "E", "F", "G", "A", "B"]
STEP_INDEX = {step: index for index, step in enumerate(STEPS)}
MINOR_FIFTHS = {"A": 0, "E": 1, "B": 2, "F#": 3, "C#": 4, "G#": 5, "D#": 6, "A#": 7, "Ab": -1, "Eb": -2, "Bb": -3, "F": -4, "C": -3, "G": -2, "D": -1}
MAJOR_FIFTHS = {"C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F#": 6, "C#": 7, "F": -1, "Bb": -2, "Eb": -3, "Ab": -4, "Db": -5, "Gb": -6, "Cb": -7}

BATCH = {
    "115": {
        "title": "Holbrook",
        "input": "work/omr/cleaned-normalized-v2-115-holbrook-a7e53368d3/work__source-images__2025__115-holbrook-a7e53368d3.mxl",
        "source_image": "work/source-images/2025/115-holbrook-a7e53368d3.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/115-Holbrook/115.jpg",
        "key": "F#",
        "mode": "minor",
        "time": ("2", "4"),
        "meter": "Particular Meter",
        "blocking_findings": [
            "The retained source scan visibly prints F# minor and 2/4, but the normalized OMR input carries inconsistent key values across parts; the corrected derivative normalizes these visible attributes without asserting pitch correctness.",
            "The 22-measure, four-part structure is present, but source-to-OMR duration checks still show over/under-full measures in multiple parts, so note and rhythm fidelity is not established.",
            "A diagonal DO NOT COPY watermark crosses the lower-middle source systems; note intersections and four-shape identities in those regions cannot be asserted from the OMR alone.",
            "The source lyrics are legible, but the OMR has no reliable lyric underlay; lyrics are omitted from this draft without treating that omission as an independent notation blocker.",
        ],
    },
    "116": {
        "title": "Hooper",
        "input": "work/omr/cleaned-normalized-v2-116-hooper-12dea70831/work__source-images__2025__116-hooper-12dea70831.mxl",
        "source_image": "work/source-images/2025/116-hooper-12dea70831.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/116-Hooper/116.jpg",
        "key": "B",
        "mode": "minor",
        "time": ("6", "4"),
        "meter": "Particular Meter",
        "blocking_findings": [
            "The retained source scan visibly prints B minor and 6/4, while the normalized OMR input reads 3/4; the corrected derivative changes the meter to the source-observed value but does not silently rewrite all event durations.",
            "The 13-measure, four-part structure is present, but source-to-OMR duration checks still show over/under-full measures in multiple parts, so note and rhythm fidelity is not established.",
            "A diagonal DO NOT COPY watermark crosses the lower-middle source systems; note intersections and four-shape identities in those regions cannot be asserted from the OMR alone.",
            "The source lyrics are legible, but the OMR has no reliable lyric underlay; lyrics are omitted from this draft without treating that omission as an independent notation blocker.",
        ],
    },
    "130": {
        "title": "The Old Graveyard",
        "input": "work/omr/clean-source-candidates/130-the-old-graveyard-boast-ye-not-8s-7s-1270fe4031/source-candidate.mxl",
        "source_image": "work/source-images/2025/130-the-old-graveyard-6121ddb395.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/130-The-Old-Graveyard/130.jpg",
        "key": "G",
        "mode": "minor",
        "time": ("2", "4"),
        "meter": "8s & 7s.",
        "input_status": "independent-public-candidate-omr",
        "blocking_findings": [
            "The retained source scan visibly prints The Old Graveyard, G minor, and 2/4 with 23 measures per part; the independent witness is titled Boast Ye Not, changes the left-side attribution, and contains 25 measures plus an extra third stanza.",
            "The independent witness is a public composer PDF and OMR derivative, not a publisher-delivered 2025 MusicXML source; title similarity and shared visible contours do not establish edition identity.",
            "The diagonal DO NOT COPY watermark crosses the source lower-middle systems, so every obscured note and four-shape identity cannot be asserted autonomously from the available evidence.",
            "Both structured witnesses omit lyric underlay; the source lyrics are legible but cannot be safely aligned without fabricating event-level lyrics.",
        ],
    },
    "184": {
        "title": "And Jesus Crucified",
        "input": "work/omr/clean-source-candidates/184-and-jesus-crucified-and-jesus-crucified-7s-6s-c3b76d469e/source-candidate.mxl",
        "source_image": "work/source-images/2025/184-and-jesus-crucified-bb8d27f0da.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/184-And-Jesus-Crucified/184.jpg",
        "key": "E",
        "mode": "minor",
        "time": ("6", "8"),
        "meter": "7,6,7,6,7,8,7,6",
        "input_status": "independent-public-candidate-omr",
        "blocking_findings": [
            "The retained source scan visibly prints And Jesus Crucified, E minor, and 6/8; the independent witness matches the broad four-part layout but uses a Methodist Hymn Book header and a shortened attribution.",
            "The independent witness is a public composer PDF and OMR derivative, while the retained source-scan OMR reports a divergent 12-measure structure against the 13-measure independent witness; this is not sufficient for autonomous note/rhythm proof.",
            "The diagonal DO NOT COPY watermark crosses the source middle system, so obscured note intersections and four-shape identities cannot be asserted autonomously from the available evidence.",
            "Both structured witnesses omit lyric underlay; the source lyrics are legible but cannot be safely aligned without fabricating event-level lyrics.",
        ],
    },
    "188": {
        "title": "Ephesus",
        "input": "work/omr/clean-source-candidates/188-ephesus-oak-grove-road-l-p-m-8a5fa817a0/source-candidate.mxl",
        "source_image": "work/source-images/2025/188-ephesus-aa1817a576.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/100-199/188-Ephesus/188.jpg",
        "key": "Bb",
        "mode": "major",
        "time": ("4", "4"),
        "meter": "Long Particular Meter (8,8,8,8,8,8)",
        "input_status": "independent-public-candidate-omr",
        "blocking_findings": [
            "The retained source scan visibly prints Ephesus L.P.M., B-flat major, and 4/4 with 24 measures per part; the independent witness is Oak Grove Road L.P.M., carries Isaac Watts 1707 and a different arranger-date line, and contains 28 measures per part.",
            "The independent witness is a public composer PDF and OMR derivative, not a publisher-delivered 2025 MusicXML source; close text-family and contour agreement does not establish edition identity.",
            "The diagonal DO NOT COPY watermark crosses the source middle and lower systems, so obscured note intersections and four-shape identities cannot be asserted autonomously.",
            "Both structured witnesses omit lyric underlay even though the source lyrics are legible; event-level lyrics are intentionally not fabricated.",
        ],
    },
    "231": {
        "title": "Seiler",
        "input": "work/omr/clean-source-candidates/231-seiler-seiler-c-m-6952cc9dd2/source-candidate.mxl",
        "source_image": "work/source-images/2025/231-seiler-aac0c1fe36.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/231-Seiler/231.jpg",
        "key": "E",
        "mode": "minor",
        "time": ("4", "4"),
        "meter": "Common Meter (8,6,8,6)",
        "input_status": "independent-public-candidate-omr",
        "blocking_findings": [
            "The retained source scan visibly prints Seiler C.M., E minor, and 4/4; the source-page structure is 13 measures per part while the independent candidate has 16 measures per part.",
            "The independent witness prints an expanded 2009, 2019 credit line while the 2025 source prints 2019; it is a public composer PDF and OMR derivative, not an authorized 2025 structured source.",
            "The diagonal DO NOT COPY watermark crosses the source middle systems, so obscured note intersections and four-shape identities cannot be asserted autonomously.",
            "Both structured witnesses omit lyric underlay even though the source lyrics are legible; event-level lyrics are intentionally not fabricated.",
        ],
    },
    "213b": {
        "title": "Trembling Spirit",
        "input": "work/omr/213b-trembling-spirit/source.mxl",
        "source_image": "work/source-images/2025/213b-trembling-spirit-d190953cb7.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/213b-Trembling-Spirit/213b.jpg",
        "key": "E",
        "mode": "minor",
        "time": ("4", "4"),
        "meter": "Short Meter (6,6,8,6)",
        "input_status": "retained-source-scan-omr",
        "blocking_findings": [
            "The retained source scan visibly prints Trembling Spirit S.M., E minor, and common time with four vocal parts and eight measures per part; the independent witness has the same title/text family and eight-measure structure.",
            "The independent witness is a public composer PDF and OMR derivative rather than a publisher-delivered 2025 MusicXML source; its credit line and engraving are not sufficient to establish exact edition identity by title and measure count alone.",
            "A diagonal DO NOT COPY watermark crosses the second system of the source page, obscuring note intersections and four-shape identities that cannot be asserted autonomously from the candidate event stream.",
            "The candidate has no reliable source-faithful lyric underlay; lyrics are intentionally not fabricated, and standard MusicXML does not prove each visible Sacred Harp shape without note-for-note source alignment.",
        ],
    },
    "263": {
        "title": "Every Grace",
        "input": "work/omr/263-every-grace/source.mxl",
        "source_image": "work/source-images/2025/263-every-grace-3b35cf9ccf.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/263-Every-Grace/263.jpg",
        "key": "G",
        "mode": "major",
        "time": ("4", "4"),
        "meter": "Short Meter (6,6,8,6)",
        "input_status": "retained-source-scan-omr",
        "blocking_findings": [
            "The retained source scan visibly prints Every Grace S.M., G major, common time, four vocal parts, and 13 measures per part; the independent witness has the same title/text family and 13-measure structure.",
            "The independent witness is a public composer PDF and OMR derivative rather than a publisher-delivered 2025 MusicXML source; matching title and measure count do not establish exact edition identity or every note and rhythm.",
            "A diagonal DO NOT COPY watermark crosses the source lower-middle systems, obscuring note intersections and four-shape identities that cannot be asserted autonomously from the candidate event stream.",
            "The candidate lyric underlay is not reliable enough to prove the two source stanzas event-by-event; lyrics are intentionally not fabricated, and derived shape tags remain non-authoritative.",
        ],
    },
    "367": {
        "title": "Nassau",
        "input": "work/omr/367-nassau/source.mxl",
        "source_image": "work/source-images/2025/367-nassau-2726211e88.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/367-Nassau/367.jpg",
        "key": "A",
        "mode": "minor",
        "time": ("4", "4"),
        "meter": "Common Meter Double (8,6,8,6,8,6,8,6)",
        "input_status": "retained-source-scan-omr",
        "blocking_findings": [
            "The retained source scan visibly prints Nassau C.M.D., A minor, common time, four vocal parts, and 24 measures per part; the independent witness has the same title/text family and 24-measure structure.",
            "The independent witness is a public composer PDF and OMR derivative rather than a publisher-delivered 2025 MusicXML source; matching title and measure count do not establish exact edition identity or every note and rhythm.",
            "A diagonal DO NOT COPY watermark crosses the source middle systems, obscuring note intersections and four-shape identities that cannot be asserted autonomously from the candidate event stream.",
            "The candidate lyric underlay does not prove all source text alignment event-by-event; lyrics are intentionally not fabricated, and derived shape tags remain non-authoritative.",
        ],
    },
    "526": {
        "title": "Schwab",
        "input": "work/omr/526-schwab/source.mxl",
        "source_image": "work/source-images/2025/526-schwab-83789d8f31.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/526-Schwab/526.jpg",
        "key": "F#",
        "mode": "minor",
        "time": ("2", "4"),
        "meter": "Long Meter Half (8,8)",
        "input_status": "retained-source-scan-omr",
        "blocking_findings": [
            "The retained source scan visibly prints Schwab L.M.H., F# minor, 2/4, four vocal parts, and 16 measures per part; the same-title public witness has 18 measures per part.",
            "The independent witness is a public composer PDF and OMR derivative rather than a publisher-delivered 2025 MusicXML source; title and related text do not establish exact edition identity.",
            "A diagonal DO NOT COPY watermark crosses the source lower-middle systems, obscuring note intersections and four-shape identities that cannot be asserted autonomously.",
            "The candidate lyric underlay does not provide source-faithful event alignment; lyrics are intentionally not fabricated and derived shape tags remain non-authoritative.",
        ],
    },
    "255": {
        "title": "Mechanicville",
        "input": "work/omr/255-mechanicville/255-mechanicville.mxl",
        "source_image": "work/source-transcriptions/2025/255-mechanicville.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/255-Mechanicville/255.jpg",
        "key": "E",
        "mode": "minor",
        "time": ("4", "4"),
        "meter": "Long Meter (8,8,8,8)",
        "input_status": "retained-source-scan-omr",
        "blocking_findings": [
            "The retained source scan visibly prints Mechanicville L.M., E minor, 4/4, four vocal parts, and 18 measures per part; the same-title public witness has 22 measures per part.",
            "The independent witness is a public composer PDF and OMR derivative rather than a publisher-delivered 2025 MusicXML source; title and text agreement do not establish exact edition identity.",
            "A diagonal DO NOT COPY watermark crosses the source middle systems, obscuring note intersections and four-shape identities that cannot be asserted autonomously.",
            "The candidate lyrics are not a source-faithful event alignment; lyrics are intentionally not fabricated and derived shape tags remain non-authoritative.",
        ],
    },
    "256": {
        "title": "Northampton",
        "input": "work/omr/256-northampton/256-northampton.mxl",
        "source_image": "work/source-transcriptions/2025/256-northampton.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/256-Northampton/256.jpg",
        "key": "F#",
        "mode": "minor",
        "time": ("4", "4"),
        "meter": "Long Meter (8,8,8,8)",
        "input_status": "retained-source-scan-omr",
        "blocking_findings": [
            "The retained source scan visibly prints Northampton L.M., F# minor, 4/4, four vocal parts, and 21 measures per part; the same-title public witness has 18 measures per part.",
            "The independent witness is a public composer PDF and OMR derivative rather than a publisher-delivered 2025 MusicXML source; title and text agreement do not establish exact edition identity.",
            "A diagonal DO NOT COPY watermark crosses the source lower-middle systems, obscuring note intersections and four-shape identities that cannot be asserted autonomously.",
            "The candidate lyrics are not a source-faithful event alignment; lyrics are intentionally not fabricated and derived shape tags remain non-authoritative.",
        ],
    },
    "571": {
        "title": "Hamrick",
        "input": "work/omr/571-hamrick/source.mxl",
        "source_image": "work/source-images/2025/571-hamrick-6571677dbf.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/500-599/571-Hamrick/571.jpg",
        "key": "Bb",
        "mode": "major",
        "time": ("3", "4"),
        "meter": "7s.",
        "input_status": "retained-source-scan-omr",
        "blocking_findings": [
            "The retained source scan visibly prints Hamrick 7s., B-flat major, 3/4, and four vocal parts; its source-scan OMR records 13 measures per part while the same-title public witness records 16.",
            "The retained source-scan OMR duration/event grouping is not source-verified at every measure; the independent public witness is secondary and cannot repair those events by title alone.",
            "A diagonal DO NOT COPY watermark crosses the second and third source systems; only the specifically intersecting events are unresolved for that reason, while the remaining events still fail closed on OMR uncertainty.",
            "Lyrics are retained only when present in the source-derived event stream; their omission is not an independent blocker where notation remains usable.",
        ],
    },
    "463": {
        "title": "Morel",
        "input": "work/omr/463-morel/source.mxl",
        "source_image": "work/source-images/2025/463-morel-7a60147b31.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/463-Morel/463.jpg",
        "key": "E",
        "mode": "minor",
        "time": ("4", "4"),
        "meter": "Common Meter (8,6,8,6)",
        "input_status": "retained-source-scan-omr",
        "blocking_findings": [
            "The retained source scan visibly prints Morel C.M., E minor, 4/4, four vocal parts, and 17 measures per part; the same-title public witness is a related alternate page with 19 measures per part.",
            "The retained source-scan OMR has non-target measure durations at P1 m6,7,8,9,11,12,13,15,17; P2 m1-17; P3 m1,3,4,6-17; and P4 m1-4,6-8,10-13,15-17. Those exact event groups remain unverified; the alternate public witness cannot repair them by title/text agreement alone.",
            "A diagonal DO NOT COPY watermark crosses the lower-middle source systems, so only the specifically intersecting source events are unresolved for that reason; the remaining draft still fails closed on its duration audit.",
            "Lyrics are optional for this gate and are not used as an independent blocker; no unsupported lyric alignment is inserted into the structured draft.",
        ],
    },
    "459": {
        "title": "Hurricane Creek",
        "input": "work/omr/459-hurricane-creek/source.mxl",
        "source_image": "work/source-images/2025/459-hurricane-creek-7c66fd96d3.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/459-Hurricane-Creek/459.jpg",
        "key": "A",
        "mode": "major",
        "time": ("2", "4"),
        "meter": "Long Meter Half (8,8)",
        "input_status": "retained-source-scan-omr",
        "blocking_findings": [
            "The retained source scan visibly prints Hurricane Creek L.M.H., A major, 2/4, and four vocal parts; its source-scan OMR records 19 measures per part while the related public witness records 24.",
            "The retained source-scan OMR has non-target measure durations at P1 m1,4,11,15,16; P2 m3,4,7,9,11-13,15,16; P3 m1,5,9,11,12,14-16; and P4 m1,3,5,9,11,12,14-16,18,19. Those exact event groups remain unverified; the related public witness cannot repair them by title alone.",
            "A diagonal DO NOT COPY watermark crosses the lower-middle source systems; only the specifically intersecting events are unresolved for that reason, while the remaining draft still fails closed on the duration audit.",
            "Lyrics are optional for this gate and are not used as an independent blocker; no unsupported lyric alignment is inserted into the structured draft.",
        ],
    },
    "254": {
        "title": "Warsaw",
        "input": "work/omr/254-warsaw/254-warsaw.mxl",
        "source_image": "work/source-transcriptions/2025/254-warsaw.jpg",
        "source_image_url": "https://sacredharpbremen.org/wp-content/uploads/songs/200-299/254-Warsaw/254.jpg",
        "key": "A",
        "mode": "minor",
        "time": ("6", "4"),
        "meter": "Common Meter (8,6,8,6)",
        "input_status": "retained-source-scan-omr",
        "blocking_findings": [
            "The retained source scan visibly prints Warsaw C.M., A minor, 6/4, four vocal parts, and 17 measures per part; the available public witness is titled Departure C.M.D. and is not an authorized 2025 source.",
            "The retained source-scan OMR duration/event grouping is not source-verified at every measure; the alternate witness cannot repair those events by title/text similarity alone.",
            "A diagonal DO NOT COPY watermark crosses the lower-middle source systems; only the specifically intersecting events are unresolved for that reason, while the remaining draft still fails closed on the duration audit.",
            "Lyrics are optional for this gate and are not used as an independent blocker; no unsupported lyric alignment is inserted into the structured draft.",
        ],
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def first_child(parent: ET.Element, name: str) -> ET.Element | None:
    return next((child for child in parent if local_name(child.tag) == name), None)


def child_text(parent: ET.Element, name: str) -> str:
    child = first_child(parent, name)
    return (child.text or "").strip() if child is not None else ""


def ensure_child(parent: ET.Element, name: str) -> ET.Element:
    child = first_child(parent, name)
    return child if child is not None else ET.SubElement(parent, name)


def parse_key(root: str, mode: str) -> tuple[str, str, int]:
    fifths_by_mode = {"major": MAJOR_FIFTHS, "minor": MINOR_FIFTHS}
    fifths = fifths_by_mode.get(mode, {})
    if root not in fifths:
        raise ValueError(f"unsupported source key: {root} {mode}")
    return root, mode, fifths[root]


def shape_for_step(step: str, root: str, mode: str) -> str | None:
    if step not in STEP_INDEX or root[:1] not in STEP_INDEX:
        return None
    relative_major = STEPS[(STEP_INDEX[root[:1]] + 2) % 7] if mode == "minor" else root[:1]
    degree = (STEP_INDEX[step] - STEP_INDEX[relative_major]) % 7
    return SHAPES[degree]


def add_misc(identification: ET.Element, name: str, value: str) -> None:
    miscellaneous = first_child(identification, "miscellaneous")
    if miscellaneous is None:
        miscellaneous = ET.SubElement(identification, "miscellaneous")
    for old in [x for x in miscellaneous if x.attrib.get("name") == name]:
        miscellaneous.remove(old)
    field = ET.SubElement(miscellaneous, "miscellaneous-field", {"name": name})
    field.text = value


def ensure_identification(root: ET.Element) -> ET.Element:
    identification = first_child(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    return identification


def read_xml(path: Path) -> tuple[bytes, str]:
    with zipfile.ZipFile(path, "r") as archive:
        xml_name = next(
            name for name in archive.namelist()
            if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/")
        )
        return archive.read(xml_name), xml_name


def measure_duration(measure: ET.Element, divisions: float) -> float:
    cursor = 0.0
    maximum = 0.0
    for item in measure:
        name = local_name(item.tag)
        if name == "note":
            duration = float(child_text(item, "duration") or "0") / divisions
            if first_child(item, "chord") is None:
                cursor += duration
            maximum = max(maximum, cursor)
        elif name == "backup":
            cursor -= float(child_text(item, "duration") or "0") / divisions
        elif name == "forward":
            cursor += float(child_text(item, "duration") or "0") / divisions
    return round(maximum, 3)


def correct_xml(xml_bytes: bytes, config: dict[str, object], queue_id: str) -> tuple[bytes, dict[str, object]]:
    root = ET.fromstring(xml_bytes)
    if local_name(root.tag) != "score-partwise":
        raise ValueError("expected score-partwise MusicXML")
    _, mode, fifths = parse_key(str(config["key"]), str(config["mode"]))
    time_beats, time_type = config["time"]  # type: ignore[misc]
    part_names = {"P1": "Soprano", "P2": "Alto", "P3": "Tenor", "P4": "Bass"}
    pitched = 0
    shapes = 0
    durations: dict[str, list[float]] = {}

    for score_part in root.iter():
        if local_name(score_part.tag) == "score-part":
            part_id = score_part.attrib.get("id", "")
            if part_id in part_names:
                name = ensure_child(score_part, "part-name")
                name.text = part_names[part_id]

    for part in [x for x in root if local_name(x.tag) == "part"]:
        part_id = part.attrib.get("id", "")
        durations[part_id] = []
        divisions = 1.0
        for measure in [x for x in part if local_name(x.tag) == "measure"]:
            attributes = first_child(measure, "attributes")
            if attributes is None:
                attributes = ET.Element("attributes")
                measure.insert(0, attributes)
            divisions_text = child_text(attributes, "divisions")
            if divisions_text:
                divisions = float(divisions_text)
            key = ensure_child(attributes, "key")
            fifths_element = ensure_child(key, "fifths")
            fifths_element.text = str(fifths)
            mode_element = ensure_child(key, "mode")
            mode_element.text = mode
            time = ensure_child(attributes, "time")
            beats_element = ensure_child(time, "beats")
            beats_element.text = str(time_beats)
            beat_type_element = ensure_child(time, "beat-type")
            beat_type_element.text = str(time_type)
            durations[part_id].append(measure_duration(measure, divisions))

            for note in [x for x in measure if local_name(x.tag) == "note"]:
                pitch = first_child(note, "pitch")
                if pitch is None:
                    continue
                step = child_text(pitch, "step").upper()
                shape = shape_for_step(step, str(config["key"]), mode)
                pitched += 1
                if shape is None:
                    continue
                old = [x for x in note if local_name(x.tag) == "notehead"]
                for element in old[1:]:
                    note.remove(element)
                if old:
                    old[0].text = shape
                else:
                    notehead = ET.Element("notehead")
                    notehead.text = shape
                    insert_at = next((i for i, x in enumerate(note) if local_name(x.tag) == "stem"), len(note))
                    note.insert(insert_at, notehead)
                shapes += 1

    identification = ensure_identification(root)
    for name, value in {
        "atlas-queue-id": queue_id,
        "atlas-transcription-status": "autonomously-blocked",
        "atlas-safe-to-promote": "false",
        "atlas-source-image": str(config["source_image"]),
        "atlas-source-image-sha256": str(config["source_image_sha256"]),
        "atlas-source-key": f"{config['key']} {mode}",
        "atlas-source-meter": str(config["meter"]),
        "atlas-source-time-signature": f"{time_beats}/{time_type}",
        "atlas-shape-encoding": "derived four-shape spelling from OMR pitch steps and source-visible key; not per-note source verified",
        "atlas-lyrics": "source lyrics visible but not safely aligned in OMR; omitted rather than fabricated",
        "atlas-blocker": "; ".join(str(item) for item in config["blocking_findings"]),
    }.items():
        add_misc(identification, name, value)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True), {
        "parts": len([x for x in root if local_name(x.tag) == "part"]),
        "measuresByPart": {key: len(value) for key, value in durations.items()},
        "pitchedEvents": pitched,
        "shapeNoteheadsAdded": shapes,
        "measureDurations": durations,
    }


def write_mxl(input_path: Path, output_path: Path, xml_bytes: bytes, xml_name: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(input_path, "r") as source, zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            target.writestr(info, xml_bytes if info.filename == xml_name else source.read(info.filename))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", nargs="+", choices=sorted(BATCH), default=["115", "116"])
    args = parser.parse_args()
    observations = {item["queueId"]: item for item in json.loads(SOURCE_META.read_text())["records"]}
    manifest_path = OUTPUT_ROOT / "manifest.json"
    prior_records: dict[str, dict[str, object]] = {}
    if manifest_path.is_file():
        try:
            prior_records = {
                str(item["queueId"]): item
                for item in json.loads(manifest_path.read_text()).get("records", [])
                if item.get("queueId")
            }
        except (OSError, json.JSONDecodeError):
            prior_records = {}
    records: dict[str, dict[str, object]] = dict(prior_records)
    for song_no in args.records:
        raw_config = BATCH[song_no]
        queue_id = f"sh2025/{song_no}"
        observed = observations[queue_id]
        config = dict(raw_config)
        config["source_image_sha256"] = observed["source"]["imageSha256"]
        input_path = ROOT / str(config["input"])
        source_image = ROOT / str(config["source_image"])
        xml_bytes, xml_name = read_xml(input_path)
        corrected_xml, summary = correct_xml(xml_bytes, config, queue_id)
        output_path = OUTPUT_ROOT / f"{song_no}-autonomous-blocked.mxl"
        write_mxl(input_path, output_path, corrected_xml, xml_name)
        audit_path = output_path.with_suffix(".json")
        audit = {
            "queueId": queue_id,
            "edition": "Sacred Harp, 2025 Edition",
            "songNo": song_no,
            "title": config["title"],
            "status": "autonomously-blocked",
            "safeToPromote": False,
            "sourceAuthority": {
                "path": str(config["source_image"]),
                "url": config["source_image_url"],
                "sha256": config["source_image_sha256"],
                "immutable": True,
                "directObservations": {
                    "key": f"{config['key']} {config['mode']}",
                    "timeSignature": f"{config['time'][0]}/{config['time'][1]}",
                    "meter": config["meter"],
                    "parts": 4,
                    "measuresByPart": observed["observations"]["parts"]["measuresByPart"],
                },
            },
            "inputOmr": {
                "path": str(config["input"]),
                "sha256": sha256(input_path),
                "status": str(config.get("input_status", "normalized-v2-omr")),
            },
            "correctedDraft": {
                "path": str(output_path.relative_to(ROOT)),
                "sha256": sha256(output_path),
                "summary": summary,
                "corrections": ["four part names", "source key/mode", "source time signature", "derived four-shape notehead tags", "provenance fields"],
            },
            "comparisonEvidence": {
                "sourceScanInspected": True,
                "renderedSourcePath": str(source_image.relative_to(ROOT)),
                "renderedDraftInputs": [str((ROOT / str(config["input"])).relative_to(ROOT))],
                "method": "direct visual inspection of retained source scan plus structural/event audit of the selected OMR input",
                "blockingFindings": config["blocking_findings"],
            },
            "nextAction": "autonomous-promotion-blocked-by-unresolved-source-event-audit-or-obscured-events; requires-source-event-verification",
        }
        audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
        records[queue_id] = audit
        print(f"{queue_id}: {audit['status']} -> {output_path.relative_to(ROOT)}")

    ordered_records = [records[key] for key in sorted(records)]
    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "version": "autonomous-2025-batch-v1",
        "policy": "Corrected MusicXML derivatives remain fail-closed; no record is promoted while any promoted note, rhythm, part, key, meter, or four-shape event lacks direct source support. Lyrics are optional unless their omission makes the notation unusable.",
        "summary": {"records": len(ordered_records), "autonomouslyVerified": 0, "autonomouslyBlocked": len(ordered_records), "safeToPromote": 0},
        "records": ordered_records,
    }
    (OUTPUT_ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
