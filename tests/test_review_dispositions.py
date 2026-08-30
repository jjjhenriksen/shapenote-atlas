import unittest

from scripts.review_dispositions import (
    comparison_disposition,
    image_review_disposition,
    transcription_disposition,
)


class ReviewDispositionTests(unittest.TestCase):
    def test_comparison_states_fail_closed(self):
        self.assertEqual(comparison_disposition({"autonomousDecision": "blocked"})["state"], "autonomously-blocked")
        self.assertEqual(comparison_disposition({"comparisonStatus": "rejected-source-mismatch"})["state"], "rejected")
        self.assertEqual(comparison_disposition({"autonomousDecision": "verified-with-correction-needed"})["state"], "review-only")
        self.assertEqual(comparison_disposition({})["state"], "unavailable")

    def test_image_review_requires_human_comparison(self):
        result = image_review_disposition()
        self.assertEqual(result["state"], "review-only")
        self.assertTrue(result["humanReviewRequired"])
        self.assertTrue(result["reviewAvailable"])
        self.assertFalse(result["safeToPromote"])

    def test_source_reference_is_observed_not_structured(self):
        result = transcription_disposition("source-reference", ["https://example.test/page"])
        self.assertEqual(result["state"], "source-observed")
        self.assertFalse(result["humanReviewRequired"])
        self.assertFalse(result["safeToPromote"])


if __name__ == "__main__":
    unittest.main()
