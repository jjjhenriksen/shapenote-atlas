import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/agent-04_source_correction_140_161.py"
SPEC = importlib.util.spec_from_file_location("agent_04_source_correction_140_161", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class Agent04SourceCorrectionTests(unittest.TestCase):
    def test_only_two_assigned_records_are_in_scope_and_fail_closed(self):
        self.assertEqual(set(MODULE.TARGETS), {"140", "161"})
        receipt = json.loads((MODULE.OUTPUT_ROOT / "agent-04-source-correction-receipt.json").read_text()) if (MODULE.OUTPUT_ROOT / "agent-04-source-correction-receipt.json").is_file() else None
        if receipt is None:
            receipt = {"scope": [config["queueId"] for config in MODULE.TARGETS.values()]}
        self.assertEqual(set(receipt["scope"]), {"sh2025/140", "sh2025/161"})

    def test_candidates_keep_events_but_apply_source_metadata_and_shapes(self):
        for config in MODULE.TARGETS.values():
            receipt = MODULE.build_record(config)
            correction = receipt["correction"]
            self.assertFalse(receipt["safeToPromote"])
            self.assertFalse(receipt["directSourceShapeEvidence"])
            self.assertEqual(correction["pitchEdits"], 0)
            self.assertEqual(correction["rhythmEdits"], 0)
            self.assertEqual(correction["partStructureEdits"], 0)
            self.assertGreater(correction["derivedFourShapeNoteheadsAdded"], 0)
            self.assertTrue(correction["eventStreamPreservedFromRawOmr"])
            self.assertEqual(correction["candidateStats"]["noteheads"], correction["candidateStats"]["pitchedEvents"])
            self.assertTrue(any("watermark" in finding.lower() for finding in receipt["blockingFindings"]))
            self.assertTrue(any("direct per-event" in finding.lower() for finding in receipt["blockingFindings"]))


if __name__ == "__main__":
    unittest.main()
