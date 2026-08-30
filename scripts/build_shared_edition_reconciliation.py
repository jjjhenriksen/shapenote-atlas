#!/usr/bin/env python3
"""Build a fail-closed semantic reconciliation for shared SH1991/SH2025 records.

This is an additive report. It never merges an alternate-edition witness into
the selected edition and never changes the canonical corpus or score assets.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public" / "corpus.json"
OUTPUT = ROOT / "public" / "shared-edition-reconciliation.json"
EDITIONS = ("sh1991", "sh2025")
COMPARISON_FIELDS = (
    "title",
    "keyMode",
    "meter",
    "timeSignature",
    "lyrics",
    "repeatEndings",
    "parts",
    "notation",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def key_mode(value: Any) -> str:
    match = re.search(r"\b(major|minor)\b", str(value or ""), re.IGNORECASE)
    return match.group(1).lower() if match else "unknown"


def asset_path(score_ref: str) -> Path | None:
    if not score_ref or not score_ref.startswith("/"):
        return None
    path = ROOT / "public" / score_ref.lstrip("/")
    return path if path.is_file() else None


def event_signature(event: dict[str, Any]) -> tuple[Any, ...]:
    return (
        event.get("measure", ""),
        event.get("onset", 0),
        event.get("beats", 0),
        bool(event.get("rest")),
        event.get("step", ""),
        event.get("alter", 0),
        event.get("octave", 0),
        event.get("dots", 0),
        event.get("accidental", ""),
        bool(event.get("tieStart")),
        bool(event.get("tieStop")),
    )


def summarize_asset(asset: dict[str, Any] | None) -> dict[str, Any] | None:
    if not asset:
        return None
    ref = str(asset.get("scoreRef", ""))
    path = asset_path(ref)
    loaded = asset
    if path:
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = asset
    parts: list[dict[str, Any]] = []
    all_events: list[tuple[Any, ...]] = []
    for part in loaded.get("parts", []):
        events = part.get("events", [])
        pitched = [event for event in events if not event.get("rest") and event.get("step")]
        measures = sorted({str(event.get("measure", "")) for event in events if event.get("measure", "")})
        parts.append(
            {
                "name": part.get("name", ""),
                "eventCount": len(events),
                "pitchedEventCount": len(pitched),
                "measureCount": len(measures),
                "measures": measures,
            }
        )
        all_events.extend(event_signature(event) for event in events)
    return {
        "scoreRef": ref,
        "sourceUrl": asset.get("sourceUrl", ""),
        "keySignature": asset.get("keySignature", ""),
        "keyEvidence": asset.get("keyEvidence", {}),
        "timeSignature": asset.get("timeSignature", ""),
        "provenance": asset.get("provenance", {}),
        "parts": parts,
        "eventCount": sum(part["eventCount"] for part in parts),
        "pitchedEventCount": sum(part["pitchedEventCount"] for part in parts),
        "notationFingerprint": json_hash(all_events),
        "assetSha256": sha256(path) if path else "",
    }


def witness_summary(song: dict[str, Any], book: str) -> dict[str, Any]:
    witnesses: dict[str, Any] = {}
    for field, role in (
        ("scoreByBook", "exact-edition"),
        ("referenceScoreByBook", "alternate-reference"),
        ("draftScoreByBook", "review-draft"),
    ):
        asset = (song.get(field) or {}).get(book)
        if asset:
            summary = summarize_asset(asset)
            if summary:
                summary["role"] = role
                witnesses[field] = summary
    return witnesses


def source_summary(song: dict[str, Any], book: str) -> dict[str, Any]:
    metadata = (song.get("metadataByBook") or {}).get(book, {})
    coverage = (song.get("sourceCoverageByBook") or {}).get(book, {})
    return {
        "songNo": song.get("songNo", ""),
        "title": (song.get("titlesByBook") or {}).get(book, song.get("title", "")),
        "sourceRecordKey": metadata.get("sourceRecordKey", coverage.get("sourceRecordKey", "")),
        "sourceUrl": metadata.get("sourceUrl", ""),
        "sourceUrls": metadata.get("sourceUrls", []),
        "confidence": metadata.get("confidence", ""),
        "keySignature": metadata.get("keySignature", ""),
        "keyMode": key_mode(metadata.get("keySignature", "")),
        "keyEvidence": metadata.get("keyEvidence", {"status": "unknown", "source": "not recorded"}),
        "meter": metadata.get("meter", ""),
        "timeSignature": metadata.get("timeSignature", ""),
        "composer": metadata.get("composer", ""),
        "lyricist": metadata.get("lyricist", ""),
        "coverageStatus": coverage.get("status", ""),
        "manifestSourceUrl": coverage.get("manifestSourceUrl", ""),
        "manifestSourceSha256": coverage.get("manifestSourceSha256", ""),
        "sourceImageUrl": coverage.get("sourceImageUrl", ""),
    }


def compare_values(left: Any, right: Any, *, unavailable_reason: str = "") -> dict[str, Any]:
    if left == "" or left is None or right == "" or right is None:
        return {
            "status": "unavailable",
            "values": {EDITIONS[0]: left or "", EDITIONS[1]: right or ""},
            "reason": unavailable_reason or "edition-specific value is not present in the retained corpus",
        }
    return {
        "status": "unchanged" if left == right else "changed",
        "values": {EDITIONS[0]: left, EDITIONS[1]: right},
    }


def metadata_comparisons(song: dict[str, Any]) -> dict[str, dict[str, Any]]:
    metadata = song.get("metadataByBook") or {}
    left = metadata.get(EDITIONS[0], {})
    right = metadata.get(EDITIONS[1], {})
    result = {
        "title": compare_values(
            (song.get("titlesByBook") or {}).get(EDITIONS[0], ""),
            (song.get("titlesByBook") or {}).get(EDITIONS[1], ""),
            unavailable_reason="edition-specific title is not present",
        ),
        "keyMode": compare_values(
            left.get("keySignature", ""),
            right.get("keySignature", ""),
            unavailable_reason="one or both edition-specific source keys are unknown",
        ),
        "meter": compare_values(left.get("meter", ""), right.get("meter", "")),
        "timeSignature": compare_values(left.get("timeSignature", ""), right.get("timeSignature", "")),
    }
    text_keys = song.get("textKeysByBook") or {}
    result["lyrics"] = compare_values(
        text_keys.get(EDITIONS[0], ""),
        text_keys.get(EDITIONS[1], ""),
        unavailable_reason="the retained corpus has no edition-specific lyric alignment for this pair",
    )
    result["repeatEndings"] = {
        "status": "unavailable",
        "values": {EDITIONS[0]: "", EDITIONS[1]: ""},
        "reason": "repeat and ending semantics are not retained as edition-specific structured fields",
    }
    return result


def parts_comparison(witnesses: dict[str, dict[str, Any]]) -> dict[str, Any]:
    selected: dict[str, dict[str, Any] | None] = {}
    roles: dict[str, str] = {}
    for book in EDITIONS:
        selected[book] = None
        for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook"):
            candidate = witnesses.get(book, {}).get(field)
            if candidate:
                selected[book] = candidate
                roles[book] = candidate.get("role", "")
                break
    if not selected[EDITIONS[0]] or not selected[EDITIONS[1]]:
        return {
            "status": "unavailable",
            "roles": roles,
            "reason": "both editions do not have a structured witness to compare",
        }
    left_shape = [(part["name"], part["eventCount"], part["measureCount"]) for part in selected[EDITIONS[0]]["parts"]]
    right_shape = [(part["name"], part["eventCount"], part["measureCount"]) for part in selected[EDITIONS[1]]["parts"]]
    status = "unchanged" if left_shape == right_shape else "changed"
    if "alternate-reference" in roles.values() or "review-draft" in roles.values():
        status = "alternate-witness-only" if status == "unchanged" else "changed-alternate-witness"
    return {
        "status": status,
        "roles": roles,
        "values": {
            EDITIONS[0]: selected[EDITIONS[0]]["parts"],
            EDITIONS[1]: selected[EDITIONS[1]]["parts"],
        },
    }


def notation_comparison(witnesses: dict[str, dict[str, Any]]) -> dict[str, Any]:
    left = witnesses.get(EDITIONS[0], {}).get("scoreByBook")
    right = witnesses.get(EDITIONS[1], {}).get("scoreByBook")
    left_reference = left or witnesses.get(EDITIONS[0], {}).get("referenceScoreByBook")
    right_reference = right or witnesses.get(EDITIONS[1], {}).get("referenceScoreByBook")
    if not left_reference or not right_reference:
        return {
            "status": "unavailable",
            "reason": "both editions do not have structured notation witnesses",
            "roles": {
                EDITIONS[0]: left_reference.get("role", "") if left_reference else "",
                EDITIONS[1]: right_reference.get("role", "") if right_reference else "",
            },
        }
    same = left_reference.get("notationFingerprint") == right_reference.get("notationFingerprint")
    exact_both = left and right
    status = "unchanged" if same else "changed"
    if not exact_both:
        status = "alternate-witness-only" if same else "changed-alternate-witness"
    return {
        "status": status,
        "roles": {EDITIONS[0]: left_reference.get("role", ""), EDITIONS[1]: right_reference.get("role", "")},
        "notationFingerprints": {
            EDITIONS[0]: left_reference.get("notationFingerprint", ""),
            EDITIONS[1]: right_reference.get("notationFingerprint", ""),
        },
        "exactEditionWitnesses": bool(exact_both),
    }


def classifications(comparisons: dict[str, dict[str, Any]], sources: dict[str, dict[str, Any]], witnesses: dict[str, dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for field, comparison in comparisons.items():
        if comparison.get("status", "").startswith("changed"):
            result.append(f"{field}-difference")
    if any(comparison.get("status") == "alternate-witness-only" for comparison in comparisons.values()):
        result.append("alternate-edition-witness-only")
    if not (witnesses.get(EDITIONS[1], {}).get("scoreByBook")):
        result.append("sh2025-exact-score-unavailable")
    if sources[EDITIONS[0]].get("keyMode") == "unknown" or sources[EDITIONS[1]].get("keyMode") == "unknown":
        result.append("key-or-mode-unavailable")
    if not result:
        result.append("no-observed-difference")
    return sorted(set(result))


def build_record(song: dict[str, Any]) -> dict[str, Any]:
    sources = {book: source_summary(song, book) for book in EDITIONS}
    witnesses = {book: witness_summary(song, book) for book in EDITIONS}
    comparisons = metadata_comparisons(song)
    comparisons["parts"] = parts_comparison(witnesses)
    comparisons["notation"] = notation_comparison(witnesses)
    return {
        "relationId": f"sh-edition:{str(song.get('songNo', '')).lower()}",
        "identity": {
            "songId": song.get("id", ""),
            "songNo": song.get("songNo", ""),
            "title": song.get("title", ""),
            "titlesByBook": song.get("titlesByBook", {}),
        },
        "editions": sources,
        "witnesses": witnesses,
        "comparisons": comparisons,
        "classifications": classifications(comparisons, sources, witnesses),
        "promotion": {
            "safeToPromote": False,
            "policy": "This report compares editions; it never authorizes alternate-edition notation promotion.",
        },
    }


def main() -> int:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    shared = [song for song in corpus.get("songs", []) if set(EDITIONS).issubset(song.get("books", []))]
    records = sorted((build_record(song) for song in shared), key=lambda item: (str(item["identity"]["songNo"]).lower(), item["identity"]["songId"]))
    status_counts: dict[str, int] = {}
    classification_counts: dict[str, int] = {}
    for record in records:
        for field, comparison in record["comparisons"].items():
            key = f"{field}:{comparison.get('status', 'missing')}"
            status_counts[key] = status_counts.get(key, 0) + 1
        for label in record["classifications"]:
            classification_counts[label] = classification_counts.get(label, 0) + 1
    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "kind": "sacred-harp-shared-edition-reconciliation",
        "policy": "1991 and 2025 records remain edition-separated. Structured witnesses are evidence with explicit roles; an alternate witness never authorizes selected-edition promotion.",
        "source": {"corpus": "public/corpus.json", "editions": list(EDITIONS)},
        "summary": {
            "sharedPairs": len(records),
            "expectedBooks": list(EDITIONS),
            "statusCounts": dict(sorted(status_counts.items())),
            "classificationCounts": dict(sorted(classification_counts.items())),
            "safeToPromote": 0,
        },
        "records": records,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
