import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "agent_11_lyrics_repeats.py"
FIXTURE = ROOT / "tests" / "fixtures" / "agent-11-lyrics-repeats" / "semantic-fixture.xml"

spec = importlib.util.spec_from_file_location("agent_11_lyrics_repeats", MODULE_PATH)
assert spec and spec.loader
semantics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(semantics)


class Agent11LyricsRepeatsTests(unittest.TestCase):
    def test_source_fixture_aligns_lyrics_to_note_events_and_expands_endings(self):
        score = semantics.parse_musicxml_semantics(
            FIXTURE,
            source_id="sh2025/445",
            authority="scan-backed semantic fixture",
        )

        self.assertEqual(
            [(item["text"], item["eventIndex"], item["measure"]) for item in score["lyrics"]],
            [
                ("And", 0, "1"),
                ("must", 1, "2"),
                ("I", 2, "3"),
                ("be", 3, "4"),
                ("to", 4, "5"),
                ("judgment", 5, "6"),
                ("brought", 6, "7"),
            ],
        )
        self.assertEqual(score["availability"]["lyrics"]["status"], "encoded")
        self.assertEqual(score["availability"]["repeats"]["status"], "encoded")
        self.assertEqual(score["availability"]["numberedEndings"]["status"], "encoded")
        self.assertEqual(score["availability"]["editorialMarkings"]["count"], 1)
        self.assertEqual(
            score["playback"]["measureSequence"],
            ["1", "2", "3", "4", "5", "6", "2", "3", "4", "5", "7"],
        )
        self.assertTrue(score["playback"]["safeToApply"])

    def test_missing_repeat_semantics_stays_linear_and_unavailable(self):
        score = semantics.parse_musicxml_semantics(FIXTURE)
        measures = [measure["number"] for measure in score["parts"][0]["measures"]]
        playback = semantics.build_playback_plan(measures, [])

        self.assertEqual(playback["status"], "unavailable")
        self.assertFalse(playback["safeToApply"])
        self.assertEqual(playback["mode"], "linear-source-order")
        self.assertEqual(playback["measureSequence"], measures)

    def test_unpaired_repeat_is_blocked_without_guessing_a_region(self):
        playback = semantics.build_playback_plan(
            ["1", "2"],
            [{"measure": "2", "repeat": {"direction": "forward"}, "ending": None}],
        )

        self.assertEqual(playback["status"], "blocked")
        self.assertFalse(playback["safeToApply"])
        self.assertEqual(playback["measureSequence"], ["1", "2"])


if __name__ == "__main__":
    unittest.main()
