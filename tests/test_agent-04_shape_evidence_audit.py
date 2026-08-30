import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/agent-04_shape_evidence_audit.py"
SPEC = importlib.util.spec_from_file_location("agent_04_shape_evidence_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
ROOT = MODULE.ROOT
run_audit = MODULE.run_audit


class Agent04ShapeEvidenceAuditTests(unittest.TestCase):
    def test_audit_is_fail_closed_and_keeps_both_81b_records(self):
        report = run_audit(render_enabled=False)
        self.assertEqual(report["summary"]["safeToPromote"], 0)
        self.assertEqual(report["summary"]["directSourceShapeEvidence"], 0)
        self.assertEqual(report["summary"]["immutableSourceChanges"], 0)
        self.assertEqual(report["summary"]["publicLedgerChanges"], 0)
        self.assertEqual(report["summary"]["uiChanges"], 0)
        self.assertEqual(len(report["windlesham81b"]["records"]), 2)
        self.assertTrue(report["windlesham81b"]["duplicateGroup"]["retainedSourceCopyByteEqual"])
        self.assertTrue(report["windlesham81b"]["duplicateGroup"]["bothRecordsShareSourceWitness"])

    def test_existing_review_layers_have_complete_structural_tags_but_are_blocked(self):
        report = run_audit(render_enabled=False)
        self.assertEqual(report["reviewSummary"]["review-drafts"]["records"], 19)
        self.assertEqual(report["reviewSummary"]["source-shape-drafts"]["records"], 90)
        self.assertEqual(report["reviewSummary"]["review-drafts"]["completeStructuralFourShapeRecords"], 19)
        self.assertEqual(report["reviewSummary"]["source-shape-drafts"]["completeStructuralFourShapeRecords"], 90)
        review_records = [item for item in report["records"] if item["recordType"] in {"review-drafts", "source-shape-drafts"}]
        self.assertEqual(len(review_records), 109)
        self.assertTrue(all(item["safeToPromote"] is False for item in review_records))
        self.assertTrue(all(item["directSourceShapeEvidence"] is False for item in review_records))
        self.assertTrue(all(any("direct per-event" in finding or "direct per-event source" in finding for finding in item["findings"]) for item in review_records))

    def test_output_does_not_overwrite_public_shape_ledger(self):
        before = (ROOT / "public/shape-evidence-audit.json").read_bytes()
        report = run_audit(render_enabled=False)
        self.assertGreater(report["summary"]["recordsAudited"], 0)
        after = (ROOT / "public/shape-evidence-audit.json").read_bytes()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
