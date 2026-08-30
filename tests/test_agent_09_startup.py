from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/agent-09-startup-smoke.py"
SPEC = importlib.util.spec_from_file_location("agent_09_startup_smoke", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Agent09StartupTests(unittest.TestCase):
    def test_representatives_cover_required_states(self) -> None:
        corpus = json.loads((ROOT / "public/corpus.json").read_text(encoding="utf-8"))
        selected = MODULE.choose_representatives(corpus)
        self.assertEqual(
            {item["kind"] for item in selected.values()},
            {"exact-score", "unknown-key", "reference-witness", "review-draft", "missing-notation"},
        )
        self.assertTrue(selected["exact"]["asset"].startswith("/scores/"))
        self.assertTrue(selected["unknownKey"]["asset"].startswith("/scores/"))
        self.assertTrue(selected["reference"]["asset"].startswith("/scores/"))
        self.assertTrue(selected["draft"]["asset"].startswith("/draft-scores/"))
        self.assertIsNone(selected["missingNotation"]["asset"])

    def test_asset_check_fails_closed_for_missing_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "assets").mkdir()
            (root / "index.html").write_text('<script src="/assets/missing.js"></script>', encoding="utf-8")
            with self.assertRaises(MODULE.StartupCheckError):
                MODULE.check_html_assets(root)

    def test_resource_tree_detects_stale_packaged_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            dist = root / "dist"
            package = root / "package"
            dist.mkdir()
            package.mkdir()
            (dist / "index.html").write_text("same", encoding="utf-8")
            (package / "index.html").write_text("stale", encoding="utf-8")
            with self.assertRaises(MODULE.StartupCheckError):
                MODULE.compare_trees(dist, package)


if __name__ == "__main__":
    unittest.main()
