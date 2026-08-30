#!/usr/bin/env python3
"""Build fail-closed shape hypotheses from the retained 2025 source scans.

The input MusicXML is normalized-v2 OMR of the immutable source image. The
output is a review aid only: shape tags are derived from the observed source
key and OMR pitch steps, and are never treated as source-verified notation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_shape_review_drafts import (
    local_path,
    local_string,
    parse_key,
    sha256,
    update_xml,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_METADATA = ROOT / "public" / "source-metadata-observations.json"
CORPUS = ROOT / "public" / "corpus.json"
CLEANED_RUN = ROOT / "work" / "omr" / "cleaned-normalized-v2-run.json"
DRAFT_INDEX = ROOT / "work" / "omr" / "draft-index.json"
OUTPUT_ROOT = ROOT / "work" / "omr" / "source-shape-review-drafts" / "2025"
PUBLIC_OUTPUT_ROOT = ROOT / "public" / "review-drafts" / "2025"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add_field(xml_bytes: bytes, field_name: str, value: str) -> bytes:
    """Add one provenance field without changing musical content."""
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_bytes)
    clean = lambda tag: tag.rsplit("}", 1)[-1]
    identification = next((x for x in root if clean(x.tag) == "identification"), None)
    if identification is None:
        identification = ET.Element("identification")
        root.insert(0, identification)
    miscellaneous = next((x for x in identification if clean(x.tag) == "miscellaneous"), None)
    if miscellaneous is None:
        miscellaneous = ET.SubElement(identification, "miscellaneous")
    existing = [x for x in miscellaneous if clean(x.tag) == "miscellaneous-field" and x.attrib.get("name") == field_name]
    target = existing[0] if existing else ET.SubElement(miscellaneous, "miscellaneous-field", {"name": field_name})
    target.text = value
    for duplicate in existing[1:]:
        miscellaneous.remove(duplicate)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_review_mxl(input_path: Path, output_path: Path, public_path: Path, key: tuple[str, str, int], source: dict[str, Any], queue_id: str, source_image_sha: str, source_omr_sha: str) -> tuple[int, int]:
    import zipfile

    with zipfile.ZipFile(input_path, "r") as source_zip:
        xml_name = next((name for name in source_zip.namelist() if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/")), None)
        if xml_name is None:
            raise ValueError("source OMR has no score XML member")
        updated, pitched_count, shape_count = update_xml(source_zip.read(xml_name), key, source, queue_id)
        updated = add_field(updated, "atlas-source-image-sha256", source_image_sha)
        updated = add_field(updated, "atlas-source-omr-sha256", source_omr_sha)
        updated = add_field(updated, "atlas-shape-encoding", "derived from source-scan OMR pitch steps + observed source key; not per-note visual verification")
        updated = add_field(updated, "atlas-provenance-policy", "review-only source-scan derivative; immutable 2025 image remains authoritative; no automatic OMR or promotion")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as output_zip:
            for name in source_zip.namelist():
                output_zip.writestr(name, updated if name == xml_name else source_zip.read(name))
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_bytes(output_path.read_bytes())
    return pitched_count, shape_count


def main() -> int:
    source_payload = load_json(SOURCE_METADATA)
    corpus = load_json(CORPUS)
    cleaned = load_json(CLEANED_RUN)
    draft_index = load_json(DRAFT_INDEX)
    cleaned_by_image = {item.get("originalPath", ""): item for item in cleaned.get("records", [])}
    draft_by_record = {item.get("record", ""): item for item in draft_index.get("records", [])}
    corpus_by_number = {
        song.get("songNo", ""): song
        for song in corpus.get("songs", [])
        if "sh2025" in song.get("books", [])
    }

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for observation in source_payload.get("records", []):
        queue_id = str(observation.get("queueId", ""))
        if not queue_id.startswith("sh2025/"):
            continue
        song_no = queue_id.removeprefix("sh2025/")
        source = observation.get("source", {})
        observations = observation.get("observations", {})
        source_key = str(observations.get("key", {}).get("value", ""))
        parsed_key = parse_key(source_key)
        image_relative = str(source.get("imagePath", ""))
        image_path = local_path(image_relative)
        image_sha = str(source.get("imageSha256", ""))
        cleaned_item = cleaned_by_image.get(image_relative, {})
        omr_relative = next(iter(cleaned_item.get("draftArtifacts", [])), "")
        if not omr_relative:
            record = next((item for item in draft_by_record.values() if str(item.get("record", "")).lower().startswith(song_no.lower() + "-")), {})
            omr_relative = str(record.get("artifact", ""))
        omr_path = local_path(omr_relative)
        if parsed_key is None:
            errors.append(f"{queue_id}: source key is not parseable: {source_key}")
            continue
        if not image_path.is_file():
            errors.append(f"{queue_id}: source image missing: {image_relative}")
            continue
        if image_sha and sha256(image_path) != image_sha:
            errors.append(f"{queue_id}: source image checksum mismatch")
            continue
        if not omr_path.is_file():
            errors.append(f"{queue_id}: source OMR missing: {omr_relative}")
            continue
        omr_sha = sha256(omr_path)
        song = corpus_by_number.get(song_no, {})
        metadata = song.get("metadataByBook", {}).get("sh2025", {})
        source_context = {
            "key": source_key,
            "mode": parsed_key[1],
            "timeSignature": metadata.get("timeSignature", "") or observations.get("meter", {}).get("timeSignature", ""),
        }
        output_path = OUTPUT_ROOT / f"{song_no}-source-shape-review.mxl"
        public_path = PUBLIC_OUTPUT_ROOT / f"source-{song_no}-shape-review.mxl"
        try:
            pitched_count, shape_count = write_review_mxl(omr_path, output_path, public_path, parsed_key, source_context, queue_id, image_sha, omr_sha)
        except Exception as exc:  # noqa: BLE001 - report every source record and continue the batch
            errors.append(f"{queue_id}: {exc}")
            continue
        audit = {
            "queueId": queue_id,
            "edition": "Sacred Harp, 2025 Edition",
            "songNo": song_no,
            "title": observation.get("title", song.get("title", "")),
            "status": "review-only-source-shape-draft",
            "safeToPromote": False,
            "sourceAuthority": {
                "sourceImagePath": image_relative,
                "sourceImageSha256": image_sha,
                "sourceImageUrl": source.get("imageUrl", ""),
                "immutable": source.get("immutable") is True,
                "observedKey": source_key,
                "observedMode": parsed_key[1],
                "observations": observations,
            },
            "sourceScanOmr": {
                "path": omr_relative,
                "sha256": omr_sha,
                "selectedWorkingLayer": cleaned_item.get("selectedWorkingLayer", "normalized-v2"),
                "selectedWorkingPath": cleaned_item.get("selectedWorkingPath", ""),
                "status": "review-only-omr-input",
            },
            "reviewDraft": {
                "path": local_string(output_path),
                "sha256": sha256(output_path),
                "publicPath": local_string(public_path).removeprefix("public/"),
                "publicSha256": sha256(public_path),
                "pitchedEventsRetained": pitched_count,
                "shapeNoteheadsAdded": shape_count,
                "sourceKey": source_key,
                "sourceMode": parsed_key[1],
                "sourceTimeSignature": source_context["timeSignature"],
                "encodingBasis": "source-scan OMR pitch steps + observed source key; every event and shape requires visual review",
            },
            "humanReviewRequired": True,
            "blockingFindings": [
                "The input is OMR of the source scan, not a human-verified transcription.",
                "Derived shape tags are hypotheses from OMR pitch steps and the observed source key; they are not direct per-note shape evidence.",
                "The immutable source image remains authoritative for every pitch, rhythm, rest, repeat, lyric, and shape decision.",
            ],
            "reviewProtocol": [
                "Compare every part and measure against the untouched source image.",
                "Verify the printed major/minor key and meter, including any missing structured metadata.",
                "Replace or correct every OMR event that differs from the page, then verify all four-shape noteheads directly.",
                "Do not promote until human sign-off and playback/transposition checks pass.",
            ],
        }
        audit_path = output_path.with_suffix(".json")
        audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        records.append(audit)

    summary = {
        "sourceRecords": len(records),
        "expectedSourceRecords": len(source_payload.get("records", [])),
        "errors": len(errors),
        "pitchedEventsRetained": sum(item["reviewDraft"]["pitchedEventsRetained"] for item in records),
        "shapeNoteheadsAdded": sum(item["reviewDraft"]["shapeNoteheadsAdded"] for item in records),
        "safeToPromote": 0,
    }
    index = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "version": "source-shape-review-drafts-v1",
        "policy": "Review-only derivatives from normalized-v2 OMR of immutable 2025 source scans. Derived shape tags are hypotheses and cannot be promoted automatically.",
        "summary": summary,
        "errors": errors,
        "records": records,
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "manifest.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": local_string(OUTPUT_ROOT / "manifest.json"), **summary}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
