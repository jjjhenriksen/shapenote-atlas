#!/usr/bin/env python3
"""Audit shape-note provenance without promoting or rewriting notation.

This validator deliberately distinguishes four different facts:

* a structured source encoded a notehead value;
* a review derivative added a shape from pitch/key data; and
* a shape is absent or incompatible with the dashboard's four-shape renderer; and
* a source shape was directly verified against a visual or authoritative witness.

The current report records no direct visual/authoritative witness comparison as
verified. It does not claim that an encoded or derived shape matches a raster
page. The source image remains authoritative for that event-level comparison.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public" / "corpus.json"
REPORT = ROOT / "public" / "shape-evidence-audit.json"
REVIEW_MANIFESTS = (
    ROOT / "work" / "omr" / "review-shape-drafts" / "2025" / "manifest.json",
    ROOT / "work" / "omr" / "source-shape-review-drafts" / "2025" / "manifest.json",
)
FOUR_SHAPES = {"fa", "sol", "la", "mi"}
SEVEN_SHAPES = FOUR_SHAPES | {"do", "re", "so", "ti"}
ALLOWED_REVIEW_STATUS = {
    "review-only-shape-draft",
    "review-only-source-shape-draft",
}


def shape_for_step(step: str, key: str, mode: str) -> str | None:
    """Return the four-shape degree used by a source-keyed fixture.

    This is intentionally step/key based: it is a testable shape hypothesis,
    not a source-verification claim.
    """

    steps = ["C", "D", "E", "F", "G", "A", "B"]
    patterns = ["fa", "sol", "la", "fa", "sol", "la", "mi"]
    step = step.strip().upper()
    key_parts = key.strip().split()
    tonic = key_parts[0].replace("♯", "#").replace("♭", "b") if key_parts else ""
    if step not in steps or not tonic or tonic[0] not in steps:
        return None
    relative = tonic[0]
    if mode.lower() == "minor":
        relative = steps[(steps.index(relative) + 2) % 7]
    return patterns[(steps.index(step) - steps.index(relative)) % 7]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def asset_shape_counts(asset: dict[str, Any]) -> tuple[int, Counter[str]]:
    shapes: Counter[str] = Counter()
    pitched = 0
    for part in asset.get("parts", []):
        for event in part.get("events", []):
            if event.get("rest") or not event.get("step"):
                continue
            pitched += 1
            shape = str(event.get("shape") or event.get("notehead") or "").strip().lower()
            if shape:
                shapes[shape] += 1
    return pitched, shapes


def classify_asset(field: str, provenance: dict[str, Any], pitched: int, shapes: Counter[str]) -> str:
    provenance = provenance or {}
    if not shapes:
        return "not-encoded"
    if field == "draftScoreByBook" or provenance.get("kind") == "omr-draft":
        return "derived-review-or-draft"
    if set(shapes) - FOUR_SHAPES:
        if set(shapes) <= SEVEN_SHAPES:
            return "source-encoded-seven-shape-or-mixed"
        return "source-encoded-unmapped-notehead"
    return "source-encoded-four-shape-complete" if sum(shapes.values()) == pitched else "source-encoded-four-shape-partial"


def evidence_disposition(classification: str) -> str:
    """Map an artifact classification to the fail-closed evidence vocabulary."""

    if classification == "derived-review-or-draft":
        return "derived"
    if classification == "not-encoded":
        return "unavailable"
    if classification.startswith("source-encoded-"):
        return "source-encoded"
    return "unavailable"


def blocked_reason(classification: str) -> str | None:
    if classification == "derived-review-or-draft":
        return "Shape was derived from pitch/key data and has no event-level source witness verification."
    if classification == "not-encoded":
        return "No structured shape encoding is present in this score asset."
    if classification == "source-encoded-seven-shape-or-mixed":
        return "Structured witness contains seven-shape values; do not coerce them into four-shape rendering."
    if classification == "source-encoded-unmapped-notehead":
        return "Structured witness contains graphical/custom notehead values without a validated four-shape mapping."
    if classification == "source-encoded-four-shape-partial":
        return "Some pitched events lack a structured four-shape value; source comparison is still required."
    if classification == "source-encoded-four-shape-complete":
        return "Structured four-shape coverage is complete, but direct source comparison is not recorded."
    return "No promotable shape evidence."


def review_mxl_shape_counts(path: Path) -> tuple[int, Counter[str], dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        xml_name = next(
            name
            for name in archive.namelist()
            if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/")
        )
        root = ET.fromstring(archive.read(xml_name))

    clean = lambda tag: tag.rsplit("}", 1)[-1]
    pitched = 0
    shapes: Counter[str] = Counter()
    fields: dict[str, str] = {}
    for element in root.iter():
        if clean(element.tag) == "miscellaneous-field":
            fields[element.attrib.get("name", "")] = element.text or ""
        if clean(element.tag) != "note":
            continue
        pitch = next((child for child in element if clean(child.tag) == "pitch"), None)
        if pitch is None:
            continue
        pitched += 1
        notehead = next((child for child in element if clean(child.tag) == "notehead"), None)
        if notehead is not None and (notehead.text or "").strip():
            shapes[(notehead.text or "").strip().lower()] += 1
    return pitched, shapes, fields


def build_report() -> dict[str, Any]:
    corpus = load_json(CORPUS)
    unique_assets: dict[str, dict[str, Any]] = {}
    asset_records: list[dict[str, Any]] = []
    for song in corpus.get("songs", []):
        for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook"):
            for book_id, preview in (song.get(field) or {}).items():
                score_ref = str(preview.get("scoreRef", ""))
                if not score_ref:
                    continue
                path = ROOT / "public" / score_ref.lstrip("/")
                if not path.is_file():
                    asset_records.append({"queueId": f"{book_id}/{song.get('songNo', '')}", "field": field, "scoreRef": score_ref, "classification": "missing-asset"})
                    continue
                if score_ref not in unique_assets:
                    asset = load_json(path)
                    pitched, shapes = asset_shape_counts(asset)
                    unique_assets[score_ref] = {
                        "scoreRef": score_ref,
                        "pitchedEvents": pitched,
                        "shapeCounts": dict(sorted(shapes.items())),
                        "classification": classify_asset(field, asset.get("provenance", {}), pitched, shapes),
                        "keySignature": asset.get("keySignature", ""),
                        "keyEvidence": asset.get("keyEvidence", {}),
                        "provenance": asset.get("provenance", {}),
                    }
                    classification = unique_assets[score_ref]["classification"]
                    unique_assets[score_ref].update({
                        "evidenceDisposition": evidence_disposition(classification),
                        "sourceVerification": "not-verified",
                        "safeToPromote": False,
                        "blockedReason": blocked_reason(classification),
                    })
                asset_records.append({
                    "queueId": f"{book_id}/{song.get('songNo', '')}",
                    "title": song.get("title", ""),
                    "book": book_id,
                    "field": field,
                    "scoreRef": score_ref,
                    "classification": unique_assets[score_ref]["classification"],
                    "evidenceDisposition": unique_assets[score_ref]["evidenceDisposition"],
                    "sourceVerification": unique_assets[score_ref]["sourceVerification"],
                    "safeToPromote": unique_assets[score_ref]["safeToPromote"],
                    "blockedReason": unique_assets[score_ref]["blockedReason"],
                })

    review_records: list[dict[str, Any]] = []
    review_errors: list[str] = []
    seen_review_paths: set[str] = set()
    for manifest_path in REVIEW_MANIFESTS:
        if not manifest_path.is_file():
            review_errors.append(f"missing manifest: {manifest_path.relative_to(ROOT)}")
            continue
        manifest = load_json(manifest_path)
        for record in manifest.get("records", []):
            queue_id = str(record.get("queueId", ""))
            draft = record.get("reviewDraft", {})
            relative = str(draft.get("path", ""))
            path = ROOT / relative
            item: dict[str, Any] = {
                "queueId": queue_id,
                "manifest": manifest_path.relative_to(ROOT).as_posix(),
                "path": relative,
                "status": record.get("status", ""),
                "safeToPromote": record.get("safeToPromote"),
                "humanReviewRequired": record.get("humanReviewRequired"),
                "evidenceDisposition": "derived",
                "sourceVerification": "not-verified",
                "blockedReason": "Shape was derived from OMR/pitch/key data and remains review-only.",
            }
            if relative in seen_review_paths:
                review_errors.append(f"duplicate review artifact path: {relative}")
                review_records.append(item)
                continue
            seen_review_paths.add(relative)
            if not path.is_file():
                review_errors.append(f"missing review artifact: {queue_id} ({relative})")
                review_records.append(item)
                continue
            try:
                pitched, shapes, fields = review_mxl_shape_counts(path)
            except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile, StopIteration) as exc:
                review_errors.append(f"cannot parse review artifact {queue_id}: {exc}")
                review_records.append(item)
                continue
            item.update({
                "pitchedEvents": pitched,
                "shapeCounts": dict(sorted(shapes.items())),
                "shapeCount": sum(shapes.values()),
                "provenanceFields": sorted(fields),
                "classification": "derived-review-only",
            })
            if record.get("status") not in ALLOWED_REVIEW_STATUS:
                review_errors.append(f"{queue_id}: invalid review status {record.get('status')!r}")
            if record.get("safeToPromote") is not False:
                review_errors.append(f"{queue_id}: review artifact is not fail-closed")
            if record.get("humanReviewRequired") is not True:
                review_errors.append(f"{queue_id}: review artifact lost its review gate")
            if not shapes:
                review_errors.append(f"{queue_id}: review artifact has no derived noteheads")
            if sum(shapes.values()) != pitched or not set(shapes) <= FOUR_SHAPES:
                review_errors.append(f"{queue_id}: review artifact shape coverage/value mismatch")
            if "atlas-shape-encoding" not in fields or "atlas-safe-to-promote" not in fields:
                review_errors.append(f"{queue_id}: required shape provenance fields missing")
            review_records.append(item)

    classification_counts = Counter(item["classification"] for item in unique_assets.values())
    shape_records = [item for item in asset_records if item["classification"] != "not-encoded"]
    seven_shape_records = [item for item in asset_records if item["classification"] == "source-encoded-seven-shape-or-mixed"]
    partial_records = [item for item in asset_records if item["classification"] == "source-encoded-four-shape-partial"]
    unique_shape_assets = len(unique_assets) - classification_counts.get("not-encoded", 0)
    report = {
        "kind": "shape-evidence-audit",
        "version": "1",
        "policy": "Source-encoded shapes are not proof of raster-page equality; derived shapes are review-only; seven-shape values must not be silently coerced into four-shape rendering.",
        "verificationPolicy": "Only direct source engraving or authoritative shape-preserving witness evidence may receive source-verified status; this audit records no such promotion.",
        "summary": {
            "uniqueStructuredAssets": len(unique_assets),
            "assetRecordOccurrences": len(asset_records),
            "uniqueAssetsWithAnyEncodedShape": unique_shape_assets,
            "recordOccurrencesWithAnyEncodedShape": len(shape_records),
            "sourceEncodedFourShapeComplete": classification_counts.get("source-encoded-four-shape-complete", 0),
            "sourceEncodedFourShapePartial": classification_counts.get("source-encoded-four-shape-partial", 0),
            "sourceEncodedSevenShapeOrMixed": classification_counts.get("source-encoded-seven-shape-or-mixed", 0),
            "sourceEncodedUnmappedNotehead": classification_counts.get("source-encoded-unmapped-notehead", 0),
            "sourceVerifiedUniqueAssets": 0,
            "sourceEncodedUnverifiedUniqueAssets": unique_shape_assets,
            "unavailableUniqueAssets": classification_counts.get("not-encoded", 0),
            "derivedReviewOnlyArtifacts": len(review_records),
            "unsupportedShapeAssets": classification_counts.get("unsupported-shape-value", 0),
            "reviewArtifacts": len(review_records),
            "reviewArtifactsDerivedOnly": sum(item.get("classification") == "derived-review-only" for item in review_records),
            "safeToPromote": 0,
            "reviewErrors": len(review_errors),
        },
        "authoritativeAssetClassifications": sorted(unique_assets.values(), key=lambda item: item["scoreRef"]),
        "assetOccurrences": asset_records,
        "sevenShapeOccurrences": seven_shape_records,
        "partialFourShapeOccurrences": partial_records,
        "reviewArtifacts": review_records,
        "errors": review_errors,
        "fixtureChecks": {
            "C major C": shape_for_step("C", "C major", "major"),
            "C major E": shape_for_step("E", "C major", "major"),
            "A minor A": shape_for_step("A", "A minor", "minor"),
            "F-sharp minor F": shape_for_step("F", "F# minor", "minor"),
            "unknown key": shape_for_step("C", "", ""),
            "altered step": shape_for_step("H", "C major", "major"),
        },
    }
    return report


def validate_fixture_checks(report: dict[str, Any]) -> None:
    expected = {
        "C major C": "fa",
        "C major E": "la",
        "A minor A": "la",
        "F-sharp minor F": "la",
        "unknown key": None,
        "altered step": None,
    }
    if report.get("fixtureChecks") != expected:
        raise SystemExit(f"shape fixture drift: {report.get('fixtureChecks')!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write public/shape-evidence-audit.json")
    args = parser.parse_args()
    report = build_report()
    validate_fixture_checks(report)
    if args.write:
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": REPORT.relative_to(ROOT).as_posix(), **report["summary"]}, ensure_ascii=False, sort_keys=True))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
