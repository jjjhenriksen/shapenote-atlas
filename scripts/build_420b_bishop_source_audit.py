#!/usr/bin/env python3
"""Record the source-faithful Bishop audit when MusicXML export is unavailable.

The immutable scan remains authoritative.  The retained Audiveris container is
hashed and counted as an OMR witness only; it is not converted into a playable
score because its MusicXML export failed and no exact structured candidate is
available.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "work/omr/420b-bishop/source.jpg"
SOURCE_MXL = ROOT / "work/omr/420b-bishop/source.mxl"
OMR = ROOT / "work/omr/420b-bishop/source.omr"
AUDIT = ROOT / "work/source-transcriptions/2025/420b-bishop-source-comparison.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def archive_evidence(path: Path) -> dict[str, object]:
    entries: dict[str, str] = {}
    counts = {tag: 0 for tag in ("measure", "staff", "part", "voice", "slot", "key", "time", "repeat")}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith(".xml"):
                continue
            data = archive.read(name)
            entries[name] = sha256_bytes(data)
            if not name.startswith("sheet#") or not name.endswith(".xml"):
                continue
            decoded = data.decode("utf-8", "ignore")
            for tag in counts:
                counts[tag] += len(re.findall(fr"<(?:[^:>]+:)?{tag}(?:\s|>)", decoded))
    return {"sha256": sha256(path), "xmlEntries": entries, "xmlTagCounts": counts}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    image_hash = sha256(SOURCE_IMAGE)
    omr_evidence = archive_evidence(OMR)
    duplicate = sorted((p for p in (ROOT / "work/source-images/2025").glob("*420b*bishop*.jpg") if p.is_file()))
    blocking = [
        "The immutable page visibly prints BISHOP. C.M., F major, Octavia Bishop McGraw 1935, T. B. McGraw 1935, four vocal parts, lyrics, internal repeat bars, and first/second endings.",
        "The requested retained MusicXML witness work/omr/420b-bishop/source.mxl is absent; no source MusicXML event stream is available for correction or exact comparison.",
        "The retained work/omr/420b-bishop/source.omr is an Audiveris 5.11.0 archive, not MusicXML. Its sheet XML contains 47 raw measure nodes, 4 part nodes, 4 staff nodes, 19 voice nodes, 34 slot nodes, 79 key nodes, and 1 time node, while the latest Audiveris logs report 32 raw measures and 3 parts along 2 systems and repeated export/PAGE failures.",
        "Audiveris export is therefore not a trustworthy playable witness; no MusicXML draft was synthesized from the malformed container.",
        "The source-visible diagonal DO NOT COPY watermark crosses the alto/tenor notation and lyric regions, so obscured events and syllable alignment were not fabricated.",
        "No authorized same-title structured candidate or retained source-image duplicate exists locally.",
    ]
    audit = {
        "queueId": "sh2025/420b",
        "edition": "Sacred Harp, 2025 Edition",
        "songNo": "420b",
        "title": "Bishop",
        "comparisonStatus": "autonomously-blocked",
        "autonomousDecision": "blocked",
        "safeToPromote": False,
        "humanReviewRequired": False,
        "sourceAuthority": {
            "sourcePageUrl": "https://fasola.org/indexes/2025/?p=420b",
            "sourceImageUrl": "https://sacredharpbremen.org/wp-content/uploads/songs/400-499/420b-Bishop/420b.jpg",
            "sourceImagePath": str(SOURCE_IMAGE.relative_to(ROOT)),
            "sourceImageSha256": image_hash,
            "immutable": True,
            "directObservations": {
                "header": "BISHOP. C.M.",
                "composer": "Octavia Bishop McGraw, 1935",
                "arranger": "T. B. McGraw, 1935",
                "key": "F major",
                "mode": "major",
                "timeSignature": "3/4",
                "meter": "Common Meter (8,6,8,6)",
                "parts": 4,
                "lyricsVisible": True,
                "repeatBarsVisible": True,
                "endingsVisible": True,
                "terminalDoubleBarVisible": True,
                "watermarkIntersectsNotation": True,
                "sourceMeasureCountStatus": "not established from a trustworthy structured witness; retained Audiveris container reports conflicting raw topology",
            },
            "retainedSourceImageDuplicate": {
                "expectedGlob": "work/source-images/2025/*420b*bishop*.jpg",
                "status": "not-found" if not duplicate else "found",
                "paths": [str(p.relative_to(ROOT)) for p in duplicate],
            },
        },
        "inputOmr": {
            "path": str(OMR.relative_to(ROOT)),
            "sha256": omr_evidence["sha256"],
            "status": "retained-audiveris-omr-container-not-musicxml",
            "structuredEvidence": omr_evidence,
        },
        "missingStructuredWitness": {
            "path": str(SOURCE_MXL.relative_to(ROOT)),
            "status": "not-found",
            "sha256": None,
        },
        "candidateWitness": {"status": "none-authorized", "sameTitleStructuredCandidate": False},
        "correctedDraft": None,
        "comparisonEvidence": {
            "sourceScanInspected": True,
            "sourceScanPath": str(SOURCE_IMAGE.relative_to(ROOT)),
            "sourceScanSha256": image_hash,
            "method": "full-resolution visual inspection of immutable source scan plus Audiveris archive/log audit; no alternate witness used",
            "blockingFindings": blocking,
        },
        "blockingFindings": blocking,
        "blockingReason": "Autonomous promotion is blocked because the requested source.mxl is missing, the only retained structured witness is a malformed/non-exportable Audiveris container with conflicting topology, the watermark obscures notation/lyrics, and no authorized same-title structured witness exists. No MusicXML draft was synthesized.",
        "autonomousDisposition": "Source metadata and immutable OMR container are retained for audit; no playable/transposable derivative is admitted.",
        "nextAction": "autonomous-promotion-blocked-by-missing-musicxml-and-failed-omr-export; retain-immutable-source-and-omr-container",
        "policy": "Immutable 2025 source remains authoritative. An Audiveris container is evidence only and cannot authorize promotion or playback without a valid source-faithful MusicXML witness.",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "audit": str(AUDIT.relative_to(ROOT)),
        "record": audit["queueId"],
        "status": audit["comparisonStatus"],
        "sourceImageSha256": image_hash,
        "sourceOmrSha256": omr_evidence["sha256"],
        "sourceMxl": "missing",
        "correctedDraft": None,
        "omrEvidence": omr_evidence,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
