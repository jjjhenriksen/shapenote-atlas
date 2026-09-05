import json
import unittest
from pathlib import Path

from scripts.luna_meter_label_audit import build_audit, classify_meter, meter_candidates, write_once


ROOT = Path(__file__).resolve().parents[1]


class LunaMeterLabelAuditTests(unittest.TestCase):
    def test_established_shorthand_matches_explicit_sequence(self):
        result = classify_meter("8s,7s Double (8,7,8,7,8,7,8,7)", "8s & 7s D.")
        self.assertEqual(result["classification"], "formatting-equivalent")
        self.assertIn([8, 7, 8, 7, 8, 7, 8, 7], result["normalizedSequences"])

    def test_common_meter_equivalence_is_conservative(self):
        result = classify_meter("Common Meter (8,6,8,6)", "C.M.")
        self.assertEqual(result["classification"], "formatting-equivalent")

    def test_common_meter_modifiers_never_collapse(self):
        self.assertEqual(classify_meter("C.M. Double", "C.M.")["classification"], "potentially-substantive")
        self.assertEqual(classify_meter("Half Common Meter", "Common Meter")["classification"], "potentially-substantive")

    def test_empty_labels_are_unknown(self):
        self.assertEqual(classify_meter("", "")["classification"], "unknown")

    def test_mixed_three_token_shorthand_is_not_expanded(self):
        result = classify_meter("8s,7s,4s", "8,7,4,8,7,4")
        self.assertEqual(result["classification"], "unknown")

    def test_dotted_numeric_sequence_matches_common_meter(self):
        self.assertEqual(classify_meter("8.6.8.6", "Common Meter")["classification"], "formatting-equivalent")

    def test_unmodeled_iambic_qualifier_is_not_discarded(self):
        result = classify_meter("8s,7s Double Iambic (8,7,8,7,8,7,8,7)", "8s & 7s D.")
        self.assertEqual(result["classification"], "potentially-substantive")

    def test_explicit_sequence_dominates_shorthand_default(self):
        result = classify_meter("8s (8,8)", "8s.")
        self.assertEqual(result["classification"], "potentially-substantive")

    def test_double_and_half_are_not_collapsed(self):
        result = classify_meter("Long Meter (8,8,8,8)", "Long Meter Half (8,8)")
        self.assertEqual(result["classification"], "potentially-substantive")

    def test_missing_particular_sequence_fails_closed(self):
        result = classify_meter("Particular Meter: 8,3,8,3,8,8,8,3", "Particular Meter")
        self.assertEqual(result["classification"], "unknown")

    def test_no_lyrics_or_text_in_normalizer(self):
        self.assertEqual(meter_candidates("8s & 7s D."), {(8, 7, 8, 7, 8, 7, 8, 7)})

    def test_current_changed_set_is_complete_and_fail_closed(self):
        report = json.loads((ROOT / "public" / "shared-edition-reconciliation.json").read_text(encoding="utf-8"))
        audit = build_audit(report)
        self.assertEqual(len(audit["records"]), 156)
        self.assertEqual(audit["summary"]["safeToPromote"], 0)
        self.assertEqual(sum(audit["summary"]["byClassification"].values()), 156)
        self.assertTrue(all(item["rawLabels"]["sh1991"] and item["rawLabels"]["sh2025"] for item in audit["records"]))
        self.assertTrue(all(item["sourceUrls"]["sh1991"] and item["sourceUrls"]["sh2025"] for item in audit["records"]))

    def test_current_christian_song_regression_is_not_equivalent(self):
        report = json.loads((ROOT / "public" / "shared-edition-reconciliation.json").read_text(encoding="utf-8"))
        audit = build_audit(report)
        record = next(item for item in audit["records"] if item["relationId"] == "sh-edition:240")
        self.assertEqual(record["rawLabels"], {"sh1991": "8s (8,8)", "sh2025": "8s."})
        self.assertEqual(record["classification"], "potentially-substantive")

    def test_write_once_refuses_different_repeat_and_preserves_bytes(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            write_once(path, "first\n")
            with self.assertRaises(FileExistsError):
                write_once(path, "second\n")
            self.assertEqual(path.read_text(encoding="utf-8"), "first\n")


if __name__ == "__main__":
    unittest.main()
