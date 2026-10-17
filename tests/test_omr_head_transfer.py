"""Clone-safe transfer accounting, source-lock and failure policy checks."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_head_transfer as transfer


class TransferTests(unittest.TestCase):
    def census(self):
        return {'sourceSha256': 'source', 'completeHeadCensus': True,
                'windows': [{'staff': i, 'box': [0, i*100, 200, (i+1)*100]} for i in range(4)],
                'rows': [{'id': 'source-1', 'staff': 0, 'x': 50, 'y': 40,
                          'interline': 10, 'label': None}]}

    def test_unresolved_labels_remain_in_complete_source_denominator(self):
        labels = self.census()
        transfer.validate_census(labels, {'sourceSha256': 'source'}, (200, 400))
        summary = transfer.prior.summarize(labels['rows'], [])['0.5']['summary']
        self.assertEqual((summary['sourceHeads'], summary['knownLiteralTargets'],
                          summary['missedSourceHeads']), (1, 0, 1))

    def test_source_identity_and_completeness_required(self):
        for change in ({'sourceSha256': 'other'}, {'completeHeadCensus': False}):
            with self.assertRaises(ValueError):
                transfer.validate_census(dict(self.census(), **change),
                                         {'sourceSha256': 'source'}, (200, 400))

    def test_windows_and_observations_cannot_escape_complete_scope(self):
        original = self.census()
        bad = []
        for key, value in [('x', 200), ('interline', float('nan')), ('staff', -1),
                           ('label', 'guessed'), ('y', 100)]:
            labels = copy.deepcopy(original); labels['rows'][0][key] = value; bad.append(labels)
        labels = copy.deepcopy(original); labels['windows'][1]['box'][1] = 90; bad.append(labels)
        labels = copy.deepcopy(original); labels['windows'][0]['box'][0] = -1; bad.append(labels)
        labels = copy.deepcopy(original); labels['rows'] *= 2; bad.append(labels)
        for labels in bad:
            with self.assertRaises(ValueError):
                transfer.validate_census(labels, {'sourceSha256': 'source'}, (200, 400))

    def test_completed_raw_artifact_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d); raw = out/'raw.bin'; raw.write_bytes(b'original')
            transfer.immutable(out/'inference-lock.json', {'source': 'locked'})
            transfer.immutable(out/'recognition.json', {
                'inferenceLockSha256': transfer.digest(out/'inference-lock.json'),
                'status': 'recognition-failed',
                'artifactsSha256': {'raw.bin': transfer.digest(raw)}})
            self.assertEqual(transfer.recognize(out, out, {})['status'], 'recognition-failed')
            raw.write_bytes(b'drift')
            with self.assertRaisesRegex(ValueError, 'drift'):
                transfer.recognize(out, out, {})

    def test_started_recognition_never_implicitly_retries(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d); (out/'started.json').write_text('{}')
            p = {'engineExecutable': '/must-not-run', 'settings': {'constants': []}}
            with patch.object(transfer.subprocess, 'Popen', side_effect=AssertionError('retry')):
                with self.assertRaisesRegex(ValueError, 'no implicit retry'):
                    transfer.recognize(out, out, p)

    def test_lock_drift_fails_before_recognition(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            transfer.immutable(out/'protocol.json', {'v': 1})
            transfer.immutable(out/'source-observations.json', self.census())
            transfer.immutable(out/'inference-lock.json', {
                'protocolSha256': transfer.digest(out/'protocol.json'), 'labelsSha256': 'wrong'})
            with patch.object(transfer, 'check', return_value={}), \
                 patch.object(transfer, 'recognize', side_effect=AssertionError('inference')):
                with self.assertRaisesRegex(ValueError, 'lock drift'):
                    transfer.evaluate(out, out)

    def test_completed_report_reuses_without_inference_and_rejects_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            transfer.immutable(out/'protocol.json', {'v': 1})
            transfer.immutable(out/'source-observations.json', self.census())
            transfer.immutable(out/'inference-lock.json', {
                'protocolSha256': transfer.digest(out/'protocol.json'),
                'labelsSha256': transfer.digest(out/'source-observations.json')})
            transfer.immutable(out/'recognition.json', {'status': 'recognition-failed'})
            transfer.immutable(out/'report.json', {'result': 'retained'})
            transfer.immutable(out/'receipt.json', {
                'reportSha256': transfer.digest(out/'report.json'),
                'recognitionSha256': transfer.digest(out/'recognition.json')})
            with patch.object(transfer, 'check', return_value={}), \
                 patch.object(transfer, 'recognize', return_value={}), \
                 patch.object(transfer.prior, 'fit_bank', side_effect=AssertionError('refit')):
                self.assertEqual(transfer.evaluate(out, out), {'result': 'retained'})
                (out/'report.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'report/recognition drift'):
                    transfer.evaluate(out, out)


if __name__ == '__main__':
    unittest.main()
