#!/usr/bin/env python3
"""Audit the bounded SH25 correction-needed records for agent 02.

This audit is deliberately read-only with respect to the dashboard's source
data.  It reads the public ledger, exact score manifest, thirteen direct
comparison artifacts, retained source scans, and correction derivatives, then
writes only a temporary agent-02 report.  A source-aligned derivative is still
blocked when the scan has lyrics but the structured witness has no
unambiguous note-to-syllable assignment.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "public/source-comparison-ledger.json"
MANIFEST = ROOT / "public/shapenote-score-manifest.json"
REPORT = ROOT / "work/agent-02-corrections/correction-dispositions.json"

EXPECTED_QUEUE_IDS = {
    "sh2025/41",
    "sh2025/50t",
    "sh2025/55",
    "sh2025/118",
    "sh2025/169",
    "sh2025/415",
    "sh2025/525",
    "sh2025/537",
    "sh2025/544",
    "sh2025/545",
    "sh2025/557",
    "sh2025/563",
    "sh2025/575",
}

ALLOWED_SHAPES = {"fa", "sol", "la", "mi"}

# Confirmed during the full-resolution source-scan inspection for this pass.
# Two older comparison artifacts did not carry the flag even though their
# retained scans visibly print lyrics, so this bounded audit records the
# inspection result independently of that legacy omission.
SOURCE_SCAN_LYRICS_VISIBLE = set(EXPECTED_QUEUE_IDS)
SOURCE_SCAN_FOUR_SHAPE_VISIBLE = set(EXPECTED_QUEUE_IDS)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child(parent: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in parent if tag_name(item.tag) == name), None)


def child_text(parent: ET.Element, name: str) -> str:
    item = child(parent, name)
    return (item.text or "").strip() if item is not None else ""


def read_score(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"corrupt MusicXML archive: {path}")
        names = [
            name
            for name in archive.namelist()
            if name.lower().endswith(".xml") and "container" not in name.lower()
        ]
        if not names:
            raise ValueError(f"MusicXML archive has no score document: {path}")
        root = ET.fromstring(archive.read(names[0]))
    if tag_name(root.tag) != "score-partwise":
        raise ValueError(f"not a score-partwise MusicXML document: {path}")
    return root


def event_signature(root: ET.Element) -> list[list[tuple[str, float, tuple[str, int, int] | None, bool]]]:
    """Return event-bearing data while ignoring metadata-only corrections."""
    signatures: list[list[tuple[str, float, tuple[str, int, int] | None, bool]]] = []
    for part in [node for node in root if tag_name(node.tag) == "part"]:
        divisions = 1.0
        cursor = 0.0
        part_events: list[tuple[str, float, tuple[str, int, int] | None, bool]] = []
        for measure in [node for node in part if tag_name(node.tag) == "measure"]:
            for item in measure:
                name = tag_name(item.tag)
                if name == "attributes":
                    value = child_text(item, "divisions")
                    if value:
                        divisions = float(value)
                elif name in {"backup", "forward"}:
                    duration = float(child_text(item, "duration") or "0") / divisions
                    cursor += -duration if name == "backup" else duration
                elif name == "note":
                    duration = float(child_text(item, "duration") or "0") / divisions
                    pitch = child(item, "pitch")
                    pitch_value = None
                    if pitch is not None:
                        pitch_value = (
                            child_text(pitch, "step"),
                            int(child_text(pitch, "octave") or "0"),
                            int(child_text(pitch, "alter") or "0"),
                        )
                    is_chord = child(item, "chord") is not None
                    part_events.append(
                        (
                            measure.attrib.get("number", ""),
                            round(duration, 3),
                            pitch_value,
                            child(item, "rest") is not None,
                        )
                    )
                    if not is_chord:
                        cursor += duration
        signatures.append(part_events)
    return signatures


def signature_hash(signature: Any) -> str:
    encoded = json.dumps(signature, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def score_summary(root: ET.Element) -> dict[str, Any]:
    parts = [node for node in root if tag_name(node.tag) == "part"]
    measures = {
        part.attrib.get("id", ""): sum(1 for item in part if tag_name(item.tag) == "measure")
        for part in parts
    }
    pitched = 0
    noteheads = 0
    shape_counts: dict[str, int] = {}
    lyrics = 0
    modes: list[str] = []
    times: list[tuple[str, str]] = []
    repeats = 0
    endings = 0
    for node in root.iter():
        name = tag_name(node.tag)
        if name == "key":
            mode = child(node, "mode")
            modes.append((mode.text or "").strip().lower() if mode is not None else "")
        elif name == "time":
            times.append((child_text(node, "beats"), child_text(node, "beat-type")))
        elif name == "repeat":
            repeats += 1
        elif name == "ending":
            endings += 1
        elif name == "lyric":
            lyrics += 1
        elif name == "note":
            if child(node, "pitch") is None:
                continue
            pitched += 1
            notehead = child(node, "notehead")
            value = (notehead.text or "").strip().lower() if notehead is not None else ""
            if value:
                noteheads += 1
                shape_counts[value] = shape_counts.get(value, 0) + 1
    return {
        "parts": len(parts),
        "measuresByPart": measures,
        "pitchedEvents": pitched,
        "noteheads": noteheads,
        "shapeCounts": shape_counts,
        "lyrics": lyrics,
        "modes": modes,
        "times": times,
        "repeats": repeats,
        "endings": endings,
    }


def observed_scan_note(observations: dict[str, Any], lyrics_visible: bool) -> str:
    header = observations.get("header", "")
    key = observations.get("key", "")
    time = observations.get("timeSignature", "")
    meter = observations.get("meter", "")
    parts = observations.get("parts", "")
    measures = observations.get("measuresByPart", {})
    return (
        f"{header}; printed key {key}; {time}; {meter}; {parts} vocal parts; "
        f"measures {measures}; printed lyrics visible={lyrics_visible}"
    )


def audit(root: Path = ROOT) -> dict[str, Any]:
    ledger = json.loads((root / LEDGER.relative_to(ROOT)).read_text(encoding="utf-8"))
    manifest = json.loads((root / MANIFEST.relative_to(ROOT)).read_text(encoding="utf-8"))
    ledger_records = {
        record.get("queueId"): record
        for record in ledger.get("records", [])
        if record.get("comparisonStatus") == "verified-with-correction-needed"
    }
    errors: list[str] = []
    if set(ledger_records) != EXPECTED_QUEUE_IDS:
        errors.append(
            "correction-needed IDs differ from expected set: "
            f"actual={sorted(ledger_records)} expected={sorted(EXPECTED_QUEUE_IDS)}"
        )
    manifest_entries = manifest.get("entries", {})
    records: list[dict[str, Any]] = []
    for queue_id in sorted(EXPECTED_QUEUE_IDS):
        record = ledger_records.get(queue_id)
        if record is None:
            continue
        audit_path = root / record["auditFile"]
        if not audit_path.is_file():
            errors.append(f"{queue_id}: missing direct comparison artifact {record['auditFile']}")
            continue
        comparison = json.loads(audit_path.read_text(encoding="utf-8"))
        source_info = comparison.get("sourceAuthority", {})
        candidate_info = comparison.get("candidateWitness", {})
        corrected_info = comparison.get("correctedDraft", {})
        source_path = root / str(source_info.get("sourceImagePath", ""))
        candidate_path = root / str(candidate_info.get("candidateMusicXmlPath", ""))
        corrected_path = root / str(corrected_info.get("path", ""))
        for label, path in (("source scan", source_path), ("candidate", candidate_path), ("corrected derivative", corrected_path)):
            if not path.is_file():
                errors.append(f"{queue_id}: missing {label} {path}")
        if not all(path.is_file() for path in (source_path, candidate_path, corrected_path)):
            continue

        source_hash = sha256(source_path)
        candidate_hash = sha256(candidate_path)
        corrected_hash = sha256(corrected_path)
        if source_hash != source_info.get("sourceImageSha256"):
            errors.append(f"{queue_id}: retained source image checksum drift")
        if candidate_hash != candidate_info.get("candidateMusicXmlSha256"):
            errors.append(f"{queue_id}: candidate checksum drift")
        if corrected_hash != corrected_info.get("sha256"):
            errors.append(f"{queue_id}: corrected derivative checksum drift")

        raw_root = read_score(candidate_path)
        corrected_root = read_score(corrected_path)
        raw_summary = score_summary(raw_root)
        corrected_summary = score_summary(corrected_root)
        raw_events = event_signature(raw_root)
        corrected_events = event_signature(corrected_root)
        event_equal = raw_events == corrected_events
        if not event_equal:
            errors.append(f"{queue_id}: corrected derivative changed the event stream")
        expected_source = source_info.get("directObservations", {})
        if corrected_summary["parts"] != expected_source.get("parts"):
            errors.append(f"{queue_id}: corrected part count disagrees with source observation")
        expected_measures = expected_source.get("measuresByPart", {})
        if corrected_summary["measuresByPart"] != expected_measures:
            errors.append(f"{queue_id}: corrected measure counts disagree with source observation")
        if corrected_summary["pitchedEvents"] != corrected_info.get("summary", {}).get("pitchedEvents"):
            errors.append(f"{queue_id}: corrected pitched-event count is stale")
        if corrected_summary["noteheads"] != corrected_summary["pitchedEvents"]:
            errors.append(f"{queue_id}: not every pitched event has a derived four-shape notehead")
        if set(corrected_summary["shapeCounts"]) - ALLOWED_SHAPES:
            errors.append(f"{queue_id}: corrected derivative contains unsupported shapes")
        if corrected_summary["lyrics"] != 0 or corrected_info.get("summary", {}).get("lyricsEncoded") is not False:
            errors.append(f"{queue_id}: lyrics unexpectedly encoded in correction derivative")
        expected_mode = str(expected_source.get("key", "")).split()[-1].lower()
        if expected_mode and any(mode != expected_mode for mode in corrected_summary["modes"]):
            errors.append(f"{queue_id}: corrected mode does not match printed source mode")
        expected_time = tuple(str(expected_source.get("timeSignature", "")).split("/"))
        if len(expected_time) == 2 and any(time != expected_time for time in corrected_summary["times"]):
            errors.append(f"{queue_id}: corrected time signature does not match printed source")
        manifest_entry = manifest_entries.get(queue_id, {})
        if manifest_entry.get("rawPath") != candidate_info.get("candidateMusicXmlPath"):
            errors.append(f"{queue_id}: candidate path does not match score manifest")
        if manifest_entry.get("sourceSha256") != candidate_hash:
            errors.append(f"{queue_id}: candidate hash does not match score manifest")

        observations = expected_source
        source_lyrics_visible = queue_id in SOURCE_SCAN_LYRICS_VISIBLE
        blocker = (
            f"autonomously-blocked for {comparison.get('title', queue_id)}: printed lyrics are "
            f"visible in the retained source scan, but the exact structured witness and "
            f"correction derivative contain zero lyric "
            "elements; assigning syllables to notes across the observed voices, repetitions, "
            f"and ending semantics for {corrected_summary['parts']} parts and "
            f"{sum(corrected_summary['measuresByPart'].values())} part-measures is not "
            "established without guessing"
        )
        records.append(
            {
                "queueId": queue_id,
                "title": comparison.get("title", ""),
                "disposition": "autonomously-blocked",
                "safeToPromote": False,
                "humanReviewRequired": False,
                "blockerCode": "unencoded-lyrics-alignment",
                "blockingReason": blocker,
                "sourceScanInspection": {
                    "path": str(source_path.relative_to(root)),
                    "sha256": source_hash,
                    "immutable": source_info.get("immutable") is True,
                    "observed": observed_scan_note(observations, source_lyrics_visible),
                    "fourShapeNoteheadsVisible": queue_id in SOURCE_SCAN_FOUR_SHAPE_VISIBLE,
                    "lyricsVisible": source_lyrics_visible,
                },
                "candidateWitness": {
                    "path": str(candidate_path.relative_to(root)),
                    "sha256": candidate_hash,
                    "manifestSourceUrl": manifest_entry.get("sourceUrl", ""),
                    "manifestSourceEdition": manifest_entry.get("sourceEdition", ""),
                    "candidateRole": candidate_info.get("candidateRole", ""),
                    "rawSummary": raw_summary,
                },
                "correctedDerivative": {
                    "path": str(corrected_path.relative_to(root)),
                    "sha256": corrected_hash,
                    "summary": corrected_summary,
                },
                "eventEvidence": {
                    "eventStreamEqual": event_equal,
                    "candidateEventSignatureSha256": signature_hash(raw_events),
                    "correctedEventSignatureSha256": signature_hash(corrected_events),
                    "candidateAndCorrectedStructuralCountsAgree": (
                        raw_summary["parts"] == corrected_summary["parts"]
                        and raw_summary["measuresByPart"] == corrected_summary["measuresByPart"]
                        and raw_summary["pitchedEvents"] == corrected_summary["pitchedEvents"]
                    ),
                },
                "lyricEvidence": {
                    "sourceLyricsVisible": source_lyrics_visible,
                    "candidateLyricElements": raw_summary["lyrics"],
                    "correctedLyricElements": corrected_summary["lyrics"],
                    "directSyllableAlignmentEstablished": False,
                    "lyricsFabricated": False,
                },
                "existingComparisonArtifact": {
                    "path": str(audit_path.relative_to(root)),
                    "comparisonStatus": comparison.get("comparisonStatus"),
                    "autonomousDecision": comparison.get("autonomousDecision"),
                    "recordedEventStreamEqual": comparison.get("comparisonEvidence", {}).get("eventStreamEqual"),
                },
            }
        )
    summary = {
        "records": len(records),
        "autonomouslyBlocked": sum(item["disposition"] == "autonomously-blocked" for item in records),
        "rejected": 0,
        "safeToPromote": sum(item["safeToPromote"] is True for item in records),
        "humanReviewRequired": sum(item["humanReviewRequired"] is True for item in records),
        "errors": len(errors),
    }
    return {
        "kind": "sacred-harp-2025-agent-02-correction-dispositions",
        "version": 1,
        "status": "valid" if not errors and len(records) == len(EXPECTED_QUEUE_IDS) else "invalid",
        "policy": "Exact SH25 source scans and manifest MXLs remain authoritative. Correction derivatives remain isolated and unpromoted; visible lyrics are not encoded unless direct note-to-syllable alignment is established without inference.",
        "summary": summary,
        "errors": errors,
        "records": records,
    }


def main() -> int:
    payload = audit()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0 if payload["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
