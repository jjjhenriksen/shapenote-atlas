"""Regression checks for the bounded SH2025 433/437 blocker-clearing batch."""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = {
    "sh2025/433": ROOT / "work/source-transcriptions/2025/433-source-shape-autonomous-blocked-comparison.json",
    "sh2025/437": ROOT / "work/source-transcriptions/2025/437-source-shape-autonomous-blocked-comparison.json",
}


class Agent06SpringdaleEnochTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reports = {queue_id: json.loads(path.read_text(encoding="utf-8")) for queue_id, path in REPORTS.items()}

    def test_batch_contains_only_requested_records(self):
        self.assertEqual(set(self.reports), set(REPORTS))
        for queue_id, report in self.reports.items():
            self.assertEqual(report["queueId"], queue_id)
            self.assertEqual(report["comparisonStatus"], "external-source-blocked")
            self.assertEqual(report["autonomousDecision"], "external-source-blocked")
            self.assertFalse(report["safeToPromote"])
            self.assertNotIn("autonomously-blocked", json.dumps(report))

    def test_source_identity_and_direct_observations_are_preserved(self):
        expected = {
            "sh2025/433": ("Springdale", "F minor", "4/4", "Long Meter (8,8,8,8)", 16),
            "sh2025/437": ("Enoch", "F major", "3/4", "Short Meter (6,6,8,6)", 11),
        }
        for queue_id, (title, key, time_signature, meter, normalized_measures) in expected.items():
            report = self.reports[queue_id]
            observed = report["sourceAuthority"]["directObservations"]
            self.assertEqual(report["title"], title)
            self.assertEqual(observed["key"], key)
            self.assertEqual(observed["timeSignature"], time_signature)
            self.assertEqual(observed["meter"], meter)
            self.assertEqual(observed["parts"], 4)
            self.assertEqual(report["editionReconciliation"]["sh2025"]["summary"]["normalizedMeasuresByPart"]["P1"], normalized_measures)

    def test_1991_same_number_is_explicitly_replacement_evidence(self):
        expected = {
            "sh2025/433": ("McKay", "o the transporting rapturous scene", "4/4", 20, "398c6cf1e126346291fee100df7b49940af53d325ba04e3d00a7180ec74f8816"),
            "sh2025/437": ("Sidney", "my shepherd will supply my need", "6/8", 11, "915b301115a7d2fe5379260047235d62b536785c400145a575da2b47bd1e1969"),
        }
        for queue_id, (title, text_key, time_signature, measures, score_sha256) in expected.items():
            reconciliation = self.reports[queue_id]["editionReconciliation"]
            self.assertEqual(reconciliation["relationType"], "same-number-replacement-not-equivalence")
            self.assertFalse(reconciliation["equivalenceProven"])
            self.assertFalse(reconciliation["safeToUse1991As2025"])
            sh1991 = reconciliation["sh1991"]
            self.assertEqual((sh1991["title"], sh1991["textKey"], sh1991["timeSignature"]), (title, text_key, time_signature))
            self.assertEqual(sh1991["summary"]["measuresByPart"]["P1"], measures)
            self.assertEqual(sh1991["scoreSha256"], score_sha256)

    def test_no_unverified_score_is_admitted(self):
        for report in self.reports.values():
            self.assertFalse(report["editionReconciliation"]["sameSongWitness"]["authorizedExact2025"])
            self.assertFalse(report["editionReconciliation"]["sameSongWitness"]["independentSameTitleStructuredWitness"])
            self.assertEqual(report["correctedDraft"]["status"], "review-only-not-source-verified")
            self.assertGreater(len(report["blockingFindings"]), 3)
            self.assertIn("external-source", report["blockingReason"].lower())

    def test_retained_source_hashes_match_reports(self):
        for report in self.reports.values():
            path = ROOT / report["sourceAuthority"]["sourceImagePath"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), report["sourceAuthority"]["sourceImageSha256"])


if __name__ == "__main__":
    unittest.main()
