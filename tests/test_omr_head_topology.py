"""Clone-safe pixel/topology controls; these do not establish scan accuracy."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_head_topology as detector
import omr_head_topology_study as study
import omr_head_topology_transfer as transfer

try:
    from PIL import Image, ImageDraw
    import numpy as np
except ImportError:
    Image = ImageDraw = np = None


@unittest.skipIf(Image is None or np is None, 'Pinned image dependencies required')
class TopologyTests(unittest.TestCase):
    def staff(self):
        image = Image.new('L', (240, 120), 255)
        draw = ImageDraw.Draw(image)
        for y in range(40, 81, 10):
            draw.line((10, y, 229, y), fill=0)
        return image, draw, [{'staff': 0, 'box': [10, 10, 230, 110]}]

    def test_open_square_center_moves_with_pixels_and_source_unchanged(self):
        centers = []
        for x in (60, 110):
            image, draw, windows = self.staff()
            draw.rectangle((x-6, 51, x+6, 59), outline=0, width=2)
            before = image.tobytes()
            result = detector.propose(image, windows)
            self.assertEqual(image.tobytes(), before)
            self.assertEqual(len(result['holes']), 1)
            centers.append(result['holes'][0]['x'])
            self.assertAlmostEqual(result['holes'][0]['y'], 55, delta=1)
        self.assertEqual(centers[1]-centers[0], 50)

    def test_bisected_open_square_halves_merge_without_changing_center(self):
        image, draw, windows = self.staff()
        draw.rectangle((54, 36, 66, 44), outline=0, width=2)
        holes = detector.propose(image, windows)['holes']
        self.assertEqual(len(holes), 1)
        self.assertEqual(holes[0]['fragments'], 2)
        self.assertAlmostEqual(holes[0]['y'], 40, delta=1)

    def test_white_diagonal_outline_is_not_flooded_through_diagonal_contact(self):
        mask = np.array([[True, False, True], [False, True, False], [True, False, True]])
        self.assertEqual(sorted(map(len, detector.white_components(mask))), [1]*5)

    def test_thin_rest_rejected_while_filled_square_is_retained(self):
        image, draw, windows = self.staff()
        draw.rectangle((35, 50, 48, 55), fill=0)
        draw.rectangle((75, 50, 85, 60), fill=0)
        result = detector.propose(image, windows)
        self.assertEqual(len(result['filled']), 1)
        self.assertAlmostEqual(result['filled'][0]['x'], 80, delta=1)
        self.assertEqual(sum(r['reason'] == 'thin-central-ink' for r in result['vetoes']), 1)

    def test_closed_staff_bar_cells_do_not_become_open_heads(self):
        image, draw, windows = self.staff()
        for x in (55, 63): draw.line((x, 40, x, 80), fill=0)
        result = detector.propose(image, windows)
        self.assertEqual(result['holes'], [])
        self.assertEqual(sum(r['reason'] == 'rectangular-staff-cell' for r in result['vetoes']), 4)

    def test_unclosed_boundary_and_missing_lattice_abstain(self):
        image, draw, windows = self.staff()
        draw.line((50, 22, 60, 22, 60, 28, 50, 28), fill=0, width=2)
        self.assertEqual(detector.propose(image, windows)['holes'], [])
        image = Image.new('L', (120, 120), 255)
        ImageDraw.Draw(image).rectangle((45, 45, 55, 55), outline=0, width=2)
        result = detector.propose(image, [{'staff': 0, 'box': [10, 10, 110, 110]}])
        self.assertEqual((result['holes'], result['filled']), ([], []))

    def test_native_fusion_is_immutable_and_can_suppress_a_valid_nearby_hole(self):
        native = [{'id': 'n', 'x': 10, 'y': 20, 'staff': 0, 'prediction': 'round/filled'}]
        hole = {'id': 'h', 'x': 16, 'y': 20, 'staff': 0, 'interline': 10,
                'prediction': 'diamond/open'}
        before = copy.deepcopy(native)
        fused, suppressed = detector.dense.fuse(native, [hole])
        self.assertEqual(fused, before)
        self.assertEqual(suppressed[0]['id'], 'h')


class GateAndReplayTests(unittest.TestCase):
    def test_gate_never_forces_fill_or_shape_and_abstentions_stay_excluded(self):
        def row(id, label): return {'id': id, 'selectivePrediction': label}
        filled = [row('square', 'square/filled'), row('round', 'round/filled')]
        holes = [row('diamond', 'diamond/open'), row('ambiguous', None),
                 row('filled-hole', 'square/filled'), row('not-head', 'non_head')]
        self.assertEqual([r['id'] for r in detector.select(filled, holes)], ['square', 'diamond'])

    def test_fragment_chain_cannot_exceed_cap(self):
        holes = [{'box': [10, y, 17, y+4], 'holePixels': 28} for y in (10, 15, 20, 25)]
        groups = detector.merge_fragments(holes, 10)
        self.assertTrue(all(r['box'][3]-r['box'][1] <= 11.5 for r in groups))
        self.assertEqual(sum(r['fragments'] for r in groups), 4)

    def test_replay_rejects_report_and_protocol_drift_before_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); out = root/'out'
            study.immutable(out/'protocol.json', {'v': 1})
            study.immutable(out/'report.json', {'pages': {}})
            study.immutable(out/'receipt.json', {'reportSha256': study.digest(out/'report.json')})
            with patch.object(study, 'protocol', return_value={'v': 1}):
                self.assertEqual(study.run(root/'retained', root/'clayton', out), {'pages': {}})
                (out/'report.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'report drift'):
                    study.run(root/'retained', root/'clayton', out)
            with patch.object(study, 'protocol', return_value={'v': 2}):
                with self.assertRaisesRegex(ValueError, 'artifact drift'):
                    study.run(root/'retained', root/'clayton', out)


class NewTransferTests(unittest.TestCase):
    def test_source_freeze_rejects_changed_development_before_source_access(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); developed = root/'dev'
            study.immutable(developed/'protocol.json', {'v': 1})
            with patch.object(study, 'protocol', return_value={'v': 2}):
                with self.assertRaisesRegex(ValueError, 'Development result/code binding drift'):
                    transfer.prepare(root/'retained', root/'clayton', developed, root/'new')
            self.assertFalse((root/'new'/'protocol.json').exists())

    def test_started_recognition_never_retries_or_uses_clayton_path(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d); (out/'started.json').write_text('{}')
            p = {'engineExecutable': '/must-not-run', 'settings': {'constants': []},
                 'sourcePath': 'seventh-source.jpg'}
            with patch.object(transfer.subprocess, 'Popen', side_effect=AssertionError('retry')):
                with self.assertRaisesRegex(ValueError, 'no implicit retry'):
                    transfer.recognize(out, out, p)

    def test_native_command_binds_protocol_source_and_completed_raw_bytes(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            study.immutable(out/'inference-lock.json', {'v': 1})
            p = {'engineExecutable': '/fake', 'settings': {'constants': [], 'JAVA_OPTS': ''},
                 'JAVA_HOME': '/fake-java', 'sourcePath': 'seventh-source.jpg'}
            proc = MagicMock(); proc.wait.return_value = 1
            with patch.object(transfer, 'check', return_value=p), \
                 patch.object(transfer.subprocess, 'Popen', return_value=proc) as launch:
                receipt = transfer.recognize(out, out, p)
            self.assertEqual(launch.call_args.args[0][-1], str((out/'seventh-source.jpg').resolve()))
            self.assertEqual(receipt['status'], 'recognition-failed')
            (out/'audiveris.log').write_text('drift')
            with self.assertRaisesRegex(ValueError, 'drift'):
                transfer.recognize(out, out, p)

    @unittest.skipIf(Image is None, 'Pinned dependency required')
    def test_failed_native_has_no_zero_count_native_or_fused_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d); image_path = out/'source.png'
            Image.new('L', (200, 400), 255).save(image_path)
            p = {'sourceSha256': study.digest(image_path), 'sourcePath': 'source.png',
                 'source': 'SH2025/469', 'phase': 'frozen', 'primaryArm': 'native-plus-topology'}
            labels = {'sourceSha256': p['sourceSha256'], 'completeHeadCensus': True,
                      'windows': [{'staff': i, 'box': [0, i*100, 200, (i+1)*100]} for i in range(4)],
                      'rows': [{'id': 'a', 'staff': 0, 'x': 50, 'y': 40,
                                'interline': 10, 'label': None}]}
            study.immutable(out/'protocol.json', p)
            study.immutable(out/'source-observations.json', labels)
            study.immutable(out/'inference-lock.json', {
                'protocolSha256': study.digest(out/'protocol.json'),
                'labelsSha256': study.digest(out/'source-observations.json')})
            study.immutable(out/'recognition.json', {'status': 'recognition-failed'})
            arms = {k: {} for k in ('native', 'native-plus-old-squares', 'native-plus-topology', 'holes-all')}
            analysis = {'arms': copy.deepcopy(arms), 'predictions': copy.deepcopy(arms)}
            with patch.object(transfer, 'check', return_value=p), \
                 patch.object(transfer, 'recognize', return_value={'status': 'recognition-failed'}), \
                 patch.object(study.prior, 'retained_evidence', return_value=(None, None, {})), \
                 patch.object(study.prior, 'fit_bank', return_value={}), \
                 patch.object(study, 'analyze', return_value=analysis):
                report = transfer.evaluate(out, out)
                self.assertEqual(set(report['arms']), {'holes-all'})
                self.assertIsNone(report['nativeHeadNodesAllImage'])
                self.assertFalse(report['safeToPromote'])
                (out/'report.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'report/recognition drift'):
                    transfer.evaluate(out, out)


if __name__ == '__main__': unittest.main()
