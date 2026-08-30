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
        "playableAssets": 0,
        "samePitchDuplicateEvents": 0,
    }
    errors: list[str] = []
    for ref, label in refs.items():
        path = ROOT / "public" / ref.lstrip("/")
        if not path.is_file():
            errors.append(f"{label}: missing playback asset {ref}")
            continue
        asset = json.loads(path.read_text(encoding="utf-8"))
        counts["assets"] += 1
        parts = asset.get("parts") or []
        counts["parts"] += len(parts)
        names = [str(part.get("name", "")) for part in parts]
        if not parts or any(not name for name in names) or len(names) != len(set(names)):
            errors.append(f"{label}: playback parts are missing or duplicated")
        playable = 0
        for part in parts:
            seen_pitched_events: set[tuple[object, object, object, object, object, object]] = set()
            for index, event in enumerate(part.get("events") or []):
                counts["events"] += 1
                if not finite_number(event.get("onset")) or float(event["onset"]) < 0:
                    errors.append(f"{label} {part.get('name', '')} event {index}: invalid onset")
                if not finite_number(event.get("beats")) or float(event["beats"]) <= 0:
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
                playable += 1
        if playable:
            counts["playableAssets"] += 1
        elif asset.get("transposition", {}).get("available"):
            errors.append(f"{label}: marked transposable but has no playable events")

    if errors:
        raise SystemExit("\n".join(errors))
    print(json.dumps({**counts, "errors": []}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
