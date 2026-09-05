import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SharedEditionReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads((ROOT / "public" / "corpus.json").read_text(encoding="utf-8"))
        cls.report = json.loads(
            (ROOT / "public" / "shared-edition-reconciliation.json").read_text(encoding="utf-8")
        )
        cls.records = {
            (str(record["identity"].get("songNo", "")).lower(), record["identity"].get("songId", "")): record
            for record in cls.report["records"]
        }

    def test_current_shared_pair_set_and_witness_counts_are_reconciled(self):
        shared = {
            (str(song.get("songNo", "")).lower(), song.get("id", "")): song
            for song in self.corpus["songs"]
            if {"sh1991", "sh2025"}.issubset(song.get("books", []))
        }
        self.assertEqual(len(shared), 448)
        self.assertEqual(set(self.records), set(shared))
        self.assertEqual(self.report["summary"]["sharedPairs"], len(shared))
        self.assertEqual(
            self.report["summary"]["witnessCounts"]["sh2025"],
            {"exactScore": 0, "referenceScore": 446, "reviewDraft": 3},
        )

    def test_467_and_515_alternate_witnesses_never_count_as_exact_sh2025(self):
        for song_no in ("467", "515"):
            song = next(
                song
                for song in self.corpus["songs"]
                if song.get("songNo") == song_no and {"sh1991", "sh2025"}.issubset(song.get("books", []))
            )
            key = (song_no, song["id"])
            record = self.records[key]
            self.assertNotIn("sh2025", song.get("scoreByBook", {}))
            self.assertIn("sh2025", song.get("referenceScoreByBook", {}))
            witness = record["witnesses"]["sh2025"]["referenceScoreByBook"]
            self.assertEqual(witness["role"], "alternate-reference")
            self.assertFalse(record["comparisons"]["notation"]["exactEditionWitnesses"])
            self.assertIn("sh2025-exact-score-unavailable", record["classifications"])


if __name__ == "__main__":
    unittest.main()
