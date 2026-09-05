#!/usr/bin/env python3
"""Audit conservative equivalence of the 1991/2025 meter labels.

This is a candidate-only report. It preserves raw labels and source URLs,
never changes canonical data, and does not infer syllable counts from lyrics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "public" / "shared-edition-reconciliation.json"
PRIOR_OUTPUT_JSON = ROOT / "work" / "luna-program-20260904" / "health" / "meter-label-audit.json"
OUTPUT_JSON = ROOT / "work" / "luna-program-20260904" / "health" / "meter-label-audit-v3.json"
OUTPUT_MD = ROOT / "work" / "luna-program-20260904" / "health" / "meter-label-audit-v3.md"
EDITIONS = ("sh1991", "sh2025")
CLASSIFICATIONS = ("formatting-equivalent", "potentially-substantive", "unknown")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path: Path, content: str) -> None:
    """Write a new artifact, refusing to overwrite a different existing file."""

    encoded = content.encode("utf-8")
    if path.exists():
        if path.read_bytes() == encoded:
            return
        raise FileExistsError(f"refusing to overwrite existing audit artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)


def _numbers(value: str) -> tuple[int, ...] | None:
    # Numeric meter sequences are bounded lists, not arbitrary digit extraction.
    # Do not turn ranges, time signatures, or prose into syllable counts.
    if not re.fullmatch(r"\s*\d+(?:\s*[,.;]\s*\d+)*\s*", value):
        return None
    return tuple(int(item) for item in re.findall(r"\d+", value))


def _explicit_sequence(value: str) -> tuple[int, ...] | None:
    parenthesized = re.search(r"\(([^)]*)\)", value)
    if parenthesized:
        return _numbers(parenthesized.group(1))
    if _numbers(value):
        return _numbers(value)
    after_colon = value.split(":", 1)[1] if ":" in value else ""
    if after_colon and re.fullmatch(r"[\s\d,.;&-]+", after_colon.strip()):
        return _numbers(after_colon)
    return None


def _semantic_bucket(value: str) -> str:
    raw = value.lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", raw).strip()
    if "prose" in lowered and "irregular" not in lowered:
        return "prose"
    if "irregular" in lowered or "no meter" in lowered:
        return "irregular"
    if "common particular" in lowered:
        return "common-particular"
    if "short particular" in lowered:
        return "short-particular"
    if "hallelujah" in lowered:
        return "hallelujah"
    for name in ("common", "long", "short"):
        if name in lowered and "meter" in lowered:
            return f"half-{name}" if "half" in lowered else f"double-{name}" if "double" in lowered else name
    if re.search(r"\bc\s*\.?\s*m\.?\b", raw):
        return "half-common" if "half" in lowered else "double-common" if "double" in lowered else "common"
    if re.search(r"\bl\s*\.?\s*m\.?\b", raw):
        return "half-long" if "half" in lowered else "double-long" if "double" in lowered else "long"
    if re.search(r"\bs\s*\.?\s*m\.?\b", raw):
        return "half-short" if "half" in lowered else "double-short" if "double" in lowered else "short"
    if "double" in lowered or re.search(r"\bd\.?\b", lowered):
        return "double"
    if "half" in lowered:
        return "half"
    return "particular" if "particular" in lowered else "unclassified"


def _standard_sequence(value: str) -> tuple[int, ...] | None:
    lowered = value.lower()
    if "double" in lowered or "half" in lowered:
        return None
    if "common particular" in lowered:
        return (8, 8, 6, 8, 8, 6)
    if "common meter" in lowered or re.search(r"\bc\.?m\.?\b", lowered):
        return (8, 6, 8, 6)
    if "long meter" in lowered or re.search(r"\bl\.?m\.?\b", lowered):
        return (8, 8, 8, 8)
    if "short meter" in lowered or re.search(r"\bs\.?m\.?\b", lowered):
        return (6, 6, 8, 6)
    return None


def _shorthand_sequences(value: str) -> set[tuple[int, ...]]:
    lowered = value.lower()
    tokens = [int(item) for item in re.findall(r"(\d+)\s*s\b", lowered)]
    if not tokens:
        return set()
    double = "double" in lowered or bool(re.search(r"\bd\s*\.?\s*$", lowered))
    line_count_match = re.search(r"(\d+)\s+lines?\b", lowered)
    if line_count_match:
        line_count = int(line_count_match.group(1))
        if line_count % len(tokens) == 0:
            return {tuple(tokens * (line_count // len(tokens)))}
    # Without a line count, only established one- and two-token forms are safe.
    if len(tokens) > 2:
        return set()
    repeats = 8 if double and len(tokens) == 1 else 4 if double else 4 if len(tokens) == 1 else 2
    return {tuple(tokens * repeats)}


def _has_double(value: str) -> bool:
    lowered = value.lower()
    return "double" in lowered or bool(re.search(r"\bd\s*\.?\s*$", lowered))


def _has_half(value: str) -> bool:
    return "half" in value.lower()


def meter_candidates(value: str) -> set[tuple[int, ...]]:
    """Return only established-label or explicit-sequence candidates."""

    value = str(value or "").strip()
    if not value:
        return set()
    candidates: set[tuple[int, ...]] = set()
    explicit = _explicit_sequence(value)
    if explicit:
        # An explicit bounded sequence is authoritative; do not union it with
        # a default four-line shorthand expansion.
        return {explicit}
    standard = _standard_sequence(value)
    if standard and not explicit:
        candidates.add(standard)
    candidates.update(_shorthand_sequences(value))
    return candidates


def classify_meter(left: str, right: str) -> dict[str, Any]:
    """Classify labels without treating a missing sequence as agreement."""

    left = str(left or "").strip()
    right = str(right or "").strip()
    if not left or not right:
        return {"classification": "unknown", "reason": "empty meter label is unavailable", "normalizedSequences": {"sh1991": [], "sh2025": []}}
    if left == right:
        candidates = meter_candidates(left)
        return {"classification": "formatting-equivalent", "reason": "raw labels are identical", "normalizedSequences": [list(x) for x in sorted(candidates)]}
    # Iambic and other descriptive qualifiers are not discarded merely because
    # the syllable sequence happens to match an abbreviated label.
    if "iambic" in left.lower() or "iambic" in right.lower():
        return {"classification": "potentially-substantive", "reason": "unmodeled descriptive qualifier is present", "normalizedSequences": {"sh1991": [list(x) for x in sorted(meter_candidates(left))], "sh2025": [list(x) for x in sorted(meter_candidates(right))]}}
    if _has_double(left) != _has_double(right) or _has_half(left) != _has_half(right):
        return {"classification": "potentially-substantive", "reason": "Double/Half modifier is present on only one label", "normalizedSequences": {"sh1991": [list(x) for x in sorted(meter_candidates(left))], "sh2025": [list(x) for x in sorted(meter_candidates(right))]}}
    left_candidates = meter_candidates(left)
    right_candidates = meter_candidates(right)
    if left_candidates & right_candidates:
        return {"classification": "formatting-equivalent", "reason": "explicit or established shorthand sequences agree", "normalizedSequences": [list(x) for x in sorted(left_candidates & right_candidates)]}
    left_bucket = _semantic_bucket(left)
    right_bucket = _semantic_bucket(right)
    if left_candidates and right_candidates:
        return {"classification": "potentially-substantive", "reason": "available sequences do not agree", "normalizedSequences": {"sh1991": [list(x) for x in sorted(left_candidates)], "sh2025": [list(x) for x in sorted(right_candidates)]}}
    if left_bucket != "unclassified" and right_bucket != "unclassified" and left_bucket != right_bucket:
        return {"classification": "potentially-substantive", "reason": "established semantic labels conflict without a shared sequence", "normalizedSequences": {"sh1991": [list(x) for x in sorted(left_candidates)], "sh2025": [list(x) for x in sorted(right_candidates)]}}
    return {"classification": "unknown", "reason": "one or both labels lack a safely comparable sequence", "normalizedSequences": {"sh1991": [list(x) for x in sorted(left_candidates)], "sh2025": [list(x) for x in sorted(right_candidates)]}}


def _source_urls(edition: dict[str, Any]) -> list[str]:
    values = list(edition.get("sourceUrls") or [])
    values.extend(item for item in (edition.get("sourceUrl"), edition.get("manifestSourceUrl")) if item)
    return list(dict.fromkeys(values))


def build_audit(report: dict[str, Any], input_path: Path = INPUT, prior_path: Path = PRIOR_OUTPUT_JSON, version: str = "2026-09-04.audit-v3") -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for record in report.get("records", []):
        comparison = record.get("comparisons", {}).get("meter", {})
        if comparison.get("status") != "changed":
            continue
        editions = record.get("editions", {})
        raw = {book: editions.get(book, {}).get("meter", "") for book in EDITIONS}
        assessment = classify_meter(raw["sh1991"], raw["sh2025"])
        records.append({
            "relationId": record.get("relationId", ""),
            "songId": record.get("identity", {}).get("songId", ""),
            "songNo": record.get("identity", {}).get("songNo", ""),
            "title": record.get("identity", {}).get("title", ""),
            "rawLabels": raw,
            "sourceUrls": {book: _source_urls(editions.get(book, {})) for book in EDITIONS},
            "sourceEvidence": {book: {"confidence": editions.get(book, {}).get("confidence", ""), "coverageStatus": editions.get(book, {}).get("coverageStatus", ""), "sourceUrlPresent": bool(editions.get(book, {}).get("sourceUrl"))} for book in EDITIONS},
            "classification": assessment["classification"],
            "reason": assessment["reason"],
            "normalizedSequences": assessment["normalizedSequences"],
            "action": "candidate-only; verify both edition sources before any correction or promotion",
        })
    counts = {classification: sum(item["classification"] == classification for item in records) for classification in CLASSIFICATIONS}
    prior_relative = str(prior_path.relative_to(ROOT)) if prior_path.is_relative_to(ROOT) else str(prior_path)
    prior = {"path": prior_relative, "exists": prior_path.is_file()}
    if prior_path.is_file():
        prior.update({"bytes": prior_path.stat().st_size, "sha256": sha256(prior_path)})
    return {
        "kind": "luna-meter-label-audit",
        "version": version,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "policy": {"inputStatus": "current generated reconciliation; candidate audit only", "rawLabelsPreserved": True, "lyricsNotUsed": True, "noPromotion": True, "normalization": "Only explicit sequences and established C.M./L.M./S.M./C.P.M./shorthand-D forms are compared; missing or conflicting structure fails closed."},
        "source": {"path": str(input_path.relative_to(ROOT)), "sha256": sha256(input_path), "sharedPairs": report.get("summary", {}).get("sharedPairs"), "inputMeterChanged": report.get("summary", {}).get("statusCounts", {}).get("meter:changed")},
        "priorAudit": prior,
        "summary": {"records": len(records), "byClassification": counts, "safeToPromote": 0},
        "records": records,
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = ["# Meter-label audit", "", "Candidate-only comparison of the 156 current meter differences. Raw labels and source URLs are preserved in the JSON report; no canonical value is changed.", "", "## Summary", "", f"- Records: **{audit['summary']['records']}**", f"- Formatting-equivalent candidates: **{audit['summary']['byClassification']['formatting-equivalent']}**", f"- Potentially substantive: **{audit['summary']['byClassification']['potentially-substantive']}**", f"- Unknown: **{audit['summary']['byClassification']['unknown']}**", "- Safe to promote: **0**", "", "## Guardrails", "", "- Do not infer verse lengths from lyrics.", "- Do not normalize `Double`/`Half`, irregular/prose, or missing particular sequences into one another.", "- Verify every candidate against both edition sources before correction or promotion.", "", "## Record index", ""]
    for item in audit["records"]:
        lines.append(f"- `{item['relationId']}` / {item['songNo']} — **{item['classification']}** — `{item['rawLabels']['sh1991']}` ⇄ `{item['rawLabels']['sh2025']}`")
    lines.extend(["", "## Source", "", f"- `{audit['source']['path']}` — SHA-256 `{audit['source']['sha256']}`", "- Full raw labels, source URLs, evidence metadata, normalized sequence candidates, and reasons are in the companion JSON report."])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output-json", type=Path, default=OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=OUTPUT_MD)
    parser.add_argument("--prior-audit", type=Path, default=PRIOR_OUTPUT_JSON)
    parser.add_argument("--version", default="2026-09-04.audit-v3")
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    audit = build_audit(report, args.input, args.prior_audit, args.version)
    write_once(args.output_json, json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    write_once(args.output_md, render_markdown(audit))
    print(json.dumps({"records": len(audit["records"]), "byClassification": audit["summary"]["byClassification"], "safeToPromote": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
