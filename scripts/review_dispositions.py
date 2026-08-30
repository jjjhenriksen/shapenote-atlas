#!/usr/bin/env python3
"""Shared fail-closed state vocabulary for review and acquisition artifacts.

These helpers describe workflow state only. They never authorize notation,
change source metadata, or promote an OMR draft.  ``humanReviewRequired`` is
deliberately separate from ``reviewAvailable``: an artifact can be useful
evidence for optional inspection while its autonomous outcome is already
blocked or rejected.
"""

from __future__ import annotations

from typing import Any


ALLOWED_STATES = {
    "verified",
    "source-observed",
    "review-only",
    "external-source-blocked",
    "autonomously-blocked",
    "rejected",
    "unavailable",
}


def _result(
    state: str,
    *,
    human_review_required: bool,
    review_available: bool,
    safe_to_promote: bool = False,
    role: str,
    reason: str = "",
    autonomous_decision: str = "",
) -> dict[str, Any]:
    if state not in ALLOWED_STATES:
        raise ValueError(f"unsupported review disposition: {state}")
    return {
        "state": state,
        "role": role,
        "humanReviewRequired": human_review_required,
        "reviewAvailable": review_available,
        "safeToPromote": safe_to_promote,
        "reason": reason,
        "autonomousDecision": autonomous_decision,
    }


def comparison_disposition(record: dict[str, Any] | None) -> dict[str, Any]:
    """Map one source-comparison row to its canonical workflow disposition."""
    row = record or {}
    decision = str(row.get("autonomousDecision", "")).strip().lower()
    status = str(row.get("comparisonStatus", "")).strip().lower()
    reason = str(
        row.get("blockingReason")
        or row.get("reason")
        or row.get("nextAction")
        or ""
    )
    if decision == "verified" and row.get("safeToPromote") is True:
        return _result(
            "verified",
            human_review_required=False,
            review_available=True,
            safe_to_promote=True,
            role="source-comparison",
            reason=reason,
            autonomous_decision=decision,
        )
    if decision in {"rejected", "rejected-source-mismatch", "source-mismatch-rejected"} or status.startswith(("rejected", "source-mismatch-rejected")):
        return _result(
            "rejected",
            human_review_required=False,
            review_available=True,
            role="source-comparison",
            reason=reason or "Source/candidate mismatch was autonomously rejected.",
            autonomous_decision=decision or "rejected",
        )
    if decision == "verified-with-correction-needed" or status == "verified-with-correction-needed":
        return _result(
            "review-only",
            human_review_required=False,
            review_available=True,
            role="source-comparison-correction",
            reason=reason or "A correction-needed derivative remains review-only.",
            autonomous_decision=decision or "verified-with-correction-needed",
        )
    if decision in {"external-source-blocked", "source-external-blocked"} or status in {"external-source-blocked", "source-external-blocked"}:
        return _result(
            "external-source-blocked",
            human_review_required=False,
            review_available=True,
            role="source-comparison-external-block",
            reason=reason or "An exact authorized structured source is unavailable or obscured.",
            autonomous_decision=decision or status,
        )
    if decision == "blocked" or status.startswith("autonomously-"):
        return _result(
            "autonomously-blocked",
            human_review_required=False,
            review_available=True,
            role="source-comparison",
            reason=reason or "Exact source-faithful promotion remains blocked.",
            autonomous_decision=decision or "blocked",
        )
    if decision == "verified" or status in {"alternate-key-witness-not-promoted", "source-observed"}:
        return _result(
            "review-only",
            human_review_required=False,
            review_available=True,
            role="source-comparison-witness",
            reason=reason or "Evidence exists but the promotion gate is closed.",
            autonomous_decision=decision or status,
        )
    return _result(
        "unavailable",
        human_review_required=False,
        review_available=False,
        role="source-comparison",
        reason=reason or "No explicit autonomous disposition is recorded.",
        autonomous_decision=decision,
    )


def aggregate_comparison_disposition(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Choose one canonical state while retaining every duplicate evidence row."""
    if not records:
        return comparison_disposition(None)
    rank = {
        "verified": 0,
        "rejected": 1,
        "external-source-blocked": 2,
        "autonomously-blocked": 3,
        "review-only": 4,
        "unavailable": 5,
    }
    return min(
        (comparison_disposition(record) for record in records),
        key=lambda item: rank[item["state"]],
    )


def image_review_disposition() -> dict[str, Any]:
    """Image preparation requires human source comparison by policy."""
    return _result(
        "review-only",
        human_review_required=True,
        review_available=True,
        role="source-image-visual-comparison",
        reason="The immutable original must be compared before image evidence can support transcription.",
    )


def transcription_disposition(status: str, source_urls: list[Any] | None) -> dict[str, Any]:
    """Map non-structured-score coverage to acquisition workflow state."""
    normalized = str(status or "").strip().lower()
    has_source = bool(source_urls)
    if normalized == "source-reference" and has_source:
        return _result(
            "source-observed",
            human_review_required=False,
            review_available=True,
            role="structured-score-acquisition",
            reason="A source reference exists, but no exact structured score is mapped.",
        )
    return _result(
        "unavailable",
        human_review_required=False,
        review_available=has_source,
        role="structured-score-acquisition",
        reason=(
            "Source acquisition is explicitly blocked; no structured score is available."
            if normalized == "transcription-blocked"
            else "No usable structured-score acquisition state is recorded."
        ),
    )


def disposition_for_queue_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return the already-materialized disposition, or derive a safe fallback."""
    existing = record.get("disposition")
    if isinstance(existing, dict) and existing.get("state") in ALLOWED_STATES:
        return existing
    if "comparisonStatus" in record or "autonomousDecision" in record:
        return comparison_disposition(record)
    return transcription_disposition(str(record.get("status", "")), record.get("sourceUrls"))
