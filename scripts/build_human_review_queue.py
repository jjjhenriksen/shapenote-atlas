#!/usr/bin/env python3
"""Build a source-audit queue for local OMR transcription drafts.

The queue is deliberately separate from the playable corpus. A draft is useful
work product, but it is not source-verified notation and must not be promoted
automatically. Every record with a completed autonomous comparison receives an
explicit blocked, rejected, or verified disposition instead of a vague
human-review status.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from review_dispositions import (
    aggregate_comparison_disposition,
    comparison_disposition,
    transcription_disposition,
)


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public" / "corpus.json"
DRAFT_INDEX = ROOT / "work" / "omr" / "draft-index.json"
IMAGE_MANIFEST = ROOT / "work" / "transcription-images" / "manifest.json"
CLEANED_OMR_RUNS = (
    ROOT / "work" / "omr" / "cleaned-v1-run.json",  # retain prior review runs
    ROOT / "work" / "omr" / "cleaned-normalized-v2-run.json",  # current normalized-v2 runs win
)
CLEAN_SOURCE_CANDIDATES = ROOT / "work" / "source-transcriptions" / "2025" / "clean-source-candidates.json"
CLEAN_SOURCE_OMR_RUN = ROOT / "work" / "omr" / "clean-source-omr-run.json"
RECONCILIATION_LEDGER = ROOT / "public" / "candidate-reconciliation.json"
RECONCILIATION_ROOT = ROOT / "work" / "source-transcriptions" / "2025"
SOURCE_METADATA_OBSERVATIONS = ROOT / "public" / "source-metadata-observations.json"
SOURCE_COMPARISON_LEDGER = ROOT / "public" / "source-comparison-ledger.json"
SHAPE_REVIEW_MANIFEST = ROOT / "work" / "omr" / "review-shape-drafts" / "2025" / "manifest.json"
SOURCE_SHAPE_REVIEW_MANIFEST = ROOT / "work" / "omr" / "source-shape-review-drafts" / "2025" / "manifest.json"
OUTPUT_JSON = ROOT / "public" / "human-review-queue.json"
OUTPUT_MD = ROOT / "work" / "omr" / "human-review-queue.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def current_song_by_number(corpus: dict[str, Any]) -> dict[str, dict[str, Any]]:
    songs: dict[str, dict[str, Any]] = {}
    for song in corpus.get("songs", []):
        if "sh2025" in song.get("books", []):
            songs[song.get("songNo", "").lower()] = song
    return songs


def draft_song_number(record: str) -> str:
    match = re.match(r"(\d+[a-z]?)", record.lower())
    return match.group(1) if match else record.lower()


def source_url(song: dict[str, Any], coverage: dict[str, Any]) -> str:
    metadata = song.get("metadataByBook", {}).get("sh2025", {})
    return metadata.get("sourceUrl") or (coverage.get("sourceUrls") or [""])[0]


def source_image_url(song: dict[str, Any], coverage: dict[str, Any]) -> str:
    metadata = song.get("metadataByBook", {}).get("sh2025", {})
    return metadata.get("sourceImageUrl") or coverage.get("sourceImageUrl", "")


def cleaned_image_context(song_number: str, manifest: dict[str, Any], cleaned_run: dict[str, Any]) -> dict[str, Any]:
    """Join an edition record to its immutable-source working layers."""
    target = song_number.lower()
    matching_images = [
        item
        for item in manifest.get("records", [])
        if item.get("sourceKind") == "official-page-scan"
        and (
            Path(item.get("originalPath", "")).stem.lower() == target
            or Path(item.get("originalPath", "")).stem.lower().startswith(f"{target}-")
        )
    ]
    # Retained originals (254–259, 414t, and 484t) coexist with older hashed
    # downloads in the transcription manifest. Prefer the source path that
    # has a matching cleaned-run row so the review queue does not report a
    # completed canonical draft as "not-run" merely because a stale duplicate
    # sorted first.
    image = next((item for item in matching_images if item.get("originalPath") in cleaned_run), None)
    image = image or (matching_images[0] if matching_images else None)
    if image is None:
        return {}
    run = cleaned_run.get(image.get("originalPath", ""), {})
    return {
        "normalizedWorkingImage": image.get("workingPath", ""),
        "normalizedWorkingSha256": image.get("workingSha256", ""),
        "suppressedWorkingImage": image.get("suppressedWorkingPath", ""),
        "suppressedWorkingSha256": image.get("suppressedWorkingSha256", ""),
        "cleanedOmrStatus": run.get("status", "not-run"),
        "cleanedOmrArtifacts": run.get("draftArtifacts", []),
        "cleanedOmrLog": run.get("log", ""),
        "watermarkAssessment": image.get("watermarkAssessment", {}),
    }


def clean_source_context(
    song_number: str,
    candidates: dict[str, Any],
    omr_run: dict[str, Any],
    reconciliation: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return public clean-source candidates without treating them as scores."""
    target = song_number.lower()
    omr_by_candidate = {
        str(item.get("candidateKey", "")): item
        for item in omr_run.get("records", [])
        if item.get("candidateKey")
    }
    result = []
    for item in candidates.get("records", []):
        if str(item.get("songNo", "")).lower() != target:
            continue
        omr = omr_by_candidate.get(str(item.get("candidateKey", "")), {})
        ledger = reconciliation.get(str(item.get("candidateKey", "")), {})
        result.append(
            {
                "candidateTitle": item.get("candidateTitle", ""),
                "candidateKey": item.get("candidateKey", ""),
                "candidatePageUrl": item.get("candidatePageUrl", ""),
                "pdfUrl": item.get("pdfUrl", ""),
                "localPdf": item.get("localPdf", ""),
                "omrInputPdf": item.get("omrInputPdf", ""),
                "compositePdfPage": item.get("compositePdfPage"),
                "sha256": item.get("sha256", ""),
                "matchKind": item.get("matchKind", ""),
                "status": item.get("status", "candidate-source-needs-edition-comparison"),
                "editionVerified": item.get("editionVerified", False),
                "structuredScoreAdmissible": item.get("structuredScoreAdmissible", False),
                "omrStatus": omr.get("status", "not-run"),
                "omrArtifacts": omr.get("draftArtifacts", []),
                "omrLog": omr.get("log", ""),
                "reconciliationStatus": ledger.get("status", "not-recorded"),
                "structuralAgreement": ledger.get("structuralAgreement", False),
                "agreementFields": ledger.get("agreementFields", []),
                "discrepancies": ledger.get("discrepancies", []),
                "reconciliationSafeToPromote": ledger.get("safeToPromote", False),
            }
        )
    return result


def reconciliation_context(song_number: str) -> dict[str, Any]:
    if song_number.lower() != "256":
        return {}
    path = RECONCILIATION_ROOT / "256-northampton-reconciliation.json"
    if not path.exists():
        return {}
    payload = load_json(path)
    return {
        "reconciliationArtifact": str(path.relative_to(ROOT)),
        "reconciliationStatus": payload.get("status", ""),
        "reconciliationSafeToPromote": payload.get("safeToPromote", False),
        "reconciliationCandidateAgreement": payload.get("candidateAgreement", False),
        "reconciliationCandidateMeasureCountRanges": payload.get("candidateMeasureCountRanges", {}),
        "reconciliationBlockingFindings": payload.get("blockingFindings", []),
    }


def autonomous_disposition(comparisons: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    """Choose the strongest explicit canonical outcome for a record."""
    if not comparisons:
        return "unavailable", {}
    disposition = aggregate_comparison_disposition(comparisons)
    comparison = next(
        item for item in comparisons if comparison_disposition(item)["state"] == disposition["state"]
    )
    return disposition["state"], comparison


def review_item(
    draft: dict[str, Any],
    song: dict[str, Any] | None,
    image_manifest: dict[str, Any],
    cleaned_run: dict[str, Any],
    clean_candidates: dict[str, Any],
    clean_source_omr: dict[str, Any],
    reconciliation: dict[str, Any],
    source_metadata: dict[str, Any],
    source_comparisons: dict[str, list[dict[str, Any]]],
    shape_reviews: dict[str, Any],
    source_shape_reviews: dict[str, Any],
) -> dict[str, Any]:
    song = song or {}
    coverage = song.get("sourceCoverageByBook", {}).get("sh2025", {})
    record = draft["record"]
    song_number = draft_song_number(record)
    local_artifacts = coverage.get("localArtifacts", {})
    artifact = draft.get("artifact", "")
    artifact_path = ROOT / artifact
    pdf_candidates = [
        artifact_path.with_name(f"{artifact_path.stem}-draft.pdf"),
        artifact_path.parent / f"{record}-draft.pdf",
    ]
    pdf_path = next((candidate for candidate in pdf_candidates if candidate.exists()), pdf_candidates[0])
    local_source_image = local_artifacts.get("sourceImage", "")
    if not local_source_image:
        candidate_source_image = ROOT / "work" / "omr" / record / "source.jpg"
        if candidate_source_image.exists():
            local_source_image = str(candidate_source_image.relative_to(ROOT))
    parts = draft.get("parts", [])
    empty_measures = sum(int(part.get("emptyMeasures", 0)) for part in parts)
    total_notes = sum(int(part.get("notes", 0)) for part in parts)
    edition_status = coverage.get("editionStatus", "")
    metadata_key = song.get("metadataByBook", {}).get("sh2025", {}).get("keySignature", "")
    detected_key = draft.get("keyFifths", "")
    key_evidence = song.get("metadataByBook", {}).get("sh2025", {}).get("keyEvidence", {})
    if not metadata_key and detected_key:
        key_evidence = {"status": "omr-detected", "source": "OMR-detected MusicXML key signature"}
    elif not key_evidence:
        key_evidence = {"status": "unknown", "source": "not detected"}
    image_context = cleaned_image_context(song_number, image_manifest, cleaned_run)
    clean_source_candidates = clean_source_context(song_number, clean_candidates, clean_source_omr, reconciliation)
    reconciliation = reconciliation_context(song_number)
    source_metadata_observation = source_metadata.get(f"sh2025/{song_number}", {})
    source_comparison_records = source_comparisons.get(f"sh2025/{song_number}", [])
    source_comparison = source_comparison_records[0] if source_comparison_records else None
    disposition, disposition_comparison = autonomous_disposition(source_comparison_records)
    canonical_disposition = comparison_disposition(disposition_comparison)
    capability_fields = {}
    if canonical_disposition.get("notationStatus") == "source-aligned-playable":
        capability_fields = {
            "notationStatus": canonical_disposition["notationStatus"],
            "playbackStatus": canonical_disposition["playbackStatus"],
            "transpositionStatus": canonical_disposition["transpositionStatus"],
            "semanticLimitations": canonical_disposition["semanticLimitations"],
        }
    presentation_status = (
        "review-only"
        if canonical_disposition.get("notationStatus") == "source-aligned-playable"
        else disposition
    )
    shape_review = shape_reviews.get(f"sh2025/{song_number}")
    source_shape_review = source_shape_reviews.get(f"sh2025/{song_number}")
    return {
        "queueId": f"sh2025/{song_number}",
        "canonicalRecordId": f"sh2025/{song_number}",
        "edition": "Sacred Harp 2025",
        "songNo": song_number,
        "title": song.get("titlesByBook", {}).get("sh2025", song.get("title", song_number)),
        "status": presentation_status,
        "autonomousDisposition": disposition_comparison.get("autonomousDecision") or disposition,
        "disposition": canonical_disposition,
        **capability_fields,
        "humanReviewRequired": canonical_disposition["humanReviewRequired"],
        "reviewAvailable": canonical_disposition["reviewAvailable"],
        "reviewPurpose": "optional-source-evidence-review",
        "dispositionEvidence": disposition_comparison.get("auditFile", ""),
        "safeToPromote": False,
        "priority": 1 if edition_status == "added-in-2025" else 2,
        "editionStatus": edition_status,
        "editionEvidenceUrl": coverage.get("editionEvidenceUrl", ""),
        "editionEvidenceLabel": coverage.get("editionEvidenceLabel", ""),
        "sourcePageUrl": source_url(song, coverage),
        "sourceImageUrl": source_image_url(song, coverage),
        "localSourceImage": local_source_image,
        "localSourcePage": local_artifacts.get("pageHtml", ""),
        "sourceMetadataObservation": source_metadata_observation,
        "sourceComparison": source_comparison,
        **image_context,
        **reconciliation,
        "cleanSourceCandidates": clean_source_candidates,
        "sourceComparisons": source_comparison_records,
        "shapeReviewDraft": shape_review,
        "sourceShapeReviewDraft": source_shape_review,
        "keySignature": metadata_key,
        "keyEvidence": key_evidence,
        "timeSignature": song.get("metadataByBook", {}).get("sh2025", {}).get("timeSignature", ""),
        "meter": song.get("metadataByBook", {}).get("sh2025", {}).get("meter", ""),
        "draftArtifact": artifact,
        "draftPdf": str(pdf_path.relative_to(ROOT)) if pdf_path.exists() else "",
        "draftSha256": draft.get("sha256", ""),
        "draftSummary": {
            "parts": len(parts),
            "measuresByPart": {part.get("id", ""): part.get("measures", 0) for part in parts},
            "notes": total_notes,
            "emptyMeasures": empty_measures,
            "keyFifthsDetected": draft.get("keyFifths", ""),
            "keyEvidence": key_evidence,
            "timeSignatureDetected": draft.get("timeSignature", ""),
        },
        "reviewChecklist": [
            "Confirm the page number, title, composer, and source edition against the source page.",
            "Compare every measure in treble, alto, tenor, and bass against the source image.",
            "Verify key signature, major/minor mode, meter, rhythm values, rests, ties, repeats, and endings.",
            "Restore and verify the four-shape noteheads; this standard MusicXML draft does not preserve them.",
            "Check lyric underlay only if it is intended to be carried into the structured score.",
            "Do not promote unless the source comparison and all validators explicitly authorize it.",
        ],
        "warnings": list(dict.fromkeys(
            draft.get("warnings", [])
            + [
            "The source raster has a diagonal DO NOT COPY watermark crossing notation; watermark-overlap regions remain uncertain.",
            "The normalized working image is a cleanup aid derived from the original and must be compared against the untouched source.",
                *("A public clean-source PDF candidate is available, but it is not the 2025 engraving until note-for-note comparison is complete." for _ in [0] if clean_source_candidates),
                "This draft is available for playback and transposition as review work product, but it is not source-verified and must not be presented as the engraving.",
            ]
        )),
        "blockedReason": (
            disposition_comparison.get("blockingReason")
            or "; ".join(disposition_comparison.get("blockedReasons", []))
            or coverage.get("blockedReason", "")
        ),
        "acquisitionNeeded": coverage.get("acquisitionNeeded", ""),
    }


def backlog_item(song: dict[str, Any]) -> dict[str, Any]:
    coverage = song.get("sourceCoverageByBook", {}).get("sh2025", {})
    metadata = song.get("metadataByBook", {}).get("sh2025", {})
    queue_id = f"sh2025/{song.get('songNo', '')}"
    disposition = transcription_disposition(coverage.get("status", ""), coverage.get("sourceUrls", []))
    return {
        "queueId": queue_id,
        "canonicalRecordId": queue_id,
        "edition": "Sacred Harp 2025",
        "songNo": song.get("songNo", ""),
        "title": song.get("titlesByBook", {}).get("sh2025", song.get("title", "")),
        "status": coverage.get("status", ""),
        "disposition": disposition,
        "humanReviewRequired": False,
        "reviewAvailable": disposition["reviewAvailable"],
        "safeToPromote": False,
        "editionStatus": coverage.get("editionStatus", metadata.get("editionStatus", "")),
        "editionEvidenceUrl": coverage.get("editionEvidenceUrl", metadata.get("editionEvidenceUrl", "")),
        "nextAction": coverage.get("nextAction", ""),
        "sourcePageUrl": metadata.get("sourceUrl") or (coverage.get("sourceUrls") or [""])[0],
        "sourceImageUrl": metadata.get("sourceImageUrl", ""),
        "hasReferenceAudio": bool(coverage.get("recordingTracks")),
        "keySignature": metadata.get("keySignature", ""),
        "keyEvidence": metadata.get("keyEvidence", {"status": "unknown", "source": "not recorded"}),
        "timeSignature": metadata.get("timeSignature", ""),
        "meter": metadata.get("meter", ""),
    }


def main() -> int:
    corpus = load_json(CORPUS)
    draft_index = load_json(DRAFT_INDEX)
    image_manifest = load_json(IMAGE_MANIFEST) if IMAGE_MANIFEST.exists() else {}
    clean_candidates = load_json(CLEAN_SOURCE_CANDIDATES) if CLEAN_SOURCE_CANDIDATES.exists() else {}
    clean_source_omr = load_json(CLEAN_SOURCE_OMR_RUN) if CLEAN_SOURCE_OMR_RUN.exists() else {}
    source_metadata_payload = load_json(SOURCE_METADATA_OBSERVATIONS) if SOURCE_METADATA_OBSERVATIONS.exists() else {}
    source_metadata = {
        str(item.get("queueId")): item
        for item in source_metadata_payload.get("records", [])
        if item.get("queueId")
    }
    source_comparison_payload = load_json(SOURCE_COMPARISON_LEDGER) if SOURCE_COMPARISON_LEDGER.exists() else {}
    source_comparisons: dict[str, list[dict[str, Any]]] = {}
    for item in source_comparison_payload.get("records", []):
        queue_id = str(item.get("queueId", ""))
        if queue_id:
            source_comparisons.setdefault(queue_id, []).append(item)
    autonomously_verified_ids = {
        queue_id
        for queue_id, items in source_comparisons.items()
        if any(
            item.get("autonomousDecision") == "verified"
            and item.get("humanReviewRequired") is False
            for item in items
        )
    }
    correction_needed_ids = {
        queue_id
        for queue_id, items in source_comparisons.items()
        if any(
            item.get("comparisonStatus") == "verified-with-correction-needed"
            and item.get("safeToPromote") is False
            for item in items
        )
    }
    shape_review_payload = load_json(SHAPE_REVIEW_MANIFEST) if SHAPE_REVIEW_MANIFEST.exists() else {}
    shape_reviews = {
        str(item.get("queueId")): item
        for item in shape_review_payload.get("records", [])
        if item.get("queueId")
    }
    source_shape_review_payload = load_json(SOURCE_SHAPE_REVIEW_MANIFEST) if SOURCE_SHAPE_REVIEW_MANIFEST.exists() else {}
    source_shape_reviews = {
        str(item.get("queueId")): item
        for item in source_shape_review_payload.get("records", [])
        if item.get("queueId")
    }
    reconciliation_payload = load_json(RECONCILIATION_LEDGER) if RECONCILIATION_LEDGER.exists() else {}
    reconciliation = {
        str(item.get("candidateKey")): item
        for item in reconciliation_payload.get("records", [])
        if item.get("candidateKey")
    }
    cleaned_run: dict[str, dict[str, Any]] = {}
    for cleaned_path in CLEANED_OMR_RUNS:
        if not cleaned_path.exists():
            continue
        cleaned_payload = load_json(cleaned_path)
        # Iterate in version order so a newer v2 run replaces an older v1
        # result for the same immutable source image.
        for item in cleaned_payload.get("records", []):
            original_path = item.get("originalPath", "")
            if original_path:
                cleaned_run[original_path] = item
    songs = current_song_by_number(corpus)
    review_now = [
        review_item(
            draft,
            songs.get(draft_song_number(draft.get("record", ""))),
            image_manifest,
            cleaned_run,
            clean_candidates,
            clean_source_omr,
            reconciliation,
            source_metadata,
            source_comparisons,
            shape_reviews,
            source_shape_reviews,
        )
        for draft in draft_index.get("records", [])
        if re.match(r"^\d+[a-z]?(?:-|$)", str(draft.get("record", "")).lower())
        and f"sh2025/{draft_song_number(draft.get('record', ''))}" not in autonomously_verified_ids
    ]
    review_now.sort(key=lambda item: (item["priority"], int(re.match(r"\d+", item["songNo"]).group()), item["songNo"]))
    drafted_numbers = {item["songNo"] for item in review_now}
    missing_2025 = [
        song
        for song in corpus.get("songs", [])
        if "sh2025" in song.get("books", [])
        and not song.get("scoreByBook", {}).get("sh2025")
        and not song.get("referenceScoreByBook", {}).get("sh2025")
        and song.get("songNo", "").lower() not in drafted_numbers
    ]
    current_missing_2025_numbers = {
        song.get("songNo", "").lower()
        for song in corpus.get("songs", [])
        if "sh2025" in song.get("books", [])
        and not song.get("scoreByBook", {}).get("sh2025")
        and not song.get("referenceScoreByBook", {}).get("sh2025")
    }
    backlog = sorted(
        (backlog_item(song) for song in missing_2025),
        key=lambda item: (item["status"], item["songNo"], item["title"]),
    )
    new_review_count = sum(item.get("editionStatus") == "added-in-2025" for item in review_now)
    retained_review_count = sum(item.get("editionStatus") == "not-new-in-2025" for item in review_now)
    new_backlog_count = sum(item.get("editionStatus") == "added-in-2025" for item in backlog)
    retained_backlog_count = sum(item.get("editionStatus") == "not-new-in-2025" for item in backlog)
    autonomously_verified = []
    for queue_id in sorted(autonomously_verified_ids):
        if not queue_id.startswith("sh2025/"):
            continue
        song_number = queue_id.split("/", 1)[1]
        song = songs.get(song_number, {})
        coverage = song.get("sourceCoverageByBook", {}).get("sh2025", {})
        comparison = next(
            (item for item in source_comparisons.get(queue_id, []) if item.get("autonomousDecision") == "verified"),
            {},
        )
        canonical = comparison_disposition(comparison)
        autonomously_verified.append(
            {
                "queueId": queue_id,
                "canonicalRecordId": queue_id,
                "edition": "Sacred Harp 2025",
                "songNo": song_number,
                "title": song.get("titlesByBook", {}).get("sh2025", song.get("title", song_number)),
                "status": canonical["state"],
                "disposition": canonical,
                "safeToPromote": canonical["safeToPromote"],
                "humanReviewRequired": canonical["humanReviewRequired"],
                "reviewAvailable": canonical["reviewAvailable"],
                "sourcePageUrl": coverage.get("sourceUrls", [""])[0],
                "sourceManifestUrl": coverage.get("manifestSourceUrl", ""),
                "sourceManifestSha256": coverage.get("manifestSourceSha256", ""),
                "sourceComparison": comparison,
            }
        )
    correction_needed = []
    for queue_id in sorted(correction_needed_ids):
        if not queue_id.startswith("sh2025/"):
            continue
        song_number = queue_id.split("/", 1)[1]
        song = songs.get(song_number, {})
        coverage = song.get("sourceCoverageByBook", {}).get("sh2025", {})
        comparison = next(
            (item for item in source_comparisons.get(queue_id, []) if item.get("comparisonStatus") == "verified-with-correction-needed"),
            {},
        )
        canonical = comparison_disposition(comparison)
        correction_needed.append(
            {
                "queueId": queue_id,
                "edition": "Sacred Harp 2025",
                "songNo": song_number,
                "title": song.get("titlesByBook", {}).get("sh2025", song.get("title", song_number)),
                "status": "review-only",
                "canonicalRecordId": queue_id,
                "disposition": canonical,
                "notationStatus": canonical["notationStatus"],
                "playbackStatus": canonical["playbackStatus"],
                "transpositionStatus": canonical["transpositionStatus"],
                "semanticLimitations": canonical["semanticLimitations"],
                "safeToPromote": False,
                "humanReviewRequired": False,
                "reviewAvailable": True,
                "sourcePageUrl": coverage.get("sourceUrls", [""])[0],
                "sourceManifestUrl": coverage.get("manifestSourceUrl", ""),
                "sourceManifestSha256": coverage.get("manifestSourceSha256", ""),
                "sourceComparison": comparison,
            }
        )
    disposition_counts: dict[str, int] = {}
    for item in review_now:
        disposition = str(item.get("autonomousDisposition", "unresolved"))
        disposition_counts[disposition] = disposition_counts.get(disposition, 0) + 1
    output = {
        "generatedAt": corpus.get("generatedAt"),
        "policy": "OMR drafts are source-audit work product only. Every completed autonomous comparison is labeled verified, rejected, or blocked; only directly verified source comparisons may authorize automatic promotion.",
        "summary": {
            "reviewNow": len(review_now),
            "autonomouslyVerified": len(autonomously_verified),
            "correctionNeeded": len(correction_needed),
            "remaining2025Backlog": len(backlog),
            "draftsWithRenderedPdf": sum(bool(item["draftPdf"]) for item in review_now),
            "allCurrent2025MissingStructuredScore": len(current_missing_2025_numbers),
            "reviewNewIn2025": new_review_count,
            "reviewNotNewIn2025": retained_review_count,
            "backlogNewIn2025": new_backlog_count,
            "backlogNotNewIn2025": retained_backlog_count,
            "candidateLinks": sum(bool(item.get("cleanSourceCandidates")) for item in review_now),
            "candidateStructuralAgreements": sum(
                sum(bool(candidate.get("structuralAgreement")) for candidate in item.get("cleanSourceCandidates", []))
                for item in review_now
            ),
            "candidateNeedsHumanComparison": sum(
                sum(candidate.get("reconciliationStatus") == "needs-human-comparison" for candidate in item.get("cleanSourceCandidates", []))
                for item in review_now
            ),
            "sourceComparisons": sum(len(item.get("sourceComparisons", [])) for item in review_now) + len(autonomously_verified) + len(correction_needed),
            "sourceComparisonsSafeToPromote": sum(
                sum(bool(comparison.get("safeToPromote")) for comparison in item.get("sourceComparisons", []))
                for item in review_now
            ) + sum(bool(item.get("safeToPromote")) for item in autonomously_verified),
            "sourceShapeReviewDrafts": sum(bool(item.get("sourceShapeReviewDraft")) for item in review_now),
            "sourceShapeReviewDraftsSafeToPromote": sum(
                bool((item.get("sourceShapeReviewDraft") or {}).get("safeToPromote"))
                for item in review_now
            ),
            "autonomousDispositionCounts": disposition_counts,
            "humanReviewRequired": sum(bool(item.get("humanReviewRequired")) for item in review_now) + sum(bool(item.get("humanReviewRequired")) for item in autonomously_verified) + sum(bool(item.get("humanReviewRequired")) for item in correction_needed),
            "optionalReviewItems": sum(bool(item.get("reviewAvailable")) for item in review_now),
            "dispositionCounts": disposition_counts,
        },
        "reviewNow": review_now,
        "autonomouslyVerified": autonomously_verified,
        "correctionNeeded": correction_needed,
        "remaining2025Backlog": backlog,
        "completeEditionQueue": "public/transcription-queue.json",
    }
    OUTPUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Sacred Harp transcription review queue",
        "",
        "These are source-audit work products, not approved notation. Each record carries an explicit autonomous disposition; blocked and rejected records are retained as evidence and are not presented as a human-transcription handoff.",
        "",
        f"Generated review-now items: **{len(review_now)}** · remaining 2025 backlog: **{len(backlog)}**",
        "",
        f"Review-now split: **{new_review_count} added in 2025** · **{retained_review_count} not new in 2025**",
        "",
        "## Review now",
        "",
        "| Priority | Record | Disposition | Edition status | Draft | Source | Rendered draft | Key/mode metadata | Main risks |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in review_now:
        risks = "Watermark; shape heads need restoration"
        if item["draftSummary"]["emptyMeasures"]:
            risks += f"; {item['draftSummary']['emptyMeasures']} empty detected measures"
        source_key = item.get("sourceMetadataObservation", {}).get("observations", {}).get("key", {})
        key_display = item["keySignature"] or source_key.get("value") or "check"
        if source_key.get("value"):
            key_display = f"{key_display} (source-image OCR; review-only)"
        lines.append(
        f"| {item['priority']} | {item['songNo']} {item['title']} | `{item['autonomousDisposition']}` | {item['editionStatus'] or 'check'} | `{item['draftArtifact']}` | [source page]({item['sourcePageUrl']}) | `{item['draftPdf'] or 'not rendered'}` | {key_display} / {item['timeSignature'] or item['draftSummary']['timeSignatureDetected'] or 'check'} | {risks} |"
        )
    lines.extend([
        "",
        "## Per-item checklist",
        "",
    ])
    for item in review_now:
        lines.append(f"### {item['songNo']} {item['title']}")
        lines.append("")
        lines.append(f"- Autonomous disposition: `{item['autonomousDisposition']}`; evidence: `{item.get('dispositionEvidence') or 'not recorded'}`")
        if item.get("blockedReason"):
            lines.append(f"- Disposition reason: {item['blockedReason']}")
        source_key = item.get("sourceMetadataObservation", {}).get("observations", {}).get("key", {})
        lines.append(f"- Source image: {item['sourceImageUrl']}")
        lines.append(f"- Edition status: `{item['editionStatus'] or 'not recorded'}`")
        lines.append(f"- Edition evidence: `{item['editionEvidenceUrl'] or 'not recorded'}`")
        lines.append(f"- Local source: `{item['localSourceImage'] or 'not retained'}`")
        lines.append(f"- Conservative working image: `{item.get('normalizedWorkingImage') or 'not available'}`")
        lines.append(f"- Watermark-suppressed analysis image: `{item.get('suppressedWorkingImage') or 'not available'}` (review-only)")
        lines.append(f"- Cleaned-input Audiveris: `{item.get('cleanedOmrStatus', 'not-run')}`; artifacts: `{item.get('cleanedOmrArtifacts') or 'none'}`")
        if item.get("reconciliationArtifact"):
            lines.append(f"- Per-measure reconciliation: `{item['reconciliationArtifact']}`; status: `{item.get('reconciliationStatus', 'blocked')}`; candidate measure ranges: `{item.get('reconciliationCandidateMeasureCountRanges', {})}`")
        candidates = item.get("cleanSourceCandidates", [])
        lines.append(f"- Clean-source PDF candidates: `{len(candidates)}` (all require 2025 edition comparison)")
        for candidate in candidates:
            triage = "structural triage match" if candidate.get("structuralAgreement") else "structural differences"
            lines.append(f"  - [public candidate PDF]({candidate['pdfUrl']}) · `{candidate['localPdf'] or 'not downloaded'}` · `{candidate['matchKind']}` · `{triage}` · reconciliation `{candidate.get('reconciliationStatus', 'not-recorded')}` · OMR `{candidate['omrStatus']}` · `{candidate['sha256']}`")
            for discrepancy in candidate.get("discrepancies", []):
                lines.append(f"    - Triage note: {discrepancy}")
            for artifact in candidate.get("omrArtifacts", []):
                lines.append(f"    - OMR draft: `{artifact}` (review-only)")
        lines.append(f"- Draft: `{item['draftArtifact']}`")
        if item.get("sourceComparison"):
            comparison = item["sourceComparison"]
            lines.append(f"- Source comparison: `{comparison.get('auditFile', 'not recorded')}`; status: `{comparison.get('comparisonStatus', 'not recorded')}`; safe to promote: `{comparison.get('safeToPromote', False)}`")
            for comparison in item.get("sourceComparisons", [])[1:]:
                lines.append(f"- Additional source comparison: `{comparison.get('auditFile', 'not recorded')}`; status: `{comparison.get('comparisonStatus', 'not recorded')}`; safe to promote: `{comparison.get('safeToPromote', False)}`")
        lines.append(f"- Draft PDF: `{item['draftPdf'] or 'not rendered'}`")
        lines.append(f"- Parts/measures: `{item['draftSummary']['measuresByPart']}`; notes detected: `{item['draftSummary']['notes']}`")
        lines.append(f"- Key evidence: `{item['keySignature'] or 'unknown'}` ({item['keyEvidence']['status']}; {item['keyEvidence']['source']})")
        if source_key.get("value"):
            source = item["sourceMetadataObservation"].get("source", {})
            ocr = item["sourceMetadataObservation"].get("ocr", {})
            lines.append(f"- Source-header key observation: `{source_key['value']}` (`{source_key.get('status', 'review-only')}`; raw OCR `{ocr.get('rawTextPath', 'not retained')}`; source SHA-256 `{source.get('imageSha256', 'not recorded')}`)")
        for check in item["reviewChecklist"]:
            lines.append(f"- [ ] {check}")
        lines.append("")
    lines.extend([
        "## Remaining 2025 backlog",
        "",
        "The complete edition-wide queue, including 1991, 2025, and other books, is generated at `public/transcription-queue.json`. The 2025 records below have no exact or reference structured score and no local OMR draft yet.",
        "",
        "| Record | Title | Status | Source image | Next action |",
        "| --- | --- | --- | --- | --- |",
    ])
    for item in backlog:
        image = f"[scan]({item['sourceImageUrl']})" if item["sourceImageUrl"] else "—"
        lines.append(f"| {item['songNo']} | {item['title']} | {item['status']} | {image} | {item['nextAction']} |")
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Built {OUTPUT_JSON} with {len(review_now)} review-now drafts and {len(backlog)} remaining 2025 backlog records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
