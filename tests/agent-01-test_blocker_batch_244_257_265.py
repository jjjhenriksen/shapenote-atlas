#!/usr/bin/env python3
"""Focused receipt validation for agent-01's three-record blocker batch."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "backlogs/01-transcribe-2025/agent-01-2026-08-30-244-257-265-receipt.json"
MANIFESTS = {
    "sh2025/244": ROOT / "work/agent-01-notation/sh2025-244-plevna-blocker-batch.json",
    "sh2025/257": ROOT / "work/agent-01-notation/sh2025-257-manatawny-blocker-batch.json",
    "sh2025/265": ROOT / "work/agent-01-notation/sh2025-265-gwehelog-blocker-batch.json",
}


def read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    receipt = read_json(RECEIPT)
    expected = set(MANIFESTS)
    assert set(receipt["records"]) == expected
    assert receipt["onlyRecordsProcessed"] is True
    assert receipt["protectedRecords"] == ["sh2025/115", "sh2025/116"]
    assert receipt["protectedRecordsTouched"] is False
    assert receipt["sharedPublicLedgersModified"] is False
    assert receipt["uiFilesModified"] is False
    assert receipt["authorizedStructuredCandidates"] == 0
    assert receipt["dispositionSummary"] == {
        "records": 3,
        "autonomouslyBlocked": 3,
        "rejected": 0,
        "musicXmlProduced": 0,
        "safeToPromote": 0,
    }

    for record_id, manifest_path in MANIFESTS.items():
        manifest = read_json(manifest_path)
        assert manifest["recordId"] == record_id
        assert manifest["disposition"] == "autonomously-blocked"
        assert manifest["safeToPromote"] is False
        assert manifest["humanReviewRequired"] is False
        assert manifest["producedMusicXml"] is False
        assert len(manifest["blockingFindings"]) >= 5
        image = manifest["sourceEvidence"]["canonicalRetainedImage"]
        image_path = ROOT / image["path"]
        assert image_path.is_file(), image_path
        assert sha256(image_path) == image["sha256"]
        assert manifest["currentWitnesses"]["draftSourceImage"][
            "byteEqualToCanonicalRetainedImage"
        ] is False

    assert all(
        not Path(item).as_posix().startswith(("public/", "src/"))
        for item in receipt.get("recordManifests", [])
    )
    print("agent-01 blocker batch receipt: 3 exact records validated; 3 autonomously blocked; 0 MusicXML promoted")


if __name__ == "__main__":
    main()
