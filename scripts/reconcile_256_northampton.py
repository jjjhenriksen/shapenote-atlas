#!/usr/bin/env python3
"""Build a fail-closed, per-measure reconciliation ledger for 2025/256."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/source-transcriptions/2025/256-northampton.jpg"
AUDIT = ROOT / "work/source-transcriptions/2025/256-northampton.audit.json"
OUTPUT = ROOT / "work/source-transcriptions/2025/256-northampton-reconciliation.json"
CANDIDATES = [
    ("source-scan-omr", "Audiveris draft from source scan", "work/omr/256-northampton/256-northampton.mxl", "source-scan"),
    ("normalized-scan-omr", "Audiveris draft from deterministic normalized layer", "work/omr/cleaned-v1-256-northampton/work__source-transcriptions__2025__256-northampton.mxl", "normalized-v1"),
    ("ai-cleaned-omr", "Audiveris draft from AI-cleaned working image", "work/omr/cleaned-v1-256-northampton/256-northampton-cleaned-v1.mxl", "ai-cleaned-suspect"),
    ("composer-pdf-omr", "Audiveris draft from public composer PDF candidate", "work/omr/composer-256-northampton/northampton-8s-page.mxl", "composer-pdf-candidate"),
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def direct(element: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in element if lname(item.tag) == name), None)


def text(element: ET.Element | None, name: str) -> str:
    item = direct(element, name) if element is not None else None
    return (item.text or "").strip() if item is not None else ""


def all_named(element: ET.Element, name: str) -> list[ET.Element]:
    return [item for item in element.iter() if lname(item.tag) == name]


def unpack(path: Path) -> ET.Element:
    with ZipFile(path) as archive:
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = next(item for item in all_named(container, "rootfile"))
        return ET.fromstring(archive.read(rootfile.attrib["full-path"]))


def pitch(note: ET.Element) -> str:
    p = direct(note, "pitch")
    if p is None:
        return "rest" if direct(note, "rest") is not None else "unpitched"
    step, alter, octave = text(p, "step"), text(p, "alter"), text(p, "octave")
    return f"{step}{'+' + alter if alter else ''}{octave}"


def markers(measure: ET.Element) -> list[str]:
    result = []
    for barline in [item for item in measure if lname(item.tag) == "barline"]:
        repeat, ending = direct(barline, "repeat"), direct(barline, "ending")
        if barline.get("location"):
            result.append(f"barline:{barline.get('location')}")
        if repeat is not None:
            result.append(f"repeat:{repeat.get('direction', '')}")
        if ending is not None:
            result.append(f"ending:{ending.get('number', '')}:{ending.get('type', '')}")
    return result


def summarize(measure: ET.Element) -> dict[str, object]:
    notes = [item for item in measure if lname(item.tag) == "note"]
    return {
        "present": True,
        "noteCount": len(notes),
        "restCount": sum(direct(note, "rest") is not None for note in notes),
        "durationUnits": sum(int(text(note, "duration") or 0) for note in notes),
        "pitches": [pitch(note) for note in notes],
        "noteheadValues": [text(note, "notehead") for note in notes if text(note, "notehead")],
        "barlineMarkers": markers(measure),
    }


def parse_candidate(item: tuple[str, str, str, str]) -> dict[str, object]:
    candidate_id, label, relative, input_layer = item
    path = ROOT / relative
    result: dict[str, object] = {"id": candidate_id, "label": label, "path": relative, "inputLayer": input_layer}
    if not path.exists():
        result.update({"exists": False, "status": "missing"})
        return result
    root = unpack(path)
    parts: dict[str, object] = {}
    all_numbers: set[str] = set()
    part_list = direct(root, "part-list")
    names = {}
    if part_list is not None:
        for score_part in [item for item in part_list if lname(item.tag) == "score-part"]:
            names[score_part.get("id", "")] = text(score_part, "part-name")
    for part in [item for item in root if lname(item.tag) == "part"]:
        measures = [item for item in part if lname(item.tag) == "measure"]
        by_number = {}
        key_events, time_events = [], []
        divisions = ""
        for measure in measures:
            number = measure.get("number", "")
            all_numbers.add(number)
            by_number[number] = summarize(measure)
            attributes = direct(measure, "attributes")
            if attributes is not None:
                divisions = text(attributes, "divisions") or divisions
                key = direct(attributes, "key")
                if key is not None:
                    key_events.append({"measure": number, "fifths": text(key, "fifths"), "mode": text(key, "mode")})
                time = direct(attributes, "time")
                if time is not None:
                    time_events.append({"measure": number, "beats": text(time, "beats"), "beatType": text(time, "beat-type")})
        parts[part.get("id", "")] = {
            "name": names.get(part.get("id", ""), ""),
            "measureCount": len(measures),
            "divisions": divisions,
            "keyEvents": key_events,
            "timeEvents": time_events,
            "measures": by_number,
        }
    result.update({
        "exists": True,
        "status": "candidate",
        "sha256": digest(path),
        "partCount": len(parts),
        "parts": parts,
        "measureNumbers": sorted(all_numbers, key=lambda value: (int(value) if value.isdigit() else 9999, value)),
        "measureCountRange": sorted({int(part["measureCount"]) for part in parts.values()}),
    })
    return result


def part_measure(candidate: dict[str, object], part_id: str, number: int) -> dict[str, object]:
    part = candidate.get("parts", {}).get(part_id, {})
    return part.get("measures", {}).get(str(number), {"present": False})


def measure_record(candidates: list[dict[str, object]], number: int) -> dict[str, object]:
    observations = {}
    discrepancies = [
        "Direct source comparison is required; this artifact does not infer source notation.",
        "Standard candidate MusicXML does not establish Sacred Harp four-shape notehead identity.",
    ]
    for candidate in candidates:
        observations[candidate["id"]] = {
            part_id: part_measure(candidate, part_id, number)
            for part_id in sorted(candidate.get("parts", {}))
        }
        if not candidate.get("exists"):
            discrepancies.append(f"{candidate['id']}: candidate artifact missing")
        elif str(number) not in candidate.get("measureNumbers", []):
            discrepancies.append(f"{candidate['id']}: measure {number} absent from this candidate")
    if number == 1:
        discrepancies.extend([
            "Authoritative source header states F# minor; candidate key events require reconciliation.",
            "Authoritative source header states 4/4; candidate time events require reconciliation.",
        ])
    if number in {20, 21}:
        discrepancies.append("Authoritative scan visibly shows final first/second-ending marks; reconcile exact repeat semantics.")
    return {
        "measure": number,
        "sourceStatus": "needs-human-comparison",
        "sourceFacts": {
            "presentOnAuthoritativePage": True,
            "partCount": 4,
            "key": "F# minor" if number == 1 else "see source header",
            "time": "4/4" if number == 1 else "see source header",
            "endingEvidence": "final first/second endings visible" if number in {20, 21} else "not asserted",
        },
        "candidateObservations": observations,
        "discrepancies": discrepancies,
        "safeToPromote": False,
    }


def main() -> int:
    candidates = [parse_candidate(item) for item in CANDIDATES]
    ranges = {item["id"]: item.get("measureCountRange", []) for item in candidates}
    generated = datetime.now(timezone.utc).isoformat()
    payload = {
        "record": "sh2025/256",
        "edition": "Sacred Harp, 2025 Edition",
        "page": "256",
        "title": "Northampton",
        "generatedAt": generated,
        "status": "blocked",
        "safeToPromote": False,
        "sourceAuthority": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": digest(SOURCE),
            "dimensions": "1312x976",
            "measureCount": 21,
            "partCount": 4,
            "key": "F# minor",
            "time": "4/4",
            "shapeNoteEvidence": "visible on source scan; candidate MusicXML does not establish shape identity",
            "repeatEvidence": "final first/second-ending marks visible; exact encoding requires comparison",
        },
        "candidateAgreement": False,
        "candidateMeasureCountRanges": ranges,
        "blockingFindings": [
            "Candidate measure counts disagree with the authoritative 21-measure page: 21, 21, 19, and 18 per part.",
            "Candidate key events do not establish a consistent F# minor four-part score.",
            "Pitch, rhythm, rests, repeats, endings, and shape-note identity remain unresolved against the untouched scan.",
        ],
        "candidates": candidates,
        "measures": [measure_record(candidates, number) for number in range(1, 22)],
        "reviewProtocol": [
            "Use only the untouched source image as notation authority.",
            "Compare treble, alto, tenor, and bass independently for every measure.",
            "Record source pitch, rhythm, rest, accidental, tie, repeat, ending, and four-shape decisions before editing MusicXML.",
            "Do not promote or expose as source-faithful until all 21 measures reconcile.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if AUDIT.exists():
        audit = json.loads(AUDIT.read_text(encoding="utf-8"))
        audit["reconciliation"] = {
            "artifact": str(OUTPUT.relative_to(ROOT)),
            "generatedAt": generated,
            "status": "blocked",
            "safeToPromote": False,
            "candidateAgreement": False,
            "candidateMeasureCountRanges": ranges,
        }
        AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT} with 21 measure records; promotion remains blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
