import importlib.util
import hashlib
import tempfile
import unittest
import zipfile
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
            authority="synthetic-review-evidence",
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
            ["1", "2", "3", "4", "5", "6", "7"],
        )
        self.assertEqual(
            score["playback"]["measureSequenceIndices"],
            [0, 1, 2, 3, 4, 5, 6],
        )
        self.assertTrue(all(item["status"] == "encoded" for item in score["measureBoundaries"]))
        # The retained evidence deliberately carries times="1" alongside a
        # numbered second ending. That conflicts with the source structure;
        # preserve it as blocked evidence instead of silently applying it.
        self.assertFalse(score["playback"]["safeToApply"])
        self.assertEqual(score["playback"]["status"], "blocked")
        self.assertIn("exceeds repeat pass count", score["playback"]["reason"])
        self.assertEqual(score["playback"]["measureStarts"]["1"], 0.0)
        self.assertEqual(score["playback"]["measureDurations"]["1"], 1.0)

    def test_source_anchored_review_derivative_preserves_raw_verse_identifier_and_event_join(self):
        # This is a lane-created source-anchored review derivative, not the
        # original lyricless source MXL. Its recorded hash makes the fixture
        # identity explicit and keeps it out of canonical promotion claims.
        source = ROOT / "work" / "luna-program-20260904" / "sh2025" / "50t-devotion-correction-v1.mxl"
        self.assertEqual(
            hashlib.sha256(source.read_bytes()).hexdigest(),
            "76761d734ac2694644055ac3c3b85a35dc1468de89e6eb2e71791f465417c3a8",
        )
        root = semantics.read_root(source)
        raw_note = next(
            note
            for part in root
            if semantics.local_name(part.tag) == "part" and part.attrib.get("id") == "P1"
            for measure in part
            if semantics.local_name(measure.tag) == "measure" and measure.attrib.get("number") == "17"
            for note in measure
            if semantics.local_name(note.tag) == "note"
            and semantics.child(note, "lyric") is not None
        )
        raw_lyric = semantics.child(raw_note, "lyric")
        self.assertEqual(raw_lyric.attrib.get("number"), "1")
        self.assertEqual(semantics.text(raw_lyric, "text"), "sound.")

        score = semantics.parse_musicxml_semantics(
            source,
            source_id="sh2025/50t",
            authority="source-anchored-review-derivative",
        )
        observed = next(item for item in score["lyrics"] if item["partId"] == "P1")
        self.assertEqual(
            (observed["measure"], observed["eventIndex"], observed["verse"], observed["text"]),
            ("17", 41, "1", "sound."),
        )

    def test_retained_445_source_exposes_repeat_evidence_but_blocks_malformed_topology(self):
        source = ROOT / "work" / "445.mxl"
        score = semantics.parse_musicxml_semantics(
            source,
            source_id="sh2025/445",
            authority="retained-source-mxl",
        )
        self.assertEqual(score["availability"]["repeats"]["status"], "encoded")
        self.assertEqual(score["availability"]["numberedEndings"]["status"], "encoded")
        self.assertFalse(score["playback"]["safeToApply"])
        self.assertEqual(score["playback"]["status"], "blocked")

    def test_measure_zero_and_empty_silent_part_remain_explicit_in_global_boundaries(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Treble</part-name></score-part>
    <score-part id="P2"><part-name>Bass</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="0">
      <attributes><divisions>1</divisions></attributes>
      <note><rest/><duration>1</duration><voice>1</voice><type>quarter</type></note>
    </measure>
    <measure number="1">
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>half</type></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="0">
      <attributes><divisions>1</divisions></attributes>
      <note><rest/><duration>1</duration><voice>1</voice><type>quarter</type></note>
    </measure>
    <measure number="1"/>
  </part>
</score-partwise>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pickup.mxl"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("score.xml", xml)
            score = semantics.parse_musicxml_semantics(path, source_id="fixture://pickup")

        self.assertEqual([item["number"] for item in score["measureBoundaries"]], ["0", "1"])
        self.assertEqual(score["measureBoundaries"][0]["status"], "encoded")
        self.assertEqual(score["measureBoundaries"][1]["status"], "unavailable")
        self.assertEqual(score["playback"]["measureSequence"], ["0", "1"])
        self.assertEqual(score["playback"]["measureStarts"], {})
        self.assertEqual(score["playback"]["measureDurations"], {})
        self.assertFalse(score["playback"]["safeToApply"])

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

    def test_repeat_times_is_total_pass_count(self):
        boundaries = [
            {"number": number, "status": "encoded", "start": index, "duration": 1}
            for index, number in enumerate(["1", "2"])
        ]
        for times, expected_passes in (("1", 1), ("2", 2), ("3", 3)):
            playback = semantics.build_playback_plan(
                ["1", "2"],
                [
                    {"measure": "1", "repeat": {"direction": "forward"}},
                    {"measure": "2", "repeat": {"direction": "backward", "times": times}},
                ],
                measure_boundaries=boundaries,
            )
            self.assertTrue(playback["safeToApply"])
            self.assertEqual(playback["passes"][0]["passCount"], expected_passes)
            self.assertEqual(playback["measureSequence"], ["1", "2"] * expected_passes)

    def test_numbered_endings_select_first_and_second_passes(self):
        measures = [str(number) for number in range(1, 8)]
        boundaries = [
            {"number": number, "status": "encoded", "start": index, "duration": 1}
            for index, number in enumerate(measures)
        ]
        playback = semantics.build_playback_plan(
            measures,
            [
                {"measure": "2", "repeat": {"direction": "forward"}},
                {"measure": "6", "ending": {"number": "1", "type": "start"}},
                {"measure": "6", "repeat": {"direction": "backward"}, "ending": {"number": "1", "type": "discontinue"}},
                {"measure": "7", "ending": {"number": "2", "type": "start"}},
                {"measure": "7", "ending": {"number": "2", "type": "discontinue"}},
            ],
            measure_boundaries=boundaries,
        )
        self.assertTrue(playback["safeToApply"])
        self.assertEqual(
            playback["measureSequence"],
            ["1", "2", "3", "4", "5", "6", "2", "3", "4", "5", "7"],
        )
        self.assertEqual(playback["passes"][0]["passCount"], 2)

    def test_multi_number_ending_is_membership_union(self):
        boundaries = [
            {"number": number, "status": "encoded", "start": index, "duration": 1}
            for index, number in enumerate(["1", "2"])
        ]
        playback = semantics.build_playback_plan(
            ["1", "2"],
            [
                {"measure": "1", "repeat": {"direction": "forward"}},
                {"measure": "2", "ending": {"number": "1,2", "type": "start"}},
                {"measure": "2", "repeat": {"direction": "backward"}, "ending": {"number": "1,2", "type": "discontinue"}},
            ],
            measure_boundaries=boundaries,
        )
        self.assertTrue(playback["safeToApply"])
        self.assertEqual(playback["measureSequence"], ["1", "2", "1", "2"])

    def test_unclosed_and_mismatched_endings_are_blocked(self):
        boundaries = [
            {"number": number, "status": "encoded", "start": index, "duration": 1}
            for index, number in enumerate(["1", "2", "3"])
        ]
        unclosed = semantics.build_playback_plan(
            ["1", "2", "3"],
            [
                {"measure": "1", "repeat": {"direction": "forward"}},
                {"measure": "2", "repeat": {"direction": "backward", "times": "2"}},
                {"measure": "2", "ending": {"number": "1", "type": "start"}},
            ],
            measure_boundaries=boundaries,
        )
        mismatched = semantics.build_playback_plan(
            ["1", "2", "3"],
            [
                {"measure": "1", "repeat": {"direction": "forward"}},
                {"measure": "2", "repeat": {"direction": "backward", "times": "2"}},
                {"measure": "2", "ending": {"number": "2", "type": "stop"}},
            ],
            measure_boundaries=boundaries,
        )
        self.assertFalse(unclosed["safeToApply"])
        self.assertIn("unclosed", unclosed["reason"])
        self.assertFalse(mismatched["safeToApply"])
        self.assertIn("without an opening", mismatched["reason"])

    def test_cross_part_repeat_disagreement_is_blocked(self):
        boundaries = [
            {"number": number, "status": "encoded", "start": index, "duration": 1}
            for index, number in enumerate(["1", "2", "3"])
        ]
        first = [
            {"measure": "1", "repeat": {"direction": "forward"}},
            {"measure": "2", "repeat": {"direction": "backward", "times": "2"}},
        ]
        second = [
            {"measure": "1", "repeat": {"direction": "forward"}},
            {"measure": "3", "repeat": {"direction": "backward", "times": "2"}},
        ]
        playback = semantics.build_playback_plan(
            ["1", "2", "3"],
            first,
            measure_boundaries=boundaries,
            part_barlines=[first, second],
        )
        self.assertFalse(playback["safeToApply"])
        self.assertIn("disagree across source parts", playback["reason"])


if __name__ == "__main__":
    unittest.main()
