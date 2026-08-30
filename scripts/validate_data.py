#!/usr/bin/env python3
"""Validate the generated atlas index and lazy score assets."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

from review_dispositions import (
    ALLOWED_STATES,
    comparison_disposition,
    image_review_disposition,
    transcription_disposition,
)


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public/corpus.json"
COVERAGE = ROOT / "public/source-coverage.json"
QUEUE = ROOT / "public/transcription-queue.json"
HUMAN_REVIEW_QUEUE = ROOT / "public/human-review-queue.json"
EDITION_ADDITIONS_2025 = ROOT / "public/edition-2025-additions.json"
CLEAN_SOURCE_CANDIDATES = ROOT / "work/source-transcriptions/2025/clean-source-candidates.json"
CANDIDATE_RECONCILIATION = ROOT / "public/candidate-reconciliation.json"
IMAGE_REVIEW_QUEUE = ROOT / "public/image-review-queue.json"
SOURCE_COMPARISON_LEDGER = ROOT / "public/source-comparison-ledger.json"
AUTONOMOUS_RECONCILIATION = ROOT / "public/sacred-harp-2025-autonomous-reconciliation.json"
SOURCE_METADATA_OBSERVATIONS = ROOT / "public/source-metadata-observations.json"
SHAPENOTE_2025_SCORE_AUDIT = ROOT / "public/shapenote-2025-score-audit.json"


def main() -> int:
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    coverage_data = json.loads(COVERAGE.read_text(encoding="utf-8"))
    queue_data = json.loads(QUEUE.read_text(encoding="utf-8"))
    human_review_data = json.loads(HUMAN_REVIEW_QUEUE.read_text(encoding="utf-8"))
    additions_data = json.loads(EDITION_ADDITIONS_2025.read_text(encoding="utf-8"))
    candidate_data = json.loads(CLEAN_SOURCE_CANDIDATES.read_text(encoding="utf-8"))
    candidate_reconciliation = json.loads(CANDIDATE_RECONCILIATION.read_text(encoding="utf-8"))
    image_review_data = json.loads(IMAGE_REVIEW_QUEUE.read_text(encoding="utf-8"))
    source_comparison_data = json.loads(SOURCE_COMPARISON_LEDGER.read_text(encoding="utf-8"))
    autonomous_reconciliation = json.loads(AUTONOMOUS_RECONCILIATION.read_text(encoding="utf-8"))
    source_metadata_data = json.loads(SOURCE_METADATA_OBSERVATIONS.read_text(encoding="utf-8"))
    shapenote_2025_score_audit = json.loads(SHAPENOTE_2025_SCORE_AUDIT.read_text(encoding="utf-8"))
    source_metadata_by_id = {
        str(item.get("queueId", "")).lower(): item
        for item in source_metadata_data.get("records", [])
        if item.get("queueId")
    }
    candidate_records = candidate_data.get("records", [])
    candidate_by_key = {
        str(record.get("candidateKey")): record
        for record in candidate_records
        if record.get("candidateKey")
    }
    if len(candidate_by_key) != len(candidate_records):
        raise SystemExit("clean-source candidate keys are missing or duplicated")
    reconciliation_records = candidate_reconciliation.get("records", [])
    reconciliation_by_key = {
        str(record.get("candidateKey")): record
        for record in reconciliation_records
        if record.get("candidateKey")
    }
    if set(reconciliation_by_key) != set(candidate_by_key):
        raise SystemExit("candidate reconciliation records do not match the candidate manifest")
    if candidate_reconciliation.get("safeToPromote") is not False:
        raise SystemExit("candidate reconciliation ledger is not fail-closed")
    allowed_reconciliation_statuses = {"needs-human-comparison", "autonomously-blocked-source-comparison"}
    for record in reconciliation_records:
        if (
            record.get("status") not in allowed_reconciliation_statuses
            or record.get("safeToPromote") is not False
            or record.get("autonomousDecision") != "blocked"
        ):
            raise SystemExit(f"candidate reconciliation is not fail-closed: {record.get('candidateKey', '')}")
    expected_image_queue = {
        f"sh2025/{song.get('songNo', '').lower()}"
        for song in data.get("songs", [])
        if "sh2025" in song.get("books", [])
        and not song.get("scoreByBook", {}).get("sh2025")
        and not song.get("referenceScoreByBook", {}).get("sh2025")
    }
    image_queue_records = image_review_data.get("records", [])
    actual_image_queue = {item.get("queueId") for item in image_queue_records}
    if actual_image_queue != expected_image_queue or len(actual_image_queue) != len(image_queue_records):
        raise SystemExit("image review queue does not exactly cover current 2025 missing structured scores")
    if image_review_data.get("summary", {}).get("total") != len(image_queue_records):
        raise SystemExit("image review queue total is stale")
    if image_review_data.get("summary", {}).get("safeToPromote") != 0:
        raise SystemExit("image review queue is not fail-closed")
    for item in image_queue_records:
        label = item.get("queueId", "")
        if item.get("canonicalRecordId") != label or item.get("humanReviewRequired") is not True or item.get("reviewAvailable") is not True or item.get("safeToPromote") is not False:
            raise SystemExit(f"image review item is not fail-closed: {label}")
        if item.get("disposition") != image_review_disposition():
            raise SystemExit(f"image review disposition is not canonical: {label}")
        original = item.get("original", {})
        if not original.get("immutable") or not (ROOT / original.get("path", "")).is_file():
            raise SystemExit(f"image review item is missing immutable original: {label}")
        layers = item.get("workingLayers", {})
        if not (ROOT / layers.get("normalized-v2", {}).get("path", "")).is_file():
            raise SystemExit(f"image review item is missing normalized layer: {label}")
        if not (ROOT / layers.get("suppressed-v2", {}).get("path", "")).is_file():
            raise SystemExit(f"image review item is missing suppressed layer: {label}")
    source_metadata_records = source_metadata_data.get("records", [])
    source_metadata_by_id = {item.get("queueId"): item for item in source_metadata_records}
    if set(source_metadata_by_id) != actual_image_queue or len(source_metadata_by_id) != len(source_metadata_records):
        raise SystemExit("source metadata observations do not exactly cover the image review queue")
    if source_metadata_data.get("summary", {}).get("safeToPromote") != 0:
        raise SystemExit("source metadata observations are not fail-closed")
    for item in source_metadata_records:
        label = item.get("queueId", "")
        if item.get("humanReviewRequired") is not True or item.get("safeToPromote") is not False:
            raise SystemExit(f"source metadata observation is not fail-closed: {label}")
        source = item.get("source", {})
        image = next((record for record in image_queue_records if record.get("queueId") == label), {})
        original = image.get("original", {})
        if source.get("imageSha256") != original.get("sha256") or source.get("immutable") is not True:
            raise SystemExit(f"source metadata checksum drift: {label}")
        ocr_path = ROOT / item.get("ocr", {}).get("rawTextPath", "")
        if not ocr_path.is_file():
            raise SystemExit(f"source metadata OCR artifact is missing: {label}")
    audit_records = shapenote_2025_score_audit.get("records", [])
    if shapenote_2025_score_audit.get("edition") != "sh2025" or len(audit_records) != 26:
        raise SystemExit("Shape-Note 2025 score audit does not cover exactly 26 MusicXML links")
    if shapenote_2025_score_audit.get("summary", {}).get("errors") != 0:
        raise SystemExit("Shape-Note 2025 score audit has acquisition or parse errors")
    promotable_audit_ids = {
        item.get("queueId")
        for item in shapenote_2025_score_audit.get("records", [])
        if item.get("safeToPromote") is True
    }
    if promotable_audit_ids or shapenote_2025_score_audit.get("summary", {}).get("safeToPromote") != 0:
        raise SystemExit("Shape-Note 2025 score audit must remain fail-closed until source-visible corrections are complete")
    for item in audit_records:
        expected_safe_to_promote = False
        comparison_status = item.get("comparisonStatus")
        if comparison_status not in {"external-source-blocked", "verified-with-correction-needed", "autonomously-verified-source-score"} or item.get("safeToPromote") is not expected_safe_to_promote:
            raise SystemExit(f"Shape-Note 2025 score audit promotion state is invalid: {item.get('queueId', '')}")
        if comparison_status == "external-source-blocked":
            evidence = item.get("externalSourceEvidence") or {}
            if evidence.get("status") != "external-source-blocked" or not evidence.get("reason"):
                raise SystemExit(f"Shape-Note 2025 score audit external block evidence is missing: {item.get('queueId', '')}")
            if not evidence.get("missingEvidence") or not evidence.get("sourceUrls"):
                raise SystemExit(f"Shape-Note 2025 score audit external block is imprecise: {item.get('queueId', '')}")
            if not item.get("blockedReasons"):
                raise SystemExit(f"Shape-Note 2025 score audit external block dropped blockedReasons: {item.get('queueId', '')}")
        elif item.get("externalSourceEvidence") is not None:
            raise SystemExit(f"Shape-Note 2025 score audit has stray external block evidence: {item.get('queueId', '')}")
        source_path = ROOT / item.get("rawPath", "")
        if not source_path.is_file() or hashlib.sha256(source_path.read_bytes()).hexdigest() != item.get("sourceSha256"):
            raise SystemExit(f"Shape-Note 2025 score audit checksum drift: {item.get('queueId', '')}")
    corpus_candidate_keys: set[str] = set()
    addition_records = {str(record).lower() for record in additions_data.get("records", [])}
    if additions_data.get("edition") != "sh2025" or additions_data.get("count") != 113 or len(addition_records) != 113:
        raise SystemExit("2025 additions register is missing, duplicated, or has the wrong count")
    coverage_records = {
        (record.get("songId"), record.get("bookId")): record
        for record in coverage_data.get("records", [])
    }
    allowed_statuses = {"structured-score", "source-reference", "metadata-only", "transcription-blocked", "mapping-gap"}
    seen_refs: set[str] = set()
    seen_draft_refs: set[str] = set()
    expected_queue: set[tuple[str, str]] = set()
    attached_source_observation_ids: set[str] = set()
    for song in data["songs"]:
        for book_id in song.get("books", []):
            coverage = song.get("sourceCoverageByBook", {}).get(book_id)
            if not coverage:
                raise SystemExit(f"{song['id']} {book_id}: missing source coverage record")
            if book_id == "sh2025":
                expected_edition_status = "added-in-2025" if song.get("songNo", "").lower() in addition_records else "not-new-in-2025"
                if coverage.get("editionStatus") != expected_edition_status or not coverage.get("editionEvidenceUrl"):
                    raise SystemExit(f"{song['id']} {book_id}: missing 2025 edition status evidence")
            if coverage.get("status") not in allowed_statuses:
                raise SystemExit(f"{song['id']} {book_id}: invalid source coverage status")
            manifest_score_audit = coverage.get("manifestScoreAudit")
            if manifest_score_audit:
                audit_status = manifest_score_audit.get("status")
                if audit_status not in {
                    "external-source-blocked",
                    "verified-with-correction-needed",
                    "autonomously-verified-source-score",
                }:
                    raise SystemExit(f"{song['id']} {book_id}: invalid manifest score-audit status")
                if manifest_score_audit.get("safeToPromote") is not False:
                    raise SystemExit(f"{song['id']} {book_id}: manifest score-audit is not fail-closed")
                if audit_status == "external-source-blocked":
                    evidence = manifest_score_audit.get("externalSourceEvidence") or {}
                    if (
                        evidence.get("status") != "external-source-blocked"
                        or not evidence.get("reason")
                        or not evidence.get("missingEvidence")
                        or not evidence.get("sourceUrls")
                        or not manifest_score_audit.get("blockedReasons")
                    ):
                        raise SystemExit(f"{song['id']} {book_id}: manifest score-audit external block is imprecise")
            observation = coverage.get("sourceMetadataObservation")
            if observation:
                if book_id != "sh2025":
                    raise SystemExit(f"{song['id']} {book_id}: source image observation is attached to the wrong edition")
                observation_id = f"sh2025/{str(song.get('songNo', '')).lower()}"
                source_record = source_metadata_by_id.get(observation_id)
                if not source_record:
                    raise SystemExit(f"{song['id']} {book_id}: attached source observation is not in the observation ledger")
                attached_source_observation_ids.add(observation_id)
                if observation.get("status") != "review-only-source-observation":
                    raise SystemExit(f"{song['id']} {book_id}: source observation is not explicitly review-only")
                if observation.get("safeToPromote") is not False or observation.get("humanReviewRequired") is not True:
                    raise SystemExit(f"{song['id']} {book_id}: source observation gate is not fail-closed")
                attached_source = observation.get("source", {})
                ledger_source = source_record.get("source", {})
                if (
                    attached_source.get("imageSha256") != ledger_source.get("imageSha256")
                    or attached_source.get("immutable") is not True
                    or ledger_source.get("immutable") is not True
                ):
                    raise SystemExit(f"{song['id']} {book_id}: attached source observation checksum or immutability drift")
                attached_key = observation.get("key", {})
                ledger_key = source_record.get("observations", {}).get("key", {})
                if attached_key.get("status") != ledger_key.get("status") or attached_key.get("value") != ledger_key.get("value"):
                    raise SystemExit(f"{song['id']} {book_id}: attached source key observation drift")
            for candidate in coverage.get("cleanSourceCandidates", []):
                candidate_key = str(candidate.get("candidateKey", ""))
                indexed_candidate = candidate_by_key.get(candidate_key)
                if not indexed_candidate:
                    raise SystemExit(f"{song['id']} {book_id}: source candidate is not in the manifest: {candidate_key}")
                if candidate.get("editionVerified") is not False or candidate.get("structuredScoreAdmissible") is not False:
                    raise SystemExit(f"{song['id']} {book_id}: source candidate is marked admissible: {candidate_key}")
                if not candidate.get("pdfUrl", "").startswith("https://"):
                    raise SystemExit(f"{song['id']} {book_id}: source candidate is missing a public PDF URL: {candidate_key}")
                corpus_candidate_keys.add(candidate_key)
            if coverage.get("status") != "structured-score":
                expected_queue.add((song["id"], book_id))
            for track in coverage.get("recordingTracks", []):
                if not track.get("url", "").startswith("https://") or not track.get("url", "").lower().endswith(".mp3"):
                    raise SystemExit(f"{song['id']} {book_id}: invalid source recording URL")
                if track.get("kind") == "full-song-source-witness" and track.get("isFullSong") is not True:
                    raise SystemExit(f"{song['id']} {book_id}: full-song source witness is not explicitly marked")
            for recording_source in coverage.get("recordingSourcePages", []):
                if not recording_source.startswith("https://") and not recording_source.startswith("work/"):
                    raise SystemExit(f"{song['id']} {book_id}: invalid recording source page")
            indexed_coverage = coverage_records.get((song["id"], book_id))
            if indexed_coverage != {
                "songId": song["id"],
                "songNo": song["songNo"],
                "title": song["title"],
                "bookId": book_id,
                **coverage,
            }:
                raise SystemExit(f"{song['id']} {book_id}: source coverage index drift")
        if "sh1991" in song.get("books", []) and "sh2025" in song.get("books", []):
            relation = song.get("editionReconciliation")
            if not relation or relation.get("books") != ["sh1991", "sh2025"]:
                raise SystemExit(f"{song['id']}: missing 1991/2025 reconciliation")
            expected_metadata_differences = {}
            for field in ("keySignature", "mode", "timeSignature"):
                left = song.get("metadataByBook", {}).get("sh1991", {}).get(field, "")
                right = song.get("metadataByBook", {}).get("sh2025", {}).get(field, "")
                if left and right and left != right:
                    expected_metadata_differences[field] = {
                        "sh1991": left,
                        "sh2025": right,
                    }
            actual_metadata_differences = (relation.get("changes") or {}).get("source_metadata_difference", {})
            if actual_metadata_differences != expected_metadata_differences:
                raise SystemExit(f"{song['id']}: edition metadata reconciliation drift")
            if expected_metadata_differences and relation.get("status") != "change-flagged":
                raise SystemExit(f"{song['id']}: source metadata difference is not change-flagged")
        relation = song.get("editionReconciliation", {})
        if relation.get("relationId"):
            records = relation.get("records", {})
            if set(records) != {"sh1991", "sh2025"}:
                raise SystemExit(f"{song['id']}: incomplete edition relation records")
            for record in records.values():
                if not record.get("songNo") or not record.get("title") or not record.get("url"):
                    raise SystemExit(f"{song['id']}: incomplete edition relation source record")
            if set(relation.get("scoreAvailability", {})) != {"sh1991", "sh2025"}:
                raise SystemExit(f"{song['id']}: incomplete edition relation score availability")
        for metadata in song.get("metadataByBook", {}).values():
            source_url = metadata.get("sourceUrl", "")
            source_urls = metadata.get("sourceUrls", [])
            if source_url and source_url not in source_urls:
                raise SystemExit(f"{song['id']}: sourceUrl missing from sourceUrls")
        if "sh2025" in song.get("books", []):
            expected_2025_source = f"https://fasola.org/indexes/2025/?p={song['songNo']}"
            if song.get("metadataByBook", {}).get("sh2025", {}).get("sourceUrl") != expected_2025_source:
                raise SystemExit(f"{song['id']}: 2025 metadata is not anchored to the current edition index")
        for book_id, score in song.get("scoreByBook", {}).items():
            ref = score.get("scoreRef", "")
            if not ref.startswith("/scores/"):
                raise SystemExit(f"{song['id']} {book_id}: invalid scoreRef {ref!r}")
            path = ROOT / "public" / ref.lstrip("/")
            if not path.exists():
                raise SystemExit(f"{song['id']} {book_id}: missing {path}")
            asset = json.loads(path.read_text(encoding="utf-8"))
            if not asset.get("sourceUrl") or not asset.get("parts"):
                raise SystemExit(f"{song['id']} {book_id}: incomplete score asset")
            if not any(part.get("events") for part in asset["parts"]):
                raise SystemExit(f"{song['id']} {book_id}: score has no events")
            transposition = asset.get("transposition", {})
            if transposition.get("hasPitchedEvents") and not transposition.get("available") and not transposition.get("manualKeyAllowed"):
                raise SystemExit(f"{song['id']} {book_id}: pitched score is neither transposable nor marked for source-key entry")
            seen_refs.add(ref)
        for book_id, score in song.get("referenceScoreByBook", {}).items():
            if score.get("provenance", {}).get("kind") != "alternate-source":
                raise SystemExit(f"{song['id']} {book_id}: reference score has invalid provenance")
            ref = score.get("scoreRef", "")
            if not ref.startswith("/scores/"):
                raise SystemExit(f"{song['id']} {book_id}: invalid reference scoreRef {ref!r}")
            path = ROOT / "public" / ref.lstrip("/")
            if not path.exists():
                raise SystemExit(f"{song['id']} {book_id}: missing reference score asset {path}")
            asset = json.loads(path.read_text(encoding="utf-8"))
            if not asset.get("sourceUrl") or not asset.get("parts") or not any(part.get("events") for part in asset["parts"]):
                raise SystemExit(f"{song['id']} {book_id}: incomplete reference score asset")
            transposition = asset.get("transposition", {})
            if transposition.get("hasPitchedEvents") and not transposition.get("available") and not transposition.get("manualKeyAllowed"):
                raise SystemExit(f"{song['id']} {book_id}: pitched reference is neither transposable nor marked for source-key entry")
        for book_id, score in song.get("draftScoreByBook", {}).items():
            if score.get("provenance", {}).get("kind") != "omr-draft" or score.get("provenance", {}).get("reviewRequired") is not True:
                raise SystemExit(f"{song['id']} {book_id}: draft score has invalid provenance")
            ref = score.get("scoreRef", "")
            if not ref.startswith("/draft-scores/"):
                raise SystemExit(f"{song['id']} {book_id}: invalid draft scoreRef {ref!r}")
            path = ROOT / "public" / ref.lstrip("/")
            if not path.exists():
                raise SystemExit(f"{song['id']} {book_id}: missing draft score asset {path}")
            asset = json.loads(path.read_text(encoding="utf-8"))
            if not asset.get("sourceUrl", "").startswith("draft://") or not asset.get("parts") or not any(part.get("events") for part in asset["parts"]):
                raise SystemExit(f"{song['id']} {book_id}: incomplete draft score asset")
            transposition = asset.get("transposition", {})
            if transposition.get("hasPitchedEvents") and not transposition.get("available") and not transposition.get("manualKeyAllowed"):
                raise SystemExit(f"{song['id']} {book_id}: pitched draft is neither transposable nor marked for source-key entry")
            coverage = song.get("sourceCoverageByBook", {}).get(book_id, {})
            if coverage.get("draftScoreRef") != ref or coverage.get("draftScoreStatus") != "needs-human-review":
                raise SystemExit(f"{song['id']} {book_id}: draft score coverage marker drift")
            seen_draft_refs.add(ref)
    coverage = data["coverage"]["byBook"]
    expected_edition_records = sum(book.get("records", 0) for book in coverage.values())
    if coverage_data.get("summary", {}).get("editionRecords") != expected_edition_records:
        raise SystemExit("source coverage edition-record count does not match corpus coverage")
    expected_reference_witnesses = sum(
        1
        for song in data["songs"]
        for book_id in song.get("books", [])
        if song.get("referenceScoreByBook", {}).get(book_id)
    )
    if coverage_data.get("summary", {}).get("transposableReferenceWitnesses") != expected_reference_witnesses:
        raise SystemExit("source coverage reference-witness count does not match corpus")
    expected_draft_scores = sum(
        1
        for song in data["songs"]
        for book_id in song.get("books", [])
        if song.get("draftScoreByBook", {}).get(book_id)
    )
    if len(seen_draft_refs) != expected_draft_scores:
        raise SystemExit("draft score assets do not match corpus draft scores")
    if len(coverage_records) != expected_edition_records:
        raise SystemExit("source coverage ledger contains duplicate or missing edition records")
    if corpus_candidate_keys != set(candidate_by_key):
        missing = sorted(set(candidate_by_key) - corpus_candidate_keys)
        extra = sorted(corpus_candidate_keys - set(candidate_by_key))
        raise SystemExit(f"corpus clean-source candidate links drift (missing={missing}, extra={extra})")
    queue_records = queue_data.get("records", [])
    actual_queue = {(record.get("songId"), record.get("bookId")) for record in queue_records}
    if actual_queue != expected_queue or len(queue_records) != len(actual_queue):
        raise SystemExit("transcription queue does not exactly match non-structured coverage records")
    for record in queue_records:
        if record.get("status") not in allowed_statuses - {"structured-score"}:
            raise SystemExit(f"invalid transcription queue status: {record.get('status')!r}")
        if not record.get("queueId") or not record.get("nextAction"):
            raise SystemExit("incomplete transcription queue record")
        if not isinstance(record.get("sourceUrls"), list):
            raise SystemExit("transcription queue sourceUrls must be a list")
        if record.get("status") == "source-reference" and not record.get("sourceUrls"):
            raise SystemExit("source-reference queue record is missing its source URLs")
        source_image_url = record.get("sourceImageUrl", "")
        if source_image_url and not source_image_url.startswith("https://"):
            raise SystemExit("transcription queue sourceImageUrl must be an https URL")
        expected_disposition = transcription_disposition(record.get("status", ""), record.get("sourceUrls", []))
        if record.get("canonicalRecordId") != record.get("queueId") or record.get("disposition") != expected_disposition:
            raise SystemExit(f"transcription queue disposition is not canonical: {record.get('queueId', '')}")
        if record.get("humanReviewRequired") is not False or record.get("safeToPromote") is not False:
            raise SystemExit(f"transcription queue is not fail-closed: {record.get('queueId', '')}")

    ledger_records = source_comparison_data.get("records", [])
    ledger_ids = [record.get("queueId", "") for record in ledger_records]
    if any(not queue_id.startswith("sh2025/") for queue_id in ledger_ids):
        raise SystemExit("source comparison ledger contains a non-canonical queue ID")
    if any(record.get("canonicalRecordId") != record.get("queueId") for record in ledger_records):
        raise SystemExit("source comparison ledger canonical IDs are missing or mismatched")
    for record in ledger_records:
        expected_disposition = comparison_disposition(record)
        if expected_disposition["state"] not in ALLOWED_STATES or record.get("disposition") != expected_disposition:
            raise SystemExit(f"source comparison disposition is not canonical: {record.get('queueId', '')}")
        if record.get("safeToPromote") is True and expected_disposition["state"] != "verified":
            raise SystemExit(f"source comparison promotion state conflicts with disposition: {record.get('queueId', '')}")
    disposition_summary = source_comparison_data.get("summary", {})
    expected_counts = {}
    for record in ledger_records:
        state = record["disposition"]["state"]
        expected_counts[state] = expected_counts.get(state, 0) + 1
    if disposition_summary.get("dispositionCounts") != expected_counts:
        raise SystemExit("source comparison disposition counts are stale")

    reconciliation_records = autonomous_reconciliation.get("records", [])
    if autonomous_reconciliation.get("summary", {}).get("recordsStillWithoutAutonomousDisposition") != 0:
        raise SystemExit("autonomous reconciliation still has records without disposition")
    reconciliation_counts = {}
    for record in reconciliation_records:
        label = record.get("queueId", "")
        disposition = record.get("disposition", {})
        if record.get("canonicalRecordId") != label or disposition.get("state") not in ALLOWED_STATES:
            raise SystemExit(f"autonomous reconciliation identity/disposition is invalid: {label}")
        if record.get("humanReviewRequired") != disposition.get("humanReviewRequired") or "needs-human-review" in record.get("queueStatus", []):
            raise SystemExit(f"autonomous reconciliation review semantics are contradictory: {label}")
        if not record.get("ledgerRecordCount") or not record.get("perRecordAuditFiles"):
            raise SystemExit(f"autonomous reconciliation lacks evidence: {label}")
        state = disposition["state"]
        reconciliation_counts[state] = reconciliation_counts.get(state, 0) + 1
    if autonomous_reconciliation.get("summary", {}).get("dispositionCounts") != reconciliation_counts:
        raise SystemExit("autonomous reconciliation disposition counts are stale")
    review_now = human_review_data.get("reviewNow", [])
    autonomously_verified = human_review_data.get("autonomouslyVerified", [])
    correction_needed = human_review_data.get("correctionNeeded", [])
    backlog = human_review_data.get("remaining2025Backlog", [])
    if human_review_data.get("summary", {}).get("reviewNow") != len(review_now):
        raise SystemExit("human review queue review-now count is stale")
    if human_review_data.get("summary", {}).get("remaining2025Backlog") != len(backlog):
        raise SystemExit("human review queue backlog count is stale")
    if human_review_data.get("summary", {}).get("autonomouslyVerified") != len(autonomously_verified):
        raise SystemExit("human review queue autonomous-completed count is stale")
    if human_review_data.get("summary", {}).get("correctionNeeded") != len(correction_needed):
        raise SystemExit("human review queue correction-needed count is stale")
    for item in autonomously_verified:
        expected_safe_to_promote = False
        if item.get("canonicalRecordId") != item.get("queueId") or item.get("status") != "verified" or item.get("safeToPromote") is not expected_safe_to_promote or item.get("humanReviewRequired") is not False:
            raise SystemExit(f"autonomous-completed record is incorrectly routed to review: {item.get('queueId', '')}")
        if not item.get("sourceComparison") or item.get("sourceComparison", {}).get("autonomousDecision") != "verified":
            raise SystemExit(f"autonomous-completed record is missing verified comparison: {item.get('queueId', '')}")
        if item.get("sourceComparison", {}).get("safeToPromote") is not expected_safe_to_promote:
            raise SystemExit(f"autonomous-completed promotion state is stale: {item.get('queueId', '')}")
        if item.get("disposition", {}).get("state") != "verified":
            raise SystemExit(f"autonomous-completed disposition is not canonical: {item.get('queueId', '')}")
    for item in correction_needed:
        if item.get("canonicalRecordId") != item.get("queueId") or item.get("status") != "review-only" or item.get("safeToPromote") is not False or item.get("humanReviewRequired") is not False:
            raise SystemExit(f"correction-needed record is incorrectly routed: {item.get('queueId', '')}")
        comparison = item.get("sourceComparison", {})
        if comparison.get("autonomousDecision") != "verified-with-correction-needed" or comparison.get("safeToPromote") is not False:
            raise SystemExit(f"correction-needed record is missing fail-closed comparison: {item.get('queueId', '')}")
        if item.get("disposition", {}).get("state") != "review-only":
            raise SystemExit(f"correction-needed disposition is not canonical: {item.get('queueId', '')}")
    for item in review_now:
        if item.get("status") not in ALLOWED_STATES or item.get("safeToPromote") is not False:
            raise SystemExit("OMR audit item is not fail-closed")
        if item.get("canonicalRecordId") != item.get("queueId") or item.get("humanReviewRequired") is not False:
            raise SystemExit(f"OMR audit item has ambiguous required-review state: {item.get('queueId', '')}")
        if item.get("disposition", {}).get("state") != item.get("status") or not item.get("reviewAvailable"):
            raise SystemExit(f"OMR audit item disposition is not explicit: {item.get('queueId', '')}")
        if not item.get("draftArtifact") or not item.get("draftSha256"):
            raise SystemExit("OMR review item is missing draft identity")
        if not (ROOT / item["draftArtifact"]).exists():
            raise SystemExit(f"OMR draft missing for human review: {item['draftArtifact']}")
        draft_bytes = (ROOT / item["draftArtifact"]).read_bytes()
        if hashlib.sha256(draft_bytes).hexdigest() != item.get("draftSha256"):
            raise SystemExit(f"OMR draft checksum changed for human review: {item['draftArtifact']}")
        if item.get("draftPdf") and not (ROOT / item["draftPdf"]).exists():
            raise SystemExit(f"rendered OMR draft missing for human review: {item['draftPdf']}")
        if not item.get("reviewChecklist"):
            raise SystemExit("OMR review item is missing its checklist")
        if item.get("editionStatus") not in {"added-in-2025", "not-new-in-2025"}:
            raise SystemExit("OMR review item is missing 2025 edition status")
        for candidate in item.get("cleanSourceCandidates", []):
            if candidate.get("reconciliationStatus") not in {
                "needs-human-comparison",
                "autonomously-blocked-source-comparison",
            }:
                raise SystemExit(f"review candidate is missing reconciliation status: {candidate.get('candidateKey', '')}")
            if candidate.get("reconciliationSafeToPromote") is not False:
                raise SystemExit(f"review candidate is not fail-closed: {candidate.get('candidateKey', '')}")
            if not isinstance(candidate.get("structuralAgreement"), bool):
                raise SystemExit(f"review candidate structural triage is not boolean: {candidate.get('candidateKey', '')}")
            if not candidate.get("discrepancies"):
                raise SystemExit(f"review candidate is missing comparison notes: {candidate.get('candidateKey', '')}")
    for item in backlog:
        if item.get("canonicalRecordId") != item.get("queueId") or item.get("disposition", {}).get("state") not in ALLOWED_STATES:
            raise SystemExit(f"human review backlog disposition is not explicit: {item.get('queueId', '')}")
        if item.get("humanReviewRequired") is not False or item.get("safeToPromote") is not False:
            raise SystemExit(f"human review backlog is not fail-closed: {item.get('queueId', '')}")
    current_2025_missing = {
        song.get("songNo", "").lower()
        for song in data["songs"]
        if "sh2025" in song.get("books", [])
        and not song.get("scoreByBook", {}).get("sh2025")
        and not song.get("referenceScoreByBook", {}).get("sh2025")
    }
    expected_source_observation_ids = {f"sh2025/{song_no}" for song_no in current_2025_missing}
    if attached_source_observation_ids != expected_source_observation_ids:
        missing = sorted(expected_source_observation_ids - attached_source_observation_ids)
        extra = sorted(attached_source_observation_ids - expected_source_observation_ids)
        raise SystemExit(f"corpus source observations do not exactly cover current 2025 missing scores (missing={missing}, extra={extra})")
    queue_numbers = {item.get("songNo", "").lower() for item in review_now + backlog}
    if not current_2025_missing.issubset(queue_numbers):
        raise SystemExit("human review queue does not cover all current 2025 missing structured scores")
    expected_new_review = sum(item.get("editionStatus") == "added-in-2025" for item in review_now)
    expected_not_new_review = sum(item.get("editionStatus") == "not-new-in-2025" for item in review_now)
    if human_review_data.get("summary", {}).get("reviewNewIn2025") != expected_new_review:
        raise SystemExit("human review queue new-in-2025 count is stale")
    if human_review_data.get("summary", {}).get("reviewNotNewIn2025") != expected_not_new_review:
        raise SystemExit("human review queue retained/revised count is stale")
    expected_candidate_links = sum(bool(item.get("cleanSourceCandidates")) for item in review_now)
    expected_candidate_agreements = sum(
        sum(bool(candidate.get("structuralAgreement")) for candidate in item.get("cleanSourceCandidates", []))
        for item in review_now
    )
    expected_candidate_comparisons = sum(
        sum(candidate.get("reconciliationStatus") == "needs-human-comparison" for candidate in item.get("cleanSourceCandidates", []))
        for item in review_now
    )
    summary = human_review_data.get("summary", {})
    if summary.get("candidateLinks") != expected_candidate_links:
        raise SystemExit("human review queue candidate-link count is stale")
    if summary.get("candidateStructuralAgreements") != expected_candidate_agreements:
        raise SystemExit("human review queue candidate-agreement count is stale")
    if summary.get("candidateNeedsHumanComparison") != expected_candidate_comparisons:
        raise SystemExit("human review queue candidate-comparison count is stale")
    current_2025_records = {
        song.get("songNo", "").lower()
        for song in data["songs"]
        if "sh2025" in song.get("books", [])
    }
    if not addition_records.issubset(current_2025_records):
        raise SystemExit("2025 additions register contains records absent from the current display corpus")
    if coverage["sh1991"]["localScoreRecords"] < 500:
        raise SystemExit("Sacred Harp 1991 score coverage unexpectedly low")
    if coverage["sh2025"]["localScoreRecords"] < 13:
        raise SystemExit("Sacred Harp 2025 exact score coverage unexpectedly low")
    current_2025 = {
        song.get("songNo", "").lower()
        for song in data["songs"]
        if "sh2025" in song.get("books", [])
    }
    if len(current_2025) != 590 or not {"106", "414t", "484t"}.issubset(current_2025):
        raise SystemExit("Sacred Harp 2025 display corpus is not aligned with the current 590-song index")
    if {"264b"} & current_2025:
        raise SystemExit("Superseded pre-publication 2025 records leaked into the current display corpus")
    if any(record.get("songNo", "").lower() == "264b" for record in data.get("legacyEditionRecords", [])):
        raise SystemExit("Hallucinated 2025 record 264b was retained in the audit payload")
    current_414b = next(
        (song for song in data["songs"] if "sh2025" in song.get("books", []) and song.get("songNo", "").lower() == "414b"),
        None,
    )
    if not current_414b or current_414b.get("title") != "Parting Friend":
        raise SystemExit("Sacred Harp 2025 record 414b is not the current Parting Friend entry")
    if not current_414b.get("referenceScoreByBook", {}).get("sh2025"):
        raise SystemExit("Sacred Harp 2025 record 414b lost its verified transposable reference witness")
    if not data.get("legacyEditionRecords"):
        raise SystemExit("Superseded 2025 records are not preserved for audit")
    if coverage["shenandoah"]["records"] != 468:
        raise SystemExit("Shenandoah corpus record count changed unexpectedly")
    print(f"Validated {len(data['songs'])} songs, {len(seen_refs)} lazy full-score assets, {len(seen_draft_refs)} review draft assets, {len(queue_records)} transcription queue records, {len(image_queue_records)} image review records, and all book coverage counters.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
