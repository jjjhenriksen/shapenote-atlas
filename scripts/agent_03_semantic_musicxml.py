"""Source-faithful MusicXML semantics for the agent-03 audit.

This module is deliberately additive.  It records only information present in
the MusicXML witness: lyric attachments, repeat/ending directives, editorial
markings, and event timing.  Missing source elements remain absent from the
corresponding lists and are reflected as ``unavailable`` in
``semanticAvailability``.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(element: ET.Element, name: str) -> str:
    for child in element:
        if local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _attributes(element: ET.Element, names: tuple[str, ...] = ()) -> dict[str, str]:
    return {
        name: element.attrib[name]
        for name in names
        if element.attrib.get(name, "") != ""
    }


def _text_nodes(element: ET.Element, name: str) -> list[str]:
    return [
        (node.text or "").strip()
        for node in element.iter()
        if local_name(node.tag) == name and (node.text or "").strip()
    ]


def _root_from_archive(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        rootfile = ""
        if "META-INF/container.xml" in names:
            container = ET.fromstring(archive.read("META-INF/container.xml"))
            for node in container.iter():
                if local_name(node.tag) == "rootfile" and node.attrib.get("full-path"):
                    rootfile = node.attrib["full-path"]
                    break
        candidates = [rootfile] if rootfile and rootfile in names else []
        candidates.extend(
            name
            for name in archive.namelist()
            if name.endswith((".xml", ".musicxml"))
            and "container" not in name.lower()
            and name not in candidates
        )
        for name in candidates:
            root = ET.fromstring(archive.read(name))
            if local_name(root.tag) in {"score-partwise", "score-timewise"}:
                return root
        raise ValueError("archive contains no score-partwise or score-timewise XML")


def _parse_number(value: str, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_lyric(lyric: ET.Element) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("number", "name", "justify", "placement"):
        if lyric.attrib.get(key, ""):
            result[key] = lyric.attrib[key]
    text = child_text(lyric, "text")
    syllabic = child_text(lyric, "syllabic")
    if text:
        result["text"] = text
    if syllabic:
        result["syllabic"] = syllabic
    elisions = _text_nodes(lyric, "elision")
    if elisions:
        result["elision"] = elisions
    extend = next((node for node in lyric if local_name(node.tag) == "extend"), None)
    if extend is not None:
        result["extend"] = _attributes(extend, ("type", "default-x", "default-y", "relative-x", "relative-y"))
    return result


def _parse_editorial(node: ET.Element, location: dict[str, str]) -> list[dict[str, Any]]:
    markings: list[dict[str, Any]] = []
    for child in node.iter():
        kind = local_name(child.tag)
        if kind == "notations":
            continue
        if child is node:
            continue
        if kind in {
            "articulations", "ornaments", "technical", "fermata", "arpeggiate",
            "accent", "strong-accent", "staccato", "staccatissimo", "tenuto",
            "caesura", "trill-mark", "turn", "inverted-mordent", "up-bow",
            "down-bow", "fingering", "breath-mark", "other-articulation",
            "other-ornament", "other-technical", "footnote", "level",
            "tied", "tuplet", "slur", "glissando", "slide",
        }:
            marking: dict[str, Any] = {"kind": kind, **location}
            marking.update(_attributes(child, tuple(sorted(child.attrib))))
            text = (child.text or "").strip()
            if text:
                marking["text"] = text
            markings.append(marking)
    return markings


def _parse_direction(direction: ET.Element, measure: str) -> dict[str, Any]:
    item: dict[str, Any] = {"measure": measure, "kind": "direction"}
    item.update(_attributes(direction, ("placement", "directive", "voice", "staff")))
    types: list[dict[str, Any]] = []
    for node in direction.iter():
        kind = local_name(node.tag)
        if kind not in {"words", "rehearsal", "dynamics", "segno", "coda", "pedal", "metronome", "octave-shift"}:
            continue
        entry: dict[str, Any] = {"kind": kind}
        text = (node.text or "").strip()
        if text:
            entry["text"] = text
        entry.update(_attributes(node, tuple(sorted(node.attrib))))
        types.append(entry)
    if types:
        item["types"] = types
    return item


def _parse_barline(barline: ET.Element, measure: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    location = {"measure": measure}
    barline_info: dict[str, Any] = {"kind": "barline", **location}
    barline_info.update(_attributes(barline, ("location", "bar-style", "segno", "coda", "divisions")))
    for child in barline:
        kind = local_name(child.tag)
        if kind == "repeat":
            directive: dict[str, Any] = {"kind": "repeat", **location}
            directive.update(_attributes(child, tuple(sorted(child.attrib))))
            result.append(directive)
        elif kind == "ending":
            directive = {"kind": "ending", **location}
            directive.update(_attributes(child, tuple(sorted(child.attrib))))
            text = (child.text or "").strip()
            if text:
                directive["text"] = text
            result.append(directive)
    if len(barline_info) > 2:
        result.append(barline_info)
    return result


def _parse_sound(sound: ET.Element, measure: str) -> dict[str, Any]:
    result: dict[str, Any] = {"kind": "sound", "measure": measure}
    result.update(_attributes(sound, tuple(sorted(sound.attrib))))
    return result


def parse_source(path: Path) -> dict[str, Any]:
    """Parse a zipped MusicXML source with semantic and timing evidence."""
    root = _root_from_archive(path)
    part_names = {
        node.attrib["id"]: child_text(node, "part-name") or node.attrib["id"]
        for node in root.iter()
        if local_name(node.tag) == "score-part" and node.attrib.get("id")
    }
    parts: list[dict[str, Any]] = []
    key_declarations: list[dict[str, Any]] = []
    time_declarations: list[str] = []
    lyrics: list[dict[str, Any]] = []
    repeat_semantics: list[dict[str, Any]] = []
    editorial_markings: list[dict[str, Any]] = []

    for part in root:
        if local_name(part.tag) != "part":
            continue
        part_id = part.attrib.get("id", "")
        part_name = part_names.get(part_id, part_id or "Part")
        cursor = 0.0
        divisions = 1.0
        events: list[dict[str, Any]] = []
        measure_numbers: list[str] = []
        measure_semantics: list[dict[str, Any]] = []
        current_clefs: dict[str, str] = {}
        default_clef = "treble"

        for measure in part:
            if local_name(measure.tag) != "measure":
                continue
            measure_number = measure.attrib.get("number", "")
            measure_numbers.append(measure_number)
            measure_start = cursor
            measure_max_cursor = measure_start
            previous_note: tuple[tuple[str, str], float] | None = None
            measure_record: dict[str, Any] = {"measure": measure_number, "start": round(measure_start, 3)}
            barlines: list[dict[str, Any]] = []
            directions: list[dict[str, Any]] = []

            for item in measure:
                item_name = local_name(item.tag)
                if item_name == "attributes":
                    raw_divisions = child_text(item, "divisions")
                    parsed_divisions = _parse_number(raw_divisions)
                    if parsed_divisions and parsed_divisions > 0:
                        divisions = parsed_divisions
                    key = next((node for node in item if local_name(node.tag) == "key"), None)
                    if key is not None and child_text(key, "fifths"):
                        declaration = {
                            "fifths": child_text(key, "fifths"),
                            "mode": child_text(key, "mode"),
                            "modePresent": bool(child_text(key, "mode")),
                        }
                        key_declarations.append(declaration)
                    time = next((node for node in item if local_name(node.tag) == "time"), None)
                    if time is not None and child_text(time, "beats") and child_text(time, "beat-type"):
                        time_declarations.append(f"{child_text(time, 'beats')}/{child_text(time, 'beat-type')}")
                    for clef in (node for node in item if local_name(node.tag) == "clef"):
                        sign = child_text(clef, "sign").upper()
                        clef_name = {"G": "treble", "C": "alto", "F": "bass"}.get(sign, default_clef)
                        if child_text(clef, "clef-octave-change") == "-1":
                            clef_name = "tenor"
                        number = clef.attrib.get("number", "1")
                        current_clefs[number] = clef_name
                        if number == "1":
                            default_clef = clef_name
                elif item_name in {"backup", "forward"}:
                    duration = _parse_number(child_text(item, "duration"), 0.0) or 0.0
                    delta = duration / divisions
                    cursor = cursor - delta if item_name == "backup" else cursor + delta
                    measure_max_cursor = max(measure_max_cursor, cursor)
                    previous_note = None
                elif item_name == "barline":
                    parsed = _parse_barline(item, measure_number)
                    barlines.extend(parsed)
                    repeat_semantics.extend({"part": part_id or part_name, **entry} for entry in parsed if entry["kind"] in {"repeat", "ending"})
                elif item_name == "direction":
                    parsed = _parse_direction(item, measure_number)
                    directions.append(parsed)
                    editorial_markings.append({"part": part_id or part_name, **parsed})
                elif item_name == "sound":
                    parsed = _parse_sound(item, measure_number)
                    directions.append(parsed)
                    repeat_semantics.append({"part": part_id or part_name, **parsed})
                elif item_name == "note":
                    raw_duration = child_text(item, "duration")
                    duration = _parse_number(raw_duration)
                    beats = duration / divisions if duration is not None else None
                    voice = child_text(item, "voice")
                    staff = child_text(item, "staff") or "1"
                    stream = (voice, staff)
                    chord = any(local_name(child.tag) == "chord" for child in item)
                    onset = cursor
                    if chord and previous_note is not None and previous_note[0] == stream:
                        onset = previous_note[1]
                    pitch = next((node for node in item if local_name(node.tag) == "pitch"), None)
                    event: dict[str, Any] = {
                        "onset": round(onset, 3),
                        "beats": round(beats, 3) if beats is not None else None,
                        "measure": measure_number,
                        "measureOnset": round(onset - measure_start, 3),
                        "rest": pitch is None,
                        "voice": voice,
                        "staff": staff,
                        "type": child_text(item, "type"),
                        "dots": sum(local_name(child.tag) == "dot" for child in item),
                        "accidental": child_text(item, "accidental"),
                        "notehead": child_text(item, "notehead"),
                        "clef": current_clefs.get(staff, default_clef),
                    }
                    if pitch is not None:
                        event.update({
                            "step": child_text(pitch, "step"),
                            "alter": int(child_text(pitch, "alter") or "0"),
                            "octave": int(child_text(pitch, "octave") or "4"),
                        })
                    lyric_items = [_parse_lyric(node) for node in item if local_name(node.tag) == "lyric"]
                    lyric_items = [entry for entry in lyric_items if entry]
                    if lyric_items:
                        event["lyrics"] = lyric_items
                        lyrics.append({
                            "part": part_id or part_name,
                            "measure": measure_number,
                            "eventIndex": len(events),
                            "onset": round(onset, 3),
                            "syllables": lyric_items,
                        })
                    note_editorial = _parse_editorial(
                        next((node for node in item if local_name(node.tag) == "notations"), item),
                        {"part": part_id or part_name, "measure": measure_number, "eventIndex": str(len(events))},
                    )
                    if note_editorial:
                        event["editorialMarkings"] = note_editorial
                        editorial_markings.extend(note_editorial)
                    ties = [child.attrib.get("type", "") for child in item if local_name(child.tag) == "tie"]
                    ties.extend(child.attrib.get("type", "") for node in item if local_name(node.tag) == "notations" for child in node.iter() if local_name(child.tag) == "tied")
                    if "start" in ties:
                        event["tieStart"] = True
                    if "stop" in ties:
                        event["tieStop"] = True
                    events.append(event)
                    previous_note = (stream, onset)
                    if beats is not None:
                        measure_max_cursor = max(measure_max_cursor, onset + beats)
                        if not chord:
                            cursor += beats

            measure_record["end"] = round(measure_max_cursor, 3)
            if barlines:
                measure_record["barlines"] = barlines
            if directions:
                measure_record["directions"] = directions
            measure_semantics.append(measure_record)
            cursor = measure_max_cursor

        parts.append({
            "name": part_name,
            "events": events,
            "measureNumbers": measure_numbers,
            "measureSemantics": measure_semantics,
            "clefs": current_clefs,
        })

    for node in root.iter():
        if local_name(node.tag) in {"footnote", "level"}:
            editorial_markings.extend(_parse_editorial(node, {"scope": "document"}))

    all_events = [event for part in parts for event in part["events"]]
    missing_duration_events = sum(event.get("beats") is None for event in all_events)
    non_positive_duration_events = sum(event.get("beats") is not None and event["beats"] <= 0 for event in all_events)
    negative_onsets = sum(event["onset"] < 0 for event in all_events)
    negative_measure_onsets = sum(event["measureOnset"] < 0 for event in all_events)
    timing_status = (
        "unavailable"
        if not all_events or missing_duration_events == len(all_events)
        else "encoded"
        if not missing_duration_events and not non_positive_duration_events and not negative_onsets and not negative_measure_onsets
        else "partial"
    )
    return {
        "workTitle": next(((node.text or "").strip() for node in root.iter() if local_name(node.tag) == "work-title" and (node.text or "").strip()), ""),
        "parts": parts,
        "keyDeclarations": key_declarations,
        "timeDeclarations": list(dict.fromkeys(time_declarations)),
        "lyrics": lyrics,
        "repeatSemantics": repeat_semantics,
        "editorialMarkings": editorial_markings,
        "timingAudit": {
            "events": len(all_events),
            "missingDurationEvents": missing_duration_events,
            "nonPositiveDurationEvents": non_positive_duration_events,
            "negativeOnsets": negative_onsets,
            "negativeMeasureOnsets": negative_measure_onsets,
        },
        "semanticAvailability": {
            "lyrics": "encoded" if lyrics else "unavailable",
            "repeats": "encoded" if any(item.get("kind") == "repeat" for item in repeat_semantics) else "unavailable",
            "endings": "encoded" if any(item.get("kind") == "ending" for item in repeat_semantics) else "unavailable",
            "editorialMarkings": "encoded" if editorial_markings else "unavailable",
            "eventTiming": timing_status,
        },
    }
