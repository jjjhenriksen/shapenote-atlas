#!/usr/bin/env python3
"""Build fail-closed, shape-bearing MusicXML review derivatives.

These files are not transcriptions. They preserve a candidate witness's
pitched events and add a review-only four-shape spelling derived from the
source key. They must never be promoted without measure-by-measure comparison
against the immutable 2025 page.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "public" / "source-comparison-ledger.json"
OUTPUT_ROOT = ROOT / "work" / "omr" / "review-shape-drafts" / "2025"
PUBLIC_OUTPUT_ROOT = ROOT / "public" / "review-drafts" / "2025"

MAJOR_FIFTHS = {"C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F#": 6, "C#": 7, "Db": -5, "Ab": -4, "Eb": -3, "Bb": -2, "F": -1}
MINOR_FIFTHS = {"A": 0, "E": 1, "B": 2, "F#": 3, "C#": 4, "G#": 5, "D#": 6, "A#": 7, "Ab": -1, "Eb": -2, "Bb": -3, "F": -4, "C": -3, "G": -2, "D": -1}
STEP_ORDER = ["C", "D", "E", "F", "G", "A", "B"]
STEP_INDEX = {step: index for index, step in enumerate(STEP_ORDER)}
SHAPES = ["fa", "sol", "la", "fa", "sol", "la", "mi"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_path(relative: str) -> Path:
    return ROOT / relative


def local_string(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def clean_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_key(label: str, mode_hint: str = "") -> tuple[str, str, int] | None:
    match = re.match(r"^\s*([A-G])(?:#| sharp|\s+sharp|-sharp|b| flat|\s+flat|-flat)?\s+(major|minor)\s*$", label or "", re.IGNORECASE)
    if not match:
        return None
    root = match.group(1).upper()
    raw = (label or "").lower()
    if "sharp" in raw or "#" in raw:
        root += "#"
    elif "flat" in raw or re.search(r"[A-G]b", label or ""):
        root += "b"
    mode = match.group(2).lower() or mode_hint.lower()
    fifths = (MINOR_FIFTHS if mode == "minor" else MAJOR_FIFTHS).get(root)
    if fifths is None:
        return None
    return root, mode, fifths


def shape_for_step(step: str, root: str, mode: str) -> str | None:
    root_letter = root[:1]
    if step not in STEP_INDEX or root_letter not in STEP_INDEX:
        return None
    relative_major = STEP_ORDER[(STEP_INDEX[root_letter] + 2) % 7] if mode == "minor" else root_letter
    degree = (STEP_INDEX[step] - STEP_INDEX[relative_major]) % 7
    return SHAPES[degree]


def first_child(parent: ET.Element, name: str) -> ET.Element | None:
    return next((child for child in parent if clean_tag(child.tag) == name), None)


def add_or_replace_child(parent: ET.Element, name: str, text: str, after: set[str] | None = None) -> None:
    existing = [child for child in parent if clean_tag(child.tag) == name]
    if existing:
        existing[0].text = text
        for duplicate in existing[1:]:
            parent.remove(duplicate)
        return
    element = ET.Element(name)
    element.text = text
    if after:
        indexes = [index for index, child in enumerate(parent) if clean_tag(child.tag) in after]
        parent.insert(max(indexes) + 1 if indexes else len(parent), element)
    else:
        parent.append(element)


def add_miscellaneous_field(identification: ET.Element, name: str, value: str) -> None:
    miscellaneous = first_child(identification, "miscellaneous")
    if miscellaneous is None:
        miscellaneous = ET.SubElement(identification, "miscellaneous")
    field = ET.SubElement(miscellaneous, "miscellaneous-field", {"name": name})
    field.text = value


def update_xml(xml_bytes: bytes, key: tuple[str, str, int], source: dict[str, Any], queue_id: str) -> tuple[bytes, int, int]:
    root = ET.fromstring(xml_bytes)
    root.tag = clean_tag(root.tag)
    root_name = clean_tag(root.tag)
    if root_name != "score-partwise":
        raise ValueError(f"expected score-partwise XML, found {root_name}")
    root[:] = [child for child in root]

    root_key, mode, fifths = key
    shape_count = 0
    pitched_count = 0
    first_key = None
    first_time = None
    for part in root.iter():
        if clean_tag(part.tag) != "measure":
            continue
        attributes = first_child(part, "attributes")
        if attributes is not None:
            key_element = first_child(attributes, "key")
            if key_element is not None and first_key is None:
                first_key = key_element
            time_element = first_child(attributes, "time")
            if time_element is not None and first_time is None:
                first_time = time_element

        for note in [child for child in part if clean_tag(child.tag) == "note"]:
            pitch = first_child(note, "pitch")
            if pitch is None:
                continue
            step_element = first_child(pitch, "step")
            if step_element is None or not (step_element.text or "").strip():
                continue
            pitched_count += 1
            shape = shape_for_step((step_element.text or "").strip().upper(), root_key, mode)
            if shape is None:
                continue
            add_or_replace_child(note, "notehead", shape, {"stem", "type", "accidental", "dot"})
            shape_count += 1

    if first_key is None:
        first_measure = next((element for element in root.iter() if clean_tag(element.tag) == "measure"), None)
        if first_measure is not None:
            attributes = first_child(first_measure, "attributes")
            if attributes is None:
                attributes = ET.Element("attributes")
                first_measure.insert(0, attributes)
            first_key = ET.SubElement(attributes, "key")
    if first_key is not None:
        add_or_replace_child(first_key, "fifths", str(fifths))
        add_or_replace_child(first_key, "mode", mode, {"fifths"})

    identification = first_child(root, "identification")
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    source_key = source.get("key", "")
    source_mode = source.get("mode", mode) or mode
    add_miscellaneous_field(identification, "atlas-review-queue-id", queue_id)
    add_miscellaneous_field(identification, "atlas-review-status", "needs-human-measure-by-measure-review")
    add_miscellaneous_field(identification, "atlas-safe-to-promote", "false")
    add_miscellaneous_field(identification, "atlas-source-key", source_key)
    add_miscellaneous_field(identification, "atlas-source-mode", source_mode)
    add_miscellaneous_field(identification, "atlas-source-time-signature", str(source.get("timeSignature", "")))
    add_miscellaneous_field(identification, "atlas-shape-encoding", "derived from candidate pitches and source key; visually supported only at witness/page level")
    add_miscellaneous_field(identification, "atlas-provenance-policy", "review-only derivative; immutable 2025 source remains authoritative; no automatic OMR or promotion")

    output = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return output, pitched_count, shape_count


def write_review_mxl(
    candidate: Path,
    output: Path,
    public_output: Path,
    key: tuple[str, str, int],
    source: dict[str, Any],
    queue_id: str,
) -> tuple[int, int]:
    with zipfile.ZipFile(candidate, "r") as source_zip:
        xml_name = next((name for name in source_zip.namelist() if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/")), None)
        if xml_name is None:
            raise ValueError("candidate MXL has no score XML member")
        updated_xml, pitched_count, shape_count = update_xml(source_zip.read(xml_name), key, source, queue_id)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as output_zip:
            for name in source_zip.namelist():
                output_zip.writestr(name, updated_xml if name == xml_name else source_zip.read(name))
    public_output.parent.mkdir(parents=True, exist_ok=True)
    public_output.write_bytes(output.read_bytes())
    return pitched_count, shape_count


def main() -> int:
    ledger = load_json(LEDGER)
    records = []
    errors = []
    skipped = []
    for comparison in ledger.get("records", []):
        if comparison.get("comparisonStatus") != "strong-visual-match-not-promoted":
            skipped.append(comparison.get("queueId", ""))
            continue
        queue_id = str(comparison.get("queueId", ""))
        song_no = queue_id.removeprefix("sh2025/")
        source = comparison.get("sourceMetadata", {})
        parsed_key = parse_key(str(source.get("key", "")), str(source.get("mode", "")))
        candidate_relative = comparison.get("candidateWitness", {}).get("candidateMusicXmlPath", "")
        source_relative = comparison.get("sourceAuthority", {}).get("sourceImagePath", "")
        candidate = local_path(candidate_relative)
        source_image = local_path(source_relative)
        if parsed_key is None:
            errors.append(f"{queue_id}: source key is not parseable: {source.get('key', '')}")
            continue
        if not candidate.is_file():
            errors.append(f"{queue_id}: candidate MXL missing: {candidate_relative}")
            continue
        if not source_image.is_file():
            errors.append(f"{queue_id}: source image missing: {source_relative}")
            continue
        expected_candidate_sha = comparison.get("candidateWitness", {}).get("candidateMusicXmlSha256", "")
        if expected_candidate_sha and sha256(candidate) != expected_candidate_sha:
            errors.append(f"{queue_id}: candidate MXL checksum mismatch")
            continue
        expected_source_sha = comparison.get("sourceAuthority", {}).get("sourceImageSha256", "")
        if expected_source_sha and sha256(source_image) != expected_source_sha:
            errors.append(f"{queue_id}: source image checksum mismatch")
            continue

        output = OUTPUT_ROOT / f"{song_no}-shape-review.mxl"
        public_output = PUBLIC_OUTPUT_ROOT / f"{song_no}-shape-review.mxl"
        try:
            pitched_count, shape_count = write_review_mxl(candidate, output, public_output, parsed_key, source, queue_id)
        except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile) as exc:
            errors.append(f"{queue_id}: {exc}")
            continue
        audit = {
            "queueId": queue_id,
            "edition": "Sacred Harp, 2025 Edition",
            "title": comparison.get("title", ""),
            "status": "review-only-shape-draft",
            "safeToPromote": False,
            "sourceAuthority": {
                "path": source_relative,
                "sha256": expected_source_sha,
                "immutable": comparison.get("sourceAuthority", {}).get("immutable") is True,
                "visualShapeSupport": comparison.get("visualObservations", {}).get("shapeIdentity", ""),
            },
            "candidateWitness": {
                "path": candidate_relative,
                "sha256": expected_candidate_sha,
                "isOmrDerivative": comparison.get("candidateWitness", {}).get("candidateMusicXmlIsOmrDerivative") is True,
            },
            "reviewDraft": {
                "path": local_string(output),
                "sha256": sha256(output),
                "publicPath": local_string(public_output).removeprefix("public/"),
                "publicSha256": sha256(public_output),
                "pitchedEventsRetained": pitched_count,
                "shapeNoteheadsAdded": shape_count,
                "sourceKey": source.get("key", ""),
                "sourceMode": source.get("mode", "") or parsed_key[1],
                "sourceTimeSignature": source.get("timeSignature", ""),
                "encodingBasis": "candidate pitch steps + source key; not per-note visual verification",
            },
            "humanReviewRequired": True,
            "blockingFindings": comparison.get("blockingFindings", []),
            "reviewProtocol": [
                "Compare every retained pitched event and duration against the untouched 2025 page.",
                "Verify every four-shape notehead directly against the page; derived shape tags are hypotheses only.",
                "Verify source key, major/minor mode, meter, rests, repeats, endings, and lyric alignment.",
                "Do not promote until a human signs off and playback/transposition checks pass.",
            ],
        }
        audit_path = output.with_suffix(".json")
        audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        records.append(audit)

    summary = {
        "selectedStrongMatches": len(records),
        "skippedNonStrongMatches": len(skipped),
        "errors": len(errors),
        "pitchedEventsRetained": sum(item["reviewDraft"]["pitchedEventsRetained"] for item in records),
        "shapeNoteheadsAdded": sum(item["reviewDraft"]["shapeNoteheadsAdded"] for item in records),
        "safeToPromote": 0,
    }
    index = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "version": "shape-review-drafts-v2",
        "policy": "Review-only MusicXML derivatives. They add derived four-shape noteheads and source metadata to candidate OMR witnesses; they are not source-verified notation and cannot be promoted automatically.",
        "summary": summary,
        "errors": errors,
        "records": records,
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "manifest.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": local_string(OUTPUT_ROOT / "manifest.json"), **summary}, ensure_ascii=False, indent=2))
    if errors:
        print(json.dumps({"errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
