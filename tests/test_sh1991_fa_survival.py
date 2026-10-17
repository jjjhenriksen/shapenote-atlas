"""Clone-safe attribution tests; no scan, Java build or recognition required."""
from pathlib import Path
import sys
import unittest
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sh1991_fa_survival import graph_rows, unique_export_witnesses, exported_notes, log_evidence, verify_training_cohort


def fixture(begin=True, time='0', number='7', extra_notes='', special=''):
    sheet = ET.fromstring(f'''<sheet><scale><interline main="10"/></scale><page><system id="1">
      <stack id="{number}" {special}><slot id="1" time-offset="{time}"/></stack>
      <part id="1"><staff id="1" left="0"/><measure><head-chords>c1</head-chords>
      <voice id="1"><slots><entry><key>1</key><value chord="c1" status="{'BEGIN' if begin else 'CONTINUE'}"/>
      </entry></slots></voice></measure></part>
      <sig><inters><head id="h1" staff="1" shape="NOTEHEAD_VOID"><bounds x="100" y="90" w="10" h="10"/></head>
      <stem id="s1"/><head-chord id="c1"/></inters><relations>
      <relation source="h1" target="s1"><head-stem/></relation>
      <relation source="c1" target="s1"><chord-stem/></relation>
      <relation source="c1" target="h1"><containment/></relation>
      </relations></sig></system></page></sheet>''')
    export = ET.fromstring(f'''<score-partwise><part id="P1"><measure number="{number}">
      <note default-x="100"><pitch><step>F</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice></note>
      {extra_notes}</measure></part></score-partwise>''')
    return sheet, export


class SurvivalTest(unittest.TestCase):
    def test_same_ids_cannot_hide_changed_labels_or_a_heldout_record(self):
        row = {'songNo': '1', 'split': 'train', 'label': {'sha256': 'frozen'}}
        parent = {'records': [row]}
        verify_training_cohort({'records': [row]}, parent, ['1'])
        with self.assertRaisesRegex(ValueError, 'source/label metadata differs'):
            verify_training_cohort({'records': [{**row, 'label': {'sha256': 'changed'}}]}, parent, ['1'])
        with self.assertRaisesRegex(ValueError, 'only frozen training probe'):
            verify_training_cohort({'records': [{**row, 'split': 'test'}]}, parent, ['1'])

    def test_attachments_and_measure_membership_do_not_imply_rhythm_or_export(self):
        sheet, export = fixture(begin=False)
        rows, summary = graph_rows(sheet, export)
        self.assertTrue(all(rows['h1'][k] for k in ('headStem', 'chord', 'chordStem', 'measure')))
        self.assertFalse(rows['h1']['voiceBegin'])
        self.assertFalse(rows['h1']['timedSlot'])
        self.assertFalse(rows['h1']['exportWitness'])
        self.assertEqual(summary['stages']['exportedTimedWithoutUniqueGraphWitness'], 1)

    def test_measure_labels_not_positions_and_pitch_not_used_for_witness(self):
        sheet, export = fixture(number='7')
        rows, _ = graph_rows(sheet, export)
        self.assertEqual(rows['h1']['exportNote'], 'P1/m7/n1')
        export.find('.//step').text = 'D'
        self.assertTrue(graph_rows(sheet, export)[0]['h1']['exportWitness'])
        export.find('.//measure').set('number', '8')
        self.assertFalse(graph_rows(sheet, export)[0]['h1']['exportWitness'])

    def test_begin_must_reference_a_real_timed_slot(self):
        sheet, export = fixture()
        sheet.find('.//slot').attrib.pop('time-offset')
        row = graph_rows(sheet, export)[0]['h1']
        self.assertTrue(row['voiceBegin']); self.assertFalse(row['timedSlot'])
        sheet.find('.//slot').set('time-offset', '-1/4')
        with self.assertRaisesRegex(ValueError, 'negative saved slot time'):
            graph_rows(sheet, export)

    def test_dangling_stem_or_chord_reference_does_not_become_attachment(self):
        sheet, export = fixture()
        for node in list(sheet.findall('.//sig/inters/stem')):
            sheet.find('.//sig/inters').remove(node)
        row = graph_rows(sheet, export)[0]['h1']
        self.assertFalse(row['headStem']); self.assertFalse(row['chordStem'])
        self.assertTrue(row['chord'])
        sheet.find('.//relation[containment]').set('source', 'missing')
        row = graph_rows(sheet, export)[0]['h1']
        self.assertFalse(row['chord']); self.assertFalse(row['measure'])

    def test_ambiguous_export_matches_remain_unresolved_without_reuse(self):
        row = {'exportContext': ['P1','7','1','1'], 'expectedExportX': 100}
        note = {'id': 'n1', 'part': 'P1', 'measure': '7', 'voice': '1', 'staff': '1', 'x': 100}
        witnesses, candidates = unique_export_witnesses({'h1': row, 'h2': row}, [note])
        self.assertEqual(witnesses, {}); self.assertEqual(len(candidates['h1']), 1)
        witnesses, _ = unique_export_witnesses({'h1': row}, [note, {**note, 'id': 'n2'}])
        self.assertEqual(witnesses, {})
        witnesses, _ = unique_export_witnesses({'h1': row}, [{**note, 'x': 103}])
        self.assertEqual(witnesses, {})

    def test_head_and_chord_must_share_the_same_stem_to_count_consistency(self):
        sheet, export = fixture()
        self.assertTrue(graph_rows(sheet, export)[0]['h1']['sharedStem'])
        ET.SubElement(sheet.find('.//sig/inters'), 'stem', id='s2')
        sheet.find('.//relation[head-stem]').set('target', 's2')
        row = graph_rows(sheet, export)[0]['h1']
        self.assertTrue(row['headStem']); self.assertTrue(row['chordStem'])
        self.assertFalse(row['sharedStem'])

    def test_grace_and_rest_notes_not_counted_as_timed_pitched_exports(self):
        _, export = fixture(extra_notes='<note><grace/><pitch><step>C</step></pitch></note><note><rest/><duration>1</duration></note>')
        self.assertEqual(len(exported_notes(export)), 1)

    def test_cautionary_stacks_not_misidentified_as_exported_measure(self):
        sheet, export = fixture(special='special="CAUTIONARY"')
        rows, summary = graph_rows(sheet, export)
        self.assertEqual(summary['topology']['cautionaryStacks'], 1)
        self.assertTrue(rows['h1']['timedSlot']); self.assertFalse(rows['h1']['exportWitness'])

    def test_part_mapping_fails_closed_instead_of_guessing(self):
        sheet, export = fixture()
        export.find('part').set('id', 'P2')
        with self.assertRaisesRegex(ValueError, 'unsupported part/staff mapping'):
            graph_rows(sheet, export)

    def test_barline_actions_are_evidence_with_original_line_numbers(self):
        log = ('INFO [] MeasuresBuilder 428 | S1 deleting   half column: s1:G(x:317)[6]\n'
               'INFO [] MeasuresBuilder 424 | S2 expanding major column: s2:G(x:400)[7]\n'
               'WARN [] PartwiseBuilder 2230 | Error visiting Measure{#2P4}\n')
        result = log_evidence(log)
        self.assertEqual(result['columnActionCounts'], {'deleting half': 1, 'expanding major': 1})
        self.assertEqual(result['columnActions'][0]['line'], 1)
        self.assertEqual(result['warningLines'][0]['line'], 3)


if __name__ == '__main__':
    unittest.main()
