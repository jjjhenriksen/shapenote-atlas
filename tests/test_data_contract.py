import importlib.util
import hashlib
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_data.py"
FIXTURE = ROOT / "tests" / "fixtures" / "agent-11-lyrics-repeats" / "semantic-fixture.xml"
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location("build_data", MODULE_PATH)
assert spec and spec.loader
build_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_data)


class DataContractTests(unittest.TestCase):
    def test_ch7_batch_source_images_are_retained_and_linked_without_score_promotion(self):
        expected = {"1", "10", "100", "101", "102"}
        manifest = json.loads((ROOT / "public" / "source-image-manifest.json").read_text(encoding="utf-8"))
        corpus = json.loads((ROOT / "public" / "corpus.json").read_text(encoding="utf-8"))
        queue = json.loads((ROOT / "public" / "transcription-queue.json").read_text(encoding="utf-8"))
        songs = {
            song["songNo"]: song
            for song in corpus["songs"]
            if song.get("id", "").startswith("ch7 ") and song.get("songNo") in expected
        }
        queue_records = {record["queueId"]: record for record in queue["records"]}
        self.assertEqual(set(songs), expected)
        for song_no in sorted(expected):
            key = f"ch7/{song_no}"
            image = manifest["records"][key]
            image_path = ROOT / image["sourceImagePath"]
            self.assertTrue(image_path.is_file())
            self.assertEqual(
                hashlib.sha256(image_path.read_bytes()).hexdigest(),
                image["sourceImageSha256"],
            )
            self.assertTrue(image["sourcePageUrl"].startswith("https://sevenshapes.sacredharpbremen.org/"))
            self.assertTrue(image["sourceImageUrl"].startswith("https://sevenshapes.sacredharpbremen.org/wp-content/"))
            self.assertEqual(image["sourceImageStatus"], "source-observed-image-only")
            self.assertTrue(image["sourceImageImmutable"])

            metadata = songs[song_no]["metadataByBook"]["ch7"]
            coverage = songs[song_no]["sourceCoverageByBook"]["ch7"]
            queued = queue_records[key]
            for projected in (metadata, coverage, queued):
                self.assertEqual(projected["sourceImagePath"], image["sourceImagePath"])
                self.assertEqual(projected["sourceImageSha256"], image["sourceImageSha256"])
                self.assertEqual(projected["sourceImageUrl"], image["sourceImageUrl"])
                self.assertEqual(projected["sourcePageUrl"], image["sourcePageUrl"])
                self.assertEqual(projected["sourceImageOriginUrl"], image["sourceImageOriginUrl"])
                self.assertEqual(projected["sourceImageStatus"], image["sourceImageStatus"])
                self.assertTrue(projected["sourceImageImmutable"])
            self.assertIn(image["sourcePageUrl"], metadata["sourceUrls"])
            self.assertIn(image["sourcePageUrl"], coverage["sourceUrls"])
            self.assertIn(image["sourcePageUrl"], queued["sourceUrls"])
            self.assertEqual(metadata["keySignature"], "")
            self.assertFalse(songs[song_no].get("scoreByBook", {}).get("ch7"))

    def test_twelve_sh25_witnesses_are_record_level_alternate_references(self):
        expected = {
            "27b", "50b", "51", "54", "160t", "178b", "308",
            "438", "452t", "467", "497b", "515",
        }
        self.assertEqual(set(build_data.SH2025_ALTERNATE_WITNESS_RECORDS), expected)
        for song_no in sorted(expected):
            provenance = build_data.score_provenance(
                "sh2025",
                "https://example.invalid/witness.mxl",
                {"sourceEdition": "sh2025"},
                song_no,
            )
            self.assertEqual(provenance["kind"], "alternate-source")
            self.assertEqual(provenance["sourceEdition"], "alternate-reference")
            self.assertEqual(provenance["sourceRecordKey"], song_no)
            self.assertIn("witnessEdition", provenance)
            self.assertIn("witnessRecordKey", provenance)

    def test_non_blocked_sh25_named_witness_can_remain_exact_candidate(self):
        provenance = build_data.score_provenance(
            "sh2025",
            "https://shapenote.net/musicxml/SH25-LISBON-Chandler.mxl",
            {"sourceEdition": "sh2025"},
            "575",
        )
        self.assertEqual(provenance["kind"], "edition-source")

    def test_parse_score_materializes_versioned_semantic_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.mxl"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("score.xml", FIXTURE.read_text(encoding="utf-8"))
            score = build_data.parse_score("fixture://semantic", path)

        self.assertIsNotNone(score)
        contract = score["semanticContract"]
        self.assertEqual(contract["schemaVersion"], 1)
        self.assertEqual(contract["availability"]["lyrics"]["status"], "encoded")
        self.assertEqual(contract["availability"]["repeats"]["status"], "encoded")
        self.assertFalse(contract["playback"]["safeToApply"])
        self.assertEqual(contract["playback"]["status"], "blocked")
        self.assertIn("exceeds repeat pass count", contract["playback"]["reason"])
        self.assertIn("1", contract["playback"]["measureStarts"])
        self.assertIn("1", contract["playback"]["measureDurations"])
        self.assertEqual(contract["parts"][0]["lyrics"][0]["eventIndex"], 0)
        self.assertTrue(
            any(marker["type"] == "repeat" for marker in contract["parts"][0]["barlines"])
        )
        self.assertEqual(score["lyrics"][0]["text"], "And")
        self.assertTrue(score["parts"][0]["events"][0]["lyrics"])

    def test_absent_semantics_are_explicitly_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.mxl"
            xml = FIXTURE.read_text(encoding="utf-8")
            xml = re.sub(r"\s*<lyric[^>]*>.*?</lyric>", "", xml)
            xml = xml.replace('<repeat direction="forward"/>', "")
            xml = xml.replace('<repeat direction="backward" times="1"/>', "")
            xml = xml.replace('<ending number="1" type="start"/>', "")
            xml = xml.replace('<ending number="1" type="discontinue"/>', "")
            xml = xml.replace('<ending number="2" type="start"/>', "")
            xml = xml.replace('<ending number="2" type="discontinue"/>', "")
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("score.xml", xml)
            score = build_data.parse_score("fixture://missing", path)

        contract = score["semanticContract"]
        self.assertEqual(contract["availability"]["lyrics"]["status"], "unavailable")
        self.assertEqual(contract["availability"]["repeats"]["status"], "unavailable")
        self.assertFalse(contract["playback"]["safeToApply"])
        self.assertEqual(contract["playback"]["mode"], "linear-source-order")
        self.assertIn("1", contract["playback"]["measureStarts"])
        self.assertIn("1", contract["playback"]["measureDurations"])
        self.assertEqual(score["lyrics"], [])

    def test_invalid_draft_durations_are_quarantined_without_repairing_events(self):
        corpus = json.loads((ROOT / "public" / "corpus.json").read_text(encoding="utf-8"))
        quarantined = 0
        for song in corpus["songs"]:
            for book_id, draft in (song.get("draftScoreByBook") or {}).items():
                asset = json.loads(
                    (ROOT / "public" / draft["scoreRef"].lstrip("/")).read_text(encoding="utf-8")
                )
                invalid = [
                    (part, index, event)
                    for part in asset.get("parts", [])
                    for index, event in enumerate(part.get("events", []))
                    if not event.get("grace") and (
                        not isinstance(event.get("beats"), (int, float)) or event["beats"] <= 0
                    )
                ]
                validation = asset.get("playbackValidation")
                if not invalid:
                    self.assertIsNone(validation)
                    self.assertNotIn("playbackValidation", draft)
                    continue
                quarantined += 1
                self.assertIsNotNone(validation)
                self.assertEqual(validation["status"], "quarantined")
                self.assertFalse(validation["safeToApply"])
                self.assertFalse(asset["transposition"]["available"])
                self.assertFalse(asset["transposition"]["manualKeyAllowed"])
                self.assertEqual(asset["transposition"]["reason"], "playback-quarantined")
                self.assertEqual(draft["playbackValidation"], validation)
                evidence = {
                    (item["part"], item["eventIndex"]): item
                    for item in validation["invalidEvents"]
                }
                self.assertEqual(len(evidence), len(invalid))
                for part, event_index, event in invalid:
                    item = evidence[(part["name"], event_index)]
                    self.assertEqual(item["measure"], str(event.get("measure", "")))
                    self.assertEqual(item["beats"], event.get("beats"))
                    self.assertEqual(
                        item["sourcePath"],
                        f"parts[{asset['parts'].index(part)}].events[{event_index}].beats",
                    )
        self.assertGreater(quarantined, 0)

    def test_draft_quarantine_records_missing_and_nonfinite_duration_values(self):
        score = {
            "parts": [{
                "name": "Treble",
                "events": [
                    {"measure": "1", "beats": None, "timingStatus": "unavailable"},
                    {"measure": "2", "beats": "nan", "timingStatus": "invalid"},
                ],
            }]
        }
        validation = build_data.build_draft_playback_validation(
            "sh2025/test", score, {"artifact": "test.mxl", "sha256": "abc"}
        )
        self.assertEqual(validation["status"], "quarantined")
        self.assertEqual(len(validation["invalidEvents"]), 2)
        self.assertIsNone(validation["invalidEvents"][0]["beats"])
        self.assertEqual(validation["invalidEvents"][1]["beats"], "nan")


if __name__ == "__main__":
    unittest.main()
