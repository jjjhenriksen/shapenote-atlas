#!/usr/bin/env python3
"""Record fail-closed key/mode outcomes for every unknown score asset."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public" / "corpus.json"
OUTPUT = ROOT / "public" / "key-mode-reconciliation.json"
AUDIT_ROOT = ROOT / "work" / "source-transcriptions" / "2025"
OBSERVATIONS = ROOT / "public" / "source-metadata-observations.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_audits() -> dict[str, dict]:
    result = {}
    for path in AUDIT_ROOT.glob("*.audit.json"):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        record = str(audit.get("record", "")).lower()
        if record:
            result[record] = audit
    return result


def load_observations() -> dict[str, dict]:
    try:
        payload = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        str(item.get("queueId", "")).lower(): item
        for item in payload.get("records", [])
        if item.get("queueId")
    }


def declaration_summary(asset: dict) -> dict:
    declarations = asset.get("musicXmlKeyDeclarations") or []
    fifths = sorted({str(item.get("fifths", "")) for item in declarations if item.get("fifths", "")})
    modes = sorted({str(item.get("mode", "")) for item in declarations if item.get("mode", "")})
    return {
        "declarationCount": len(declarations),
        "fifths": fifths,
        "modes": modes,
        "modePresent": any(item.get("modePresent") is True for item in declarations),
    }


def blocker(book_id: str, song_no: str, field: str, asset: dict, metadata: dict, audit: dict | None) -> tuple[str, str]:
    candidate = metadata.get("keyCandidate") or {}
    declarations = declaration_summary(asset)
    if candidate:
        return (
            "secondary-cross-edition-candidate",
            f"{book_id}/{song_no} has only the non-authoritative secondary key candidate "
            f"{candidate.get('value', '')!r}; it is inherited from another edition and "
            "cannot establish this edition's major/minor mode.",
        )
    if audit and audit.get("sourceKey"):
        return (
            "source-audit-not-attached-to-asset",
            f"{book_id}/{song_no} has a source-audit key {audit['sourceKey']!r}, but this "
            "asset remains unknown because the audit does not prove this structured "
            "asset's complete notation identity.",
        )
    if field == "draftScoreByBook":
        return (
            "omr-draft-without-authoritative-key",
            f"{book_id}/{song_no} is an OMR draft without source-authoritative key/mode "
            "evidence; OMR output cannot supply it autonomously.",
        )
    if declarations["fifths"] and not declarations["modePresent"]:
        return (
            "raw-fifths-without-mode",
            f"{book_id}/{song_no} preserves raw MusicXML fifths "
            f"{declarations['fifths']!r} but the source omits <mode>; fifths alone do not "
            "distinguish major from minor.",
        )
    return (
        "raw-musicxml-without-key",
        f"{book_id}/{song_no} has pitch-bearing structured notation but no usable "
        "source-encoded key/mode declaration.",
    )


def external_source_evidence(
    category: str,
    book_id: str,
    song_no: str,
    field: str,
    source_urls: list[str],
) -> dict:
    """Describe the evidence still required without relabeling uncertainty as a task blocker."""
    missing_by_category = {
        "secondary-cross-edition-candidate": [
            "An authoritative key and mode printed for this edition's engraving/setting; the inherited cross-edition candidate is insufficient."
        ],
        "omr-draft-without-authoritative-key": [
            "A source-authoritative key and mode witness for the draft's complete notation identity; OMR output is not authoritative."
        ],
        "raw-fifths-without-mode": [
            "An authoritative source that explicitly supplies the omitted major/minor mode; raw MusicXML fifths alone are insufficient."
        ],
        "raw-musicxml-without-key": [
            "An authoritative source that explicitly supplies both key and major/minor mode for this edition."
        ],
    }
    return {
        "status": "external-source-blocked",
        "reason": (
            f"Local structured-score, source-audit, and retained-observation checks are exhausted for "
            f"{book_id}/{song_no} ({field}); no source-authoritative key/mode evidence is present."
        ),
        "missingEvidence": missing_by_category.get(category, [
            "A source-authoritative key and major/minor mode witness."
        ]),
        "sourceUrls": source_urls,
    }


def main() -> int:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    audits = load_audits()
    observations = load_observations()
    records = []
    resolved_missing_mode = []
    seen = set()

    for song in corpus.get("songs", []):
        for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook"):
            for book_id, preview in (song.get(field) or {}).items():
                score_ref = preview.get("scoreRef", "")
                if not score_ref or score_ref in seen:
                    continue
                seen.add(score_ref)
                score_path = ROOT / "public" / score_ref.lstrip("/")
                if not score_path.exists():
                    continue
                asset = json.loads(score_path.read_text(encoding="utf-8"))
                declarations = declaration_summary(asset)
                if (
                    (asset.get("keyEvidence") or {}).get("status") == "source-verified"
                    and declarations["declarationCount"]
                    and not declarations["modePresent"]
                ):
                    resolved_missing_mode.append(
                        {
                            "bookId": book_id,
                            "songNo": str(song.get("songNo", "")),
                            "title": song.get("title", ""),
                            "assetField": field,
                            "scoreRef": score_ref,
                            "keySignature": asset.get("keySignature", ""),
                            "keyEvidence": asset.get("keyEvidence", {}),
                            "rawMusicXml": declarations,
                            "safeToPromote": field != "draftScoreByBook",
                        }
                    )
                if (asset.get("keyEvidence") or {}).get("status") != "unknown":
                    continue
                song_no = str(song.get("songNo", ""))
                metadata = (song.get("metadataByBook") or {}).get(book_id, {}) or {}
                audit = audits.get(f"{book_id}/{song_no}".lower())
                category, reason = blocker(book_id, song_no, field, asset, metadata, audit)
                observation = observations.get(f"{book_id}/{song_no}".lower())
                source_urls = list(dict.fromkeys(
                    url for url in [
                        asset.get("sourceUrl", ""),
                        metadata.get("sourceUrl", ""),
                        *(metadata.get("sourceUrls") or []),
                        (f"https://fasola.org/indexes/2025/?p={song_no}" if book_id == "sh2025" else ""),
                        (
                            f"https://ccel.org/ccel/walker/harmony/harmony.H{song_no}.html"
                            if book_id == "southernharmony" else ""
                        ),
                    ] if url
                ))
                records.append(
                    {
                        "queueId": f"{book_id}/{song_no}",
                        "songId": song.get("id", ""),
                        "bookId": book_id,
                        "songNo": song_no,
                        "title": song.get("title", ""),
                        "assetField": field,
                        "scoreRef": score_ref,
                        "scoreAssetSha256": sha256(score_path),
                        "sourceUrl": asset.get("sourceUrl", ""),
                        "keySignature": "",
                        "keyEvidence": asset.get("keyEvidence", {"status": "unknown"}),
                        "rawMusicXml": declaration_summary(asset),
                        "secondaryKeyCandidate": metadata.get("keyCandidate"),
                        "sourceAudit": {
                            "present": bool(audit),
                            "sourceKey": audit.get("sourceKey", "") if audit else "",
                            "status": audit.get("status", "") if audit else "",
                        },
                        "sourceObservation": {
                            "present": bool(observation),
                            "status": (observation or {}).get("observations", {}).get("key", {}).get("status", ""),
                            "value": (observation or {}).get("observations", {}).get("key", {}).get("value", ""),
                            "safeToPromote": False,
                        },
                        "outcome": "external-source-blocked",
                        "safeToPromote": False,
                        "humanReviewRequired": False,
                        "blockerCategory": category,
                        "blocker": reason,
                        "externalSourceEvidence": external_source_evidence(
                            category, book_id, song_no, field, source_urls
                        ),
                    }
                )

    records.sort(key=lambda item: (item["bookId"], int("".join(c for c in item["songNo"] if c.isdigit()) or 0), item["songNo"], item["scoreRef"]))
    by_book = Counter(item["bookId"] for item in records)
    by_category = Counter(item["blockerCategory"] for item in records)
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "kind": "sacred-harp-key-mode-reconciliation",
        "version": 2,
        "authority": {
            "scope": "Every unique pitch-bearing score/reference/draft asset whose keyEvidence is unknown",
            "policy": "Only direct edition/source evidence can resolve key and mode. Missing MusicXML mode is never treated as major; OMR and secondary-edition values remain non-authoritative.",
        },
        "inputs": [{"path": "public/corpus.json", "sha256": sha256(CORPUS)}],
        "summary": {
            "unknownAssets": len(records),
            "autonomouslyBlocked": 0,
            "externalSourceBlocked": len(records),
            "safeToPromote": 0,
            "humanReviewRequired": 0,
            "recordsStillWithoutAutonomousDisposition": 0,
            "resolvedMissingModeAssets": len(resolved_missing_mode),
            "resolvedMissingModeByBook": dict(sorted(Counter(item["bookId"] for item in resolved_missing_mode).items())),
            "rawFifthsConflicts": sum(
                1 for item in resolved_missing_mode if (item.get("keyEvidence") or {}).get("rawFifthsConflict")
            ),
            "byBook": dict(sorted(by_book.items())),
            "byBlockerCategory": dict(sorted(by_category.items())),
        },
        "resolvedMissingMode": resolved_missing_mode,
        "records": records,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
