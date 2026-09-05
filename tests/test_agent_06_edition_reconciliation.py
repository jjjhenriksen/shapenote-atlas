import unittest

from scripts.agent_06_audit_edition_reconciliation import build_audit


class Agent06EditionReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_audit()
        cls.pairs = {pair["pairId"]: pair for pair in cls.report["pairs"]}

    def test_all_canonical_shared_pairs_are_present_and_fail_closed(self):
        self.assertEqual(self.report["summary"]["canonicalSharedPairs"], 448)
        self.assertEqual(len(self.pairs), 448)
        self.assertEqual(self.report["summary"]["safeToPromote"], 0)
        self.assertTrue(all(pair["safeToPromote"] is False for pair in self.pairs.values()))

    def test_samaria_preserves_key_conflict_and_alternate_witness(self):
        pair = self.pairs["sh-edition:26"]
        self.assertEqual(pair["comparisons"]["keyMode"]["status"], "unavailable")
        self.assertEqual(pair["comparisons"]["keyMode"]["values"], {"sh1991": "Ab major", "sh2025": ""})
        self.assertEqual(pair["editions"]["sh2025"]["keyCandidate"]["value"], "F minor")
        self.assertEqual(pair["editions"]["sh2025"]["keyEvidence"]["status"], "unknown")
        self.assertEqual(pair["witnesses"]["sh2025"]["referenceScoreByBook"]["sourceEdition"], "sh1991")
        self.assertEqual(pair["comparisons"]["notation"]["status"], "alternate-witness-only")

    def test_key_comparison_does_not_promote_secondary_candidates(self):
        key_mode = self.report["summary"]["keyMode"]
        self.assertEqual(key_mode["exactMetadataComparablePairs"], 0)
        self.assertEqual(key_mode["exactMetadataUnavailablePairs"], 448)
        self.assertEqual(key_mode["sh2025SecondaryCandidates"], 366)
        self.assertEqual(key_mode["existingLedgerChangedCandidates"], [])

    def test_golden_harp_same_slot_is_not_silently_merged(self):
        candidates = [item for item in self.report["mappingAudit"]["sameSlotCandidates"] if item["slot"] == "274t"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["status"], "unmapped-same-title-candidate")
        self.assertFalse(candidates[0]["safeToPair"])
        self.assertFalse(candidates[0]["textKeyExactAfterNormalization"])

    def test_lyrics_and_repeats_are_truthfully_unavailable(self):
        self.assertEqual(self.report["summary"]["repeatEndings"]["unavailable"], 448)
        self.assertEqual(self.report["summary"]["lyrics"]["verseLevelEvidence"], "unavailable")
        self.assertGreater(self.report["summary"]["lyrics"]["textKeySame"], 0)
        self.assertGreater(self.report["summary"]["lyrics"]["noTextKey"], 0)
        for pair in self.pairs.values():
            self.assertEqual(pair["comparisons"]["repeatEndings"]["status"], "unavailable")

    def test_sh2025_exact_score_gap_and_reference_provenance(self):
        witnesses = self.report["summary"]["sh2025Witnesses"]
        self.assertEqual(witnesses["exactEditionScores"], 0)
        self.assertEqual(witnesses["alternateReferenceScores"], 446)
        self.assertEqual(witnesses["reviewDrafts"], 3)
        self.assertEqual(witnesses["exactScoreUnavailable"], 448)
        self.assertEqual(self.report["summary"]["referenceProvenance"], {"alternate-reference": 2, "sh1991": 444})


if __name__ == "__main__":
    unittest.main()
