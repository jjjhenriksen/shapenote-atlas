#!/usr/bin/env python3
"""Read-only integrity tests for the agent-04 Cunningham/Mournful Joy receipt."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/agent-04_source_verification_561_562.py"
spec = importlib.util.spec_from_file_location("agent_04_source_verification_561_562", SCRIPT)
MODULE = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(MODULE)


class SourceVerification561562Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt_path = ROOT / "work/agent-04-shapes/blocker-clearing-561-562/agent-04-source-verification-receipt.json"
        cls.receipt = json.loads(cls.receipt_path.read_text(encoding="utf-8"))

    def test_receipt_is_exactly_scoped_and_fail_closed(self) -> None:
        self.assertEqual(self.receipt["scope"], ["sh2025/561", "sh2025/562"])
        self.assertEqual(self.receipt["summary"]["records"], 2)
        self.assertEqual(self.receipt["summary"]["blocked"], 2)
        self.assertEqual(self.receipt["summary"]["safeToPromote"], 0)
        self.assertEqual(self.receipt["summary"]["directPerEventSourceShapeMatches"], 0)
        self.assertEqual(self.receipt["summary"]["verifiedPitchedEvents"], 0)

    def test_candidates_preserve_events_and_have_review_only_metadata(self) -> None:
        for record in self.receipt["records"]:
            candidate = ROOT / record["candidate"]["path"]
            raw = ROOT / record["rawOmr"]["path"]
            self.assertEqual(hashlib.sha256(candidate.read_bytes()).hexdigest(), record["candidate"]["sha256"])
            with zipfile.ZipFile(candidate) as candidate_zip, zipfile.ZipFile(raw) as raw_zip:
                self.assertIsNone(candidate_zip.testzip())
                self.assertIsNone(raw_zip.testzip())
                candidate_name = next(name for name in candidate_zip.namelist() if name.endswith(".xml") and not name.startswith("META-INF/"))
                raw_name = next(name for name in raw_zip.namelist() if name.endswith(".xml") and not name.startswith("META-INF/"))
                candidate_root = ET.fromstring(candidate_zip.read(candidate_name))
                raw_root = ET.fromstring(raw_zip.read(raw_name))
            self.assertEqual(MODULE.event_signature(candidate_root), MODULE.event_signature(raw_root))
            fields = {field.attrib.get("name"): field.text for field in candidate_root.findall(".//miscellaneous-field")}
            self.assertEqual(fields["atlas-safe-to-promote"], "false")
            self.assertEqual(fields["atlas-review-status"], "agent-04-source-verification-needed")
            self.assertGreater(record["candidate"]["derivedFourShapeNoteheads"], 0)
            shapes = {node.text for node in candidate_root.findall(".//notehead")}
            self.assertTrue(shapes <= MODULE.ALLOWED_SHAPES)

    def test_playable_witness_is_not_source_verified(self) -> None:
        for record in self.receipt["records"]:
            playable = record["playableDraft"]
            self.assertEqual(playable["keyEvidence"]["status"], "source-observed")
            self.assertEqual(playable["timeSignature"], "")
            self.assertTrue(all(not declaration["modePresent"] for declaration in playable["keyDeclarations"]))


if __name__ == "__main__":
    unittest.main()
