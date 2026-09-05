"""Regression checks for the current generated-report contract.

These checks read generated reports only. They do not rebuild data, refresh
source-health timestamps, start a server, or change the user's checkout.
Generated counts are owned by the data and health lanes and may change as
source evidence is integrated; these checks validate cross-report invariants
and fail-closed promotion semantics instead of pinning a stale snapshot.
"""

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_SPEC = importlib.util.spec_from_file_location("verify_all", ROOT / "scripts/verify_all.py")
assert VERIFY_SPEC and VERIFY_SPEC.loader
VERIFY_MODULE = importlib.util.module_from_spec(VERIFY_SPEC)
VERIFY_SPEC.loader.exec_module(VERIFY_MODULE)


def load_public(name: str) -> dict:
    return json.loads((ROOT / "public" / name).read_text(encoding="utf-8"))


class Agent10ReproducibleValidationTests(unittest.TestCase):
    def test_dependency_lock_preflight_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts/verify_dependencies.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_command_timeout_terminates_its_process_group(self) -> None:
        check = VERIFY_MODULE.run_command(
            "sleeping-test",
            [sys.executable, "-c", "import time; time.sleep(10)"],
            timeout=1,
        )
        self.assertEqual(check["status"], "failed")
        self.assertIn("timed out", check["detail"])

    def test_browser_receipt_override_is_explicit_and_narrow(self) -> None:
        default_command = VERIFY_MODULE.browser_smoke_command()
        override = Path("work/luna-program-20260904/ui/agent-11-browser-receipt.json")
        override_command = VERIFY_MODULE.browser_smoke_command(override)
        self.assertIsNotNone(default_command)
        self.assertIsNotNone(override_command)
        assert default_command is not None and override_command is not None
        self.assertEqual(override_command[:-2], default_command)
        self.assertEqual(override_command[-2:], ["--receipt", str((ROOT / override).resolve())])

    def test_shared_edition_reconciliation_gate_is_registered_and_passes(self) -> None:
        commands = dict(VERIFY_MODULE.validation_commands())
        self.assertEqual(
            commands["shared-edition-reconciliation"],
            [sys.executable, "scripts/validate_shared_edition_reconciliation.py"],
        )
        names = [name for name, _ in VERIFY_MODULE.validation_commands()]
        self.assertLess(names.index("shared-edition-reconciliation"), names.index("omr-audit"))
        completed = subprocess.run(
            commands["shared-edition-reconciliation"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('"sharedPairs": 448', completed.stdout)

    def test_generated_report_counts_match_current_snapshot(self) -> None:
        corpus = load_public("corpus.json")
        coverage = load_public("source-coverage.json")
        transcription = load_public("transcription-queue.json")
        review = load_public("human-review-queue.json")
        comparison = load_public("source-comparison-ledger.json")
        score_audit = load_public("shapenote-2025-score-audit.json")
        key_reconciliation = load_public("sh2025-reference-key-reconciliation.json")
        autonomous = load_public("sacred-harp-2025-autonomous-reconciliation.json")
        source_health = load_public("source-health.json")

        self.assertIsInstance(corpus.get("songs"), list)
        self.assertGreater(len(corpus["songs"]), 0)
        coverage_summary = coverage["summary"]
        for key in ("editionRecords", "structuredScores", "transposableReferenceWitnesses", "sourceReferences", "metadataOnly", "mappingGaps"):
            self.assertIsInstance(coverage_summary.get(key), int)
            self.assertGreaterEqual(coverage_summary[key], 0)
        self.assertEqual(
            coverage_summary["editionRecords"],
            coverage_summary["structuredScores"] + coverage_summary["sourceReferences"] + transcription["summary"]["byStatus"].get("transcription-blocked", 0),
        )
        self.assertEqual(transcription["summary"]["total"], sum(transcription["summary"]["byBook"].values()))
        self.assertEqual(transcription["summary"]["total"], sum(transcription["summary"]["byStatus"].values()))
        self.assertGreaterEqual(review["summary"]["optionalReviewItems"], 0)
        self.assertEqual(review["summary"]["humanReviewRequired"], 0)
        self.assertEqual(review["summary"]["sourceComparisonsSafeToPromote"], 0)
        self.assertEqual(comparison["summary"]["records"], sum(comparison["summary"]["statusCounts"].values()))
        self.assertEqual(comparison["summary"]["errors"], 0)
        self.assertEqual(comparison["summary"]["safeToPromote"], 0)
        self.assertEqual(score_audit["summary"]["errors"], 0)
        self.assertEqual(score_audit["summary"]["safeToPromote"], 0)
        self.assertEqual(key_reconciliation["summary"]["safeToPromote"], 0)
        self.assertEqual(key_reconciliation["summary"]["humanReviewRequired"], 0)
        self.assertEqual(autonomous["summary"]["recordsStillWithoutAutonomousDisposition"], 0)
        self.assertEqual(autonomous["summary"]["recordsStillWithoutAutonomousDisposition"], 0)
        self.assertEqual(autonomous["summary"]["safeToPromote"], 0)
        source_summary = source_health["summary"]
        self.assertIsInstance(source_summary.get("totalUrls"), int)
        self.assertGreater(source_summary["totalUrls"], 0)
        self.assertIsInstance(source_summary.get("byStatus"), dict)
        self.assertEqual(sum(source_summary["byStatus"].values()), source_summary["totalUrls"])
        self.assertGreaterEqual(source_summary.get("withLocalEvidence", 0), 0)
        self.assertLessEqual(source_summary.get("withLocalEvidence", 0), source_summary["totalUrls"])

    def test_current_sh2025_population_is_partitioned_without_double_counting(self) -> None:
        corpus = load_public("corpus.json")
        rows = [song for song in corpus["songs"] if "sh2025" in song.get("books", [])]
        structured = [song for song in rows if song.get("scoreByBook", {}).get("sh2025")]
        reference = [song for song in rows if song.get("referenceScoreByBook", {}).get("sh2025")]
        missing = [
            song
            for song in rows
            if not song.get("scoreByBook", {}).get("sh2025")
            and not song.get("referenceScoreByBook", {}).get("sh2025")
        ]
        self.assertGreater(len(rows), 0)
        self.assertEqual(len(rows), len(structured) + len(reference) + len(missing))


if __name__ == "__main__":
    unittest.main()
