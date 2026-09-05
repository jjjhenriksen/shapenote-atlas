#!/usr/bin/env python3
"""Extract source-encoded lyric, barline, ending, and editorial semantics.

This module is deliberately separate from ``build_data.parse_score``.  Agent
11 can validate the new contract without regenerating the shared corpus or
silently changing playback for existing records.  It reads only information
that is explicitly present in the supplied MusicXML; an absent element is
reported as unavailable, never guessed from a tune title, scan text, or
another edition.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


SHAPE_NOTE_MARKINGS = {
    "articulations",
    "ornaments",
    "technical",
    "fermata",
    "arpeggiate",
    "glissando",
    "slide",
    "tremolo",
    "tuplet",
}
SEQUENCE_MARKINGS = {
    "coda",
    "dynamics",
    "metronome",
    "rehearsal",
    "segno",
    "sound",
    "wedge",
    "words",
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(element: ET.Element, name: str) -> Iterable[ET.Element]:
    return (child for child in element if local_name(child.tag) == name)


def child(element: ET.Element, name: str) -> ET.Element | None:
    return next(children(element, name), None)


def text(element: ET.Element | None, name: str) -> str:
    if element is None:
        return ""
    found = child(element, name)
    return (found.text or "").strip() if found is not None else ""


def attributes(element: ET.Element) -> dict[str, str]:
    return {local_name(key): value for key, value in element.attrib.items()}


def read_root(source_path: Path) -> ET.Element:
    if source_path.suffix.lower() == ".mxl":
        with zipfile.ZipFile(source_path) as archive:
            names = set(archive.namelist())
            rootfile = ""
            if "META-INF/container.xml" in names:
                container = ET.fromstring(archive.read("META-INF/container.xml"))
                rootfile_node = next(
                    (node for node in container.iter() if local_name(node.tag) == "rootfile"),
                    None,
                )
                rootfile = rootfile_node.attrib.get("full-path", "") if rootfile_node is not None else ""
            xml_names = [
                name
                for name in archive.namelist()
                if name.lower().endswith(".xml") and "container" not in name.lower()
            ]
            if rootfile and rootfile in names:
                xml_names.insert(0, rootfile)
            if not xml_names:
                raise ValueError(f"no MusicXML document in {source_path}")
            for xml_name in dict.fromkeys(xml_names):
                root = ET.fromstring(archive.read(xml_name))
                if local_name(root.tag) in {"score-partwise", "score-timewise"}:
                    return root
            raise ValueError(f"archive contains no score-partwise MusicXML document: {source_path}")
    return ET.fromstring(source_path.read_bytes())


def lyric_for_note(
    note: ET.Element,
    *,
    part_id: str,
    measure_number: str,
    event_index: int,
    onset: float,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for lyric in children(note, "lyric"):
        lyric_text = text(lyric, "text")
        result.append(
            {
                "partId": part_id,
                "measure": measure_number,
                "eventIndex": event_index,
                "onset": round(onset, 3),
                "number": lyric.attrib.get("number", ""),
                "name": lyric.attrib.get("name", ""),
                # ``verse`` is a source identifier only.  An empty value means
                # MusicXML did not label the lyric verse; it is never guessed
                # to be verse one.
                "verse": lyric.attrib.get("number", "") or lyric.attrib.get("name", ""),
                "text": lyric_text,
                "syllabic": text(lyric, "syllabic"),
                "elision": [
                    (elision.text or "").strip()
                    for elision in children(lyric, "elision")
                    if (elision.text or "").strip()
                ],
                "extend": child(lyric, "extend") is not None,
                "endLine": child(lyric, "end-line") is not None,
                "endParagraph": child(lyric, "end-paragraph") is not None,
            }
        )
    return result


def note_markings(note: ET.Element, *, part_id: str, measure_number: str, event_index: int) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    notations = child(note, "notations")
    if notations is None:
        return result
    for group in notations:
        group_name = local_name(group.tag)
        if group_name not in SHAPE_NOTE_MARKINGS and group_name not in {"technical", "ornaments"}:
            continue
        if not list(group):
            result.append(
                {
                    "partId": part_id,
                    "measure": measure_number,
                    "eventIndex": event_index,
                    "kind": group_name,
                    "group": group_name,
                    "attributes": attributes(group),
                }
            )
            continue
        for marker in group:
            result.append(
                {
                    "partId": part_id,
                    "measure": measure_number,
                    "eventIndex": event_index,
                    "kind": local_name(marker.tag),
                    "group": group_name,
                    "attributes": attributes(marker),
                }
            )
    return result


def direction_markings(direction: ET.Element, *, part_id: str, measure_number: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    direction_type = child(direction, "direction-type")
    if direction_type is None:
        return result
    for marker in direction_type:
        marker_name = local_name(marker.tag)
        if marker_name not in SEQUENCE_MARKINGS:
            continue
        marker_text = " ".join(
            (node.text or "").strip() for node in marker.iter() if (node.text or "").strip()
        )
        result.append(
            {
                "partId": part_id,
                "measure": measure_number,
                "kind": marker_name,
                "text": marker_text,
                "attributes": attributes(marker),
            }
        )
    return result


def parse_barline(barline: ET.Element, *, part_id: str, measure_number: str) -> dict[str, Any]:
    repeat = child(barline, "repeat")
    ending = child(barline, "ending")
    return {
        "partId": part_id,
        "measure": measure_number,
        "location": barline.attrib.get("location", ""),
        "style": text(barline, "bar-style"),
        "repeat": {"direction": repeat.attrib.get("direction", ""), **attributes(repeat)}
        if repeat is not None
        else None,
        "ending": {"number": ending.attrib.get("number", ""), **attributes(ending)}
        if ending is not None
        else None,
    }


def _measure_key(value: str) -> str:
    return str(value).strip()


def _ending_ranges(
    measures: list[str], barlines: list[dict[str, Any]]
) -> tuple[list[tuple[frozenset[str], int, int]], str]:
    index_by_measure = {_measure_key(measure): index for index, measure in enumerate(measures)}
    starts: dict[frozenset[str], int] = {}
    ranges: list[tuple[frozenset[str], int, int]] = []
    for marker in barlines:
        ending = marker.get("ending") or {}
        number = str(ending.get("number", "")).strip()
        kind = str(ending.get("type", "")).strip()
        measure = _measure_key(marker.get("measure", ""))
        if not number:
            return [], "numbered ending marker has no source number"
        if measure not in index_by_measure:
            return [], "numbered ending marker references an unknown measure"
        membership = frozenset(item.strip() for item in number.split(",") if item.strip())
        if not membership:
            return [], "numbered ending marker has no source number"
        if kind == "start":
            if membership in starts:
                return [], f"numbered ending {number} is opened more than once"
            starts[membership] = index_by_measure[measure]
        elif kind in {"stop", "discontinue"}:
            start = starts.pop(membership, None)
            if start is None:
                return [], f"numbered ending {number} closes without an opening marker"
            ranges.append((membership, start, index_by_measure[measure]))
        else:
            return [], f"numbered ending uses unsupported type {kind!r}"
    if starts:
        return [], "numbered ending marker is unclosed"
    return ranges, ""


def _structural_barline_signature(marker: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    repeat = marker.get("repeat") or {}
    ending = marker.get("ending") or {}
    return (
        _measure_key(marker.get("measure", "")),
        str(marker.get("location", "")),
        str(repeat.get("direction", "")),
        str(repeat.get("times", "")),
        str(ending.get("number", "")),
        str(ending.get("type", "")),
    )


def build_global_measure_boundaries(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build shared source-time boundaries without using a single voice.

    Measure numbers remain strings because MusicXML permits ``0``, pickup
    labels, and nonnumeric labels.  Each boundary also carries a stable
    zero-based index.  A boundary is complete only when every part that
    contains the measure supplies a positive encoded span and all parts agree
    on its start/end; otherwise playback must remain fail-closed.
    """
    ordered_numbers: list[str] = []
    observations: dict[str, list[dict[str, Any]]] = {}
    for part in parts:
        for measure in part.get("measures", []):
            number = _measure_key(measure.get("number", ""))
            if number not in ordered_numbers:
                ordered_numbers.append(number)
            observations.setdefault(number, []).append(measure)

    boundaries: list[dict[str, Any]] = []
    part_count = len(parts)
    for index, number in enumerate(ordered_numbers):
        measures = observations.get(number, [])
        starts = [float(item["onset"]) for item in measures if item.get("onset") is not None]
        ends = [float(item["end"]) for item in measures if item.get("end") is not None]
        durations = [float(item["duration"]) for item in measures if item.get("durationAvailable")]
        start = min(starts) if starts else None
        end = max(ends) if ends else None
        starts_agree = len({round(value, 3) for value in starts}) <= 1
        ends_agree = len({round(value, 3) for value in ends}) <= 1
        complete = (
            len(measures) == part_count
            and len(durations) == part_count
            and start is not None
            and end is not None
            and end > start
            and starts_agree
            and ends_agree
        )
        boundaries.append(
            {
                "number": number,
                "index": index,
                "start": round(start, 3) if start is not None else None,
                "end": round(end, 3) if end is not None else None,
                "duration": round(end - start, 3) if complete and start is not None and end is not None else None,
                "status": "encoded" if complete else "unavailable",
                "partCount": len(measures),
                "expectedPartCount": part_count,
            }
        )
    return boundaries


def build_playback_plan(
    measures: list[str],
    barlines: list[dict[str, Any]],
    *,
    measure_boundaries: list[dict[str, Any]] | None = None,
    part_barlines: list[list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Return an explicit source-order plan, or a fail-closed blocked plan.

    MusicXML ``repeat/@times`` is the total number of passes through the
    repeated section.  Missing ``times`` uses the MusicXML default of two
    passes.  Numbered endings are applied only inside the repeated section;
    malformed endings and disagreements between parts remain blocked.
    """

    original = list(measures)
    measure_boundaries = list(measure_boundaries or [])
    boundary_by_number = {
        _measure_key(item.get("number", "")): item for item in measure_boundaries
    }
    boundaries_complete = bool(measures) and all(
        boundary_by_number.get(_measure_key(number), {}).get("status") == "encoded"
        for number in measures
    )
    boundary_reason = (
        "shared global measure boundaries are source-encoded across all parts"
        if boundaries_complete
        else "shared global measure boundaries are unavailable or disagree across parts"
    )
    measure_starts = (
        {number: boundary_by_number[number]["start"] for number in measures}
        if boundaries_complete
        else {}
    )
    measure_durations = (
        {number: boundary_by_number[number]["duration"] for number in measures}
        if boundaries_complete
        else {}
    )

    def linear_result(status: str, reason: str) -> dict[str, Any]:
        return {
            "status": status,
            "safeToApply": False,
            "mode": "linear-source-order",
            "measureSequence": original,
            "measureSequenceIndices": list(range(len(original))),
            "measureBoundaries": measure_boundaries,
            "measureStarts": measure_starts,
            "measureDurations": measure_durations,
            "durationStatus": "encoded" if boundaries_complete else "unavailable",
            "reason": reason,
        }

    structural_barlines = part_barlines or [barlines]
    signatures = [
        tuple(_structural_barline_signature(marker) for marker in markers if marker.get("repeat") or marker.get("ending"))
        for markers in structural_barlines
    ]
    if signatures and any(signature != signatures[0] for signature in signatures[1:]):
        return linear_result("blocked", "repeat or ending markers disagree across source parts")

    repeat_markers = [marker for marker in barlines if marker.get("repeat")]
    ending_markers = [marker for marker in barlines if marker.get("ending")]
    if not repeat_markers and not ending_markers:
        return linear_result("unavailable", "source contains no encoded repeat or ending markers")

    index_by_measure = {_measure_key(measure): index for index, measure in enumerate(measures)}
    forward = [
        index_by_measure[_measure_key(marker["measure"])]
        for marker in repeat_markers
        if (marker.get("repeat") or {}).get("direction") == "forward"
        and _measure_key(marker.get("measure", "")) in index_by_measure
    ]
    backward = [
        marker
        for marker in repeat_markers
        if (marker.get("repeat") or {}).get("direction") == "backward"
        and _measure_key(marker.get("measure", "")) in index_by_measure
    ]
    unknown_directions = [
        marker
        for marker in repeat_markers
        if (marker.get("repeat") or {}).get("direction") not in {"forward", "backward"}
    ]
    if unknown_directions or not backward:
        return linear_result("blocked", "repeat markers are incomplete or use an unsupported direction")

    ranges, ending_error = _ending_ranges(measures, ending_markers)
    if ending_error:
        return linear_result("blocked", ending_error)
    plan: list[str] = []
    passes: list[dict[str, Any]] = []
    cursor = 0
    for marker in backward:
        end = index_by_measure[_measure_key(marker["measure"])]
        starts = [candidate for candidate in forward if cursor <= candidate <= end]
        start = starts[-1] if starts else 0
        if start < cursor or start > end:
            return linear_result("blocked", "repeat regions overlap or are not ordered")
        plan.extend(measures[cursor:start])
        repeat = marker.get("repeat") or {}
        try:
            repeat_count = int(repeat.get("times", "2") or "2")
        except (TypeError, ValueError):
            return linear_result("blocked", "repeat times is not numeric")
        if repeat_count < 1:
            return linear_result("blocked", "repeat times must be a positive total pass count")
        pass_count = repeat_count
        ending_numbers = {
            int(number)
            for membership, _, _ in ranges
            for number in membership
            if number.isdigit()
        }
        if any(not number.isdigit() for membership, _, _ in ranges for number in membership):
            return linear_result("blocked", "numbered ending is not numeric")
        if ending_numbers and max(ending_numbers) > pass_count:
            return linear_result("blocked", "numbered ending exceeds repeat pass count")
        region_end = max(
            [end]
            + [ending_end for _, ending_start, ending_end in ranges if ending_start >= start]
        )
        if any(ending_start < start or ending_end > region_end for _, ending_start, ending_end in ranges):
            return linear_result("blocked", "numbered ending falls outside the repeat region")
        pass_sequences: list[list[str]] = []
        for pass_number in range(1, pass_count + 1):
            selected: list[str] = []
            selected_ending = False
            for index in range(start, region_end + 1):
                matching_endings = [
                    membership
                    for membership, ending_start, ending_end in ranges
                    if ending_start <= index <= ending_end
                ]
                if not matching_endings or any(str(pass_number) in membership for membership in matching_endings):
                    selected.append(measures[index])
                    if matching_endings:
                        selected_ending = True
            if ranges and not selected_ending:
                return linear_result("blocked", f"no numbered ending is encoded for repeat pass {pass_number}")
            pass_sequences.append(selected)
            plan.extend(selected)
        passes.append(
            {
                "startMeasure": measures[start],
                "endMeasure": measures[region_end],
                "passCount": pass_count,
                "sequences": pass_sequences,
            }
        )
        cursor = region_end + 1
    plan.extend(measures[cursor:])
    sequence_indices = [index_by_measure[_measure_key(number)] for number in plan]
    safe_to_apply = boundaries_complete
    return {
        "status": "encoded" if safe_to_apply else "blocked",
        "safeToApply": safe_to_apply,
        "mode": "explicit-repeat-and-ending-sequence",
        "measureSequence": plan,
        "measureSequenceIndices": sequence_indices,
        "measureBoundaries": measure_boundaries,
        "measureStarts": measure_starts,
        "measureDurations": measure_durations,
        "durationStatus": "encoded" if boundaries_complete else "unavailable",
        "passes": passes,
        "reason": (
            "sequence derived only from encoded forward/backward repeats and numbered endings"
            if safe_to_apply
            else boundary_reason
        ),
    }


def parse_musicxml_semantics(
    source_path: Path,
    *,
    source_id: str = "",
    authority: str = "structured-musicxml",
) -> dict[str, Any]:
    root = read_root(source_path)
    part_names = {
        score_part.attrib.get("id", ""): text(score_part, "part-name")
        for score_part in root.iter()
        if local_name(score_part.tag) == "score-part"
    }
    parts: list[dict[str, Any]] = []
    all_barlines: list[dict[str, Any]] = []
    all_lyrics: list[dict[str, Any]] = []
    all_markings: list[dict[str, Any]] = []
    for part in (node for node in root if local_name(node.tag) == "part"):
        part_id = part.attrib.get("id", "")
        part_name = part_names.get(part_id) or part_id or "Part"
        events: list[dict[str, Any]] = []
        measures: list[dict[str, Any]] = []
        cursor = 0.0
        divisions = 1.0
        for measure in (node for node in part if local_name(node.tag) == "measure"):
            measure_number = measure.attrib.get("number", "")
            measure_start = cursor
            previous_note: tuple[str, str, float] | None = None
            measure_barlines = [
                parse_barline(barline, part_id=part_id, measure_number=measure_number)
                for barline in children(measure, "barline")
            ]
            all_barlines.extend(measure_barlines)
            measure_markings: list[dict[str, Any]] = []
            for direction in children(measure, "direction"):
                measure_markings.extend(
                    direction_markings(direction, part_id=part_id, measure_number=measure_number)
                )
            all_markings.extend(measure_markings)
            max_cursor = cursor
            for item in measure:
                item_name = local_name(item.tag)
                if item_name == "attributes":
                    divisions_text = text(item, "divisions")
                    if divisions_text:
                        try:
                            divisions = float(divisions_text)
                        except ValueError:
                            divisions = 1.0
                    continue
                elif item_name == "backup":
                    try:
                        cursor -= float(text(item, "duration")) / divisions
                    except ValueError:
                        pass
                    previous_note = None
                    continue
                elif item_name == "forward":
                    try:
                        cursor += float(text(item, "duration")) / divisions
                    except ValueError:
                        pass
                    previous_note = None
                    continue
                elif item_name != "note":
                    continue
                try:
                    beats = float(text(item, "duration")) / divisions
                except ValueError:
                    beats = 0.0
                voice = text(item, "voice")
                staff = text(item, "staff") or "1"
                stream = (voice, staff)
                onset = cursor
                if child(item, "chord") is not None and previous_note and previous_note[:2] == stream:
                    onset = previous_note[2]
                event_index = len(events)
                event = {
                    "index": event_index,
                    "partId": part_id,
                    "measure": measure_number,
                    "onset": round(onset, 3),
                    "beats": round(max(beats, 0.0), 3),
                    "voice": voice,
                    "staff": staff,
                    "rest": child(item, "pitch") is None,
                }
                pitch = child(item, "pitch")
                if pitch is not None:
                    event.update(
                        {
                            "step": text(pitch, "step"),
                            "octave": text(pitch, "octave"),
                            "alter": text(pitch, "alter") or "0",
                        }
                    )
                events.append(event)
                lyrics = lyric_for_note(
                    item,
                    part_id=part_id,
                    measure_number=measure_number,
                    event_index=event_index,
                    onset=onset,
                )
                all_lyrics.extend(lyrics)
                markings = note_markings(
                    item,
                    part_id=part_id,
                    measure_number=measure_number,
                    event_index=event_index,
                )
                all_markings.extend(markings)
                previous_note = (voice, staff, onset)
                max_cursor = max(max_cursor, onset + beats)
                if child(item, "chord") is None:
                    cursor += beats
            cursor = max_cursor
            measures.append(
                {
                    "number": measure_number,
                    "index": len(measures),
                    "onset": round(measure_start, 3),
                    "end": round(max_cursor, 3),
                    "duration": round(max(0.0, max_cursor - measure_start), 3),
                    "durationAvailable": bool(max_cursor > measure_start),
                    "barlines": measure_barlines,
                    "editorialMarkings": measure_markings,
                }
            )
        parts.append(
            {
                "id": part_id,
                "name": part_name,
                "measures": measures,
                "events": events,
                "lyrics": [item for item in all_lyrics if item["partId"] == part_id],
                "barlines": [item for item in all_barlines if item["partId"] == part_id],
                "editorialMarkings": [item for item in all_markings if item["partId"] == part_id],
            }
        )

    canonical_measures = [measure["number"] for measure in parts[0]["measures"]] if parts else []
    canonical_barlines = parts[0]["barlines"] if parts else []
    measure_boundaries = build_global_measure_boundaries(parts)
    endings_present = any(marker.get("ending") for marker in all_barlines)
    repeats_present = any(marker.get("repeat") for marker in all_barlines)
    lyrics_present = any(item.get("text") for item in all_lyrics)
    return {
        "source": {
            "id": source_id,
            "path": str(source_path),
            "authority": authority,
            "editionScoped": True,
        },
        "parts": parts,
        "lyrics": all_lyrics,
        "barlines": all_barlines,
        "editorialMarkings": all_markings,
        "playback": build_playback_plan(
            canonical_measures,
            canonical_barlines,
            measure_boundaries=measure_boundaries,
            part_barlines=[part["barlines"] for part in parts],
        ),
        "measureBoundaries": measure_boundaries,
        "availability": {
            "lyrics": {
                "status": "encoded" if lyrics_present else "unavailable",
                "count": sum(1 for item in all_lyrics if item.get("text")),
                "reason": "source contains aligned lyric elements"
                if lyrics_present
                else "source MusicXML contains no lyric text",
            },
            "repeats": {
                "status": "encoded" if repeats_present else "unavailable",
                "count": sum(1 for item in all_barlines if item.get("repeat")),
                "reason": "source contains repeat barlines"
                if repeats_present
                else "source MusicXML contains no repeat barlines",
            },
            "numberedEndings": {
                "status": "encoded" if endings_present else "unavailable",
                "count": sum(1 for item in all_barlines if item.get("ending")),
                "reason": "source contains numbered ending barlines"
                if endings_present
                else "source MusicXML contains no numbered ending barlines",
            },
            "editorialMarkings": {
                "status": "encoded" if all_markings else "unavailable",
                "count": len(all_markings),
                "reason": "source contains supported editorial marking elements"
                if all_markings
                else "source MusicXML contains no supported editorial markings",
            },
        },
    }


def write_json_report(source_path: Path, output_path: Path, *, source_id: str = "") -> None:
    output_path.write_text(
        json.dumps(parse_musicxml_semantics(source_path, source_id=source_id), indent=2) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "build_global_measure_boundaries",
    "build_playback_plan",
    "parse_musicxml_semantics",
    "write_json_report",
]
