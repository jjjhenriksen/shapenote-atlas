import tempfile
import unittest
import zipfile
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_data import parse_score


FIXTURE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Treble</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths><mode>major</mode></key>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration><voice>1</voice><type>quarter</type>
      </note>
      <note>
        <chord/>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>1</duration><voice>1</voice><type>quarter</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>1</duration><voice>1</voice><type>quarter</type>
      </note>
      <backup><duration>2</duration></backup>
      <note>
        <pitch><step>G</step><octave>3</octave></pitch>
        <duration>1</duration><voice>2</voice><type>quarter</type>
      </note>
      <note>
        <chord/>
        <pitch><step>B</step><octave>3</octave></pitch>
        <duration>1</duration><voice>2</voice><type>quarter</type>
      </note>
    </measure>
    <measure number="2">
      <note>
        <pitch><step>A</step><octave>3</octave></pitch>
        <duration>1</duration><voice>1</voice><type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>
"""


class MusicXMLParserTests(unittest.TestCase):
    def test_chord_notes_share_anchor_onset_per_voice(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_path = Path(temporary_directory) / "fixture.mxl"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("score.xml", FIXTURE_XML)

            score = parse_score("fixture://chord-onset", source_path=archive_path)

        self.assertIsNotNone(score)
        events = score["parts"][0]["events"]
        self.assertEqual(
            [(event["step"], event["onset"], event["voice"]) for event in events],
            [("C", 0.0, "1"), ("E", 0.0, "1"), ("F", 1.0, "1"), ("G", 0.0, "2"), ("B", 0.0, "2"), ("A", 2.0, "1")],
        )


if __name__ == "__main__":
    unittest.main()
