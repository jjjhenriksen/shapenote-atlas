#!/usr/bin/env python3
"""Build a fail-closed structural triage ledger for clean-source candidates.

The report compares alternate/public-source OMR with the existing 2025 scan
draft only to prioritize human review. It never promotes a candidate or
asserts note-for-note agreement; the untouched 2025 source remains the
authority for edition-faithful notation.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "work/source-transcriptions/2025/clean-source-candidates.json"
CANDIDATE_OMR = ROOT / "work/omr/clean-source-omr-run.json"
DRAFT_INDEX = ROOT / "work/omr/draft-index.json"
CORPUS = ROOT / "public/corpus.json"
OUTPUT = ROOT / "public/candidate-reconciliation.json"


def lname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def direct(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    return next((item for item in element if lname(item.tag) == name), None)


def text(element: ET.Element | None, name: str) -> str:
    item = direct(element, name)
    return (item.text or "").strip() if item is not None else ""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unpack(path: Path) -> ET.Element:
    with ZipFile(path) as archive:
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = next(item for item in container.iter() if lname(item.tag) == "rootfile")
        return ET.fromstring(archive.read(rootfile.attrib["full-path"]))


def parse_musicxml(path: Path) -> dict[str, object]:
    if not path.is_file() or not path.read_bytes().startswith(b"PK"):
        return {"exists": False, "path": str(path.relative_to(ROOT))}
    root = unpack(path)
    part_names: dict[str, str] = {}
    part_list = direct(root, "part-list")
    score_parts = list(part_list) if part_list is not None else []
    for score_part in [item for item in score_parts if lname(item.tag) == "score-part"]:
        part_names[score_part.get("id", "")] = text(score_part, "part-name")
    parts: list[dict[str, object]] = []
    key_events: list[dict[str, str]] = []
    time_events: list[dict[str, str]] = []
    total_notes = 0
    total_pitched = 0
    total_rests = 0
    for part in [item for item in root if lname(item.tag) == "part"]:
        measures = [item for item in part if lname(item.tag) == "measure"]
        note_count = 0
        pitched_count = 0
        rest_count = 0
        measure_numbers: list[str] = []
        durations: list[str] = []
        part_keys: list[dict[str, str]] = []
        part_times: list[dict[str, str]] = []
        for measure in measures:
            number = measure.get("number", "")
            measure_numbers.append(number)
            attributes = direct(measure, "attributes")
            key = direct(attributes, "key")
            if key is not None:
                event = {"measure": number, "fifths": text(key, "fifths"), "mode": text(key, "mode")}
                part_keys.append(event)
                key_events.append(event)
            time = direct(attributes, "time")
            if time is not None:
                event = {"measure": number, "beats": text(time, "beats"), "beatType": text(time, "beat-type")}
                part_times.append(event)
                time_events.append(event)
            for note in [item for item in measure if lname(item.tag) == "note"]:
                note_count += 1
                duration = text(note, "duration")
                if duration:
                    durations.append(duration)
                if direct(note, "rest") is not None:
                    rest_count += 1
                elif direct(note, "pitch") is not None:
                    pitched_count += 1
        total_notes += note_count
        total_pitched += pitched_count
        total_rests += rest_count
        parts.append({
            "id": part.get("id", ""),
            "name": part_names.get(part.get("id", ""), ""),
            "measureCount": len(measures),
            "measureNumbers": measure_numbers,
            "noteCount": note_count,
            "pitchedCount": pitched_count,
            "restCount": rest_count,
            "durationUnits": sum(int(value) for value in durations if value.isdigit()),
            "keyEvents": part_keys,
            "timeEvents": part_times,
        })
    return {
        "exists": True,
        "path": str(path.relative_to(ROOT)),
        "sha256": digest(path),
        "partCount": len(parts),
        "parts": parts,
        "measureCountRange": sorted({int(part["measureCount"]) for part in parts}),
        "totalNotes": total_notes,
        "pitchedNotes": total_pitched,
        "rests": total_rests,
        "keyEvents": key_events,
        "timeEvents": time_events,
    }


def first_key(score: dict[str, object]) -> tuple[str, str]:
    events = score.get("keyEvents", [])
    if not events:
        return "", ""
    event = events[0]
    return str(event.get("fifths", "")), str(event.get("mode", ""))


def first_time(score: dict[str, object]) -> tuple[str, str]:
    events = score.get("timeEvents", [])
    if not events:
        return "", ""
    event = events[0]
    return str(event.get("beats", "")), str(event.get("beatType", ""))


def draft_for_song(song_no: str, records: list[dict[str, object]]) -> dict[str, object] | None:
    pattern = re.compile(rf"^{re.escape(song_no)}(?:-|$)", re.IGNORECASE)
    return next((record for record in records if pattern.search(str(record.get("record", "")))), None)


def compare(candidate: dict[str, object], source: dict[str, object]) -> dict[str, object]:
    agreements: list[str] = []
    discrepancies: list[str] = [
        "Structural agreement is triage evidence only; direct visual comparison is still required.",
        "Standard MusicXML does not establish Sacred Harp four-shape notehead identity.",
    ]
    if not candidate.get("exists"):
        discrepancies.append("Candidate MusicXML artifact is missing.")
    if not source.get("exists"):
        discrepancies.append("2025 source-scan MusicXML artifact is missing.")
    if candidate.get("partCount") == source.get("partCount"):
        agreements.append("part-count")
    else:
        discrepancies.append(f"Part counts differ: candidate {candidate.get('partCount')} vs 2025 draft {source.get('partCount')}.")
    if candidate.get("measureCountRange") == source.get("measureCountRange"):
        agreements.append("measure-count-range")
    else:
        discrepancies.append(f"Measure-count ranges differ: candidate {candidate.get('measureCountRange')} vs 2025 draft {source.get('measureCountRange')}.")
    candidate_key, candidate_mode = first_key(candidate)
    source_key, source_mode = first_key(source)
    if candidate_key and source_key and candidate_key == source_key and candidate_mode == source_mode:
        agreements.append("key-signature")
    elif candidate_key or source_key:
        discrepancies.append(f"Key events differ or are incomplete: candidate {candidate_key}:{candidate_mode} vs 2025 draft {source_key}:{source_mode}.")
    candidate_time = first_time(candidate)
    source_time = first_time(source)
    if candidate_time and source_time and candidate_time == source_time:
        agreements.append("time-signature")
    elif candidate_time or source_time:
        discrepancies.append(f"Time events differ or are incomplete: candidate {candidate_time} vs 2025 draft {source_time}.")
    if candidate.get("pitchedNotes", 0) and source.get("pitchedNotes", 0):
        agreements.append("pitched-events-present")
    else:
        discrepancies.append("One comparison artifact has no pitched events.")
    structural_agreement = {"part-count", "measure-count-range", "pitched-events-present"}.issubset(agreements)
    return {
        "status": "autonomously-blocked-source-comparison",
        "safeToPromote": False,
        "structuralAgreement": structural_agreement,
        "agreementFields": agreements,
        "discrepancies": discrepancies,
    }


def main() -> int:
    candidates = json.loads(CANDIDATES.read_text(encoding="utf-8")).get("records", [])
    omr_records = json.loads(CANDIDATE_OMR.read_text(encoding="utf-8")).get("records", [])
    draft_records = json.loads(DRAFT_INDEX.read_text(encoding="utf-8")).get("records", [])
    corpus = json.loads(CORPUS.read_text(encoding="utf-8")).get("songs", [])
    omr_by_key = {str(item.get("candidateKey")): item for item in omr_records if item.get("candidateKey")}
    source_by_song = {}
    for song in corpus:
        if "sh2025" not in song.get("books", []):
            continue
        source_by_song[str(song.get("songNo", "")).lower()] = song
    output_records: list[dict[str, object]] = []
    for item in candidates:
        candidate_key = str(item.get("candidateKey", ""))
        song_no = str(item.get("songNo", ""))
        omr = omr_by_key.get(candidate_key, {})
        candidate_artifact = next((ROOT / artifact for artifact in omr.get("draftArtifacts", []) if (ROOT / artifact).is_file()), None)
        source_index = draft_for_song(song_no, draft_records)
        source_artifact = ROOT / str(source_index.get("artifact", "")) if source_index else None
        candidate_score = parse_musicxml(candidate_artifact) if candidate_artifact else {"exists": False, "path": ""}
        source_score = parse_musicxml(source_artifact) if source_artifact else {"exists": False, "path": ""}
        source_song = source_by_song.get(song_no.lower(), {})
        source_coverage = source_song.get("sourceCoverageByBook", {}).get("sh2025", {})
        comparison = compare(candidate_score, source_score)
        output_records.append({
            "candidateKey": candidate_key,
            "bookId": "sh2025",
            "songNo": song_no,
            "title": item.get("title", ""),
            "candidateTitle": item.get("candidateTitle", ""),
            "matchKind": item.get("matchKind", ""),
            "candidatePdfUrl": item.get("pdfUrl", ""),
            "candidatePdfSha256": item.get("sha256", ""),
            "candidateOmr": candidate_score,
            "sourceScanDraft": source_score,
            "sourceAuthority": {
                "sourceUrls": source_coverage.get("sourceUrls", []),
                "sourceImageUrl": source_coverage.get("sourceImageUrl", ""),
                "keySignature": source_song.get("metadataByBook", {}).get("sh2025", {}).get("keySignature", ""),
                "timeSignature": source_song.get("metadataByBook", {}).get("sh2025", {}).get("timeSignature", ""),
            },
            **comparison,
            "autonomousDecision": "blocked",
            "blockingReason": "No direct note-for-note and four-shape evidence is available from the current structured candidate/source artifacts; review-only candidates are not counted as completed.",
            "reviewProtocol": [
                "Keep the untouched authorized 2025 source as notation authority.",
                "Do not promote this candidate: the available evidence is insufficient for an autonomous source-faithful decision.",
            ],
        })
    output_records.sort(key=lambda item: (not item["structuralAgreement"], item["songNo"], item["candidateKey"]))
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "edition": "Sacred Harp, 2025 Edition",
        "status": "autonomous-decision-ledger",
        "safeToPromote": False,
        "policy": "Candidate/source structural agreement is never sufficient for promotion. The exact 2025 source remains authoritative; insufficient evidence is autonomously blocked and review-only candidates are not counted as completed.",
        "summary": {
            "candidates": len(output_records),
            "structuralAgreement": sum(bool(item["structuralAgreement"]) for item in output_records),
            "autonomouslyBlocked": sum(item.get("status") == "autonomously-blocked-source-comparison" for item in output_records),
            "safeToPromote": 0,
        },
        "records": output_records,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
