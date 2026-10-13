import json
import tempfile
import unittest
from pathlib import Path

from scripts.agent_07_additions_audit import ROOT, audit


def fixture(root, corrected=False):
    public = root / "public"
    public.mkdir()
    songs = []
    for number in range(1, 6):
        kind = "structured-score" if number in (1, 2) else "source-only"
        row = {"songNo": str(number), "books": ["sh2025"], "sourceCoverageByBook": {"sh2025": {"status": kind, "editionStatus": "added-in-2025" if number < 5 else "not-new-in-2025"}}}
        if number in (1, 2):
            row["scoreByBook"] = {"sh2025": {"transposition": {"available": number == 1}}}
        if number == 3:
            row["referenceScoreByBook"] = {"sh2025": {"transposition": {"available": True}}}
        if number == 4:
            row["draftScoreByBook"] = {"sh2025": {"kind": "unverified"}}
        if number == 5:
            row["books"].append("sh1991")
        songs.append(row)
    if corrected:
        songs[1]["referenceScoreByBook"] = songs[1].pop("scoreByBook")
        songs[1]["sourceCoverageByBook"]["sh2025"]["status"] = "reference-only"
    queued = [3, 4, 5] + ([2] if corrected else [])
    payloads = {
        "corpus.json": {"songs": songs, "legacyEditionRecords": [{"bookId": "sh2025", "songNo": "414b"}]},
        "edition-2025-additions.json": {"edition": "sh2025", "count": 4, "records": ["1", "2", "3", "4"]},
        "transcription-queue.json": {"records": [{"queueId": f"sh2025/{n}"} for n in queued]},
        "human-review-queue.json": {"reviewNow": [{"queueId": "sh2025/4"}]},
        "image-review-queue.json": {"records": [{"queueId": f"sh2025/{n}"} for n in [4, 5]]},
        "shapenote-2025-score-audit.json": {"records": [
            {"queueId": "sh2025/1", "comparisonStatus": "verified-with-correction-needed"},
            {"queueId": "sh2025/2", "comparisonStatus": "external-source-blocked"},
        ]},
    }
    for name, payload in payloads.items():
        (public / name).write_text(json.dumps(payload))


class Agent07AdditionsAuditTests(unittest.TestCase):
    def test_controlled_historical_defect_is_detected_without_promoting_drafts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            report = audit(root)
        counts = report["counts"]
        self.assertEqual(counts["current2025Records"], 5)
        self.assertEqual(counts["additions"], 4)
        self.assertEqual(counts["additionExactSourcePendingCorrection"], 1)
        self.assertEqual(counts["additionReferenceOnly"], 2)
        self.assertEqual(counts["additionReferenceTransposable"], 1)
        self.assertEqual(counts["additionReferenceManualKey"], 1)
        self.assertEqual(counts["additionSourceOnlyOrDraft"], 1)
        self.assertEqual(report["ids"]["alternateSourceMisclassifiedAsExactIds"], ["sh2025/2"])
        self.assertEqual(report["ids"]["strictQueueMissingIds"], ["sh2025/2"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["policy"]["drafts"], "draftScoreByBook is never completion or promotion evidence.")

    def test_corrected_reference_is_separate_and_has_its_own_queue_row(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, corrected=True)
            report = audit(root)
        self.assertEqual(report["ids"]["alternateSourceMisclassifiedAsExactIds"], [])
        self.assertEqual(report["ids"]["strictQueueMissingIds"], [])
        self.assertEqual(report["counts"]["additionExactSourcePendingCorrection"], 1)
        self.assertEqual(report["counts"]["additionReferenceOnly"], 2)

    def test_current_corpus_partitions_without_historical_snapshot_counts(self):
        report = audit(ROOT)
        counts = report["counts"]
        additions = json.loads((ROOT / "public" / "edition-2025-additions.json").read_text())
        self.assertEqual(counts["additions"], len(additions["records"]))
        self.assertEqual(counts["additions"] + counts["sharedRevisionRecords"] + counts["currentIndexOnlyRecords"], counts["current2025Records"])
        self.assertEqual(counts["additionExactSourcePendingCorrection"] + counts["additionReferenceOnly"] + counts["additionSourceOnlyOrDraft"], counts["additions"])
        self.assertEqual(report["ids"]["missingAdditionIds"], [])
        self.assertEqual(report["ids"]["alternateSourceMisclassifiedAsExactIds"], [])
        self.assertTrue(report["readOnlyPublicInputs"])


if __name__ == "__main__":
    unittest.main()
