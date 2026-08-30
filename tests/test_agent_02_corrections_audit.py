from __future__ import annotations

import unittest
import importlib.util
import json
from pathlib import Path

from scripts.review_dispositions import comparison_disposition

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts/agent-02_corrections_audit.py"
SPEC = importlib.util.spec_from_file_location("agent_02_corrections_audit", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
EXPECTED_QUEUE_IDS = MODULE.EXPECTED_QUEUE_IDS
ROOT = MODULE.ROOT
audit = MODULE.audit


class Agent02CorrectionsAuditTests(unittest.TestCase):
    def test_bounded_batch_is_complete_and_fail_closed(self) -> None:
        payload = audit(ROOT)
        self.assertEqual(payload["status"], "valid", payload["errors"])
        self.assertEqual(payload["summary"]["records"], 13)
        self.assertEqual(payload["summary"]["autonomouslyBlocked"], 13)
        self.assertEqual(payload["summary"]["rejected"], 0)
        self.assertEqual(payload["summary"]["safeToPromote"], 0)
        self.assertEqual(
            {record["queueId"] for record in payload["records"]}, EXPECTED_QUEUE_IDS
        )

    def test_every_record_has_independent_event_and_lyric_evidence(self) -> None:
        payload = audit(ROOT)
        for record in payload["records"]:
            self.assertTrue(record["eventEvidence"]["eventStreamEqual"], record["queueId"])
            self.assertTrue(
                record["eventEvidence"]["candidateAndCorrectedStructuralCountsAgree"],
                record["queueId"],
            )
            self.assertTrue(record["lyricEvidence"]["sourceLyricsVisible"], record["queueId"])
            self.assertTrue(
                record["sourceScanInspection"]["fourShapeNoteheadsVisible"],
                record["queueId"],
            )
            self.assertEqual(record["lyricEvidence"]["candidateLyricElements"], 0)
            self.assertEqual(record["lyricEvidence"]["correctedLyricElements"], 0)
            self.assertFalse(record["lyricEvidence"]["directSyllableAlignmentEstablished"])
            self.assertFalse(record["lyricEvidence"]["lyricsFabricated"])

    def test_13_correction_records_expose_usable_notation_separately(self) -> None:
        ledger = json.loads(
            (ROOT / "public/source-comparison-ledger.json").read_text(encoding="utf-8")
        )
        rows = [
            row
            for row in ledger["records"]
            if row.get("comparisonStatus") == "verified-with-correction-needed"
            and row.get("autonomousDecision") == "blocked"
        ]
        self.assertEqual(len(rows), 13)
        for row in rows:
            disposition = comparison_disposition(row)
            self.assertEqual(disposition["state"], "review-only", row["queueId"])
            self.assertEqual(
                disposition["notationStatus"], "source-aligned-playable", row["queueId"]
            )
            self.assertEqual(disposition["playbackStatus"], "source-order", row["queueId"])
            self.assertEqual(
                disposition["transpositionStatus"], "available", row["queueId"]
            )
            self.assertEqual(disposition["semanticLimitations"], ["lyrics-not-encoded"])
            self.assertFalse(disposition["safeToPromote"])


if __name__ == "__main__":
    unittest.main()
