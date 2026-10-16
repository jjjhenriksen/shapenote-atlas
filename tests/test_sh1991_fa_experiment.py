"""No engine needed: guard the no-rerun cache boundary and training selection."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import sh1991_fa_experiment as fa
import sh1991_pilot as pilot


class FaExperimentTest(unittest.TestCase):
    def test_better_detection_cannot_hide_worse_score_or_bad_fill(self):
        rule = {'triangleRetainedRecallGainAtLeast': .25, 'fillCorrectAmongRetainedTrianglesAtLeast': .8,
                'nonTriangleHeadRetentionAtLeast': .98, 'candidatePitchRecallGainAtLeast': .02,
                'candidatePitchPrecisionLossAtMost': .02, 'candidateDurationRecallLossAtMost': .01,
                'candidateOnsetRecallLossAtMost': .01}
        before = dict(candidatePitchRecall=.6, candidatePitchPrecision=.9,
                      candidateDurationRecall=.7, candidateOnsetRecall=.5, exports=5)
        after = dict(candidatePitchRecall=.3, candidatePitchPrecision=.5,
                     candidateDurationRecall=.4, candidateOnsetRecall=.1, exports=5)
        old = {'triangle': {'retainedRecall': .1}, 'other': {'retainedRecall': 1}}
        new = {'triangle': {'retainedRecall': .95, 'fillCorrectAmongRetained': .7},
               'other': {'retainedRecall': .97}}
        checks = fa.gate(rule, before, after, old, new, True)
        self.assertTrue(checks['triangleRecovery'])
        self.assertTrue(checks['exportCount'])
        self.assertFalse(any(checks[k] for k in ('triangleFill', 'otherHeadRetention',
                         'candidatePitchRecall', 'candidatePitchPrecision', 'candidateDuration', 'candidateOnset')))
        improved = {**before, 'candidatePitchRecall': .65}
        good_heads = {'triangle': {'retainedRecall': .95, 'fillCorrectAmongRetained': .9},
                      'other': {'retainedRecall': 1}}
        self.assertTrue(all(fa.gate(rule, before, improved, old, good_heads, True).values()))
        self.assertFalse(all(fa.gate(rule, before, improved, old, good_heads, False).values()))

    def test_prepare_is_idempotent_and_refuses_metadata_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); parent = root / 'dataset.json'; work = root / 'replay'
            pilot.write(parent, {'records': [{'songNo': '1', 'split': 'train'},
                                            {'songNo': '2', 'split': 'test'}]})
            frozen = root / 'frozen.json'
            pilot.write(frozen, {'protocol': {'trainingProbe': ['1'],
                'parentDatasetSha256': pilot.digest(parent.read_bytes())}, 'engine': {'version': 'frozen'}})
            with patch.object(fa, 'FROZEN_REPORT', frozen), patch.object(pilot, 'DEFAULT_WORK', root), \
                 patch.object(pilot, 'validate_dataset'):
                fa.prepare(work)
                paths = list(work.rglob('*.json')); original = {p: p.read_bytes() for p in paths}
                fa.prepare(work)
                self.assertEqual(original, {p: p.read_bytes() for p in paths})
                self.assertEqual([r['songNo'] for r in pilot.load(work / 'on/dataset.json')['records']], ['1'])
                pilot.write(work / 'on/dataset.json', {'records': []})
                with self.assertRaisesRegex(ValueError, 'refusing to replace'):
                    fa.prepare(work)
                self.assertEqual(pilot.load(work / 'on/dataset.json'), {'records': []})
                # Even a correctly hashed parent may not move a selected record into test.
                changed = pilot.load(parent); changed['records'][0]['split'] = 'test'; pilot.write(parent, changed)
                report = pilot.load(frozen); report['protocol']['parentDatasetSha256'] = pilot.digest(parent.read_bytes())
                pilot.write(frozen, report)
                with self.assertRaisesRegex(ValueError, 'frozen training records'):
                    fa.prepare(root / 'other-replay')

    def test_cached_recognition_reused_only_for_identical_constants(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); image = root / 'scan'; image.write_bytes(b'source')
            label = root / 'label'; label.write_bytes(b'label')
            engine = root / 'Audiveris'; engine.write_bytes(b'launcher')
            row = {'songNo': '1', 'split': 'train', 'group': 'g',
                   'pairingStatus': 'candidate-needs-independent-event-review',
                   'image': {'path': str(image), 'sha256': pilot.digest(image.read_bytes())},
                   'label': {'path': str(label), 'sha256': pilot.digest(label.read_bytes())}}
            pilot.write(root / 'dataset.json', {'records': [row]})
            command = [str(engine), '-batch', '-export', '-constant', 'faHeads=false',
                       '-output', str(root / 'baseline/1'), str(image)]
            receipt = {'songNo': '1', 'split': 'train', 'status': 'no-export', 'seconds': 1,
                       'datasetSha256': pilot.digest((root / 'dataset.json').read_bytes()),
                       'inputSha256': row['image']['sha256'], 'labelSha256': row['label']['sha256'],
                       'engineIdentity': {'version': 'same'}, 'command': command}
            pilot.write(root / 'baseline/1/run.json', receipt)
            fake_score = {'parts': [{'events': [{'pitch': ['C', '0', 4]}]}]}
            with patch.object(pilot, 'engine_identity', return_value={'version': 'same'}), \
                 patch.object(pilot, 'score', return_value=fake_score), \
                 patch.object(pilot.subprocess, 'Popen') as launch:
                pilot.run(root, engine, 1, 1, engine_constants=['faHeads=false'])
                with self.assertRaisesRegex(ValueError, 'cached command changed'):
                    pilot.run(root, engine, 1, 1, engine_constants=['faHeads=true'])
                launch.assert_not_called()
            self.assertEqual(pilot.load(root / 'baseline/1/run.json'), receipt)


if __name__ == '__main__':
    unittest.main()
