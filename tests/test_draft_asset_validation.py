"""Both draft sources remain usable without admitting broken or certified assets."""

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_data import validate_draft_score


class DraftAssetValidationTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.ref = "/draft-scores/tune-v1.json"
        self.path = self.root / "public" / self.ref.lstrip("/")
        self.path.parent.mkdir(parents=True)
        self.downloads = self.root / "public/review-publications"
        self.downloads.mkdir()
        xml = b"<score-partwise/>"
        for name, payload in (("tune.musicxml", xml), ("source.jpg", b"scan"), ("evidence.json", b"{}")):
            (self.downloads / name).write_bytes(payload)
        publication = {
            "musicXmlUrl": "/review-publications/tune.musicxml",
            "sourceUrl": "/review-publications/source.jpg",
            "evidenceUrl": "/review-publications/evidence.json",
            "version": "v1", "completeness": "partial", "limitations": ["Opening measure only."],
        }
        self.asset = {
            "sourceUrl": publication["musicXmlUrl"],
            "reviewPublication": publication,
            "provenance": {
                "kind": "omr-draft", "reviewRequired": True, "sourceEdition": "ch7",
                "sourceKeyVerified": False, "sourceSha256": hashlib.sha256(xml).hexdigest(),
            },
            "keySignature": "", "keyEvidence": {"status": "unknown"},
            "parts": [{"name": "Tenor", "events": [{"step": "C", "octave": 4, "beats": 1}]}],
            "transposition": {"hasPitchedEvents": True, "available": False, "manualKeyAllowed": True},
        }
        self.preview = copy.deepcopy(self.asset)
        self.preview.update(scoreRef=self.ref, parts=[{"name": "Tenor", "events": []}])
        self.song = {"id": "ch7 10 — Test", "sourceCoverageByBook": {"ch7": {
            "draftScoreRef": self.ref, "draftScoreStatus": "needs-human-review",
        }}}

    def validate(self):
        self.path.write_text(json.dumps(self.asset))
        return validate_draft_score(self.song, "ch7", self.preview, self.root)

    def test_unknown_key_published_draft_is_usable_and_unchanged(self):
        before = copy.deepcopy((self.song, self.preview, self.asset))
        self.assertEqual(self.validate(), self.ref)
        self.assertEqual((self.song, self.preview, self.asset), before)

    def test_legacy_draft_source_still_validates(self):
        self.asset.pop("reviewPublication")
        self.preview.pop("reviewPublication")
        self.asset["sourceUrl"] = "draft://ch7/10"
        self.assertEqual(self.validate(), self.ref)

    def test_missing_asset_and_empty_events_are_rejected(self):
        with self.assertRaisesRegex(SystemExit, "missing draft score asset"):
            validate_draft_score(self.song, "ch7", self.preview, self.root)
        self.asset["parts"][0]["events"] = []
        with self.assertRaisesRegex(SystemExit, "incomplete draft score asset"):
            self.validate()

    def test_unregistered_or_mismatched_publication_is_rejected(self):
        original = copy.deepcopy(self.asset)
        for change in (lambda a: a.pop("reviewPublication"),
                       lambda a: a.update(sourceUrl="https://example.org/score.musicxml"),
                       lambda a: a["reviewPublication"].update(version="v2")):
            with self.subTest(change=change):
                self.asset = copy.deepcopy(original)
                change(self.asset)
                with self.assertRaisesRegex(SystemExit, "invalid published draft provenance"):
                    self.validate()

    def test_missing_or_changed_downloads_are_rejected(self):
        for name in ("tune.musicxml", "source.jpg", "evidence.json"):
            with self.subTest(name=name):
                path = self.downloads / name
                payload = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(SystemExit, "missing published draft"):
                    self.validate()
                path.write_bytes(payload)
        (self.downloads / "tune.musicxml").write_bytes(b"changed")
        with self.assertRaisesRegex(SystemExit, "MusicXML checksum drift"):
            self.validate()

    def test_publication_cannot_claim_verified_provenance(self):
        self.asset["provenance"]["sourceKeyVerified"] = True
        self.preview["provenance"]["sourceKeyVerified"] = True
        with self.assertRaisesRegex(SystemExit, "invalid published draft provenance"):
            self.validate()

    def test_coverage_and_manual_key_requirements_remain_enforced(self):
        self.asset["transposition"]["manualKeyAllowed"] = False
        with self.assertRaisesRegex(SystemExit, "neither transposable nor marked for source-key entry"):
            self.validate()
        self.asset["transposition"]["manualKeyAllowed"] = True
        self.song["sourceCoverageByBook"]["ch7"]["draftScoreStatus"] = "verified"
        with self.assertRaisesRegex(SystemExit, "coverage marker drift"):
            self.validate()

    def test_quarantined_draft_cannot_advertise_transposition(self):
        self.asset["playbackValidation"] = {"status": "quarantined"}
        with self.assertRaisesRegex(SystemExit, "quarantined draft advertises"):
            self.validate()
        self.asset["transposition"]["manualKeyAllowed"] = False
        self.assertEqual(self.validate(), self.ref)


if __name__ == "__main__":
    unittest.main()
