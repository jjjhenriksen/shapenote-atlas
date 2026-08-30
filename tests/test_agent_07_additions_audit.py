import json
import unittest

from scripts.agent_07_additions_audit import ROOT, audit


class Agent07AdditionsAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit(ROOT)

    def test_register_and_corpus_counts_are_reconciled(self):
        counts = self.report["counts"]
        self.assertEqual(counts["current2025Records"], 590)
        self.assertEqual(counts["additions"], 113)
        self.assertEqual(self.report["ids"]["missingAdditionIds"], [])
        self.assertEqual(counts["currentNonAdditions"], 477)
        self.assertEqual(counts["sharedRevisionRecords"], 446)
        self.assertEqual(counts["additionSharedRevisionRecords"], 2)
        self.assertEqual(counts["currentIndexOnlyRecords"], 31)
        self.assertEqual(
            counts["additions"] + counts["sharedRevisionRecords"] + counts["currentIndexOnlyRecords"],
            counts["current2025Records"],
        )

    def test_addition_semantics_are_explicit_and_fail_closed(self):
        counts = self.report["counts"]
        self.assertEqual(counts["additionExactSourcePendingCorrection"], 13)
        self.assertEqual(counts["additionReferenceOnly"], 13)
        self.assertEqual(counts["additionSourceOnlyOrDraft"], 87)
        self.assertEqual(counts["additionExactSourceTransposable"], 13)
        self.assertEqual(counts["additionExactSourceManualKey"], 0)
        self.assertEqual(counts["additionReferenceTransposable"], 9)
        self.assertEqual(counts["additionReferenceManualKey"], 4)
        self.assertEqual(
            counts["additionExactSourcePendingCorrection"]
            + counts["additionReferenceOnly"]
            + counts["additionSourceOnlyOrDraft"],
            113,
        )
        self.assertEqual(counts["exactTransposableScoreRows"], 21)
        self.assertEqual(counts["exactManualKeyRows"], 4)
        self.assertEqual(
            self.report["policy"]["drafts"],
            "draftScoreByBook is never completion or promotion evidence.",
        )

    def test_known_semantic_blockers_are_named(self):
        ids = self.report["ids"]
        self.assertEqual(ids["legacyIds"], ["sh2025/414b"])
        self.assertEqual(ids["knownSupersededExcludedIds"], ["sh2025/264b"])
        self.assertEqual(len(ids["alternateSourceMisclassifiedAsExactIds"]), 12)
        self.assertEqual(ids["nonCurrentSourceAuditIds"], ["sh2025/54-as-written"])
        self.assertEqual(len(ids["strictQueueMissingIds"]), 12)
        self.assertEqual(self.report["counts"]["additionCoverageQueueUnexpectedOmissions"], 0)
        self.assertEqual(self.report["counts"]["additionStrictQueueMissing"], 12)
        self.assertEqual(self.report["status"], "blocked")
        self.assertTrue(self.report["blockers"])

    def test_agent_report_is_written_only_under_agent_workspace(self):
        report_path = ROOT / "work" / "agent-07-additions" / "agent-07-additions-audit.json"
        # The test does not create the report; the prefixed validator does.
        if report_path.exists():
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schemaVersion"], 1)
            self.assertTrue(payload["readOnlyPublicInputs"])


if __name__ == "__main__":
    unittest.main()
