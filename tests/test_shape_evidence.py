import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from scripts import validate_shape_evidence as shape_audit
from collections import Counter

from scripts.validate_shape_evidence import (
    build_report,
    classify_asset,
    evidence_disposition,
    shape_for_step,
    validate_fixture_checks,
)


class ShapeEvidenceTests(unittest.TestCase):
    def test_four_shape_fixture_key_cases(self):
        self.assertEqual(shape_for_step("C", "C major", "major"), "fa")
        self.assertEqual(shape_for_step("E", "C major", "major"), "la")
        self.assertEqual(shape_for_step("A", "A minor", "minor"), "la")
        self.assertEqual(shape_for_step("F", "F# minor", "minor"), "la")

    def test_unknown_and_altered_steps_fail_closed(self):
        self.assertIsNone(shape_for_step("C", "", ""))
        self.assertIsNone(shape_for_step("H", "C major", "major"))

    def test_non_four_shape_encodings_are_not_coerced(self):
        seven = classify_asset("scoreByBook", {}, 3, Counter({"do": 1, "so": 1, "ti": 1}))
        unmapped = classify_asset("scoreByBook", {}, 1, Counter({"diamond": 1}))
        derived = classify_asset("draftScoreByBook", {"kind": "omr-draft"}, 1, Counter({"fa": 1}))
        self.assertEqual(seven, "source-encoded-seven-shape-or-mixed")
        self.assertEqual(unmapped, "source-encoded-unmapped-notehead")
        self.assertEqual(evidence_disposition(seven), "source-encoded")
        self.assertEqual(evidence_disposition(derived), "derived")

    def test_report_fixture_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            public = root / "public"
            public.mkdir()
            assets = {
                "encoded.json": {"parts": [{"events": [{"step": "C", "notehead": "fa"}]}]},
                "unavailable.json": {"parts": [{"events": [{"step": "C"}]}]},
            }
            for name, payload in assets.items():
                (public / name).write_text(json.dumps(payload))
            corpus = {"songs": [{"songNo": name, "scoreByBook": {"sh1991": {"scoreRef": "/" + name}}} for name in assets]}
            corpus_path = public / "corpus.json"
            corpus_path.write_text(json.dumps(corpus))
            with patch.object(shape_audit, "ROOT", root), patch.object(shape_audit, "CORPUS", corpus_path), patch.object(shape_audit, "REVIEW_MANIFESTS", []):
                report = build_report()
        validate_fixture_checks(report)
        self.assertEqual(report["summary"]["safeToPromote"], 0)
        self.assertEqual(report["summary"]["sourceVerifiedUniqueAssets"], 0)
        self.assertEqual(report["summary"]["sourceEncodedUnverifiedUniqueAssets"], 1)
        self.assertEqual(report["summary"]["unavailableUniqueAssets"], 1)

    def test_current_corpus_remains_unpromoted_without_verification(self):
        report = build_report()
        validate_fixture_checks(report)
        self.assertEqual(report["summary"]["safeToPromote"], 0)
        self.assertEqual(report["summary"]["sourceVerifiedUniqueAssets"], 0)
        for asset in report["authoritativeAssetClassifications"]:
            self.assertFalse(asset["safeToPromote"])
            self.assertEqual(asset["sourceVerification"], "not-verified")
        for manifest in shape_audit.REVIEW_MANIFESTS:
            if not manifest.exists():
                self.assertIn(f"missing manifest: {manifest.relative_to(shape_audit.ROOT)}", report["errors"])


if __name__ == "__main__":
    unittest.main()
