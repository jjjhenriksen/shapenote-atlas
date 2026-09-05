#!/usr/bin/env python3
"""Build a deterministic manifest of retained-source fidelity dependencies.

The canonical public bundle is intentionally not self-sufficient: several
validators consume retained MusicXML, scans, candidate PDFs, OMR derivatives,
and image-preparation layers under ``work/``.  This report enumerates those
dependencies from the manifests the validators actually read.  It records
missing files as missing; it never downloads, regenerates, or turns an absent
retained witness into a passing condition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "work" / "luna-program-20260904" / "data" / "retained-source-dependency-manifest.json"
CLOUD_PLACEHOLDER_FLAG = 0x40000000

SOURCE_HEALTH_JSON_SOURCES = (
    "public/corpus.json",
    "public/shapenote-score-manifest.json",
    "public/source-image-manifest.json",
    "public/candidate-reconciliation.json",
    "public/shapenote-2025-score-audit.json",
    "work/source-images/manifest.json",
    "work/source-transcriptions/2025/recording-index.json",
    "work/source-transcriptions/2025/debut-recording-index.json",
    "work/source-transcriptions/2025/clean-source-candidates.json",
    "work/luna-program-20260904/source_only/retention-manifest.json",
    "work/luna-program-20260904/existing_books/christian-harmony-batch-01.json",
)

CANONICAL_MANIFESTS = (
    ("public/corpus.json", "canonical-generated-manifest", ("scripts/validate_data.py", "scripts/validate_playback.py", "scripts/validate_transposition.py"), ("data", "playback", "transposition")),
    ("public/shapenote-score-manifest.json", "dependency-manifest", ("scripts/build_data.py", "scripts/check_source_health.py"), ("data", "source-health")),
    ("public/shapenote-2025-score-audit.json", "dependency-manifest", ("scripts/build_data.py", "scripts/check_source_health.py"), ("data", "source-health")),
    ("public/source-image-manifest.json", "dependency-manifest", ("scripts/build_data.py", "scripts/check_source_health.py"), ("data", "source-health")),
    ("public/candidate-reconciliation.json", "dependency-manifest", ("scripts/validate_source_candidates.py", "scripts/check_source_health.py"), ("source-candidates", "source-health")),
    ("public/source-coverage.json", "canonical-generated-manifest", ("scripts/validate_data.py",), ("data",)),
    ("public/transcription-queue.json", "canonical-generated-manifest", ("scripts/validate_data.py",), ("data",)),
    ("public/human-review-queue.json", "canonical-generated-manifest", ("scripts/validate_data.py", "scripts/verify_all.py"), ("data", "queue-contradictions")),
    ("public/source-health.json", "canonical-generated-manifest", ("scripts/validate_source_health.py", "scripts/verify_all.py"), ("source-health",)),
    ("work/source-images/manifest.json", "dependency-manifest", ("scripts/check_source_health.py",), ("source-health",)),
    ("work/source-transcriptions/2025/recording-index.json", "dependency-manifest", ("scripts/check_source_health.py",), ("source-health",)),
    ("work/source-transcriptions/2025/debut-recording-index.json", "dependency-manifest", ("scripts/check_source_health.py",), ("source-health",)),
    ("work/source-transcriptions/2025/clean-source-candidates.json", "dependency-manifest", ("scripts/validate_source_candidates.py", "scripts/validate_data.py", "scripts/check_source_health.py"), ("source-candidates", "data", "source-health")),
    ("work/omr/clean-source-omr-run.json", "dependency-manifest", ("scripts/validate_source_candidates.py",), ("source-candidates",)),
    ("work/omr/review-shape-drafts/2025/manifest.json", "dependency-manifest", ("scripts/validate_shape_review_drafts.py", "scripts/validate_shape_evidence.py"), ("shape-review",)),
    ("work/omr/source-shape-review-drafts/2025/manifest.json", "dependency-manifest", ("scripts/validate_source_shape_review_drafts.py", "scripts/validate_shape_evidence.py"), ("source-shape-review",)),
    ("work/transcription-images/manifest.json", "dependency-manifest", ("scripts/validate_transcription_images.py",), ("transcription-images",)),
    ("work/omr/cleaned-v1-run.json", "dependency-manifest", ("scripts/validate_transcription_images.py",), ("transcription-images",)),
    ("work/omr/cleaned-normalized-v2-run.json", "dependency-manifest", ("scripts/validate_transcription_images.py",), ("transcription-images",)),
    ("work/luna-program-20260904/source_only/retention-manifest.json", "dependency-manifest", ("scripts/check_source_health.py",), ("source-health",)),
    ("work/luna-program-20260904/existing_books/christian-harmony-batch-01.json", "dependency-manifest", ("scripts/check_source_health.py",), ("source-health",)),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, issues: list[str]) -> dict[str, Any]:
    if not path.is_file():
        issues.append(f"missing manifest: {path.relative_to(ROOT).as_posix()}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        issues.append(f"unreadable manifest: {path.relative_to(ROOT).as_posix()}: {error}")
        return {}
    if not isinstance(value, dict):
        issues.append(f"unexpected manifest shape: {path.relative_to(ROOT).as_posix()}")
        return {}
    return value


def tracked_paths() -> set[str] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return {item.decode("utf-8") for item in result.stdout.split(b"\0") if item}


def path_text(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return ""
    candidate = Path(value)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            return ""
    try:
        resolved = (ROOT / candidate).resolve()
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return ""


def url_values(value: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        urls.append(value)
    elif isinstance(value, list):
        for child in value:
            urls.extend(url_values(child))
    elif isinstance(value, dict):
        for child in value.values():
            urls.extend(url_values(child))
    return urls


def acquisition_requirement(artifact_class: str, source_urls: list[str]) -> str:
    if artifact_class == "immutable-retained-source":
        return "Restore the exact retained source bytes and verify the recorded hash; do not synthesize, normalize, or infer source content."
    if artifact_class == "exact-score-witness":
        return "Restore the exact publisher MusicXML bytes from the recorded source URL and verify the recorded hash; do not regenerate from PDF or OMR."
    if artifact_class == "candidate-pdf-witness":
        return "Re-acquire the candidate PDF from its recorded candidate URL, then verify the recorded hash and retain its review-only status."
    if artifact_class == "derived-candidate-mxl":
        return "Restore the candidate PDF first, then rerun the bounded clean-source OMR step and verify the resulting MXL hash; never promote it as exact evidence."
    if artifact_class == "derived-normalized-image":
        return "Restore the original source image, rerun the recorded normalization pipeline, and verify the derived image hash; it is not source engraving evidence."
    if artifact_class == "derived-suppressed-image":
        return "Restore the original source image, rerun the recorded watermark-suppression pipeline, and verify the derived image hash; it is not source engraving evidence."
    if artifact_class == "derived-review-draft":
        return "Restore the retained source and candidate/OMR witnesses, rebuild the review draft, and verify its hash; keep it fail-closed and review-only."
    if artifact_class == "derived-public-copy":
        return "Restore or rebuild the linked local review draft, copy it deterministically, and verify local/public hash equality; do not promote it."
    if artifact_class == "derived-transcription-artifact":
        return "Restore the source image and rerun the bounded transcription/OMR preparation step; do not use an absent artifact as proof of fidelity."
    if artifact_class == "source-health-local-evidence":
        return "Restore the exact local evidence named by the source-health record, or rebuild only when its recorded kind is explicitly derived; recheck the recorded hash before offline health validation."
    if artifact_class == "dependency-manifest":
        return "Preserve this manifest or rebuild it from its named lane inputs before running the consuming validator; missing manifests remain blocking."
    if artifact_class == "canonical-generated-manifest":
        return "Restore the canonical generated artifact from the exact commit or rebuild it with the repository builder after retained inputs are available."
    return "Restore the exact recorded bytes or rebuild from retained inputs, then verify the resulting hash before treating the validator as reproducible."


class DependencyCollector:
    def __init__(self, tracked: set[str] | None) -> None:
        self.tracked = tracked
        self.records: dict[str, dict[str, Any]] = {}

    def add(
        self,
        value: Any,
        *,
        artifact_class: str,
        consumers: tuple[str, ...] = (),
        gates: tuple[str, ...] = (),
        source_urls: list[str] | tuple[str, ...] = (),
        expected_sha256: Any = "",
        expected_bytes: Any = None,
        immutable: bool | None = None,
        derived: bool | None = None,
        reference: str = "",
        requirement: str = "",
    ) -> None:
        path = path_text(value)
        if not path:
            return
        item = self.records.setdefault(
            path,
            {
                "path": path,
                "artifactClasses": set(),
                "consumers": set(),
                "gates": set(),
                "sourceUrls": set(),
                "references": set(),
                "expectedSha256": set(),
                "expectedBytes": set(),
                "immutableValues": set(),
                "derivedValues": set(),
            },
        )
        item["artifactClasses"].add(artifact_class)
        item["consumers"].update(consumers)
        item["gates"].update(gates)
        item["sourceUrls"].update(url for url in source_urls if isinstance(url, str) and url.startswith(("http://", "https://")))
        if reference:
            item["references"].add(reference)
        if expected_sha256:
            item["expectedSha256"].add(str(expected_sha256))
        if expected_bytes not in (None, ""):
            try:
                item["expectedBytes"].add(int(expected_bytes))
            except (TypeError, ValueError):
                item["expectedBytes"].add(str(expected_bytes))
        if immutable is not None:
            item["immutableValues"].add(bool(immutable))
        if derived is not None:
            item["derivedValues"].add(bool(derived))
        if requirement:
            item.setdefault("requirements", set()).add(requirement)

    def finish(self) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for path, item in sorted(self.records.items()):
            absolute = ROOT / path
            status = "missing"
            actual_bytes: int | None = None
            actual_hash = ""
            error = ""
            conflicting_expectations = len(item["expectedSha256"]) > 1 or len(item["expectedBytes"]) > 1
            try:
                stat_result = absolute.stat()
                if getattr(stat_result, "st_flags", 0) & CLOUD_PLACEHOLDER_FLAG or (stat_result.st_size > 0 and stat_result.st_blocks == 0):
                    status = "unavailable-cloud-placeholder"
                elif not absolute.is_file():
                    status = "missing"
                else:
                    actual_bytes = stat_result.st_size
                    actual_hash = sha256(absolute)
                    expected_hashes = item["expectedSha256"]
                    expected_sizes = item["expectedBytes"]
                    if conflicting_expectations:
                        status = "conflicting-expectations"
                    elif expected_hashes and actual_hash not in expected_hashes:
                        status = "hash-mismatch"
                    elif expected_sizes and actual_bytes not in expected_sizes:
                        status = "byte-count-mismatch"
                    else:
                        status = "present"
            except FileNotFoundError:
                status = "missing"
            except (OSError, ValueError) as exc:
                status = "unavailable"
                error = str(exc)
            if conflicting_expectations:
                status = "conflicting-expectations"

            classes = sorted(item["artifactClasses"])
            class_for_policy = next(
                (
                    candidate
                    for candidate in (
                        "exact-score-witness",
                        "immutable-retained-source",
                        "candidate-pdf-witness",
                        "derived-candidate-mxl",
                        "derived-normalized-image",
                        "derived-suppressed-image",
                        "derived-review-draft",
                        "derived-public-copy",
                        "derived-transcription-artifact",
                        "dependency-manifest",
                        "canonical-generated-manifest",
                    )
                    if candidate in item["artifactClasses"]
                ),
                classes[0] if classes else "unknown",
            )
            immutable_values = item["immutableValues"]
            derived_values = item["derivedValues"]
            record: dict[str, Any] = {
                "path": path,
                "artifactClasses": classes,
                "status": status,
                "bytes": actual_bytes,
                "sha256": actual_hash,
                "expectedSha256": sorted(item["expectedSha256"]),
                "expectedBytes": sorted(item["expectedBytes"], key=str),
                "sourceUrls": sorted(item["sourceUrls"]),
                "consumers": sorted(item["consumers"]),
                "gates": sorted(item["gates"]),
                "references": sorted(item["references"]),
                "tracked": None if self.tracked is None else path in self.tracked,
                "immutable": True if immutable_values == {True} else False if immutable_values == {False} else None,
                "derived": True if derived_values == {True} else False if derived_values == {False} else None,
                "acquisitionRequirement": acquisition_requirement(class_for_policy, sorted(item["sourceUrls"])),
            }
            if len(immutable_values) > 1 or len(derived_values) > 1:
                record["classificationNote"] = "This path is consumed in more than one role; preserve the strictest retained-source interpretation."
            if error:
                record["availabilityError"] = error
            output.append(record)
        return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="report path (default: work/luna-program-20260904/data/retained-source-dependency-manifest.json)")
    args = parser.parse_args()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    issues: list[str] = []
    tracked = tracked_paths()
    collector = DependencyCollector(tracked)
    loaded: dict[str, dict[str, Any]] = {}

    for relative, artifact_class, consumers, gates in CANONICAL_MANIFESTS:
        path = ROOT / relative
        loaded[relative] = load_json(path, issues)
        collector.add(relative, artifact_class=artifact_class, consumers=consumers, gates=gates, reference="canonical-validator-input", immutable=False, derived=artifact_class != "dependency-manifest")

    # Every raw score path in either exact-score manifest is an independent
    # retained witness.  The 2025 audit is separate because its catalog is not
    # identical to the long-lived 1991 score manifest.
    score_manifest = loaded.get("public/shapenote-score-manifest.json", {})
    for record_key, entry in sorted((score_manifest.get("entries") or {}).items()):
        if not isinstance(entry, dict):
            continue
        collector.add(
            entry.get("rawPath"),
            artifact_class="exact-score-witness",
            consumers=("scripts/build_data.py", "scripts/validate_data.py", "scripts/validate_playback.py", "scripts/validate_transposition.py", "scripts/check_source_health.py"),
            gates=("data", "playback", "transposition", "source-health"),
            source_urls=url_values(entry.get("sourceUrl")),
            expected_sha256=entry.get("sourceSha256"),
            expected_bytes=entry.get("sourceBytes"),
            immutable=True,
            derived=False,
            reference=f"public/shapenote-score-manifest.json:{record_key}",
        )

    audit = loaded.get("public/shapenote-2025-score-audit.json", {})
    for record in audit.get("records", []):
        if not isinstance(record, dict):
            continue
        collector.add(
            record.get("rawPath"),
            artifact_class="exact-score-witness",
            consumers=("scripts/build_data.py", "scripts/validate_data.py", "scripts/validate_playback.py", "scripts/validate_transposition.py", "scripts/check_source_health.py"),
            gates=("data", "playback", "transposition", "source-health"),
            source_urls=url_values(record.get("sourceUrl")) + url_values((record.get("recordSourceMetadata") or {}).get("sourceUrls", [])),
            expected_sha256=record.get("sourceSha256"),
            expected_bytes=record.get("sourceBytes"),
            immutable=True,
            derived=False,
            reference=f"public/shapenote-2025-score-audit.json:{record.get('queueId', record.get('songNo', 'unknown'))}",
        )

    # Candidate PDFs are retained witnesses for alternate-source comparison;
    # candidate MXLs are always derived OMR and remain non-promotable.
    candidate_manifest = loaded.get("work/source-transcriptions/2025/clean-source-candidates.json", {})
    candidates_by_key: dict[str, dict[str, Any]] = {}
    for record in candidate_manifest.get("records", []):
        if not isinstance(record, dict):
            continue
        key = str(record.get("candidateKey", record.get("songNo", "unknown")))
        candidates_by_key[key] = record
        urls = url_values(record.get("pdfUrl")) + url_values(record.get("candidatePageUrl"))
        collector.add(
            record.get("localPdf"),
            artifact_class="candidate-pdf-witness",
            consumers=("scripts/validate_source_candidates.py", "scripts/validate_data.py", "scripts/check_source_health.py"),
            gates=("source-candidates", "data", "source-health"),
            source_urls=urls,
            expected_sha256=record.get("sha256"),
            immutable=True,
            derived=False,
            reference=f"work/source-transcriptions/2025/clean-source-candidates.json:{key}",
        )

    omr_run = loaded.get("work/omr/clean-source-omr-run.json", {})
    for record in omr_run.get("records", []):
        if not isinstance(record, dict):
            continue
        key = str(record.get("candidateKey", record.get("songNo", "unknown")))
        urls = url_values(record.get("candidatePdfUrl")) + url_values(record.get("candidatePageUrl"))
        candidate_pdf = record.get("candidatePdf") or record.get("omrInputPdf")
        candidate = candidates_by_key.get(key, {})
        collector.add(
            candidate_pdf,
            artifact_class="candidate-pdf-witness",
            consumers=("scripts/validate_source_candidates.py", "scripts/validate_data.py"),
            gates=("source-candidates", "data"),
            source_urls=urls,
            expected_sha256=record.get("candidatePdfSha256") or record.get("omrInputSha256") or candidate.get("sha256"),
            immutable=True,
            derived=False,
            reference=f"work/omr/clean-source-omr-run.json:{key}:pdf",
        )
        for artifact in record.get("draftArtifacts", []):
            collector.add(
                artifact,
                artifact_class="derived-candidate-mxl",
                consumers=("scripts/validate_source_candidates.py", "scripts/validate_shape_review_drafts.py", "scripts/validate_source_shape_review_drafts.py"),
                gates=("source-candidates", "shape-review", "source-shape-review"),
                source_urls=urls,
                derived=True,
                immutable=False,
                reference=f"work/omr/clean-source-omr-run.json:{key}:draft",
            )

    reconciliation = loaded.get("public/candidate-reconciliation.json", {})
    for record in reconciliation.get("records", []):
        if not isinstance(record, dict):
            continue
        key = str(record.get("candidateKey", record.get("songNo", "unknown")))
        source = record.get("sourceAuthority") if isinstance(record.get("sourceAuthority"), dict) else {}
        urls = url_values(record.get("candidatePdfUrl")) + url_values(record.get("candidatePageUrl")) + url_values(source)
        candidate_omr = record.get("candidateOmr") if isinstance(record.get("candidateOmr"), dict) else {}
        collector.add(
            candidate_omr.get("path"),
            artifact_class="derived-candidate-mxl",
            consumers=("scripts/validate_source_candidates.py", "scripts/validate_shape_review_drafts.py", "scripts/validate_source_shape_review_drafts.py", "scripts/validate_shape_evidence.py"),
            gates=("source-candidates", "shape-review", "source-shape-review"),
            source_urls=urls,
            expected_sha256=candidate_omr.get("sha256"),
            derived=True,
            immutable=False,
            reference=f"public/candidate-reconciliation.json:{key}:candidateOmr",
        )

    def add_shape_manifest(relative: str, source_shape: bool) -> None:
        payload = loaded.get(relative, {})
        for record in payload.get("records", []):
            if not isinstance(record, dict):
                continue
            key = str(record.get("queueId", record.get("songNo", "unknown")))
            source = record.get("sourceAuthority") if isinstance(record.get("sourceAuthority"), dict) else {}
            source_urls = url_values(source)
            source_image = source.get("sourceImagePath") or source.get("path")
            collector.add(
                source_image,
                artifact_class="immutable-retained-source",
                consumers=("scripts/validate_shape_review_drafts.py", "scripts/validate_source_shape_review_drafts.py", "scripts/validate_shape_evidence.py", "scripts/check_source_health.py"),
                gates=("shape-review", "source-shape-review", "source-health"),
                source_urls=source_urls,
                expected_sha256=source.get("sourceImageSha256") or source.get("sha256"),
                immutable=True,
                derived=False,
                reference=f"{relative}:{key}:source",
            )
            if source_shape:
                scan = record.get("sourceScanOmr") if isinstance(record.get("sourceScanOmr"), dict) else {}
                collector.add(
                    scan.get("path"),
                    artifact_class="derived-candidate-mxl",
                    consumers=("scripts/validate_source_shape_review_drafts.py", "scripts/validate_shape_evidence.py"),
                    gates=("source-shape-review",),
                    source_urls=source_urls,
                    expected_sha256=scan.get("sha256"),
                    derived=True,
                    immutable=False,
                    reference=f"{relative}:{key}:sourceScanOmr",
                )
                collector.add(
                    scan.get("selectedWorkingPath"),
                    artifact_class="derived-normalized-image",
                    consumers=("scripts/validate_source_shape_review_drafts.py", "scripts/validate_transcription_images.py"),
                    gates=("source-shape-review", "transcription-images"),
                    source_urls=source_urls,
                    derived=True,
                    immutable=False,
                    reference=f"{relative}:{key}:selectedWorkingPath",
                )
            candidate = record.get("candidateWitness") if isinstance(record.get("candidateWitness"), dict) else {}
            collector.add(
                candidate.get("path"),
                artifact_class="derived-candidate-mxl",
                consumers=("scripts/validate_shape_review_drafts.py", "scripts/validate_shape_evidence.py"),
                gates=("shape-review",),
                source_urls=source_urls,
                expected_sha256=candidate.get("sha256"),
                derived=True,
                immutable=False,
                reference=f"{relative}:{key}:candidateWitness",
            )
            draft = record.get("reviewDraft") if isinstance(record.get("reviewDraft"), dict) else {}
            collector.add(
                draft.get("path"),
                artifact_class="derived-review-draft",
                consumers=("scripts/validate_shape_review_drafts.py", "scripts/validate_source_shape_review_drafts.py", "scripts/validate_shape_evidence.py"),
                gates=("shape-review", "source-shape-review"),
                source_urls=source_urls,
                expected_sha256=draft.get("sha256"),
                derived=True,
                immutable=False,
                reference=f"{relative}:{key}:reviewDraft",
            )
            public_path = draft.get("publicPath", "")
            if public_path:
                collector.add(
                    f"public/{public_path}",
                    artifact_class="derived-public-copy",
                    consumers=("scripts/validate_shape_review_drafts.py", "scripts/validate_source_shape_review_drafts.py"),
                    gates=("shape-review", "source-shape-review"),
                    source_urls=source_urls,
                    expected_sha256=draft.get("publicSha256"),
                    derived=True,
                    immutable=False,
                    reference=f"{relative}:{key}:reviewDraft.publicPath",
                )

    add_shape_manifest("work/omr/review-shape-drafts/2025/manifest.json", False)
    add_shape_manifest("work/omr/source-shape-review-drafts/2025/manifest.json", True)

    image_manifest = loaded.get("work/transcription-images/manifest.json", {})
    for record in image_manifest.get("records", []):
        if not isinstance(record, dict):
            continue
        source_urls = url_values(record.get("sourceUrl")) + url_values(record.get("sourceImageUrl"))
        key = str(record.get("originalPath", "unknown"))
        collector.add(record.get("originalPath"), artifact_class="immutable-retained-source", consumers=("scripts/validate_transcription_images.py", "scripts/check_source_health.py"), gates=("transcription-images", "source-health"), source_urls=source_urls, expected_sha256=record.get("originalSha256"), expected_bytes=record.get("originalBytes"), immutable=True, derived=False, reference=f"work/transcription-images/manifest.json:{key}:original")
        collector.add(record.get("workingPath"), artifact_class="derived-normalized-image", consumers=("scripts/validate_transcription_images.py",), gates=("transcription-images",), source_urls=source_urls, expected_sha256=record.get("workingSha256"), immutable=False, derived=True, reference=f"work/transcription-images/manifest.json:{key}:working")
        collector.add(record.get("suppressedWorkingPath"), artifact_class="derived-suppressed-image", consumers=("scripts/validate_transcription_images.py",), gates=("transcription-images",), source_urls=source_urls, expected_sha256=record.get("suppressedWorkingSha256"), immutable=False, derived=True, reference=f"work/transcription-images/manifest.json:{key}:suppressed")
    for record in image_manifest.get("explicitWorkingImages", []):
        if isinstance(record, dict):
            collector.add(record.get("workingPath"), artifact_class="derived-normalized-image", consumers=("scripts/validate_transcription_images.py",), gates=("transcription-images",), expected_sha256=record.get("workingSha256"), derived=True, immutable=False, reference=f"work/transcription-images/manifest.json:explicit:{record.get('workingPath', 'unknown')}")
    for record in image_manifest.get("aiEditedSamples", []):
        if isinstance(record, dict):
            collector.add(record.get("path"), artifact_class="derived-transcription-artifact", consumers=("scripts/validate_transcription_images.py",), gates=("transcription-images",), expected_sha256=record.get("sha256"), derived=True, immutable=False, reference=f"work/transcription-images/manifest.json:ai-sample:{record.get('sampleKey', 'unknown')}")
    for relative in ("work/omr/cleaned-v1-run.json", "work/omr/cleaned-normalized-v2-run.json"):
        payload = loaded.get(relative, {})
        for record in payload.get("records", []):
            if not isinstance(record, dict):
                continue
            key = str(record.get("originalPath", "unknown"))
            for artifact in record.get("draftArtifacts", []):
                collector.add(artifact, artifact_class="derived-transcription-artifact", consumers=("scripts/validate_transcription_images.py",), gates=("transcription-images",), derived=True, immutable=False, reference=f"{relative}:{key}:draftArtifact")
            collector.add(record.get("selectedWorkingPath"), artifact_class="derived-normalized-image", consumers=("scripts/validate_transcription_images.py",), gates=("transcription-images",), derived=True, immutable=False, reference=f"{relative}:{key}:selectedWorkingPath")
            collector.add(record.get("fallbackDraft"), artifact_class="derived-transcription-artifact", consumers=("scripts/validate_transcription_images.py",), gates=("transcription-images",), expected_sha256=record.get("fallbackDraftSha256"), derived=True, immutable=False, reference=f"{relative}:{key}:fallbackDraft")

    # Source-health is itself a validator input, and its localEvidence list is
    # the authoritative list of retained paths that must be available during
    # an offline health check.  Bind each local body to the URL whose record
    # declared it; never bind a page URL to a downloaded image by inference.
    source_health = loaded.get("public/source-health.json", {})
    for record in source_health.get("records", []):
        if not isinstance(record, dict):
            continue
        source_url = record.get("url", "")
        for evidence in record.get("localEvidence", []):
            if not isinstance(evidence, dict):
                continue
            collector.add(
                evidence.get("path"),
                artifact_class="source-health-local-evidence",
                consumers=("scripts/validate_source_health.py", "scripts/check_source_health.py"),
                gates=("source-health",),
                source_urls=[source_url] if isinstance(source_url, str) else [],
                expected_sha256=evidence.get("expectedSha256"),
                expected_bytes=evidence.get("expectedBytes"),
                immutable=True if evidence.get("immutable") is True else None,
                derived=False if evidence.get("immutable") is True else None,
                reference=f"public/source-health.json:{source_url}",
            )

    records = collector.finish()
    counts: dict[str, int] = {}
    for record in records:
        for artifact_class in record["artifactClasses"]:
            counts[artifact_class] = counts.get(artifact_class, 0) + 1
    status_counts: dict[str, int] = {}
    for record in records:
        status_counts[record["status"]] = status_counts.get(record["status"], 0) + 1

    payload = {
        "schemaVersion": 1,
        "policy": {
            "purpose": "Reproduce the retained-source inputs required by the fidelity validators from a fresh checkout.",
            "failClosed": True,
            "missingOrUnavailableIsNotPassing": True,
            "network": "No downloads or network requests are performed by this builder.",
            "sourceFaithfulness": "Do not infer lyrics, notation, keys, modes, repeats, endings, or shapes from absent or alternate witnesses.",
        },
        "builder": "scripts/build_retained_source_dependency_manifest.py",
        "validatorInputs": [relative for relative, _, _, _ in CANONICAL_MANIFESTS],
        "summary": {
            "totalDependencies": len(records),
            "statusCounts": dict(sorted(status_counts.items())),
            "artifactClassCounts": dict(sorted(counts.items())),
            "trackedDependencies": sum(record["tracked"] is True for record in records),
            "untrackedDependencies": sum(record["tracked"] is False for record in records),
            "trackingStateUnavailable": sum(record["tracked"] is None for record in records),
            "missingOrUnavailable": sum(record["status"] != "present" for record in records),
            "manifestIssues": sorted(set(issues)),
        },
        "records": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), **payload["summary"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
