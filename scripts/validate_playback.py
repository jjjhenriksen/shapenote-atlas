#!/usr/bin/env python3
"""Validate that every bundled structured asset has schedulable playback data."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALID_STEP = re.compile(r"^[A-G]$")


def finite_number(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def same_numeric_or_raw(left: object, right: object) -> bool:
    if left == right:
        return True
    try:
        left_number = float(left)
        right_number = float(right)
    except (TypeError, ValueError):
        return False
    if math.isnan(left_number) and math.isnan(right_number):
        return True
    return math.isfinite(left_number) and math.isfinite(right_number) and left_number == right_number


def main() -> int:
    corpus = json.loads((ROOT / "public" / "corpus.json").read_text(encoding="utf-8"))
    refs: dict[str, str] = {}
    for song in corpus.get("songs", []):
        for field in ("scoreByBook", "referenceScoreByBook", "draftScoreByBook"):
            for book_id, preview in (song.get(field) or {}).items():
                ref = preview.get("scoreRef", "")
                if ref:
                    refs.setdefault(ref, f"{song.get('id', '')} {book_id} {field}")

    counts = {
        "assets": 0,
        "parts": 0,
        "events": 0,
        "pitchedEvents": 0,
        "rests": 0,
        "assetsWithPitchedEvents": 0,
        "playableAssets": 0,
        "samePitchDuplicateEvents": 0,
        "quarantinedDraftAssets": 0,
        "quarantinedInvalidDurations": 0,
    }
    errors: list[str] = []
    for ref, label in refs.items():
        path = ROOT / "public" / ref.lstrip("/")
        if not path.is_file():
            errors.append(f"{label}: missing playback asset {ref}")
            continue
        asset = json.loads(path.read_text(encoding="utf-8"))
        counts["assets"] += 1
        playback_validation = asset.get("playbackValidation") or {}
        quarantined_event_details = {
            (str(item.get("part", "")), int(item.get("eventIndex"))): item
            for item in playback_validation.get("invalidEvents", [])
            if str(item.get("eventIndex", "")).isdigit()
        }
        quarantined_events = set(quarantined_event_details)
        observed_quarantine_events: set[tuple[str, int]] = set()
        if playback_validation.get("status") == "quarantined":
            if (
                "draftScoreByBook" not in label
                or playback_validation.get("safeToApply") is not False
                or not playback_validation.get("reason")
                or not quarantined_events
            ):
                errors.append(f"{label}: invalid draft quarantine metadata")
            counts["quarantinedDraftAssets"] += 1
            transposition = asset.get("transposition") or {}
            if transposition.get("available") or transposition.get("manualKeyAllowed"):
                errors.append(f"{label}: quarantined draft advertises transposition capability")
        parts = asset.get("parts") or []
        counts["parts"] += len(parts)
        names = [str(part.get("name", "")) for part in parts]
        if not parts or any(not name for name in names) or len(names) != len(set(names)):
            errors.append(f"{label}: playback parts are missing or duplicated")
        playable = 0
        pitched_in_asset = False
        for part_index, part in enumerate(parts):
            seen_pitched_events: set[tuple[object, object, object, object, object, object]] = set()
            for index, event in enumerate(part.get("events") or []):
                counts["events"] += 1
                if not finite_number(event.get("onset")) or float(event["onset"]) < 0:
                    errors.append(f"{label} {part.get('name', '')} event {index}: invalid onset")
                if event.get("grace"):
                    continue
                if not finite_number(event.get("beats")) or float(event["beats"]) <= 0:
                    quarantine_key = (str(part.get("name", "")), index)
                    if playback_validation.get("status") == "quarantined" and quarantine_key in quarantined_events:
                        evidence = quarantined_event_details[quarantine_key]
                        if (
                            str(event.get("measure", "")) != str(evidence.get("measure", ""))
                            or not same_numeric_or_raw(event.get("beats"), evidence.get("beats"))
                            or event.get("timingStatus") != evidence.get("timingStatus")
                            or evidence.get("sourcePath") != f"parts[{part_index}].events[{index}].beats"
                        ):
                            errors.append(f"{label} {part.get('name', '')} event {index}: quarantine evidence drift")
                        observed_quarantine_events.add(quarantine_key)
                        counts["quarantinedInvalidDurations"] += 1
                    else:
                        errors.append(f"{label} {part.get('name', '')} event {index}: invalid duration")
                if event.get("rest"):
                    counts["rests"] += 1
                    continue
                if not VALID_STEP.fullmatch(str(event.get("step", ""))) or event.get("octave") is None:
                    errors.append(f"{label} {part.get('name', '')} event {index}: unplayable pitched event")
                    continue
                if not finite_number(event.get("octave")):
                    errors.append(f"{label} {part.get('name', '')} event {index}: invalid octave")
                    continue
                if event.get("alter") is not None and not finite_number(event.get("alter")):
                    errors.append(f"{label} {part.get('name', '')} event {index}: invalid accidental")
                    continue
                duplicate_key = (
                    event.get("voice", ""),
                    event.get("staff", "1"),
                    event.get("onset"),
                    event.get("step"),
                    event.get("octave"),
                    event.get("alter", 0),
                )
                if duplicate_key in seen_pitched_events:
                    counts["samePitchDuplicateEvents"] += 1
                    if "draftScoreByBook" not in label:
                        errors.append(
                            f"{label} {part.get('name', '')} event {index}: duplicate pitch at the same onset in one voice/staff"
                        )
                else:
                    seen_pitched_events.add(duplicate_key)
                counts["pitchedEvents"] += 1
                pitched_in_asset = True
                playable += 1
        if pitched_in_asset:
            counts["assetsWithPitchedEvents"] += 1
        if playable and playback_validation.get("status") != "quarantined":
            counts["playableAssets"] += 1
        elif asset.get("transposition", {}).get("available"):
            errors.append(f"{label}: marked transposable but has no playable events")
        stale_quarantine_events = quarantined_events - observed_quarantine_events
        for part_name, index in sorted(stale_quarantine_events):
            errors.append(f"{label} {part_name} event {index}: quarantine evidence does not identify an invalid duration")

    if errors:
        raise SystemExit("\n".join(errors))
    print(json.dumps({**counts, "errors": []}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
