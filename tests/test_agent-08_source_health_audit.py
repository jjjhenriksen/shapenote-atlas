#!/usr/bin/env python3
"""Focused regression tests for the agent-08 read-only source audit."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent-08_source_health_audit.py"
SPEC = importlib.util.spec_from_file_location("agent_08_source_health_audit", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Agent08SourceHealthTests(unittest.TestCase):
    def test_walk_urls_includes_scalar_urls_inside_arrays(self) -> None:
        inventory = {}
        MODULE.walk_urls({"urls": ["https://example.test/one", {"sourceUrl": "https://example.test/two"}]}, "/fixture", books=["sh2025"], reference="fixture", inventory=inventory)
        self.assertEqual(set(inventory), {"https://example.test/one", "https://example.test/two"})
        self.assertEqual(inventory["https://example.test/one"]["books"], {"sh2025"})

    def test_local_evidence_reports_exact_and_drifted_without_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "source.bin"
            path.write_bytes(b"original")
            relative = path.relative_to(root)
            evidence = {"path": str(relative), "expectedSha256": hashlib.sha256(b"original").hexdigest(), "expectedBytes": 8}
            original_root = MODULE.ROOT
            MODULE.ROOT = root
            try:
                self.assertEqual(MODULE.local_evidence_status(evidence)["status"], "exact")
                path.write_bytes(b"changed")
                self.assertEqual(MODULE.local_evidence_status(evidence)["status"], "drifted")
            finally:
                MODULE.ROOT = original_root

    def test_offline_cache_distinguishes_cached_and_not_checked(self) -> None:
        cache = {"https://example.test/cached": {"httpStatus": 200, "finalUrl": "https://example.test/cached", "checkedAt": "2026-08-30T00:00:00+00:00"}}
        cached = MODULE.cached_result("https://example.test/cached", cache)
        missing = MODULE.cached_result("https://example.test/missing", cache)
        self.assertEqual(cached["status"], "cached")
        self.assertEqual(cached["healthMode"], "cached-offline")
        self.assertEqual(missing["status"], "not-checked-offline")
        self.assertEqual(missing["healthMode"], "offline-no-cache")

    def test_report_keeps_all_books_and_81b_evidence(self) -> None:
        report = MODULE.build_report(offline=True, timeout=1, workers=1, max_urls=0)
        self.assertEqual(set(report["inventory"]["books"]), MODULE.KNOWN_BOOKS)
        self.assertGreater(report["inventory"]["urlCount"], 7000)
        self.assertGreaterEqual(report["duplicate81b"]["duplicateGroupCount"], 4)
        self.assertEqual(report["summary"]["localDrifted"], 0)


if __name__ == "__main__":
    unittest.main()
