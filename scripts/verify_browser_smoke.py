#!/usr/bin/env python3
"""Validate a real-browser audio receipt against tracked project inputs.

The browser itself produces the receipt. This tracked checker validates that
the captured observations are current, data-linked, and complete before
``verify_all.py`` accepts them. The historical worker under ``work/`` remains
available for old callers, but is deliberately not an aggregate dependency.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_WORK = ROOT / "work" / "agent-05-browser"
RECEIPT = HISTORICAL_WORK / "agent-05-browser-receipt.json"
PLAN = ROOT / "scripts" / "browser-smoke-test-plan.md"


def fail(message: str) -> None:
    raise SystemExit(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        fail("could not resolve current git HEAD")
    return completed.stdout.strip()


def finite(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


STEP_SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
KEY_ROOTS = {
    "C": 0,
    "Db": 1,
    "D": 2,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "Gb": 6,
    "G": 7,
    "Ab": 8,
    "A": 9,
    "Bb": 10,
    "B": 11,
}


def key_root(key: str) -> int:
    root = str(key).split()[0]
    if root not in KEY_ROOTS:
        fail(f"unsupported receipt key {key!r}")
    return KEY_ROOTS[root]


def pitch_midi(event: dict) -> float | None:
    if event.get("rest") or not event.get("step") or event.get("octave") is None:
        return None
    try:
        alter = float(event.get("alter", 0) or 0)
        return (int(event["octave"]) + 1) * 12 + STEP_SEMITONES[str(event["step"])] + alter
    except (KeyError, TypeError, ValueError):
        return None


def reviewed_events(part: dict, draft: bool) -> list[dict]:
    events = list(part.get("events") or [])
    if not draft:
        return events
    counts: dict[str, int] = {}
    for event in events:
        if pitch_midi(event) is None:
            continue
        key = f"{event.get('measure', '')}|{float(event.get('onset', 0)):.3f}"
        counts[key] = counts.get(key, 0) + 1
    return [
        event
        for event in events
        if pitch_midi(event) is None
        or counts.get(f"{event.get('measure', '')}|{float(event.get('onset', 0)):.3f}", 0) <= 1
    ]


def expected_count(asset: dict, parts: list[str], draft: bool) -> int:
    by_name = {str(part.get("name")): part for part in asset.get("parts") or []}
    if set(parts) != set(by_name).intersection(parts):
        fail(f"receipt selects a part missing from asset: {parts}")
    return sum(1 for name in parts for event in reviewed_events(by_name[name], draft) if pitch_midi(event) is not None)


def first_midi(asset: dict, parts: list[str], draft: bool) -> float:
    by_name = {str(part.get("name")): part for part in asset.get("parts") or []}
    for name in parts:
        for event in reviewed_events(by_name[name], draft):
            midi = pitch_midi(event)
            if midi is not None:
                return midi
    fail("receipt case has no playable first event")


def frequency(midi: float) -> float:
    return 440 * 2 ** ((midi - 69) / 12)


def close(left: object, right: object, tolerance: float = 1e-9) -> bool:
    return finite(left) and abs(float(left) - float(right)) <= tolerance


CASE_DEFINITIONS = {
    "source-verified-major": {
        "asset": "public/scores/e1f782a69c5812f4bcd5418a.json",
        "sourceKey": "Ab major",
        "targetKey": "G major",
        "parts": ["Treble", "Alto", "Tenor", "Bass"],
        "draft": False,
        "delta": -1,
    },
    "source-verified-minor": {
        "asset": "public/scores/e8a639af812f0ca7c5298b2b.json",
        "sourceKey": "B minor",
        "targetKey": "C minor",
        "parts": ["Voice", "Voice 2", "Voice 3", "Bass"],
        "draft": False,
        "delta": 1,
    },
    "unknown-key-entry": {
        "asset": "public/scores/3509deecb75016f0d85fe47d.json",
        "sourceKey": "C minor",
        "targetKey": "D minor",
        "parts": ["Treble", "Alto", "Tenor", "Bass"],
        "draft": False,
        "delta": 2,
    },
    "reference-witness": {
        "asset": "public/scores/e1f782a69c5812f4bcd5418a.json",
        "sourceKey": "Ab major",
        "targetKey": "G major",
        "parts": ["Treble", "Alto", "Tenor", "Bass"],
        "draft": False,
        "delta": -1,
    },
    "review-draft": {
        "asset": "public/draft-scores/d70b33f990339c1c2aab49d0.json",
        "sourceKey": "G minor",
        "targetKey": "C minor",
        "parts": ["Treble", "Alto", "Tenor", "Bass"],
        "draft": True,
        "delta": 5,
    },
    "partial-parts": {
        "asset": "public/scores/e1f782a69c5812f4bcd5418a.json",
        "sourceKey": "Ab major",
        "targetKey": "Ab major",
        "parts": ["Treble", "Alto", "Tenor"],
        "draft": False,
        "delta": 0,
    },
}


def main(receipt_path: Path | None = None) -> int:
    receipt_file = receipt_path or RECEIPT
    if not receipt_file.is_absolute():
        receipt_file = ROOT / receipt_file
    if not receipt_file.is_file():
        fail(f"missing real-browser receipt {receipt_file}")
    if not PLAN.is_file():
        fail(f"missing tracked replay plan {PLAN}")
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    if receipt.get("schemaVersion") != 1:
        fail("unsupported agent-05 browser receipt schema")
    if receipt.get("git", {}).get("head") != current_head():
        fail("browser receipt was captured against a different git HEAD")
    browser = receipt.get("browser", {})
    if browser.get("url") != "http://127.0.0.1:5173/audio-harness.html":
        fail("browser receipt URL is not the isolated audio harness")
    if browser.get("title") != "Shape-Note Atlas audio harness":
        fail("browser receipt page identity drifted")
    if browser.get("contextAvailable") is not True:
        fail("browser receipt did not observe an available AudioContext")
    if browser.get("consoleErrors") or browser.get("harnessErrors"):
        fail("browser receipt contains console or harness errors")
    plan_text = PLAN.read_text(encoding="utf-8")
    for case_id in [*CASE_DEFINITIONS, "target-key-change", "automatic-end", "target-reset"]:
        if case_id not in plan_text:
            fail(f"tracked replay plan does not name required case {case_id}")

    for relative, expected_hash in (receipt.get("hashes") or {}).items():
        path = ROOT / relative
        if not path.is_file():
            fail(f"receipt hash target is missing: {relative}")
        if sha256(path) != expected_hash:
            fail(f"receipt hash is stale for {relative}")

    harness = (ROOT / "public" / "audio-harness.html").read_text(encoding="utf-8")
    wrapper_position = harness.find("window.AudioContext = TracedAudioContext")
    app_position = harness.find('app.src = "/src/main.jsx"')
    if wrapper_position < 0 or app_position < 0 or wrapper_position > app_position:
        fail("audio harness no longer wraps AudioContext before loading the app")

    observed = receipt.get("cases") or {}
    checked = 0
    for case_id, definition in CASE_DEFINITIONS.items():
        item = observed.get(case_id)
        if not isinstance(item, dict):
            fail(f"missing browser observation for {case_id}")
        asset_path = ROOT / definition["asset"]
        asset = json.loads(asset_path.read_text(encoding="utf-8"))
        expected = expected_count(asset, definition["parts"], definition["draft"])
        first = frequency(first_midi(asset, definition["parts"], definition["draft"]))
        source = item.get("source") or {}
        target = item.get("target") or {}
        if source.get("scheduled") != expected or source.get("starts") != expected:
            fail(f"{case_id}: source trace count does not match data ({expected})")
        if target.get("scheduled") != expected or target.get("starts") != expected:
            fail(f"{case_id}: target trace count does not match data ({expected})")
        if not close(source.get("firstFrequency"), first):
            fail(f"{case_id}: source first frequency is not data-derived")
        expected_target = first * 2 ** (definition["delta"] / 12)
        if not close(target.get("firstFrequency"), expected_target):
            fail(f"{case_id}: target first frequency is not the expected semitone transform")
        if not close(item.get("ratio"), 2 ** (definition["delta"] / 12)):
            fail(f"{case_id}: recorded ratio does not match the expected semitone transform")
        if item.get("manualStopCalls") != expected:
            fail(f"{case_id}: manual stop did not stop every active oscillator")
        if item.get("stopVisibleAfter") != 0 or item.get("playVisibleAfter") != 1:
            fail(f"{case_id}: stop/reset UI state was not restored")
        checked += 1

    for case_id in ("target-key-change", "automatic-end", "target-reset"):
        if not isinstance(observed.get(case_id), dict):
            fail(f"missing browser observation for {case_id}")
    cancellation = observed["target-key-change"]
    if cancellation.get("scheduled") != expected_count(
        json.loads((ROOT / CASE_DEFINITIONS["partial-parts"]["asset"]).read_text(encoding="utf-8")),
        CASE_DEFINITIONS["partial-parts"]["parts"],
        False,
    ):
        fail("target-key-change: selected-part trace count drifted")
    if cancellation.get("stopCallsFromTargetChange") != cancellation.get("scheduled"):
        fail("target-key-change: stale oscillators were not stopped")
    if cancellation.get("stopVisible") != 0 or cancellation.get("playVisible") != 1 or not cancellation.get("notice"):
        fail("target-key-change: rendered cancellation state is incomplete")

    automatic = observed["automatic-end"]
    if automatic.get("scheduled") != expected_count(
        json.loads((ROOT / CASE_DEFINITIONS["review-draft"]["asset"]).read_text(encoding="utf-8")),
        CASE_DEFINITIONS["review-draft"]["parts"],
        True,
    ):
        fail("automatic-end: draft trace count drifted")
    if automatic.get("starts") != automatic.get("scheduled") or automatic.get("stops") != automatic.get("scheduled") * 2:
        fail("automatic-end: scheduled draft oscillators did not fully end")
    if automatic.get("stopVisible") != 0 or automatic.get("playVisible") != 1:
        fail("automatic-end: Play/Stop state did not reset")

    reset = observed["target-reset"]
    if not reset.get("targetResetToSource") or reset.get("selected") != "41 — Evening Hymn":
        fail("target-reset: target key did not reset with tune selection")
    receipt_label = receipt_file.relative_to(ROOT) if receipt_file.is_relative_to(ROOT) else receipt_file
    print(json.dumps({"cases": checked, "errors": [], "receipt": str(receipt_label)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, default=RECEIPT, help="browser receipt JSON")
    raise SystemExit(main(parser.parse_args().receipt))
