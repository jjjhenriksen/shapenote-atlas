"""Focused checks for the retained-source reproducibility manifest."""

from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_retained_source_dependency_manifest.py"
SPEC = importlib.util.spec_from_file_location("retained_source_dependencies", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RetainedSourceDependencyManifestTests(unittest.TestCase):
    def build_report(self, *, cwd: Path | None = None) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "manifest.json"
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--output", str(output)],
                cwd=cwd or ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return json.loads(output.read_text(encoding="utf-8"))

    def test_report_is_deterministic_and_covers_each_requested_dependency_layer(self) -> None:
        first = self.build_report()
        with tempfile.TemporaryDirectory() as directory:
            second = self.build_report(cwd=Path(directory))
        self.assertEqual(first, second)

        records = first["records"]
        self.assertEqual(first["summary"]["totalDependencies"], len(records))
        self.assertGreaterEqual(first["summary"]["artifactClassCounts"]["exact-score-witness"], 1000)
        self.assertGreaterEqual(first["summary"]["artifactClassCounts"]["candidate-pdf-witness"], 90)
        self.assertGreaterEqual(first["summary"]["artifactClassCounts"]["derived-candidate-mxl"], 90)
        self.assertGreaterEqual(first["summary"]["artifactClassCounts"]["derived-review-draft"], 19)
        self.assertGreaterEqual(first["summary"]["artifactClassCounts"]["immutable-retained-source"], 200)
        self.assertGreaterEqual(first["summary"]["artifactClassCounts"]["derived-normalized-image"], 200)
        self.assertGreaterEqual(first["summary"]["artifactClassCounts"]["derived-suppressed-image"], 200)
        self.assertGreaterEqual(first["summary"]["artifactClassCounts"]["source-health-local-evidence"], 1)
        self.assertIn("public/source-health.json", {record["path"] for record in records})
        self.assertTrue(all(" 2" not in record["path"] for record in records))
        for record in records:
            self.assertTrue(record["path"])
            self.assertIn(record["status"], {"present", "missing", "hash-mismatch", "byte-count-mismatch", "conflicting-expectations", "unavailable", "unavailable-cloud-placeholder"})
            if record["status"] == "present":
                self.assertIsInstance(record["bytes"], int)
                self.assertEqual(len(record["sha256"]), 64)
            else:
                self.assertNotEqual(record["status"], "present")

    def test_relative_paths_are_root_anchored_and_normalized(self) -> None:
        self.assertEqual(MODULE.path_text("work/../public/corpus.json"), "public/corpus.json")
        self.assertEqual(MODULE.path_text("../outside-the-repository.txt"), "")
        report = self.build_report()
        self.assertIn("public/corpus.json", {record["path"] for record in report["records"]})

    def test_absent_retained_dependency_is_explicitly_non_passing(self) -> None:
        collector = MODULE.DependencyCollector(set())
        collector.add(
            "work/does-not-exist/retained-source.mxl",
            artifact_class="exact-score-witness",
            consumers=("scripts/validate_data.py",),
            gates=("data",),
            source_urls=("https://example.invalid/retained-source.mxl",),
            expected_sha256="0" * 64,
            immutable=True,
            derived=False,
            reference="test",
        )
        record = collector.finish()[0]
        self.assertEqual(record["status"], "missing")
        self.assertIsNone(record["bytes"])
        self.assertEqual(record["sha256"], "")
        self.assertNotEqual(record["status"], "present")

    def test_conflicting_expectations_never_accept_a_match_to_only_one_witness(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "same-source.bin"
            path.write_bytes(b"retained bytes")
            relative = path.relative_to(ROOT).as_posix()
            collector = MODULE.DependencyCollector(set())
            collector.add(relative, artifact_class="exact-score-witness", expected_sha256="1" * 64, reference="first")
            collector.add(relative, artifact_class="exact-score-witness", expected_sha256="2" * 64, reference="second")
            record = collector.finish()[0]
        self.assertEqual(record["status"], "conflicting-expectations")
        self.assertEqual(record["expectedSha256"], ["1" * 64, "2" * 64])
        self.assertEqual(record["references"], ["first", "second"])

    def test_zero_byte_regular_file_is_not_classified_as_cloud_placeholder(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "empty-source.bin"
            path.touch()
            collector = MODULE.DependencyCollector(set())
            collector.add(path.relative_to(ROOT).as_posix(), artifact_class="immutable-retained-source")
            record = collector.finish()[0]
        self.assertEqual(record["status"], "present")
        self.assertEqual(record["bytes"], 0)
        self.assertEqual(record["sha256"], hashlib.sha256(b"").hexdigest())


if __name__ == "__main__":
    unittest.main()
