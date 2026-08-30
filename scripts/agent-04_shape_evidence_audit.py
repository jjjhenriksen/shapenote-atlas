#!/usr/bin/env python3
"""Produce an isolated, fail-closed audit of shape metadata and render evidence.

This audit never edits public data or the source artifacts.  It reads the
authoritative corpus, both review-draft manifests, and both existing
Windlesham comparison records, then writes only beneath ``work/agent-04-shapes``.
Rendered PDFs are evidence that MuseScore can open the draft; they are not
evidence that a rendered notehead agrees with the immutable source page.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "work" / "agent-04-shapes"
RENDER_ROOT = OUTPUT_ROOT / "rendered"
FOUR_SHAPES = {"fa", "sol", "la", "mi"}
ALLOWED_REVIEW_STATUSES = {
    "review-only-shape-draft",
    "review-only-source-shape-draft",
}
REVIEW_MANIFESTS = (
    ("review-drafts", ROOT / "work/omr/review-shape-drafts/2025/manifest.json"),
    ("source-shape-drafts", ROOT / "work/omr/source-shape-review-drafts/2025/manifest.json"),
)
WINDLESHAM_RECORDS = (
    ROOT / "work/source-transcriptions/2025/81b-windlesham-autonomous-comparison.json",
    ROOT / "work/source-transcriptions/2025/81b-windlesham-comparison.json",
)
WINDLESHAM_RAW_OMR = ROOT / "work/omr/81b-windlesham/source.mxl"
WINDLESHAM_NORMALIZED_OMR = ROOT / "work/omr/cleaned-normalized-v2-81b-windlesham-92b7e3d6fc/work__source-images__2025__81b-windlesham-92b7e3d6fc.mxl"
WINDLESHAM_SOURCE_IMAGE = ROOT / "work/source-images/2025/81b-windlesham-92b7e3d6fc.jpg"
WINDLESHAM_SOURCE_COPY = ROOT / "work/omr/81b-windlesham/source.jpg"
WINDLESHAM_CANDIDATE_ROOT = ROOT / "work/omr/clean-source-candidates"
WINDLESHAM_IMAGEGEN = (
    ROOT / "work/transcription-images/working/imagegen-batches/batch-a/81b-imagegen-v1.png",
    ROOT / "work/transcription-images/working/imagegen-pilot/81b-windlesham-imagegen-v1.png",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def local_path(value: str) -> Path:
    return ROOT / value.lstrip("/")


def field_map(root: ET.Element) -> dict[str, str]:
    return {
        element.attrib.get("name", ""): element.text or ""
        for element in root.iter()
        if clean(element.tag) == "miscellaneous-field"
    }


def mxl_stats(path: Path) -> dict[str, Any]:
    """Read structural notehead evidence without changing the MXL."""

    with zipfile.ZipFile(path) as archive:
        corrupt_member = archive.testzip()
        if corrupt_member is not None:
            raise ValueError(f"corrupt member {corrupt_member}")
        xml_name = next(
            (
                name
                for name in archive.namelist()
                if name.lower().endswith(".xml") and not name.lower().startswith("meta-inf/")
            ),
            None,
        )
        if xml_name is None:
            raise ValueError("no score XML member")
        root = ET.fromstring(archive.read(xml_name))

    parts = [element for element in root if clean(element.tag) == "part"]
    measures_by_part: dict[str, int] = {}
    pitched = 0
    rests = 0
    noteheads = 0
    shapes: Counter[str] = Counter()
    for index, part in enumerate(parts, start=1):
        part_id = part.attrib.get("id", f"P{index}")
        measures_by_part[part_id] = sum(clean(child.tag) == "measure" for child in part)
        for note in (element for element in part.iter() if clean(element.tag) == "note"):
            pitch = next((child for child in note if clean(child.tag) == "pitch"), None)
            if pitch is None:
                if any(clean(child.tag) == "rest" for child in note):
                    rests += 1
                continue
            pitched += 1
            notehead = next((child for child in note if clean(child.tag) == "notehead"), None)
            if notehead is not None and (notehead.text or "").strip():
                noteheads += 1
                shapes[(notehead.text or "").strip().lower()] += 1
    return {
        "sha256": sha256(path),
        "parts": len(parts),
        "measuresByPart": measures_by_part,
        "pitchedEvents": pitched,
        "restEvents": rests,
        "directNoteheads": noteheads,
        "shapeCounts": dict(sorted(shapes.items())),
        "shapeValues": sorted(shapes),
        "fourShapeCoverage": (
            "complete"
            if pitched and noteheads == pitched and set(shapes) <= FOUR_SHAPES
            else "partial-or-unsupported"
        ),
        "fields": field_map(root),
    }


def mscore_path() -> Path | None:
    candidates = (
        Path("/Applications/MuseScore 4.app/Contents/MacOS/mscore"),
        shutil.which("mscore"),
        shutil.which("musescore"),
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def render(path: Path, output: Path, executable: Path | None) -> dict[str, Any]:
    """Render one MXL to an isolated PDF and report only observable output."""

    result: dict[str, Any] = {
        "input": path.relative_to(ROOT).as_posix(),
        "output": output.relative_to(ROOT).as_posix(),
        "status": "unavailable",
    }
    if executable is None:
        result["reason"] = "MuseScore executable not found"
        return result
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            [str(executable), "-o", str(output), str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["status"] = "failed"
        result["reason"] = str(exc)
        return result
    result["returncode"] = completed.returncode
    if not output.is_file() or output.stat().st_size == 0:
        result["status"] = "failed"
        result["reason"] = "MuseScore did not produce a non-empty PDF"
        result["stderrTail"] = completed.stderr[-500:]
        return result
    result.update(
        {
            "status": "rendered",
            "sha256": sha256(output),
            "bytes": output.stat().st_size,
            "stderrWarning": completed.stderr[-500:] if completed.stderr else "",
        }
    )
    try:
        info = subprocess.run(["pdfinfo", str(output)], capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        info = None
    if info and info.returncode == 0:
        for line in info.stdout.splitlines():
            if line.startswith("Pages:"):
                result["pages"] = int(line.split(":", 1)[1].strip())
                break
    return result


def verify_hash(path: Path, expected: str) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    actual = sha256(path)
    return actual == expected, actual


def audit_review_record(layer: str, manifest_path: Path, record: dict[str, Any], render_jobs: list[tuple[str, Path, Path]]) -> dict[str, Any]:
    queue_id = str(record.get("queueId", ""))
    draft = record.get("reviewDraft", {})
    draft_path = local_path(str(draft.get("path", "")))
    public_path = ROOT / "public" / str(draft.get("publicPath", ""))
    findings: list[str] = []
    checks: dict[str, Any] = {
        "manifest": manifest_path.relative_to(ROOT).as_posix(),
        "status": record.get("status"),
        "safeToPromote": record.get("safeToPromote"),
        "humanReviewRequired": record.get("humanReviewRequired"),
    }
    if record.get("status") not in ALLOWED_REVIEW_STATUSES:
        findings.append("manifest status is not a recognized review-only status")
    if record.get("safeToPromote") is not False:
        findings.append("safeToPromote is not false")
    if record.get("humanReviewRequired") is not True:
        findings.append("humanReviewRequired is not true")

    source = record.get("sourceAuthority", {})
    source_image_value = source.get("sourceImagePath", source.get("path", ""))
    source_image_hash = source.get("sourceImageSha256", source.get("sha256", ""))
    source_image = local_path(str(source_image_value))
    image_ok, image_actual = verify_hash(source_image, str(source_image_hash))
    checks["sourceImage"] = {
        "path": str(source_image_value),
        "expectedSha256": source_image_hash,
        "actualSha256": image_actual,
        "immutable": source.get("immutable") is True,
        "hashMatches": image_ok,
    }
    if not image_ok:
        findings.append("immutable source-image witness is missing or checksum-mismatched")
    if source.get("immutable") is not True:
        findings.append("source-image witness is not marked immutable")

    source_omr = record.get("sourceScanOmr", {})
    if source_omr:
        source_omr_path = local_path(str(source_omr.get("path", "")))
        omr_ok, omr_actual = verify_hash(source_omr_path, str(source_omr.get("sha256", "")))
        checks["sourceScanOmr"] = {
            "path": str(source_omr.get("path", "")),
            "expectedSha256": source_omr.get("sha256", ""),
            "actualSha256": omr_actual,
            "hashMatches": omr_ok,
            "status": source_omr.get("status"),
        }
        if not omr_ok:
            findings.append("source-scan OMR witness is missing or checksum-mismatched")
        if source_omr.get("status") != "review-only-omr-input":
            findings.append("source-scan OMR is not labeled review-only")

    local_ok, local_actual = verify_hash(draft_path, str(draft.get("sha256", "")))
    public_ok, public_actual = verify_hash(public_path, str(draft.get("publicSha256", "")))
    copies_equal = draft_path.is_file() and public_path.is_file() and draft_path.read_bytes() == public_path.read_bytes()
    checks["draftCopies"] = {
        "local": draft_path.relative_to(ROOT).as_posix(),
        "public": public_path.relative_to(ROOT).as_posix(),
        "localHashMatches": local_ok,
        "publicHashMatches": public_ok,
        "byteEqual": copies_equal,
    }
    if not local_ok or not public_ok or not copies_equal:
        findings.append("local/public review-draft provenance or byte-equality check failed")
    if not draft_path.is_file():
        findings.append("review MXL is missing")
    else:
        try:
            stats = mxl_stats(draft_path)
            checks["mxl"] = stats
            if stats["directNoteheads"] != stats["pitchedEvents"]:
                findings.append("not every pitched event has a direct notehead tag")
            if not set(stats["shapeValues"]) <= FOUR_SHAPES:
                findings.append("draft contains a non-four-shape notehead value")
            if stats["directNoteheads"] != int(draft.get("shapeNoteheadsAdded", -1)):
                findings.append("manifest shape count does not match the rendered draft input")
            if stats["pitchedEvents"] != int(draft.get("pitchedEventsRetained", -1)):
                findings.append("manifest pitched-event count does not match the rendered draft input")
            required = {"atlas-review-status", "atlas-safe-to-promote", "atlas-shape-encoding"}
            if not required <= set(stats["fields"]):
                findings.append("required shape provenance fields are missing from the MXL")
            if stats["fields"].get("atlas-safe-to-promote") != "false":
                findings.append("MXL safe-to-promote field is not false")
            render_path = RENDER_ROOT / layer / (queue_id.replace("/", "-") + ".pdf")
            render_jobs.append((f"{layer}:{queue_id}", draft_path, render_path))
        except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile, StopIteration) as exc:
            checks["mxlError"] = str(exc)
            findings.append(f"review MXL cannot be parsed: {exc}")

    # The manifest itself explicitly describes these values as derived. A PDF
    # render cannot turn them into source-verified notehead evidence.
    direct = False
    if layer == "source-shape-drafts":
        findings.append("four-shape noteheads are derived from source-scan OMR pitch/key data, not direct per-event engraving evidence")
    else:
        findings.append("four-shape noteheads are derived from a candidate/OMR witness, not direct per-event source engraving evidence")
    findings.append("PDF rendering proves only that the review derivative renders; it does not prove page-level notehead agreement")
    return {
        "recordType": layer,
        "queueId": queue_id,
        "title": record.get("title", ""),
        "disposition": "blocked" if not any("cannot" in item or "missing" in item or "checksum" in item for item in findings) else "rejected",
        "directSourceShapeEvidence": direct,
        "safeToPromote": False,
        "findings": findings,
        "checks": checks,
    }


def audit_authoritative_assets() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    corpus = load_json(ROOT / "public/corpus.json")
    assets: dict[str, dict[str, Any]] = {}
    occurrences: list[dict[str, Any]] = []
    for song in corpus.get("songs", []):
        for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook"):
            for book, preview in (song.get(field) or {}).items():
                score_ref = str(preview.get("scoreRef", ""))
                if not score_ref:
                    continue
                path = ROOT / "public" / score_ref.lstrip("/")
                if not path.is_file():
                    continue
                if score_ref not in assets:
                    asset = load_json(path)
                    pitched = 0
                    shapes: Counter[str] = Counter()
                    for part in asset.get("parts", []):
                        for event in part.get("events", []):
                            if event.get("rest") or not event.get("step"):
                                continue
                            pitched += 1
                            value = str(event.get("shape") or event.get("notehead") or "").strip().lower()
                            if value:
                                shapes[value] += 1
                    assets[score_ref] = {
                        "scoreRef": score_ref,
                        "sha256": sha256(path),
                        "pitchedEvents": pitched,
                        "shapeCounts": dict(sorted(shapes.items())),
                        "classification": (
                            "no-structured-shape"
                            if not shapes
                            else "source-encoded-four-shape-candidate"
                            if set(shapes) <= FOUR_SHAPES and sum(shapes.values()) == pitched
                            else "source-encoded-seven-shape-or-mixed"
                            if set(shapes) <= FOUR_SHAPES | {"do", "re", "so", "ti"}
                            else "source-encoded-unmapped-notehead"
                        ),
                    }
                if assets[score_ref]["classification"] != "no-structured-shape":
                    occurrences.append({
                        "queueId": f"{book}/{song.get('songNo', '')}",
                        "title": song.get("title", ""),
                        "field": field,
                        "scoreRef": score_ref,
                    })
    records: list[dict[str, Any]] = []
    for asset in assets.values():
        if asset["classification"] == "no-structured-shape":
            continue
        if asset["classification"] == "source-encoded-four-shape-candidate":
            reason = "structured four-shape coverage is complete, but no direct source-page or authoritative shape-preserving event comparison is recorded"
        elif asset["classification"] == "source-encoded-seven-shape-or-mixed":
            reason = "structured witness contains seven-shape values; do not coerce it into four-shape rendering"
        else:
            reason = "structured witness contains graphical/custom notehead values without a validated four-shape mapping"
        records.append({
            "recordType": "authoritative-structured-asset",
            "scoreRef": asset["scoreRef"],
            "disposition": "blocked",
            "directSourceShapeEvidence": False,
            "safeToPromote": False,
            "findings": [reason, "encoded metadata alone does not prove rendered notehead equality to the source engraving"],
            "asset": asset,
            "occurrences": [item for item in occurrences if item["scoreRef"] == asset["scoreRef"]],
        })
    return records, {
        "uniqueStructuredAssets": len(assets),
        "uniqueAssetsWithEncodedShape": len(records),
        "unavailableUniqueAssets": sum(item["classification"] == "no-structured-shape" for item in assets.values()),
        "encodedAssetOccurrences": len(occurrences),
    }


def audit_windlesham(render_jobs: list[tuple[str, Path, Path]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in WINDLESHAM_RECORDS:
        if not path.is_file():
            records.append({"recordType": "81b-comparison-record", "path": str(path), "disposition": "rejected", "safeToPromote": False, "findings": ["comparison record is missing"]})
            continue
        data = load_json(path)
        candidate = data.get("candidateWitness", {})
        candidate_path_value = candidate.get("candidateMusicXmlPath", "")
        candidate_path = local_path(str(candidate_path_value)) if candidate_path_value else None
        findings = [
            "duplicate comparison record is retained as a distinct record; duplicate identity does not merge evidence",
            "candidate MusicXML is an OMR derivative and does not encode direct four-shape noteheads",
            "same-title PDF/rendered page evidence is not an event-level source-shape proof",
            "generated image pixels are explicitly excluded from notation evidence",
        ]
        item: dict[str, Any] = {
            "recordType": "81b-comparison-record",
            "path": path.relative_to(ROOT).as_posix(),
            "recordSha256": sha256(path),
            "recordIdentity": data.get("recordIdentity", path.stem),
            "queueId": data.get("queueId"),
            "comparisonStatus": data.get("comparisonStatus"),
            "disposition": "blocked",
            "directSourceShapeEvidence": False,
            "safeToPromote": False,
            "findings": findings,
            "sourceImageSha256": data.get("sourceAuthority", {}).get("sourceImageSha256"),
            "retainedSourceCopy": data.get("retainedSourceImageDuplicate", {}),
            "candidateWitness": {
                "path": candidate_path_value,
                "sha256": candidate.get("candidateMusicXmlSha256"),
                "isOmrDerivative": candidate.get("candidateMusicXmlIsOmrDerivative", candidate.get("isOmrDerivative")),
            },
        }
        if data.get("safeToPromote") is not False:
            item["findings"].append("comparison record is not fail-closed")
            item["disposition"] = "rejected"
        if candidate_path and candidate_path.is_file():
            try:
                stats = mxl_stats(candidate_path)
                item["candidateMxl"] = stats
                item["candidateHashMatches"] = stats["sha256"] == candidate.get("candidateMusicXmlSha256")
                candidate_render = RENDER_ROOT / "81b-candidates" / (path.stem + ".pdf")
                render_jobs.append((f"81b:{path.stem}", candidate_path, candidate_render))
            except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile, StopIteration) as exc:
                item["findings"].append(f"candidate MusicXML cannot be parsed: {exc}")
                item["disposition"] = "rejected"
        else:
            item["findings"].append("candidate MusicXML witness is missing")
            item["disposition"] = "rejected"
        records.append(item)

    source_hash = sha256(WINDLESHAM_SOURCE_IMAGE) if WINDLESHAM_SOURCE_IMAGE.is_file() else ""
    copy_hash = sha256(WINDLESHAM_SOURCE_COPY) if WINDLESHAM_SOURCE_COPY.is_file() else ""
    common_hashes = {
        "sourceImageSha256": source_hash,
        "retainedSourceCopySha256": copy_hash,
        "retainedSourceCopyByteEqual": WINDLESHAM_SOURCE_IMAGE.is_file() and WINDLESHAM_SOURCE_COPY.is_file() and WINDLESHAM_SOURCE_IMAGE.read_bytes() == WINDLESHAM_SOURCE_COPY.read_bytes(),
        "rawOmrSha256": sha256(WINDLESHAM_RAW_OMR) if WINDLESHAM_RAW_OMR.is_file() else "",
        "normalizedOmrSha256": sha256(WINDLESHAM_NORMALIZED_OMR) if WINDLESHAM_NORMALIZED_OMR.is_file() else "",
        "comparisonRecordCount": len(records),
        "sourceImageImmutable": True,
    }
    common_hashes["bothRecordsShareSourceWitness"] = len({item.get("sourceImageSha256") for item in records}) == 1 and bool(records)
    return {"records": records, "duplicateGroup": common_hashes, "imagegenArtifacts": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha256(p) if p.is_file() else "", "notationEvidence": False} for p in WINDLESHAM_IMAGEGEN]}


def run_audit(render_enabled: bool) -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    RENDER_ROOT.mkdir(parents=True, exist_ok=True)
    render_jobs: list[tuple[str, Path, Path]] = []
    records, authoritative_summary = audit_authoritative_assets()
    review_summary: dict[str, Any] = {}
    for layer, manifest_path in REVIEW_MANIFESTS:
        if not manifest_path.is_file():
            review_summary[layer] = {"manifest": manifest_path.relative_to(ROOT).as_posix(), "records": [], "errors": ["manifest missing"]}
            continue
        manifest = load_json(manifest_path)
        layer_records = [audit_review_record(layer, manifest_path, record, render_jobs) for record in manifest.get("records", [])]
        records.extend(layer_records)
        review_summary[layer] = {
            "manifest": manifest_path.relative_to(ROOT).as_posix(),
            "manifestSummary": manifest.get("summary", {}),
            "records": len(layer_records),
            "blocked": sum(item["disposition"] == "blocked" for item in layer_records),
            "rejected": sum(item["disposition"] == "rejected" for item in layer_records),
            "completeStructuralFourShapeRecords": sum(item.get("checks", {}).get("mxl", {}).get("fourShapeCoverage") == "complete" for item in layer_records),
            "directSourceShapeEvidence": 0,
        }
    windlesham = audit_windlesham(render_jobs)
    records.extend(windlesham["records"])

    render_results: dict[str, dict[str, Any]] = {}
    if render_enabled:
        executable = mscore_path()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(render, source, output, executable): key for key, source, output in render_jobs}
            for future in as_completed(futures):
                render_results[futures[future]] = future.result()
    else:
        render_results = {key: {"status": "not-run", "input": source.relative_to(ROOT).as_posix(), "output": output.relative_to(ROOT).as_posix()} for key, source, output in render_jobs}

    for item in records:
        if item["recordType"] in {"review-drafts", "source-shape-drafts"}:
            key = f"{item['recordType']}:{item['queueId']}"
            item["render"] = render_results.get(key, {"status": "not-scheduled"})
            if item["render"].get("status") != "rendered":
                item["findings"].append(
                    "rendered notehead evidence is unavailable for this draft: "
                    + str(item["render"].get("reason", item["render"].get("status")))
                )
        elif item["recordType"] == "81b-comparison-record":
            key = f"81b:{Path(item['path']).stem}"
            item["candidateRender"] = render_results.get(key, {"status": "not-scheduled"})
            if item["candidateRender"].get("status") != "rendered":
                item["findings"].append(
                    "rendered candidate notehead evidence is unavailable: "
                    + str(item["candidateRender"].get("reason", item["candidateRender"].get("status")))
                )

    render_statuses = Counter(item.get("status") for item in render_results.values())
    report = {
        "kind": "agent-04-shape-evidence-audit",
        "version": "1",
        "policy": "Immutable source images and existing draft/comparison artifacts are read-only. Structural four-shape tags and successful PDF rendering do not establish direct source notehead agreement. safeToPromote remains false unless direct event-level source evidence is present; this audit records none.",
        "outputRoot": OUTPUT_ROOT.relative_to(ROOT).as_posix(),
        "authoritativeSummary": authoritative_summary,
        "reviewSummary": review_summary,
        "windlesham81b": windlesham,
        "renderSummary": {"scheduled": len(render_jobs), "statuses": dict(sorted(render_statuses.items())), "enabled": render_enabled},
        "summary": {
            "recordsAudited": len(records),
            "blocked": sum(item["disposition"] == "blocked" for item in records),
            "rejected": sum(item["disposition"] == "rejected" for item in records),
            "directSourceShapeEvidence": sum(item.get("directSourceShapeEvidence") is True for item in records),
            "safeToPromote": 0,
            "immutableSourceChanges": 0,
            "publicLedgerChanges": 0,
            "uiChanges": 0,
        },
        "records": records,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true", help="render every audited review/candidate MXL to work/agent-04-shapes/rendered")
    args = parser.parse_args()
    report = run_audit(args.render)
    output = OUTPUT_ROOT / "agent-04-shape-evidence-audit.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": output.relative_to(ROOT).as_posix(), **report["summary"], "renderSummary": report["renderSummary"]}, sort_keys=True))
    return 0 if report["summary"]["safeToPromote"] == 0 and report["summary"]["directSourceShapeEvidence"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
