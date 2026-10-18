from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_stemless_study as study


class StemlessStudyTest(unittest.TestCase):
    def test_missing_stages_unavailable_but_explicit_zero_observed(self):
        stages=study.stage_trace('STEMCOUNT|HEADS|EXIT|1|0',10,20)
        self.assertEqual(stages['HEADS']['terminalHeads'],0)
        self.assertIsNone(stages['REDUCTION'])

    def test_stage_heads_chords_and_voice_are_distinct(self):
        text='\n'.join(['STEMTRACE|PAGE|EXIT|1|5|WHOLE_NOTE_FA_LEFT|1|12|2|4|5|0.8|10|1|1',
                        'STEMTRACE|PAGE|EXIT|1|6|WHOLE_NOTE_NARROW|1|12|2|4|5|0.8|10|1|1',
                        'STEMCOUNT|PAGE|EXIT|1|2'])
        row=study.stage_trace(text,10,20)['PAGE']
        self.assertEqual(row['terminalHeads'],2)
        self.assertEqual(row['terminalChords'],1)
        self.assertEqual(row['terminalVoicedHeads'],2)
        self.assertEqual(row['newFamilyHeads'],2)

    def test_malformed_stage_rows_fail_closed(self):
        with self.assertRaises(ValueError):
            study.stage_trace('STEMTRACE|PAGE|EXIT|1',10,20)

    def test_existing_event_changes_fail_preservation_even_if_new_span_added(self):
        before={(0,10,20):['old']}
        after={(0,10,20):['changed'],(0,20,30):['new']}
        self.assertFalse(study.preservation(before,after)['allExistingSpansExactlyPreserved'])

    def test_unchanged_existing_spans_and_new_span_are_separate(self):
        before={(0,10,20):['old']}; after={**before,(0,20,30):['new']}
        result=study.preservation(before,after)
        self.assertTrue(result['allExistingSpansExactlyPreserved'])
        self.assertEqual(len(result['addedSpans']),1)

    def test_ambiguous_physical_layout_rejected(self):
        sheet=ET.fromstring('<sheet><page><system><stack id="1" left="10" right="20"/><stack id="1" left="20" right="30"/></system></page></sheet>')
        with self.assertRaisesRegex(ValueError,'Ambiguous'):
            study.span_inventory(sheet,ET.fromstring('<score/>'))

    def test_started_run_never_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); (out/'protocol.json').write_text('{}')
            (out/'off/469').mkdir(parents=True); (out/'off/469/started.json').write_text('{}')
            case={'id':'469'}
            with patch.object(study,'check',return_value={'cases':[case]}), patch.object(study.subprocess,'Popen') as launch:
                with self.assertRaisesRegex(ValueError,'no implicit retry'):
                    study.recognize(out,case,'off')
                launch.assert_not_called()

    def test_completed_receipt_reused_without_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); (out/'protocol.json').write_text('{}')
            (out/'off/469').mkdir(parents=True); (out/'off/469/recognition.json').write_text('{}')
            case={'id':'469'}
            with patch.object(study,'check',return_value={'cases':[case]}), patch.object(study,'verify_receipt',return_value={'status':'exported'}), patch.object(study.subprocess,'Popen') as launch:
                self.assertEqual(study.recognize(out,case,'off')['status'],'exported')
                launch.assert_not_called()

    def test_failed_control_blocks_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); (out/'protocol.json').write_text('{}'); case={'id':'469'}
            with patch.object(study,'check',return_value={'cases':[case]}), patch.object(study,'verify_controls',return_value={'allControlsMatch':False}), patch.object(study.subprocess,'Popen') as launch:
                with self.assertRaisesRegex(ValueError,'control regression'):
                    study.recognize(out,case,'on')
                launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
