"""Published queue rows stay usable, tied to retained assets, and uncertified."""

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from review_dispositions import published_review_disposition, transcription_disposition
from validate_data import validate_transcription_queue_disposition


class PublicationQueueValidationTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        public = self.root / "public"
        downloads = public / "review-publications"
        downloads.mkdir(parents=True)
        xml = b"<score-partwise/>"
        for name, payload in (("tune.musicxml", xml), ("source.jpg", b"scan"), ("evidence.json", b"{}")):
            (downloads / name).write_bytes(payload)
        publication = {
            "musicXmlUrl": "/review-publications/tune.musicxml",
            "sourceUrl": "/review-publications/source.jpg",
            "evidenceUrl": "/review-publications/evidence.json",
            "version": "v1", "completeness": "partial", "limitations": ["Opening measure only."],
        }
        ref = "/draft-scores/tune-v1.json"
        asset = {
            "sourceUrl": publication["musicXmlUrl"], "reviewPublication": publication,
            "provenance": {"kind": "omr-draft", "reviewRequired": True, "sourceEdition": "ch7",
                           "sourceKeyVerified": False, "sourceSha256": hashlib.sha256(xml).hexdigest()},
            "parts": [{"name": "Tenor", "events": [{"step": "C", "octave": 4, "beats": 1}]}],
            "transposition": {"hasPitchedEvents": True, "manualKeyAllowed": True, "available": False},
        }
        self.asset_path = public / ref.lstrip("/")
        self.asset_path.parent.mkdir()
        self.asset_path.write_text(json.dumps(asset))
        preview = copy.deepcopy(asset)
        preview.update(scoreRef=ref, parts=[{"name": "Tenor", "events": []}])
        coverage = {
            "status": "source-reference", "sourceUrls": ["https://example.org/score"],
            "draftScoreAvailable": True, "draftScoreRef": ref,
            "draftScoreStatus": "needs-human-review", "reviewPublication": publication,
            "nextAction": "review-and-correct-published-draft",
        }
        self.song = {"id": "ch7 10 — Test", "draftScoreByBook": {"ch7": preview},
                     "sourceCoverageByBook": {"ch7": copy.deepcopy(coverage)}}
        self.indexed = {"songId": self.song["id"], "bookId": "ch7", **copy.deepcopy(coverage)}
        disposition = published_review_disposition()
        self.record = {**copy.deepcopy(self.indexed), "queueId": "ch7/10", "canonicalRecordId": "ch7/10",
                       "disposition": disposition, **{field: disposition[field] for field in (
                           "humanReviewRequired", "reviewAvailable", "safeToPromote")}}

    def validate(self):
        validate_transcription_queue_disposition(self.record, self.song, self.indexed, self.root)

    def test_published_review_row_accepts_required_human_review_without_promotion(self):
        self.validate()
        self.assertEqual(self.record["disposition"]["state"], "review-only")
        self.assertIs(self.record["humanReviewRequired"], True)
        self.assertIs(self.record["safeToPromote"], False)

    def test_unpublished_acquisition_keeps_its_existing_disposition(self):
        self.record = {"queueId": "ch7/10", "canonicalRecordId": "ch7/10", "status": "source-reference",
                       "sourceUrls": ["https://example.org/score"]}
        disposition = transcription_disposition(self.record["status"], self.record["sourceUrls"])
        self.record.update(disposition=disposition, humanReviewRequired=False, reviewAvailable=True, safeToPromote=False)
        self.song = {"id": "ch7 10 — Test"}
        self.indexed = {}
        self.validate()
        self.record["disposition"] = published_review_disposition()
        with self.assertRaisesRegex(SystemExit, "not canonical"):
            self.validate()

    def test_stale_or_missing_metadata_in_any_index_is_rejected(self):
        witnesses = [self.record, self.indexed, self.song["sourceCoverageByBook"]["ch7"],
                     self.song["draftScoreByBook"]["ch7"]]
        for witness in witnesses:
            original = copy.deepcopy(witness["reviewPublication"])
            for replacement in ({**original, "version": "stale"}, None):
                with self.subTest(replacement=replacement):
                    witness["reviewPublication"] = replacement
                    with self.assertRaisesRegex(SystemExit, "metadata drift"):
                        self.validate()
            witness["reviewPublication"] = original

    def test_stale_refs_or_promoted_coverage_are_rejected(self):
        for field, value in (("draftScoreRef", "/draft-scores/stale.json"),
                             ("draftScoreAvailable", False), ("draftScoreStatus", "verified")):
            with self.subTest(field=field):
                old = self.record[field]
                self.record[field] = value
                with self.assertRaisesRegex(SystemExit, "coverage drift"):
                    self.validate()
                self.record[field] = old

    def test_forged_promotion_or_suppressed_review_is_rejected(self):
        for field, value in (("safeToPromote", True), ("humanReviewRequired", False), ("reviewAvailable", False)):
            with self.subTest(field=field):
                old = self.record[field]
                self.record[field] = value
                with self.assertRaisesRegex(SystemExit, "not fail-closed"):
                    self.validate()
                self.record[field] = old
        self.record["disposition"]["state"] = "verified"
        with self.assertRaisesRegex(SystemExit, "not canonical"):
            self.validate()

    def test_asset_and_retained_bytes_are_checked_not_just_queue_markers(self):
        asset = json.loads(self.asset_path.read_text())
        asset["reviewPublication"]["version"] = "stale"
        self.asset_path.write_text(json.dumps(asset))
        with self.assertRaisesRegex(SystemExit, "invalid published draft provenance"):
            self.validate()
        asset["reviewPublication"]["version"] = "v1"
        self.asset_path.write_text(json.dumps(asset))
        (self.root / "public/review-publications/tune.musicxml").write_bytes(b"changed")
        with self.assertRaisesRegex(SystemExit, "MusicXML checksum drift"):
            self.validate()


if __name__ == "__main__":
    unittest.main()
