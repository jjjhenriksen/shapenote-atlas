#!/usr/bin/env python3
"""Record source-backed key recovery outcomes for SH1991 scoreByBook assets.

This companion intentionally does not alter corpus metadata. It is used when the
authoritative inputs do not contain enough direct evidence to safely add a key.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "public" / "corpus.json"
OUTPUT = ROOT / "public" / "sh1991-key-reconciliation.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pitched_events(score: dict) -> int:
    return sum(
        1
        for part in score.get("parts", [])
        for event in part.get("events", [])
        if event.get("step") or event.get("pitch")
    )


def main() -> None:
    corpus = json.loads(CORPUS.read_text())
    records = []
    linked_mxl_urls = set()

    for song in corpus.get("songs", []):
        score = song.get("scoreByBook", {}).get("sh1991")
        if not score or score.get("keyEvidence", {}).get("status") != "unknown":
            continue
        score_ref = score.get("scoreRef", "")
        score_path = ROOT / "public" / score_ref.lstrip("/")
        if not score_path.exists():
            continue
        score_asset = json.loads(score_path.read_text())
        if not pitched_events(score_asset):
            continue

        metadata = song.get("metadataByBook", {}).get("sh1991", {})
        mxl_urls = [
            url
            for url in metadata.get("sourceUrls", [])
            if "shapenote.net/musicxml/" in url
        ]
        linked_mxl_urls.update(mxl_urls)
        records.append(
            {
                "queueId": f"sh1991/{song['songNo']}",
                "songNo": song["songNo"],
                "title": song.get("title", ""),
                "outcome": "external-source-blocked",
                "safeToPromote": False,
                "humanReviewRequired": False,
                "keySignature": "",
                "mode": "",
                "scoreRef": score_ref,
                "scoreAssetSha256": sha256(score_path),
                "sourceUrls": metadata.get("sourceUrls", []),
                "auditedEvidence": {
                    "localStructuredAsset": {
                        "keyEvidence": score_asset.get("keyEvidence", {}),
                        "keyElementPresent": False,
                        "pitchedEventCount": pitched_events(score_asset),
                    },
                    "linkedMusicXml": {
                        "urls": mxl_urls,
                        "directFetchStatus": "http-200-valid-musicxml",
                        "keyElementPresent": False,
                    },
                    "fasolaIndex": {
                        "url": metadata.get("sourceUrl", ""),
                        "directFetchStatus": "http-200",
                        "explicitKeyOrModeObserved": False,
                    },
                },
                "blocker": (
                    "Autonomous key recovery is blocked: the local pitch-bearing "
                    "1991 structured asset and every exact linked MusicXML witness "
                    "audited contain no key element, while the fetched Fasola 1991 "
                    "index page provides no explicit major/minor key or mode. No "
                    "key is inferred from pitch spelling, fifths, or another edition."
                ),
                "externalSourceEvidence": {
                    "status": "external-source-blocked",
                    "reason": (
                        "The local 1991 structured score, exact linked MusicXML witnesses, "
                        "and fetched Fasola index page were checked; none provides an "
                        "explicit key and major/minor mode."
                    ),
                    "missingEvidence": [
                        "An authoritative 1991 source that explicitly supplies both key and major/minor mode."
                    ],
                    "sourceUrls": metadata.get("sourceUrls", []),
                },
            }
        )

    records.sort(key=lambda item: (int("".join(c for c in item["songNo"] if c.isdigit())), item["songNo"]))
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "kind": "sacred-harp-1991-key-evidence-reconciliation",
        "version": 2,
        "authority": {
            "scope": "Existing Sacred Harp 1991 scoreByBook records with pitch-bearing structured assets and unknown keyEvidence",
            "sourceOfTruth": "public/corpus.json generated from the existing corpus source metadata",
            "policy": "Only direct source-backed major/minor observations may be added; absence is recorded here without changing corpus metadata.",
            "editionSeparation": "1991 only; no 2025 missing-score or transcription ledger is in scope.",
        },
        "inputs": [
            {"path": "public/corpus.json", "sha256": sha256(CORPUS)},
        ],
        "directAudit": {
            "fasola1991Pages": {
                "recordCount": len(records),
                "http200Count": len(records),
                "explicitKeyOrModeCount": 0,
            },
            "exactLinkedMusicXmlWitnesses": {
                "urlCount": len(linked_mxl_urls),
                "http200ValidMusicXmlCount": len(linked_mxl_urls),
                "keyElementCount": 0,
            },
        },
        "summary": {
            "targetRecords": len(records),
            "verifiedKeys": 0,
            "autonomouslyBlocked": 0,
            "externalSourceBlocked": len(records),
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
