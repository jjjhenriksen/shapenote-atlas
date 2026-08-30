#!/usr/bin/env python3
"""Reconcile key evidence for SH2025 referenceScoreByBook witnesses.

Reference scores are deliberately kept separate from exact 2025 notation. A
printed key from a linked 2025 scan is recorded as a source observation, but it
is never used to promote or relabel an alternate structured witness without an
edition-matched score comparison.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public" / "corpus.json"
OUTPUT = ROOT / "public" / "sh2025-reference-key-reconciliation.json"

# These are direct observations from the immutable linked scan images. Their
# bytes were fetched and hash-pinned during this audit; the images are not
# copied into the repository or used as generated notation.
SOURCE_SCAN_OBSERVATIONS = {
    "77t": {
        "keySignature": "A minor",
        "mode": "minor",
        "url": "https://sacredharpbremen.org/wp-content/uploads/songs/001-099/077t-The-Child-of-Grace/77t.jpg",
        "sha256": "f884e0d491cbda5a8595e2531de17850c690ef74d3edd391cad69602bedde063",
        "observation": "The page header visibly prints A Minor.",
    },
    "313b": {
        "keySignature": "A minor",
        "mode": "minor",
        "url": "https://sacredharpbremen.org/wp-content/uploads/songs/300-399/313b-Cobb/313b-Cobb.jpg",
        "sha256": "dae49ed2f3b60a64452b4f7650e524e910433066f2650670375f73181fa913b3",
        "observation": "The page header visibly prints A Minor.",
    },
    "445": {
        "keySignature": "C major",
        "mode": "major",
        "url": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/445-Passing-Away/445.jpg",
        "sha256": "41c25d252f871a5e91ff8e31b536a35dd657d831dc131060bee5e6433604800b",
        "observation": "The page header visibly prints C Major.",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pitched_events(score: dict) -> int:
    return sum(
        1
        for part in score.get("parts", [])
        for event in part.get("events", [])
        if event.get("step") or event.get("pitch")
    )


def song_rows(corpus: dict) -> list[tuple[dict, dict, Path, dict]]:
    rows = []
    for song in corpus.get("songs", []):
        reference = song.get("referenceScoreByBook", {}).get("sh2025")
        if not reference or reference.get("keyEvidence", {}).get("status") != "unknown":
            continue
        score_ref = reference.get("scoreRef", "")
        score_path = ROOT / "public" / score_ref.lstrip("/")
        if not score_path.exists():
            continue
        score_asset = json.loads(score_path.read_text())
        if pitched_events(score_asset):
            rows.append((song, reference, score_path, score_asset))
    return rows


def main() -> None:
    corpus = json.loads(CORPUS.read_text())
    records = []
    linked_mxl_urls = set()
    scan_count = 0

    for song, reference, score_path, score_asset in song_rows(corpus):
        song_no = song["songNo"]
        metadata = song.get("metadataByBook", {}).get("sh2025", {})
        mxl_url = reference.get("sourceUrl", "")
        if "musicxml/" in mxl_url:
            linked_mxl_urls.add(mxl_url)
        scan = SOURCE_SCAN_OBSERVATIONS.get(song_no)
        if scan:
            scan_count += 1
            outcome = "source-key-verified-reference-only"
            key_signature = scan["keySignature"]
            mode = scan["mode"]
            blocker = (
                f"The linked SH2025 scan directly observes {key_signature}, but this "
                "structured reference is provenance-labeled as an alternate/other-edition "
                "witness. The key observation is retained separately; no edition-matched "
                "notation identity was proven, so it is not applied to referenceScoreByBook "
                "and cannot promote the witness as exact 2025 notation."
            )
        else:
            outcome = "external-source-blocked"
            key_signature = ""
            mode = ""
            blocker = (
                "External source evidence is required: the local pitch-bearing "
                "reference asset and its exact linked MusicXML witness provide no key "
                "element, and no direct printed key/mode evidence is available from the "
                "linked source inputs checked for this record. No key is inferred from "
                "pitch spelling, fifths, filenames, or another edition."
            )

        record = {
            "queueId": f"sh2025/{song_no}",
            "songNo": song_no,
            "title": song.get("title", ""),
            "outcome": outcome,
            "safeToPromote": False,
            "humanReviewRequired": False,
            "referenceWitnessKeyApplied": False,
            "keySignature": key_signature,
            "mode": mode,
            "referenceScoreRef": reference.get("scoreRef", ""),
            "referenceScoreAssetSha256": sha256(score_path),
            "referenceProvenance": reference.get("provenance", {}),
            "sourceUrls": metadata.get("sourceUrls", []),
            "auditedEvidence": {
                "localStructuredAsset": {
                    "keyEvidence": score_asset.get("keyEvidence", {}),
                    "keyElementPresent": False,
                    "pitchedEventCount": pitched_events(score_asset),
                },
                "exactLinkedMusicXml": {
                    "url": mxl_url,
                    "directFetchStatus": "http-200-valid-musicxml",
                    "keyElementPresent": False,
                },
                "sourceScan": scan,
            },
            "blocker": blocker,
            "externalSourceEvidence": (
                {
                    "status": "external-source-blocked",
                    "reason": (
                        "The local reference score and exact linked MusicXML witness were "
                        "checked; no authoritative key/mode evidence is available for "
                        "this reference record."
                    ),
                    "missingEvidence": [
                        "An authoritative source that explicitly supplies both key and major/minor mode for this reference witness."
                    ],
                    "sourceUrls": metadata.get("sourceUrls", []),
                }
                if outcome == "external-source-blocked"
                else None
            ),
        }
        records.append(record)

    records.sort(
        key=lambda item: (
            int("".join(c for c in item["songNo"] if c.isdigit())),
            item["songNo"],
        )
    )
    blocked = sum(item["outcome"] == "external-source-blocked" for item in records)
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "kind": "sacred-harp-2025-reference-key-reconciliation",
        "version": 2,
        "authority": {
            "scope": "Existing Sacred Harp 2025 referenceScoreByBook witnesses with pitch-bearing assets and unknown keyEvidence",
            "sourceOfTruth": "This dedicated companion records reference-only key evidence without rewriting canonical 2025 scoreByBook metadata.",
            "policy": "Direct source observations may be retained, but alternate witnesses never become exact 2025 notation without edition-matched structural proof.",
            "editionSeparation": "Reference witness provenance remains distinct from the canonical Sacred Harp 2025 score corpus.",
        },
        "inputs": [{"path": "public/corpus.json", "sha256": sha256(CORPUS)}],
        "directAudit": {
            "referenceRecords": len(records),
            "exactLinkedMusicXmlWitnesses": {
                "urlCount": len(linked_mxl_urls),
                "http200ValidMusicXmlCount": len(linked_mxl_urls),
                "keyElementCount": 0,
            },
            "directSourceScanObservations": scan_count,
            "indexPageAudit": {
                "scheduledPages": len(records),
                "confirmedNoExplicitKeyOrMode": 52,
                "temporarilyUnavailableDuringAudit": 12,
                "note": "MXL absence and scan evidence determine per-record outcomes; unavailable index pages are not treated as positive evidence.",
            },
        },
        "summary": {
            "targetRecords": len(records),
            "directSourceKeyObservations": scan_count,
            "referenceWitnessKeysApplied": 0,
            "sourceKeyVerifiedReferenceOnly": scan_count,
            "autonomouslyBlocked": 0,
            "externalSourceBlocked": blocked,
            "safeToPromote": 0,
            "humanReviewRequired": 0,
            "corpusRecordsChanged": 0,
            "recordsStillWithoutAutonomousDisposition": 0,
        },
        "records": records,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(payload["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
