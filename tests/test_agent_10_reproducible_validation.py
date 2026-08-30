"""Regression checks for the agent-10 verification snapshot.

These checks read generated reports only. They do not rebuild data, refresh
source-health timestamps, start a server, or change the user's checkout.
When the generated snapshot changes, the expected values below force the
verification note and backlog evidence to be reconciled together.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_public(name: str) -> dict:
    return json.loads((ROOT / "public" / name).read_text(encoding="utf-8"))


class Agent10ReproducibleValidationTests(unittest.TestCase):
    def test_generated_report_counts_match_current_snapshot(self) -> None:
        corpus = load_public("corpus.json")
        coverage = load_public("source-coverage.json")
        transcription = load_public("transcription-queue.json")
        review = load_public("human-review-queue.json")
        comparison = load_public("source-comparison-ledger.json")
        score_audit = load_public("shapenote-2025-score-audit.json")
        key_reconciliation = load_public("sh2025-reference-key-reconciliation.json")
        autonomous = load_public("sacred-harp-2025-autonomous-reconciliation.json")
        source_health = load_public("source-health.json")

        self.assertEqual(len(corpus["songs"]), 3547)
        self.assertEqual(
            coverage["summary"],
            {
                "editionRecords": 4202,
                "structuredScores": 1167,
                "transposableReferenceWitnesses": 475,
                "sourceReferences": 3029,
                "metadataOnly": 0,
                "mappingGaps": 0,
            },
        )
        self.assertEqual(transcription["summary"]["total"], 3035)
        self.assertEqual(
            transcription["summary"]["byStatus"],
            {"source-reference": 3029, "transcription-blocked": 6},
        )
        self.assertEqual(review["summary"]["optionalReviewItems"], 122)
        self.assertEqual(review["summary"]["humanReviewRequired"], 0)
        self.assertEqual(review["summary"]["sourceShapeReviewDrafts"], 90)
        self.assertEqual(review["summary"]["sourceComparisons"], 166)
        self.assertEqual(review["summary"]["sourceComparisonsSafeToPromote"], 0)
        self.assertEqual(comparison["summary"]["records"], 180)
        self.assertEqual(comparison["summary"]["errors"], 0)
        self.assertEqual(comparison["summary"]["safeToPromote"], 0)
        self.assertEqual(score_audit["summary"], {
            "catalogEntries": 26,
            "errors": 0,
            "safeToPromote": 0,
            "statusCounts": {
                "external-source-blocked": 13,
                "verified-with-correction-needed": 13,
            },
        })
        self.assertEqual(key_reconciliation["summary"], {
            "targetRecords": 61,
            "directSourceKeyObservations": 3,
            "referenceWitnessKeysApplied": 0,
            "sourceKeyVerifiedReferenceOnly": 3,
            "autonomouslyBlocked": 0,
            "externalSourceBlocked": 58,
            "safeToPromote": 0,
            "humanReviewRequired": 0,
            "corpusRecordsChanged": 0,
            "recordsStillWithoutAutonomousDisposition": 0,
        })
        self.assertEqual(autonomous["summary"]["current2025MissingStructuredScore"], 90)
        self.assertEqual(autonomous["summary"]["recordsWithPerRecordAuditEvidence"], 90)
        self.assertEqual(autonomous["summary"]["recordsStillWithoutAutonomousDisposition"], 0)
        self.assertEqual(autonomous["summary"]["safeToPromote"], 0)
        self.assertEqual(source_health["summary"], {
            "byStatus": {"cached": 3738},
            "localDrifted": 0,
            "localExact": 1349,
            "localMissing": 0,
            "totalUrls": 3738,
            "withLocalEvidence": 1324,
        })

    def test_current_sh2025_population_is_25_structured_475_reference_90_missing(self) -> None:
        corpus = load_public("corpus.json")
        rows = [song for song in corpus["songs"] if "sh2025" in song.get("books", [])]
        structured = [song for song in rows if song.get("scoreByBook", {}).get("sh2025")]
        reference = [song for song in rows if song.get("referenceScoreByBook", {}).get("sh2025")]
        missing = [
            song
            for song in rows
            if not song.get("scoreByBook", {}).get("sh2025")
            and not song.get("referenceScoreByBook", {}).get("sh2025")
        ]
        self.assertEqual(len(rows), 590)
        self.assertEqual(len(structured), 25)
        self.assertEqual(len(reference), 475)
        self.assertEqual(len(missing), 90)


if __name__ == "__main__":
    unittest.main()
