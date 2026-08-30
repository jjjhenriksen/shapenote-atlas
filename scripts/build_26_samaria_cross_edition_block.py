#!/usr/bin/env python3
"""Record the 2025/1991 Samaria key discrepancy without promoting a witness."""

from __future__ import annotations

import hashlib
import json
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "public/shapenote-score-manifest.json"
SOURCE_IMAGE_URL = "https://sacredharpbremen.org/wp-content/uploads/songs/001-099/026-Samaria/26.jpg"
SOURCE_IMAGE = ROOT / "work/source-transcriptions/2025/26-samaria/26.jpg"
COMPARISON = ROOT / "work/source-transcriptions/2025/26-samaria-cross-edition-comparison.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(node: ET.Element, name: str) -> str:
    for child in node:
        if local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def parse_score(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        xml = next(archive.read(name) for name in archive.namelist() if name.endswith(".xml") and "container" not in name.lower())
    root = ET.fromstring(xml)
    parts = [node for node in root if local_name(node.tag) == "part"]
    key = next((node for node in root.iter() if local_name(node.tag) == "key"), None)
    time = next((node for node in root.iter() if local_name(node.tag) == "time"), None)
    return {
        "workTitle": next((node.text.strip() for node in root.iter() if local_name(node.tag) == "work-title" and node.text), ""),
        "parts": len(parts),
        "measuresByPart": [sum(1 for child in part if local_name(child.tag) == "measure") for part in parts],
        "keyFifths": child_text(key, "fifths") if key is not None else "",
        "keyMode": child_text(key, "mode") if key is not None else "",
        "timeSignature": f"{child_text(time, 'beats')}/{child_text(time, 'beat-type')}" if time is not None else "",
    }


def main() -> int:
    if not SOURCE_IMAGE.exists():
        SOURCE_IMAGE.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(SOURCE_IMAGE_URL, headers={"User-Agent": "Shape-Note-Atlas/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            SOURCE_IMAGE.write_bytes(response.read())
    image_hash = sha256(SOURCE_IMAGE)
    if SOURCE_IMAGE.stat().st_size < 1000:
        raise SystemExit("2025 Samaria source image is unexpectedly small")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["entries"]
    entry = manifest["sh1991/26"]
    witness = ROOT / entry["rawPath"]
    witness_hash = sha256(witness)
    witness_summary = parse_score(witness)
    payload = {
        "queueId": "sh2025/26",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "26",
        "title": "Samaria",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=26",
            "sourceImageUrl": SOURCE_IMAGE_URL,
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)),
            "sourceImageSha256": image_hash,
            "immutable": True,
            "directObservations": {
                "header": "SAMARIA. L.M.D.",
                "key": "F minor",
                "mode": "minor",
                "timeSignature": "6/8",
                "meter": "Long Meter Double (8,8,8,8,8,8,8,8)",
                "parts": 4,
                "fourShapeNoteheadsVisible": True,
                "sourceLyricsVisible": True,
                "observationBasis": "direct inspection of the untouched 2025 page scan",
            },
        },
        "candidateWitness": {
            "candidateMusicXmlPath": str(witness.relative_to(ROOT)),
            "candidateMusicXmlSha256": witness_hash,
            "candidateMusicXmlIsOmrDerivative": False,
            "candidateRole": "exact 1991 Denson source witness; alternate edition, not a 2025 score",
            "sourceEdition": "sh1991",
            "sourceUrl": entry["sourceUrl"],
        },
        "structuredEvidence": {
            "candidateMusicXml": witness_summary,
            "candidateKeyInterpretation": "A-flat major from the 1991 MusicXML key declaration",
            "sourceScanKey": "F minor",
        },
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "eventStreamComparison": "Not used to authorize 2025 identity because the printed source key differs from the 1991 witness.",
            "editionRelationship": "Same title and composer lineage, but the 2025 scan prints F minor while the 1991 structured witness is A-flat major.",
            "shapeEvidence": "Four-shape noteheads are visible on the 2025 scan; no 2025 structured shape encoding is inferred from the alternate witness.",
        },
        "blockingFindings": [
            "The untouched 2025 source scan prints F minor, while the available 1991 MusicXML witness declares A-flat major.",
            "The 1991 witness is an alternate-edition score and cannot be presented as exact 2025 notation without proving every edition change and event.",
            "No exact 2025 structured score is available for this record; synthesizing a key-shifted score would fabricate edition-specific evidence.",
        ],
        "promotionDisposition": "alternate-1991-witness-retained; 2025-promotion-blocked-by-source-key-discrepancy",
        "nextAction": "autonomous-promotion-blocked-by-cross-edition-key-discrepancy; acquire-exact-2025-structured-source",
        "policy": "The 2025 scan remains authoritative for the 2025 record. Alternate-edition MusicXML is retained as a separately labeled witness and is never substituted for the 2025 score.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    COMPARISON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queueId": payload["queueId"], "sourceImageSha256": image_hash, "witnessSha256": witness_hash, "witness": witness_summary}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
