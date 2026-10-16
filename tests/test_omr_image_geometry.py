"""Algorithm failure modes, not evidence of real-source OMR accuracy."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_image_geometry as geometry
import omr_image_study as study
import omr_bar_grid as grid
try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = ImageDraw = None


class EvaluationTests(unittest.TestCase):
    def test_duplicates_count_as_extra_boundaries(self):
        result = study.match_boundaries([10, 20], [10, 10, 20], 1)
        self.assertEqual((result['matched'], result['extra']), (2, 1))

    def test_outside_tolerance_is_not_a_match(self):
        result = study.match_boundaries([10, 20], [14, 20], 2)
        self.assertEqual((result['matched'], result['extra'], result['missed']), (1, 1, 1))

    def test_abstentions_remain_in_denominator_and_can_regress(self):
        rows = [{'label': 'a', 'baseline': 'a', 'prediction': None},
                {'label': 'b', 'baseline': 'a', 'prediction': 'b'},
                {'label': 'c', 'baseline': 'b', 'prediction': 'a'}]
        self.assertEqual(study.compare_predictions(rows),
                         {'samples': 3, 'baselineCorrect': 1, 'candidateCorrect': 1,
                          'abstained': 1, 'fixed': 1, 'regressed': 1, 'wrongProposals': 1})

    def test_three_neighbor_vote_and_empty_training_fail(self):
        train = [{'id': str(i), 'label': label, 'features': [v]} for i, label, v in
                 [(0, 'square', .1), (1, 'round', .11), (2, 'round', .12)]]
        self.assertEqual(geometry.geometry_predict([0], train)['prediction'], 'round')
        with self.assertRaises(ValueError):
            geometry.geometry_predict([0], [])
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            geometry.geometry_predict([0, 1], train)

    @unittest.skipIf(Image is None, "Pillow optional")
    def test_completed_run_reused_without_computing(self):
        # Test the retry contract with a deliberately small bound protocol.
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            with patch.object(study, 'protocol_inputs', return_value={}), \
                 patch.object(study, 'render_bank', return_value=[]), \
                 patch.object(study, 'bar_study', side_effect=RuntimeError('stop')):
                with self.assertRaisesRegex(RuntimeError, 'stop'):
                    study.run(out, {})
            protocol_hash = study.archive.digest(out/'protocol.json')
            (out/'report.json').write_text(json.dumps({'protocolSha256': protocol_hash}))
            with patch.object(study, 'protocol_inputs', return_value={}), \
                 patch.object(study, 'render_bank', return_value=[]), \
                 patch.object(study, 'bar_study', side_effect=AssertionError('must not replay')):
                self.assertEqual(study.run(out, {})['protocolSha256'], protocol_hash)
            # Drift is rejected before a completed result can be reused.
            with patch.object(study, 'protocol_inputs', return_value={'changed': 'hash'}), \
                 patch.object(study, 'render_bank', return_value=[]):
                with self.assertRaisesRegex(ValueError, 'Immutable artifact differs'):
                    study.run(out, {})


@unittest.skipIf(Image is None, 'Pillow optional; install Pillow for image algorithm fixtures')
class ImageTests(unittest.TestCase):
    @staticmethod
    def page():
        image = Image.new('L', (240, 340), 255)
        draw = ImageDraw.Draw(image)
        bands = []
        for index in range(4):
            top = 20+index*80
            for line in range(5):
                draw.line((10, top+line*8, 230, top+line*8), fill=0)
            bands.append([10, top-5, 231, top+38])
        return image, bands

    def test_shared_bar_survives_missing_one_staff_and_stems_do_not_pass(self):
        image, bands = self.page(); draw = ImageDraw.Draw(image)
        for index in range(4):
            top = 20+index*80
            draw.line((60, top, 60, top+32), fill=0)
            if index != 2:
                draw.line((140, top, 140, top+32), fill=0)
            if index < 2:
                draw.line((190, top, 190, top+32), fill=0)
        original = image.tobytes()
        result = geometry.shared_bar_grid(image, bands)
        self.assertEqual([r['x'] for r in result['proposals']], [60, 140])
        self.assertEqual(result['minimumSupportStaves'], 3)
        self.assertIn(190, [r['x'] for r in result['unresolved']])
        self.assertEqual(original, image.tobytes())
        self.assertIsNone(result['acceptedMeasures'])

    def test_missing_staff_is_not_removed_from_consensus_denominator(self):
        image, bands = self.page(); draw = ImageDraw.Draw(image)
        for index in [2, 3]:
            draw.rectangle((0, bands[index][1], 239, bands[index][3]), fill=255)
        for index in [0, 1]:
            top = 20+index*80
            draw.line((80, top, 80, top+32), fill=0)
        result = geometry.shared_bar_grid(image, bands)
        self.assertEqual(result['proposals'], [])
        self.assertEqual(len(result['unresolved']), 1)

    def test_empty_or_ambiguous_staff_abstains(self):
        image = Image.new('L', (240, 100), 255)
        self.assertEqual(geometry.staff_lines(image, [0, 0, 240, 100])['status'], 'unresolved')
        draw = ImageDraw.Draw(image)
        for top in [10, 60]:
            for line in range(5):
                draw.line((0, top+line*5, 239, top+line*5), fill=0)
        self.assertEqual(geometry.staff_lines(image, [0, 0, 240, 100])['reason'], 'ambiguous-five-line-lattice')

    def test_invalid_crop_and_staff_population_fail(self):
        image, bands = self.page()
        for box in [[-1, 0, 10, 10], [0, 0, 300, 10], [0, 10, 10, 0]]:
            with self.assertRaises(ValueError):
                geometry.staff_lines(image, box)
        with self.assertRaises(ValueError):
            geometry.shared_bar_grid(image, bands[:1])
        with self.assertRaises(ValueError):
            geometry.note_crop(image, 1, 1, 12)
        with self.assertRaises(ValueError):
            geometry.note_crop(image, 60, 60, 0)

    def test_staff_suppression_preserves_original_and_crossing_ink(self):
        image = Image.new('L', (100, 100), 255); draw = ImageDraw.Draw(image)
        draw.line((0, 50, 99, 50), fill=0)
        draw.line((50, 20, 50, 80), fill=0)
        before = image.tobytes()
        raw, mask = geometry.analysis_mask(image, 50, 50, 12)
        self.assertEqual(before, image.tobytes())
        self.assertLess(sum(mask.getdata()), mask.width*mask.height*255)
        self.assertGreater(sum(mask.getdata()), sum(raw.getdata()))

    def test_contour_features_distinguish_fill_and_outline(self):
        filled = Image.new('L', (48, 40), 255); draw = ImageDraw.Draw(filled)
        draw.rectangle((7, 9, 40, 30), fill=0)
        opened = filled.copy(); ImageDraw.Draw(opened).rectangle((12, 14, 35, 25), fill=255)
        a = geometry.geometry_features(filled); b = geometry.geometry_features(opened)
        self.assertEqual(a[:54], b[:54])  # same outer contour, different interior
        self.assertNotEqual(a, b)

    def test_render_comparison_penalizes_extra_ink_and_empty_candidates(self):
        observed = Image.new('L', (48, 40), 255)
        ImageDraw.Draw(observed).rectangle((10, 10, 30, 30), fill=0)
        extra = observed.copy(); ImageDraw.Draw(extra).line((35, 4, 35, 35), fill=0)
        blank = Image.new('L', observed.size, 255)
        self.assertEqual(geometry.render_distance(observed, observed), 0)
        self.assertGreater(geometry.render_distance(observed, extra), 0)
        self.assertIsNone(geometry.render_distance(observed, blank))
        result = geometry.rank_rendered(blank, [{'id': '1', 'label': 'square', 'pixels': observed}])
        self.assertIsNone(result['prediction'])

    def test_identical_alternatives_abstain_and_variants_cannot_fake_margin(self):
        observed = Image.new('L', (48, 40), 255)
        ImageDraw.Draw(observed).rectangle((10, 10, 30, 30), fill=0)
        result = geometry.rank_rendered(observed, [
            {'id': str(i), 'label': label, 'pixels': observed}
            for i, label in enumerate(['square', 'square', 'round'])])
        self.assertIsNone(result['prediction'])
        self.assertEqual(len(result['ranking']), 2)
        self.assertEqual(result['margin'], 0)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            geometry.rank_rendered(observed, [{'id': 'same', 'label': 'x', 'pixels': observed}]*2)

    def test_grid_cli_reuses_completed_result_and_rejects_source_drift(self):
        image, bands = self.page()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'page.png'; witness = root/'bands.json'
            image.save(source)
            witness.write_text(json.dumps({'sourceSha256': grid.archive.digest(source), 'bands': bands}))
            report = grid.run(source, witness, root/'out')
            with patch.object(geometry, 'shared_bar_grid', side_effect=AssertionError('must not replay')):
                self.assertEqual(grid.run(source, witness, root/'out'), report)
            Image.new('L', image.size, 0).save(source)
            with self.assertRaisesRegex(ValueError, 'source binding'):
                grid.run(source, witness, root/'out')

    def test_synthetic_perturbation_is_deterministic_nonmutating(self):
        observed = Image.new('L', (64, 64), 255)
        ImageDraw.Draw(observed).polygon([(22, 23), (41, 23), (41, 40)], fill=0)
        before = observed.tobytes()
        for condition in study.CONDITIONS:
            first = geometry.perturb_head(observed, condition)
            second = geometry.perturb_head(observed, condition)
            self.assertEqual(first.tobytes(), second.tobytes())
        self.assertEqual(before, observed.tobytes())
        with self.assertRaises(ValueError):
            geometry.perturb_head(observed, 'unknown')


if __name__ == '__main__':
    unittest.main()
