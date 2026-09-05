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
import tempfile
from unittest.mock import patch
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

    def test_dependency_preflight_rejects_installed_version_drift(self) -> None:
        spec = importlib.util.spec_from_file_location("verify_dependencies", ROOT / "scripts/verify_dependencies.py")
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            package = {"dependencies": {"react": "19.2.8", "react-dom": "19.2.8", "vite": "7.3.6"}}
            lock = {
                "lockfileVersion": 3,
                "packages": {
                    "": {"dependencies": package["dependencies"]},
                    "node_modules/react": {"version": "19.2.8"},
                    "node_modules/react-dom": {"version": "19.2.8"},
                    "node_modules/vite": {"version": "7.3.6"},
                },
            }
            (fixture / "package.json").write_text(json.dumps(package), encoding="utf-8")
            (fixture / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
            for name, version in (("react", "19.2.8"), ("react-dom", "19.2.8"), ("vite", "8.2.1")):
                package_dir = fixture / "node_modules" / name
                package_dir.mkdir(parents=True)
                (package_dir / "package.json").write_text(json.dumps({"version": version}), encoding="utf-8")
            with patch.object(module, "ROOT", fixture), patch("sys.stderr"), patch("sys.stdout"):
                self.assertEqual(module.main(), 1)

    def test_dependency_preflight_rejects_missing_local_install(self) -> None:
        spec = importlib.util.spec_from_file_location("verify_dependencies_missing", ROOT / "scripts/verify_dependencies.py")
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            dependencies = {"react": "19.2.8", "react-dom": "19.2.8", "vite": "7.3.6"}
            package = {"dependencies": dependencies}
            lock = {
                "lockfileVersion": 3,
                "packages": {
                    "": {"dependencies": dependencies},
                    **{f"node_modules/{name}": {"version": version} for name, version in dependencies.items()},
                },
            }
            (fixture / "package.json").write_text(json.dumps(package), encoding="utf-8")
            (fixture / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
            with patch.object(module, "ROOT", fixture), patch("sys.stderr"), patch("sys.stdout"):
                self.assertEqual(module.main(), 1)

    def test_dependency_preflight_rejects_missing_or_wrong_local_vite_bin(self) -> None:
        spec = importlib.util.spec_from_file_location("verify_dependencies_bin", ROOT / "scripts/verify_dependencies.py")
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        for mode in ("missing", "wrong"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                fixture = Path(directory)
                dependencies = {"react": "19.2.8", "react-dom": "19.2.8", "vite": "7.3.6"}
                package = {"dependencies": dependencies}
                lock = {
                    "lockfileVersion": 3,
                    "packages": {
                        "": {"dependencies": dependencies},
                        **{f"node_modules/{name}": {"version": version} for name, version in dependencies.items()},
                    },
                }
                (fixture / "package.json").write_text(json.dumps(package), encoding="utf-8")
                (fixture / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
                for name, version in dependencies.items():
                    package_dir = fixture / "node_modules" / name
                    package_dir.mkdir(parents=True)
                    metadata = {"version": version}
                    if name == "vite":
                        metadata["bin"] = {"vite": "bin/vite.js"}
                        (package_dir / "bin").mkdir()
                        (package_dir / "bin" / "vite.js").write_text("#!/usr/bin/env node\n", encoding="utf-8")
                    (package_dir / "package.json").write_text(json.dumps(metadata), encoding="utf-8")
                if mode == "wrong":
                    link_dir = fixture / "node_modules" / ".bin"
                    link_dir.mkdir()
                    (link_dir / "vite").symlink_to("../vite/wrong.js")
                with patch.object(module, "ROOT", fixture), patch("sys.stderr"), patch("sys.stdout"):
                    self.assertEqual(module.main(), 1)

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

    def test_browser_smoke_uses_tracked_checker(self) -> None:
        command = VERIFY_MODULE.browser_smoke_command()
        self.assertEqual(command, [sys.executable, str(ROOT / "scripts" / "verify_browser_smoke.py")])
        self.assertNotIn("work/agent-05-browser", command[1])
        completed = subprocess.run([*command, "--help"], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_fresh_checkout_prerequisite_report_is_explicit(self) -> None:
        report_script = ROOT / "scripts" / "report_fresh_checkout_prerequisites.py"
        completed = subprocess.run([sys.executable, str(report_script)], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["kind"], "fresh-checkout-retained-source-prerequisites")
        self.assertTrue(report["policy"]["fidelityValidatorsRemainFailClosed"])
        self.assertFalse(report["policy"]["exhaustiveAcrossDataLanes"])
        self.assertIn("generatedOutputs", report)
        self.assertEqual(report["summary"]["missingRetainedSourcePaths"], len(report["missing"]))
        self.assertIn("missing", report)

    def test_prerequisites_report_missing_evidence_in_empty_checkout(self) -> None:
        spec = importlib.util.spec_from_file_location("prerequisites", ROOT / "scripts/report_fresh_checkout_prerequisites.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(module, "ROOT", Path(directory)), patch.object(module, "load_public", return_value={}):
                report = module.build_report()
        self.assertGreater(report["summary"]["missingRetainedSourcePaths"], 0)
        self.assertEqual(report["summary"]["missingRetainedSourcePaths"], len(report["missing"]))
        self.assertNotIn("work/omr/draft-index.json", [item["path"] for item in report["missing"]])

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
