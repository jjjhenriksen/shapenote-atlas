import tempfile
import unittest
import zipfile
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from agent_03_semantic_musicxml import parse_source
from build_data import parse_score


FIXTURE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <work><work-title>Semantic fixture</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Treble</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths><mode>major</mode></key>
        <time><beats>2</beats><beat-type>4</beat-type></time>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration><voice>1</voice><type>quarter</type>
        <lyric number="1"><syllabic>single</syllabic><text>Come</text></lyric>
        <notations><articulations><accent/></articulations><fermata/></notations>
      </note>
      <note>
        <chord/><pitch><step>E</step><octave>4</octave></pitch>
        <duration>1</duration><voice>1</voice><type>quarter</type>
        <lyric number="1"><syllabic>single</syllabic><text>now</text></lyric>
      </note>
      <backup><duration>1</duration></backup>
      <note>
        <rest/><duration>1</duration><voice>2</voice><type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>3</octave></pitch>
        <duration>1</duration><voice>2</voice><type>quarter</type>
      </note>
      <barline location="right"><repeat direction="forward" times="2"/><ending number="1" type="start"/></barline>
    </measure>
    <measure number="2">
      <direction placement="above"><direction-type><words>Fine</words></direction-type></direction>
      <note>
        <pitch><step>A</step><octave>3</octave></pitch>
        <duration>2</duration><voice>1</voice><type>half</type>
      </note>
      <barline location="right"><ending number="1" type="stop"/><repeat direction="backward"/></barline>
    </measure>
  </part>
</score-partwise>
"""


class Agent03SemanticMusicXMLTests(unittest.TestCase):
    def _parse(self, xml: str = FIXTURE_XML):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.mxl"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("META-INF/container.xml", """<container><rootfiles><rootfile full-path="nested/score.musicxml"/></rootfiles></container>""")
                archive.writestr("nested/score.musicxml", xml)
            return parse_source(path)

    def test_chords_backups_and_measure_starts_preserve_event_timing(self):
        score = self._parse()
        events = score["parts"][0]["events"]
        self.assertEqual(
            [(event["step"] if not event["rest"] else "rest", event["onset"], event["measure"], event["voice"]) for event in events],
            [("C", 0.0, "1", "1"), ("E", 0.0, "1", "1"), ("rest", 0.0, "1", "2"), ("G", 1.0, "1", "2"), ("A", 2.0, "2", "1")],
        )
        self.assertEqual([event["measureOnset"] for event in events], [0.0, 0.0, 0.0, 1.0, 0.0])
        self.assertEqual(score["parts"][0]["measureSemantics"], [{"measure": "1", "start": 0.0, "end": 2.0, "barlines": [{"kind": "repeat", "measure": "1", "direction": "forward", "times": "2"}, {"kind": "ending", "measure": "1", "number": "1", "type": "start"}, {"kind": "barline", "measure": "1", "location": "right"}]}, {"measure": "2", "start": 2.0, "end": 4.0, "directions": [{"measure": "2", "kind": "direction", "placement": "above", "types": [{"kind": "words", "text": "Fine"}]}], "barlines": [{"kind": "ending", "measure": "2", "number": "1", "type": "stop"}, {"kind": "repeat", "measure": "2", "direction": "backward"}, {"kind": "barline", "measure": "2", "location": "right"}]}])

    def test_lyrics_repeats_endings_and_editorial_markings_remain_aligned(self):
        score = self._parse()
        events = score["parts"][0]["events"]
        self.assertEqual(events[0]["lyrics"], [{"number": "1", "text": "Come", "syllabic": "single"}])
        self.assertEqual(events[1]["lyrics"][0]["text"], "now")
        self.assertEqual([(item["measure"], item["eventIndex"], item["onset"]) for item in score["lyrics"]], [("1", 0, 0.0), ("1", 1, 0.0)])
        self.assertEqual([(item["kind"], item.get("direction"), item.get("type")) for item in score["repeatSemantics"] if item["kind"] in {"repeat", "ending"}], [("repeat", "forward", None), ("ending", None, "start"), ("ending", None, "stop"), ("repeat", "backward", None)])
        self.assertEqual(score["semanticAvailability"]["lyrics"], "encoded")
        self.assertEqual(score["semanticAvailability"]["repeats"], "encoded")
        self.assertEqual(score["semanticAvailability"]["endings"], "encoded")
        kinds = {item["kind"] for item in score["editorialMarkings"]}
        self.assertTrue({"articulations", "accent", "fermata", "direction"}.issubset(kinds))

    def test_absent_semantics_are_unavailable_not_invented(self):
        xml = FIXTURE_XML.replace("<lyric number=\"1\"><syllabic>single</syllabic><text>Come</text></lyric>", "").replace("<lyric number=\"1\"><syllabic>single</syllabic><text>now</text></lyric>", "").replace("<barline location=\"right\"><repeat direction=\"forward\" times=\"2\"/><ending number=\"1\" type=\"start\"/></barline>", "").replace("<barline location=\"right\"><ending number=\"1\" type=\"stop\"/><repeat direction=\"backward\"/></barline>", "")
        score = self._parse(xml)
        self.assertEqual(score["lyrics"], [])
        self.assertEqual(score["repeatSemantics"], [])
        self.assertEqual(score["semanticAvailability"]["lyrics"], "unavailable")
        self.assertEqual(score["semanticAvailability"]["repeats"], "unavailable")
        self.assertEqual(score["semanticAvailability"]["endings"], "unavailable")

    def test_existing_score_parser_receives_semantic_fields_without_replacing_events(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.mxl"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("score.xml", FIXTURE_XML)
            score = parse_score("fixture://agent-03", source_path=path)
        self.assertIsNotNone(score)
        self.assertEqual(score["parts"][0]["events"][0]["lyrics"][0]["text"], "Come")
        self.assertEqual(score["repeatSemantics"][0]["kind"], "repeat")
        self.assertEqual(score["parts"][0]["measureSemantics"][1]["start"], 2.0)

    def test_missing_duration_is_partial_timing_evidence(self):
        xml = FIXTURE_XML.replace("<duration>2</duration><voice>1</voice><type>half</type>", "<voice>1</voice><type>half</type>")
        score = self._parse(xml)
        self.assertIsNone(score["parts"][0]["events"][-1]["beats"])
        self.assertEqual(score["timingAudit"]["missingDurationEvents"], 1)
        self.assertEqual(score["semanticAvailability"]["eventTiming"], "partial")


if __name__ == "__main__":
    unittest.main()
