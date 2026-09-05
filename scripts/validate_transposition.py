#!/usr/bin/env python3
"""Validate provenance-aware key handling and source-faithful playback."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_data import (  # noqa: E402
    authoritative_metadata_key,
    prepare_score_for_playback,
    source_key_to_musicxml,
)


VALID_KEY = re.compile(r"^(?:-?[0-7]|[A-G](?:#|b)?):(major|minor)$|^[A-G](?:#|b)?(?:\s+(?:major|minor))?$", re.IGNORECASE)
KEY_STATUSES = {"source-verified", "source-observed", "omr-detected", "unknown"}


def close(left: object, right: object) -> bool:
    try:
        return abs(float(left) - float(right)) <= 0.001
    except (TypeError, ValueError):
        return False


def validate_key(record: dict, label: str, draft: bool = False) -> None:
    key = record.get("keySignature", "")
    evidence = record.get("keyEvidence", {})
    status = evidence.get("status", "")
    if status not in KEY_STATUSES:
        raise SystemExit(f"{label}: invalid key evidence status {status!r}")
    if key and not VALID_KEY.match(str(key)):
        raise SystemExit(f"{label}: malformed key signature {key!r}")
    if status == "unknown" and key:
        raise SystemExit(f"{label}: unknown key status has a key value")
    if status in {"source-verified", "source-observed", "omr-detected"} and not key:
        raise SystemExit(f"{label}: {status} key evidence is missing its key value")
    if not draft and status == "omr-detected":
        raise SystemExit(f"{label}: non-draft score is marked OMR-detected")


def validate_musicxml_key_provenance(record: dict, label: str) -> None:
    """Reject silent ``missing mode == major`` behavior in structured assets."""
    source_url = str(record.get("sourceUrl", ""))
    declarations = record.get("musicXmlKeyDeclarations")
    if source_url.startswith("https://shapenote.net/musicxml/") and declarations is None:
        raise SystemExit(f"{label}: structured MusicXML asset lacks raw key/mode provenance")
    if declarations is None:
        return
    if not isinstance(declarations, list):
        raise SystemExit(f"{label}: MusicXML key declarations are not a list")
    for declaration in declarations:
        if not isinstance(declaration, dict):
            raise SystemExit(f"{label}: malformed MusicXML key declaration")
        mode_present = declaration.get("modePresent")
        mode = str(declaration.get("mode", ""))
        if mode_present is not (bool(mode)):
            raise SystemExit(f"{label}: MusicXML key declaration has inconsistent mode presence")
        if not mode_present and record.get("keyEvidence", {}).get("source") == "structured MusicXML source":
            raise SystemExit(f"{label}: MusicXML key mode is missing but asset claims structured-source key evidence")
        if not mode_present and str(record.get("musicXmlDeclaredKeySignature", "")).endswith(":major"):
            raise SystemExit(f"{label}: missing MusicXML mode was silently converted to major")
    if record.get("keyEvidence", {}).get("status") == "source-verified" and any(
        not declaration.get("modePresent") for declaration in declarations if isinstance(declaration, dict)
    ):
        declared = str(record.get("keySignature", ""))
        resolved = declared if re.fullmatch(r"-?[0-7]:(?:major|minor)", declared, re.IGNORECASE) else source_key_to_musicxml(declared)
        expected_fifths = resolved.split(":", 1)[0] if resolved else ""
        raw_fifths = {
            str(declaration.get("fifths", ""))
            for declaration in declarations
            if isinstance(declaration, dict) and declaration.get("fifths", "")
        }
        conflict = record.get("keyEvidence", {}).get("rawFifthsConflict")
        if expected_fifths and raw_fifths and (raw_fifths - {expected_fifths}) and not conflict:
            raise SystemExit(f"{label}: source key disagrees with raw fifths without an explicit preserved conflict")
        if conflict and set(conflict.get("conflictingFifths", [])) != raw_fifths - {expected_fifths}:
            raise SystemExit(f"{label}: preserved raw-fifths conflict is incomplete")


def validate_metadata_key_provenance(song: dict, label: str) -> None:
    """Ensure secondary/cross-edition keys cannot become edition authority."""
    for book_id, metadata in (song.get("metadataByBook") or {}).items():
        metadata = metadata or {}
        key = str(metadata.get("keySignature", ""))
        evidence = metadata.get("keyEvidence", {}) or {}
        status = evidence.get("status", "unknown")
        confidence = str(metadata.get("confidence", "")).strip().lower()
        candidate = metadata.get("keyCandidate")
        if key and status == "unknown":
            raise SystemExit(f"{label} {book_id}: unknown metadata key has a value")
        if key and source_key_to_musicxml(key) == "":
            raise SystemExit(f"{label} {book_id}: metadata key cannot be canonically encoded: {key!r}")
        direct_source_evidence = bool(evidence.get("sourceImageUrl") and evidence.get("sourceImageSha256"))
        if confidence == "secondary" and key and evidence.get("source") != "source audit" and not direct_source_evidence:
            raise SystemExit(f"{label} {book_id}: secondary metadata key was promoted to edition authority")
        if candidate is not None:
            if not isinstance(candidate, dict) or candidate.get("status") != "secondary":
                raise SystemExit(f"{label} {book_id}: malformed metadata key candidate")
            candidate_value = str(candidate.get("value", ""))
            if not candidate_value or not source_key_to_musicxml(candidate_value):
                raise SystemExit(f"{label} {book_id}: malformed secondary metadata key candidate")
            if key or status != "unknown":
                raise SystemExit(f"{label} {book_id}: secondary metadata candidate is authoritative")

        # Exercise the same authority function used by the build. This guards
        # against future changes that reintroduce a truthy fallback through a
        # different code path.
        row = {"key_signature": metadata.get("keySignature", ""), "confidence": confidence}
        if candidate:
            row = {"key_signature": candidate.get("value", ""), "confidence": confidence}
        resolved, resolved_evidence, resolved_candidate = authoritative_metadata_key(row, None)
        if confidence == "secondary" and candidate is not None:
            if resolved or resolved_evidence.get("status") != "unknown" or not resolved_candidate:
                raise SystemExit(f"{label} {book_id}: secondary metadata authority regression")


def validate_asset(path: Path, label: str, draft: bool = False) -> None:
    asset = json.loads(path.read_text(encoding="utf-8"))
    validate_key(asset, label, draft=draft)
    validate_musicxml_key_provenance(asset, label)
    has_pitched_events = any(
        not event.get("rest") and event.get("step") and event.get("octave") is not None
        for part in asset.get("parts", [])
        for event in part.get("events", [])
    )
    key_status = asset.get("keyEvidence", {}).get("status", "unknown")
    playback_quarantined = (asset.get("playbackValidation") or {}).get("status") == "quarantined"
    expected_transposable = (
        has_pitched_events
        and key_status in {"source-verified", "source-observed", "omr-detected"}
        and not playback_quarantined
    )
    capability = asset.get("transposition", {})
    if capability.get("hasPitchedEvents") is not has_pitched_events or capability.get("available") is not expected_transposable:
        raise SystemExit(f"{label}: transposition capability metadata does not match score content")
    if capability.get("keyStatus") != key_status:
        raise SystemExit(f"{label}: transposition capability key status drift")
    transform = asset.get("playbackTransform")
    if not transform or transform.get("sourcePreserved") is not True:
        raise SystemExit(f"{label}: missing source-preserving playback transform")
    removed = bool(transform.get("finalChordRemoved"))
    if removed:
        if transform.get("reason") != "reliable-final-chord" or int(transform.get("removedEventCount", 0)) < 2:
            raise SystemExit(f"{label}: invalid reliable final-chord transform")
        onset = transform.get("onset")
        if any(close(event.get("onset"), onset) for part in asset.get("parts", []) for event in part.get("events", [])):
            raise SystemExit(f"{label}: removed final chord is still in playback data")
    elif transform.get("reason") not in {"final-chord-not-reliably-identifiable", "source-final-chord-preserved"} or transform.get("removedEventCount") != 0:
        raise SystemExit(f"{label}: source ending was not preserved")


def main() -> int:
    expected_source_keys = {
        "A major": "3:major",
        "B minor": "2:minor",
        "D minor": "-1:minor",
        "E minor": "1:minor",
        "F# minor": "3:minor",
        "F minor": "-4:minor",
    }
    for source_key, encoded_key in expected_source_keys.items():
        if source_key_to_musicxml(source_key) != encoded_key:
            raise SystemExit(f"source key conversion drift: {source_key}")
    corpus = json.loads((ROOT / "public/corpus.json").read_text(encoding="utf-8"))
    seen: set[str] = set()
    counts = {"assets": 0, "trimmed": 0, "preserved": 0, "omrDetected": 0, "unknown": 0}
    for song in corpus.get("songs", []):
        validate_metadata_key_provenance(song, str(song.get("id", "song")))
        for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook"):
            for book_id, preview in song.get(field, {}).items():
                ref = preview.get("scoreRef", "")
                if not ref:
                    continue
                already_seen = ref in seen
                seen.add(ref)
                path = ROOT / "public" / ref.lstrip("/")
                if not path.exists():
                    raise SystemExit(f"{song.get('id')} {book_id}: missing {ref}")
                draft = field == "draftScoreByBook"
                label = f"{song.get('id')} {book_id} {field}"
                asset = json.loads(path.read_text(encoding="utf-8"))
                if not already_seen:
                    validate_asset(path, label, draft=draft)
                    counts["assets"] += 1
                    counts["trimmed" if asset["playbackTransform"]["finalChordRemoved"] else "preserved"] += 1
                    status = asset.get("keyEvidence", {}).get("status")
                    if status == "omr-detected":
                        counts["omrDetected"] += 1
                    if status == "unknown":
                        counts["unknown"] += 1

                metadata = (song.get("metadataByBook") or {}).get(book_id, {})
                metadata_key = source_key_to_musicxml(metadata.get("keySignature", ""))
                asset_key = source_key_to_musicxml(asset.get("keySignature", "")) or asset.get("keySignature", "")
                preview_key = source_key_to_musicxml(preview.get("keySignature", "")) or preview.get("keySignature", "")
                if asset_key != preview_key:
                    raise SystemExit(
                        f"{label}: preview/asset key drift ({preview.get('keySignature')!r} != {asset.get('keySignature')!r})"
                    )
                provenance = preview.get("provenance", {})
                if (
                    provenance.get("kind") == "edition-source"
                    and metadata.get("keyEvidence", {}).get("status") == "source-verified"
                    and metadata_key
                    and asset_key != metadata_key
                ):
                    raise SystemExit(
                        f"{song.get('id')} {book_id} {field}: edition key drift "
                        f"({asset.get('keySignature')!r} != {metadata.get('keySignature')!r})"
                    )

    for book_id, coverage in corpus.get("coverage", {}).get("byBook", {}).items():
        expected = {"transposableRecords": 0, "transposableLocalScoreRecords": 0, "transposableReferenceRecords": 0, "transposableDraftRecords": 0, "keyUnknownStructuredRecords": 0}
        for song in corpus.get("songs", []):
            if book_id not in song.get("books", []):
                continue
            assets = []
            for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook"):
                preview = (song.get(field) or {}).get(book_id)
                if preview:
                    assets.append((field, preview))
            if any(preview.get("transposition", {}).get("available") for _, preview in assets):
                expected["transposableRecords"] += 1
            for field, counter in (("scoreByBook", "transposableLocalScoreRecords"), ("referenceScoreByBook", "transposableReferenceRecords"), ("draftScoreByBook", "transposableDraftRecords")):
                preview = (song.get(field) or {}).get(book_id)
                if preview and preview.get("transposition", {}).get("available"):
                    expected[counter] += 1
            if assets and not any(preview.get("transposition", {}).get("available") for _, preview in assets) and any(
                preview.get("transposition", {}).get("hasPitchedEvents") for _, preview in assets
            ):
                expected["keyUnknownStructuredRecords"] += 1
        for field, value in expected.items():
            if coverage.get(field) != value:
                raise SystemExit(f"{book_id}: coverage field {field} is stale ({coverage.get(field)!r} != {value!r})")

    reliable = {
        "parts": [
            {"name": "Treble", "events": [{"onset": 0, "beats": 1, "step": "C", "octave": 5}, {"onset": 4, "beats": 2, "step": "C", "octave": 5}]},
            {"name": "Bass", "events": [{"onset": 0, "beats": 1, "step": "C", "octave": 3}, {"onset": 4, "beats": 2, "step": "F", "octave": 3}]},
        ]
    }
    prepared = prepare_score_for_playback(reliable)
    if prepared["playbackTransform"]["finalChordRemoved"] or prepared["playbackTransform"]["removedEventCount"] != 0:
        raise SystemExit("synthetic final chord was not preserved")
    if len(prepared["parts"][0]["events"]) != 2 or len(prepared["parts"][1]["events"]) != 2:
        raise SystemExit("synthetic final chord events were altered")

    ambiguous = {
        "parts": [{"name": "Solo", "events": [{"onset": 0, "beats": 1, "step": "C", "octave": 5}]}]
    }
    preserved = prepare_score_for_playback(ambiguous)
    if preserved["playbackTransform"]["finalChordRemoved"] or len(preserved["parts"][0]["events"]) != 1:
        raise SystemExit("synthetic ambiguous ending was altered")

    missing_mode = {
        "sourceUrl": "https://shapenote.net/musicxml/example.mxl",
        "keySignature": "0:major",
        "keyEvidence": {"status": "source-verified", "source": "structured MusicXML source"},
        "musicXmlKeyDeclarations": [{"fifths": "0", "mode": "", "modePresent": False}],
        "musicXmlDeclaredKeySignature": "0:major",
    }
    try:
        validate_musicxml_key_provenance(missing_mode, "synthetic missing-mode asset")
    except SystemExit:
        pass
    else:
        raise SystemExit("synthetic missing MusicXML mode was accepted as major")

    secondary = {"key_signature": "A major", "confidence": "secondary"}
    resolved, evidence, candidate = authoritative_metadata_key(secondary, None)
    if resolved or evidence.get("status") != "unknown" or not candidate:
        raise SystemExit("synthetic secondary key was promoted to edition authority")

    audited = {"key_signature": "A major", "confidence": "secondary"}
    resolved, evidence, candidate = authoritative_metadata_key(audited, {"sourceKey": "F# minor"})
    if resolved != "F# minor" or evidence.get("status") != "source-verified" or candidate:
        raise SystemExit("synthetic source audit did not override secondary candidate safely")

    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
