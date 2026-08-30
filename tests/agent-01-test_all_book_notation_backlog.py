#!/usr/bin/env python3
"""Focused invariants for the agent-01 all-book backlog report."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent-01-build-all-book-notation-backlog.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("agent_01_backlog_builder", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load agent-01 backlog builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Agent01AllBookNotationBacklogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_builder()
        cls.report = cls.builder.build_report()

    def test_current_queue_is_fully_covered_across_all_books(self):
        summary = self.report["summary"]
        self.assertEqual(summary["books"], 11)
        self.assertEqual(summary["records"], 3035)
        self.assertEqual(summary["sourceReferenceRecords"], 3029)
        self.assertEqual(summary["transcriptionBlockedRecords"], 6)
        self.assertEqual(summary["structuredManifestEntries"], 1169)

    def test_every_record_is_fail_closed_and_has_source_evidence(self):
        records = self.report["records"]
        self.assertEqual(len({item["canonicalRecordId"] for item in records}), len(records))
        for item in records:
            self.assertTrue(item["sourceEvidence"]["sourceUrls"], item["canonicalRecordId"])
            self.assertFalse(item["sourceEvidence"]["manifestExactScoreEntry"])
            self.assertFalse(item["sourceEvidence"]["noteLevelComparisonRecorded"])
            self.assertFalse(item["sourceEvidence"]["musicXmlProduced"])
            self.assertFalse(item["disposition"]["safeToPromote"])
            self.assertTrue(item["disposition"]["reason"])

    def test_protected_records_are_explicit_and_untouched(self):
        by_id = {item["canonicalRecordId"]: item for item in self.report["records"]}
        for record_id in ("sh2025/115", "sh2025/116"):
            self.assertEqual(by_id[record_id]["disposition"]["state"], "protected-active-first-batch")
            self.assertIn("untouched", by_id[record_id]["disposition"]["reason"])

    def test_report_is_reproducible_from_current_input_contract(self):
        report_path = ROOT / "work" / "agent-01-notation" / "all-book-notation-backlog.json"
        if report_path.exists():
            materialized = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(materialized["summary"], self.report["summary"])
            self.assertEqual(materialized["byBook"], self.report["byBook"])


if __name__ == "__main__":
    unittest.main()
