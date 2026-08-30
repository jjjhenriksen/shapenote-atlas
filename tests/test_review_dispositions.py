import unittest

from scripts.review_dispositions import (
    aggregate_comparison_disposition,
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

    def test_correction_needed_separates_playable_notation_from_lyrics_limit(self):
        result = comparison_disposition(
            {
                "autonomousDecision": "verified-with-correction-needed",
                "comparisonEvidence": {
                    "sourceScanInspected": True,
                    "eventStreamEqual": True,
                },
                "correctedDraft": {
                    "path": "work/corrected.mxl",
                    "summary": {
                        "parts": 4,
                        "measuresByPart": {"P1": 8, "P2": 8, "P3": 8, "P4": 8},
                        "pitchedEvents": 20,
                        "shapeNoteheadsAdded": 20,
                    },
                },
            }
        )
        self.assertEqual(result["state"], "review-only")
        self.assertEqual(result["notationStatus"], "source-aligned-playable")
        self.assertEqual(result["playbackStatus"], "source-order")
        self.assertEqual(result["transpositionStatus"], "available")
        self.assertEqual(result["semanticLimitations"], ["lyrics-not-encoded"])
        self.assertFalse(result["safeToPromote"])

    def test_correction_needed_without_event_proof_stays_unavailable(self):
        result = comparison_disposition(
            {"autonomousDecision": "verified-with-correction-needed"}
        )
        self.assertEqual(result["notationStatus"], "unavailable")
        self.assertEqual(result["playbackStatus"], "unavailable")
        self.assertEqual(result["transpositionStatus"], "unavailable")
        self.assertEqual(result["semanticLimitations"], [])

    def test_source_aligned_correction_wins_over_duplicate_external_block(self):
        result = aggregate_comparison_disposition(
            [
                {
                    "comparisonStatus": "external-source-blocked",
                    "autonomousDecision": "external-source-blocked",
                },
                {
                    "comparisonStatus": "verified-with-correction-needed",
                    "autonomousDecision": "blocked",
                    "comparisonEvidence": {
                        "sourceScanInspected": True,
                        "eventStreamEqual": True,
                    },
                    "correctedDraft": {
                        "path": "work/corrected.mxl",
                        "summary": {
                            "parts": 4,
                            "measuresByPart": {"P1": 8, "P2": 8, "P3": 8, "P4": 8},
                            "pitchedEvents": 20,
                            "shapeNoteheadsAdded": 20,
                        },
                    },
                },
            ]
        )
        self.assertEqual(result["state"], "review-only")
        self.assertEqual(result["notationStatus"], "source-aligned-playable")
        self.assertFalse(result["safeToPromote"])

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
