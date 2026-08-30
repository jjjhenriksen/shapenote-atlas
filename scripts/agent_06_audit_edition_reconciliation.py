#!/usr/bin/env python3
"""Audit SH1991/SH2025 reconciliation without changing shared public data.

The public shared-edition ledger is deliberately read-only input here.  This
agent-owned report makes two gaps explicit that the public ledger cannot safely
resolve on its own: text keys are not verse lyrics, and most SH2025 witnesses
are inherited SH1991 references.  Same-number records are reported as
mapping candidates only; they are never merged by this script.
"""

from __future__ import annotations

import ast
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "public" / "corpus.json"
LEDGER_PATH = ROOT / "public" / "shared-edition-reconciliation.json"
BUILD_DATA_PATH = ROOT / "scripts" / "build_data.py"
CHANGE_REGISTER_PATH = Path("/Users/jacquelinehenriksen/sh-corpus-scripts/changed_across_editions.csv")
OUTPUT_PATH = ROOT / "work" / "agent-06-editions" / "agent-06-edition-reconciliation.json"
EDITIONS = ("sh1991", "sh2025")
FIELDS = ("title", "keyMode", "meter", "timeSignature", "lyrics", "repeatEndings", "parts", "notation")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = text.replace("’", "'").replace("–", "-").replace("—", "-")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def key_mode(value: Any) -> str:
    match = re.search(r"\b(major|minor)\b", str(value or ""), re.IGNORECASE)
    return match.group(1).lower() if match else "unknown"


def compare(left: Any, right: Any, reason: str) -> dict[str, Any]:
    if left in (None, "") or right in (None, ""):
        return {
            "status": "unavailable",
            "values": {EDITIONS[0]: left or "", EDITIONS[1]: right or ""},
            "reason": reason,
        }
    return {
        "status": "unchanged" if left == right else "changed",
        "values": {EDITIONS[0]: left, EDITIONS[1]: right},
    }


def source_descriptor(song: dict[str, Any], edition: str) -> dict[str, Any]:
    metadata = (song.get("metadataByBook") or {}).get(edition, {}) or {}
    coverage = (song.get("sourceCoverageByBook") or {}).get(edition, {}) or {}
    return {
        "songNo": song.get("songNo", ""),
        "title": (song.get("titlesByBook") or {}).get(edition, song.get("title", "")),
        "sourceRecordKey": metadata.get("sourceRecordKey", coverage.get("sourceRecordKey", "")),
        "sourceUrl": metadata.get("sourceUrl", ""),
        "sourceUrls": metadata.get("sourceUrls", []),
        "sourceHashes": [coverage.get("manifestSourceSha256", "")] if coverage.get("manifestSourceSha256") else [],
        "keySignature": metadata.get("keySignature", ""),
        "keyMode": key_mode(metadata.get("keySignature", "")),
        "keyCandidate": metadata.get("keyCandidate", {}),
        "keyEvidence": metadata.get("keyEvidence", {"status": "unknown", "source": "not recorded"}),
        "meter": metadata.get("meter", ""),
        "timeSignature": metadata.get("timeSignature", ""),
        "composer": metadata.get("composer", ""),
        "lyricist": metadata.get("lyricist", ""),
        "coverageStatus": coverage.get("status", ""),
        "manifestSourceEdition": coverage.get("manifestSourceEdition", ""),
    }


def witness_descriptor(song: dict[str, Any], edition: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook"):
        asset = (song.get(field) or {}).get(edition)
        if not asset:
            continue
        provenance = asset.get("provenance", {}) or {}
        result[field] = {
            "scoreRef": asset.get("scoreRef", ""),
            "sourceUrl": asset.get("sourceUrl", ""),
            "sourceEdition": provenance.get("sourceEdition", edition if field == "scoreByBook" else ""),
            "sourceRecordKey": provenance.get("sourceRecordKey", ""),
            "kind": provenance.get("kind", ""),
            "assetSha256": asset.get("assetSha256", ""),
            "role": "exact-edition" if field == "scoreByBook" else ("alternate-reference" if field == "referenceScoreByBook" else "review-draft"),
        }
    return result


def literal_constant(name: str) -> Any:
    tree = ast.parse(BUILD_DATA_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError(f"constant not found: {name}")


def mapping_configuration() -> dict[str, Any]:
    metadata_aliases = literal_constant("METADATA_KEY_ALIASES")
    reference_aliases = literal_constant("CROSS_EDITION_SCORE_REFERENCES")
    explicit_relations = literal_constant("EXPLICIT_EDITION_RECONCILIATIONS")
    return {
        "metadataKeyAliases": [
            {"edition": edition, "from": source, "to": target}
            for edition, aliases in metadata_aliases.items()
            for source, target in aliases.items()
        ],
        "crossEditionReferenceAliases": [
            {"targetEdition": target[0], "targetRecord": target[1], "sourceEdition": source[0], "sourceRecord": source[1]}
            for target, source in reference_aliases.items()
        ],
        "explicitEditionRelations": [
            {"edition": key[0], "record": key[1], "relationId": value.get("relationId", ""), "status": value.get("status", "")}
            for key, value in explicit_relations.items()
        ],
    }


def load_change_register() -> list[dict[str, str]]:
    if not CHANGE_REGISTER_PATH.is_file():
        return []
    with CHANGE_REGISTER_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def record_for_slot(song: dict[str, Any], edition: str) -> dict[str, Any]:
    metadata = (song.get("metadataByBook") or {}).get(edition, {}) or {}
    return {
        "id": song.get("id", ""),
        "songNo": song.get("songNo", ""),
        "title": (song.get("titlesByBook") or {}).get(edition, song.get("title", "")),
        "textKey": (song.get("textKeysByBook") or {}).get(edition, ""),
        "sourceRecordKey": metadata.get("sourceRecordKey", ""),
    }


def mapping_audit(songs: list[dict[str, Any]]) -> dict[str, Any]:
    sh_records: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for song in songs:
        if song.get("bookFamily") != "sh":
            continue
        for edition in EDITIONS:
            if edition in song.get("books", []):
                descriptor = record_for_slot(song, edition)
                sh_records[descriptor["songNo"].lower()][edition].append(descriptor)

    shared = [song for song in songs if set(EDITIONS).issubset(song.get("books", []))]
    shared_by_no = {str(song.get("songNo", "")).lower(): song for song in shared}
    rows = load_change_register()
    by_slot: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_slot[row.get("song_no", "").lower()].append(row)

    candidates: list[dict[str, Any]] = []
    for slot, slot_rows in sorted(by_slot.items()):
        editions = {row.get("book_id") for row in slot_rows}
        if editions != set(EDITIONS) or len(slot_rows) != 2:
            continue
        left = next(row for row in slot_rows if row["book_id"] == EDITIONS[0])
        right = next(row for row in slot_rows if row["book_id"] == EDITIONS[1])
        title_exact = normalize(left.get("title")) == normalize(right.get("title"))
        text_exact = normalize(left.get("text_key")) == normalize(right.get("text_key"))
        if slot in shared_by_no:
            status = "covered-by-canonical-shared-record"
        elif title_exact:
            status = "unmapped-same-title-candidate"
        else:
            status = "unmapped-replacement-candidate"
        candidates.append({
            "slot": slot,
            "status": status,
            "safeToPair": False,
            "titleExactAfterNormalization": title_exact,
            "textKeyExactAfterNormalization": text_exact,
            "sourceRows": {EDITIONS[0]: left, EDITIONS[1]: right},
            "corpusRecords": {edition: sh_records.get(slot, {}).get(edition, []) for edition in EDITIONS},
        })

    unmerged: list[dict[str, Any]] = []
    for slot in sorted(set(sh_records)):
        if slot in shared_by_no:
            continue
        if not all(sh_records[slot].get(edition) for edition in EDITIONS):
            continue
        unmerged.append({
            "slot": slot,
            "safeToPair": False,
            "reason": "same numeric slot has separate edition records; title/text/setting identity is not assumed",
            "records": {edition: sh_records[slot][edition] for edition in EDITIONS},
        })

    unpaired_rows = [
        {"slot": slot, "rows": slot_rows, "safeToPair": False, "reason": "change register does not contain one row for each edition"}
        for slot, slot_rows in sorted(by_slot.items())
        if not ({row.get("book_id") for row in slot_rows} == set(EDITIONS) and len(slot_rows) == 2)
    ]
    return {
        "canonicalSharedPairs": len(shared),
        "canonicalSharedSongNumbers": sorted(shared_by_no),
        "changeRegisterRows": len(rows),
        "changeRegisterPairSlots": len(candidates),
        "changeRegisterPairSlotsCoveredByCanonical": sum(c["status"] == "covered-by-canonical-shared-record" for c in candidates),
        "changeRegisterPairSlotsUnmapped": sum(c["status"] != "covered-by-canonical-shared-record" for c in candidates),
        "sameSlotCandidates": candidates,
        "sameNumberUnmerged": unmerged,
        "unpairedChangeRows": unpaired_rows,
        "configuration": mapping_configuration(),
    }


def pair_audit(song: dict[str, Any], ledger_by_key: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    source = {edition: source_descriptor(song, edition) for edition in EDITIONS}
    witnesses = {edition: witness_descriptor(song, edition) for edition in EDITIONS}
    text_keys = song.get("textKeysByBook") or {}
    metadata = song.get("metadataByBook") or {}
    left, right = metadata.get(EDITIONS[0], {}) or {}, metadata.get(EDITIONS[1], {}) or {}
    existing = ledger_by_key.get((str(song.get("songNo", "")).lower(), song.get("id", "")), {})
    existing_comparisons = existing.get("comparisons", {}) or {}
    lyrics = compare(text_keys.get(EDITIONS[0], ""), text_keys.get(EDITIONS[1], ""), "no edition-specific text key is retained")
    if lyrics["status"] == "unchanged":
        lyrics["semanticStatus"] = "text-key-same-no-verse-proof"
        lyrics["reason"] = "matching text keys identify a text family only; verse lyrics and alignment are not retained"
    elif lyrics["status"] == "changed":
        lyrics["semanticStatus"] = "text-key-changed"
        lyrics["reason"] = "text-key difference is evidence of a first-line/text-family difference, not a complete verse diff"
    else:
        lyrics["semanticStatus"] = "unavailable-no-text-key"

    comparisons = {
        "title": compare(source[EDITIONS[0]]["title"], source[EDITIONS[1]]["title"], "edition-specific title is not present"),
        "keyMode": compare(left.get("keySignature", ""), right.get("keySignature", ""), "one or both edition-specific source keys are unknown"),
        "meter": compare(left.get("meter", ""), right.get("meter", ""), "one or both edition-specific meters are unavailable"),
        "timeSignature": compare(left.get("timeSignature", ""), right.get("timeSignature", ""), "one or both edition-specific time signatures are unavailable"),
        "lyrics": lyrics,
        "repeatEndings": {
            "status": "unavailable",
            "values": {edition: "" for edition in EDITIONS},
            "reason": "repeat bars, numbered endings, and volta semantics are not retained as structured edition-specific fields",
        },
        "parts": existing_comparisons.get("parts", {"status": "unavailable", "reason": "no retained structured witnesses"}),
        "notation": existing_comparisons.get("notation", {"status": "unavailable", "reason": "no retained structured witnesses"}),
    }
    return {
        "pairId": f"sh-edition:{str(song.get('songNo', '')).lower()}",
        "songId": song.get("id", ""),
        "editions": source,
        "witnesses": witnesses,
        "comparisons": comparisons,
        "safeToPromote": False,
        "promotionReason": "reconciliation evidence does not authorize alternate-edition notation promotion",
    }


def build_audit() -> dict[str, Any]:
    corpus = load_json(CORPUS_PATH)
    ledger = load_json(LEDGER_PATH)
    songs = corpus.get("songs", [])
    shared = [song for song in songs if set(EDITIONS).issubset(song.get("books", []))]
    ledger_by_key = {
        (str(record.get("identity", {}).get("songNo", "")).lower(), record.get("identity", {}).get("songId", "")): record
        for record in ledger.get("records", [])
    }
    pairs = sorted((pair_audit(song, ledger_by_key) for song in shared), key=lambda pair: (pair["pairId"], pair["songId"]))
    field_status: dict[str, Counter[str]] = {field: Counter(pair["comparisons"][field].get("status", "missing") for pair in pairs) for field in FIELDS}
    source_key_evidence = Counter(pair["editions"][edition]["keyEvidence"].get("status", "missing") for pair in pairs for edition in EDITIONS)
    reference_provenance = Counter(
        pair["witnesses"]["sh2025"]["referenceScoreByBook"].get("sourceEdition", "missing")
        for pair in pairs
        if "referenceScoreByBook" in pair["witnesses"]["sh2025"]
    )
    exact_2025 = sum("scoreByBook" in pair["witnesses"]["sh2025"] for pair in pairs)
    draft_2025 = sum("draftScoreByBook" in pair["witnesses"]["sh2025"] for pair in pairs)
    reference_2025 = sum("referenceScoreByBook" in pair["witnesses"]["sh2025"] for pair in pairs)
    missing_exact_2025 = len(pairs) - exact_2025
    report = {
        "kind": "agent-06-sacred-harp-edition-reconciliation-audit",
        "source": {
            "corpus": "public/corpus.json",
            "existingLedger": "public/shared-edition-reconciliation.json",
            "changeRegister": str(CHANGE_REGISTER_PATH),
            "sourceGeneratedAt": corpus.get("generatedAt", ""),
            "existingLedgerGeneratedAt": ledger.get("generatedAt", ""),
            "existingLedgerGenerationDiffers": ledger.get("generatedAt", "") != corpus.get("generatedAt", ""),
        },
        "policy": "1991 and 2025 remain edition-separated. Same-number, same-title, shared-text, alternate-score, and visual similarities are evidence only; unavailable exact music remains unavailable.",
        "summary": {
            "canonicalSharedPairs": len(pairs),
            "pairIdsUnique": len({pair["pairId"] for pair in pairs}) == len(pairs),
            "fieldStatusCounts": {field: dict(sorted(counts.items())) for field, counts in field_status.items()},
            "sourceKeyEvidenceCounts": dict(sorted(source_key_evidence.items())),
            "keyMode": {
                "exactMetadataComparablePairs": sum(
                    all(pair["editions"][edition]["keySignature"] for edition in EDITIONS) for pair in pairs
                ),
                "exactMetadataUnavailablePairs": sum(
                    not all(pair["editions"][edition]["keySignature"] for edition in EDITIONS) for pair in pairs
                ),
                "sh2025SecondaryCandidates": sum(bool(pair["editions"]["sh2025"]["keyCandidate"]) for pair in pairs),
                "existingLedgerChangedCandidates": [
                    {
                        "pairId": record.get("relationId", ""),
                        "values": record.get("comparisons", {}).get("keyMode", {}).get("values", {}),
                        "status": "retained-as-unverified-candidate",
                    }
                    for record in ledger.get("records", [])
                    if record.get("comparisons", {}).get("keyMode", {}).get("status") == "changed"
                ],
            },
            "sh2025Witnesses": {
                "exactEditionScores": exact_2025,
                "alternateReferenceScores": reference_2025,
                "reviewDrafts": draft_2025,
                "exactScoreUnavailable": missing_exact_2025,
            },
            "referenceProvenance": dict(sorted(reference_provenance.items())),
            "lyrics": {
                "textKeySame": field_status["lyrics"]["unchanged"],
                "textKeyChanged": field_status["lyrics"]["changed"],
                "noTextKey": field_status["lyrics"]["unavailable"],
                "verseLevelEvidence": "unavailable",
            },
            "repeatEndings": {
                "structuredComparisons": field_status["repeatEndings"].get("changed", 0) + field_status["repeatEndings"].get("unchanged", 0),
                "unavailable": field_status["repeatEndings"].get("unavailable", 0),
            },
            "safeToPromote": 0,
        },
        "mappingAudit": mapping_audit(songs),
        "pairs": pairs,
    }
    return report


def main() -> int:
    report = build_audit()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
