"""Terminal evidence and vectorized crop-scoring contracts, not source accuracy."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_crop_scoring as scoring
import omr_followup_study as study
import omr_terminal_grid as terminal
import omr_terminal_worklist as worklist

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = ImageDraw = None
try:
    import numpy as np
except ImportError:
    np = None


@unittest.skipIf(Image is None, 'Pillow required for terminal evidence')
class TerminalTests(unittest.TestCase):
    def fixture(self, truncated=3):
        image = Image.new('L', (200, 210), 255)
        draw = ImageDraw.Draw(image)
        bands = []
        for staff, top in enumerate((15, 80, 145)):
            bands.append([5, top-5, 195, top+45])
            for dy in range(0, 41, 10):
                draw.line((0, top+dy, 199, top+dy), fill=0)
            draw.line((60, top, 60, top+40), fill=0)
            draw.line((100, top+5 if staff < truncated else top, 100, top+40), fill=0)
        return image, bands

    def test_aligned_short_stems_are_retained_but_not_bar_proposals(self):
        image, bands = self.fixture()
        before = image.tobytes()
        raw = terminal.geometry.shared_bar_grid(image, bands)
        frozen = copy.deepcopy(raw)
        self.assertEqual([r['x'] for r in raw['proposals']], [60, 100])
        refined = terminal.refine(image, raw)
        self.assertEqual([r['x'] for r in refined['proposals']], [60])
        rejected = next(r for r in refined['unresolved'] if r['x'] == 100)
        self.assertEqual(rejected['rawSupportStaves'], [0, 1, 2])
        self.assertEqual(rejected['supportStaves'], [])
        self.assertEqual(raw, frozen)
        self.assertEqual(image.tobytes(), before)

    def test_one_staff_cannot_supply_majority_after_terminal_rejection(self):
        image, bands = self.fixture(truncated=2)
        refined = terminal.shared_bar_grid(image, bands)
        self.assertEqual(refined['minimumSupportStaves'], 2)
        self.assertNotIn(100, [r['x'] for r in refined['proposals']])
        rejected = next(r for r in refined['unresolved'] if r['x'] == 100)
        self.assertEqual(rejected['supportStaves'], [2])

    def test_full_height_strokes_still_need_majority_and_are_not_certified(self):
        image, bands = self.fixture(truncated=0)
        refined = terminal.shared_bar_grid(image, bands)
        self.assertEqual([r['x'] for r in refined['proposals']], [60, 100])
        self.assertIsNone(refined['acceptedMeasures'])
        self.assertFalse(refined['recognizerChanged'])

    def test_native_adapter_preserves_boxes_and_completed_result(self):
        from test_omr_measure_loop import WorklistRunnerTests
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest, score = WorklistRunnerTests().fixture(root)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            result = worklist.run(manifest, score, root/'out')
            self.assertEqual(result['nativeHeads'], 2)
            self.assertEqual(sum(result['counts'].values()), 2)
            self.assertIsNone(result['exportEventMap'])
            with patch.object(terminal, 'refine', side_effect=AssertionError('must reuse')):
                self.assertEqual(worklist.run(manifest, score, root/'out'), result)
            self.assertEqual(before, {name: (root/name).read_bytes() for name in before})


@unittest.skipIf(Image is None or np is None, 'Pinned Pillow + NumPy required in CI')
class ScoringTests(unittest.TestCase):
    def rows(self):
        rows = []
        for index, box in enumerate(((3, 3, 20, 16), (6, 5, 17, 14), (2, 7, 21, 12))):
            image = Image.new('L', (24, 20), 255)
            draw = ImageDraw.Draw(image)
            if index == 1:
                draw.ellipse(box, fill=0)
            else:
                draw.rectangle(box, fill=0)
            rows.append({'id': str(index), 'label': 'round/filled' if index == 1 else 'square/filled', 'pixels': image})
        return rows

    def test_integer_ssd_and_winner_match_pillow_on_multiple_queries(self):
        rows = self.rows(); old = scoring.previous.fit(rows); bank = scoring.fit(rows)
        for row in rows:
            result = scoring.predict(row['pixels'], bank)['raw-ssd']
            previous = scoring.previous.predict(row['pixels'], old)
            for key in ('prediction', 'neighborId', 'scale', 'offset', 'distance'):
                self.assertEqual(result[key], previous[key])

    def test_extreme_pixel_and_gradient_deltas_do_not_overflow(self):
        rows = self.rows(); bank = scoring.fit(rows)
        result = scoring.predict(Image.new('L', (24, 20), 0), bank)
        for arm in result.values():
            self.assertGreaterEqual(arm['distance'], 0)
            self.assertTrue(np.isfinite(arm['distance']))

    def test_multiple_variants_do_not_count_as_distinct_exemplar_votes(self):
        bank = {'rows': [{'id': id, 'label': label, 'scale': 1., 'offset': [0, 0]}
                         for id, label in [('a', 'square/filled'), ('a', 'square/filled'),
                                           ('b', 'square/filled'), ('c', 'round/filled')]]}
        result = scoring.rank([0, 1, 100, 40], bank, top_k=3)
        # Square class score is mean(0,100), not mean(0,1,100).
        self.assertEqual(result['prediction'], 'round/filled')
        self.assertEqual(result['distance'], 40)
        self.assertEqual(result['distinctExemplarsScored'], 1)

    def test_flat_contrast_and_identical_classes_abstain_selectively(self):
        image = Image.new('L', (24, 20), 255)
        bank = scoring.fit([{'id': 'a', 'label': 'square/open', 'pixels': image},
                            {'id': 'b', 'label': 'round/open', 'pixels': image}])
        for arm in scoring.predict(image, bank).values():
            self.assertIsNone(arm['selectivePrediction'])


class ProtocolTests(unittest.TestCase):
    def test_code_input_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'development-protocol.json').write_text('{}')
            with patch.object(study, 'protocol', return_value={'changed': True}):
                with self.assertRaises(ValueError):
                    study.check(root)

    @unittest.skipIf(Image is None, 'Transfer requires Pillow')
    def test_transfer_cannot_create_a_missing_pre_source_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(study, 'check', return_value={}):
                with self.assertRaisesRegex(ValueError, 'BEFORE'):
                    study.transfer(Path(d), Path(d)/'not-read.json')

    def test_freeze_binds_development_outcome_and_detects_changed_selection(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'development-protocol.json').write_text('{}')
            dev = {'protocolSha256': study.prior.archive.digest(root/'development-protocol.json'), 'selectedArm': 'raw-ssd'}
            (root/'development.json').write_text(json.dumps(dev))
            current = {'selected': {'songNo': '80t'}, 'sourceSha256': 'source', 'scope': 'scope'}
            with patch.object(study, 'check', return_value=current):
                frozen = study.freeze(root)
                self.assertEqual(frozen['selectedArm'], 'raw-ssd')
                dev['selectedArm'] = 'class-top3'
                (root/'development.json').write_text(json.dumps(dev))
                with self.assertRaises(ValueError):
                    study.freeze(root)


if __name__ == '__main__':
    unittest.main()
