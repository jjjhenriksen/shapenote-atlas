import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_terminal_diagnosis as diagnosis


class TerminalDiagnosisTest(unittest.TestCase):
    def test_probe_missing_remains_unobserved_not_zero(self):
        result = diagnosis.probes('FAPROBE|a|WHOLE_NOTE|1|2|0.4|NaN|MIDDLE_LEFT|false|false', ['a', 'b'])
        self.assertEqual(result['a']['WHOLE_NOTE']['minimumDistance'], .4)
        self.assertEqual(result['b'], {})

    def test_probe_unknown_identity_rejected(self):
        with self.assertRaises(ValueError):
            diagnosis.probes('FAPROBE|other|WHOLE_NOTE|1|2|0.4|NaN|MIDDLE_LEFT|false|false', ['a'])

    def test_final_region_has_no_recognized_music(self):
        sheet = ET.fromstring('''<sheet><page><system><stack left="20" right="40" special="CAUTIONARY"/>
          <part><measure><right-barline/></measure></part><sig><inters>
          <head><bounds x="10" y="1" w="2" h="2"/></head>
          <barline><bounds x="39" y="1" w="2" h="2"/></barline>
          </inters></sig></system></page></sheet>''')
        result = diagnosis.terminal(sheet, ET.fromstring('<score><part><measure/></part></score>'))
        self.assertEqual(result['objectCounts'], {})
        self.assertEqual(result['measureHeadChordCounts'], [0])
        self.assertEqual(result['measureVoiceCounts'], [0])

    def test_started_diagnostic_never_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory); (out/'protocol.json').write_text('{}')
            (out/'469').mkdir(); (out/'469/started.json').write_text('{}')
            with patch.object(diagnosis, 'check', return_value={}), patch.object(diagnosis.subprocess, 'Popen') as launch:
                with self.assertRaisesRegex(ValueError, 'no implicit retry'):
                    diagnosis.recognize(out, {'id': '469'})
                launch.assert_not_called()

    def test_input_drift_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory); data = out/'input'; data.write_text('before')
            (out/'protocol.json').write_text(json.dumps({'filesSha256': {str(data): diagnosis.digest(data)}}))
            data.write_text('after')
            with self.assertRaisesRegex(ValueError, 'input/code drift'):
                diagnosis.check(out)

    def test_completed_diagnostic_only_verifies_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory); (out/'protocol.json').write_text('{}')
            (out/'469').mkdir(); (out/'469/recognition.json').write_text('{}')
            with patch.object(diagnosis, 'check', return_value={}), patch.object(diagnosis, 'verify', return_value={'status': 'exported'}), patch.object(diagnosis.subprocess, 'Popen') as launch:
                self.assertEqual(diagnosis.recognize(out, {'id': '469'}), {'status': 'exported'})
                launch.assert_not_called()

    def test_control_mismatch_blocks_probe_interpretation(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory); (out/'protocol.json').write_text('{}')
            (out/'469').mkdir(); (out/'469/new.mxl').write_bytes(b'new')
            (out/'469/recognition.json').write_text('{}')
            archive = out/'archive.mxl'; archive.write_bytes(b'old')
            p = {'cases': [{'id': '469', 'archivedExport': str(archive)}]}
            with patch.object(diagnosis, 'check', return_value=p), patch.object(diagnosis, 'verify', return_value={'status': 'exported', 'export': 'new.mxl'}), patch.object(diagnosis.pilot, 'score', side_effect=lambda data: data), patch.object(diagnosis, 'probes') as probes:
                result = diagnosis.analyze(out)
                self.assertEqual(result['cases']['469']['status'], 'control-mismatch')
                self.assertIsNone(result['cases']['469']['diagnostics'])
                self.assertFalse(result['allScoreInventoriesExactlyReproduced'])
                probes.assert_not_called()


if __name__ == '__main__':
    unittest.main()
