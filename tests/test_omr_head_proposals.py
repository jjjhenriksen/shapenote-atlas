"""Image-only localization, conservative fusion and immutable development replay."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_head_proposals as detector
import omr_head_proposal_study as study

try:
    from PIL import Image, ImageDraw
    import numpy
except ImportError:
    Image = ImageDraw = numpy = None


@unittest.skipIf(Image is None or numpy is None, 'Pinned image dependencies required in CI')
class ImageProposalTests(unittest.TestCase):
    def staff(self):
        image = Image.new('L', (240, 120), 255)
        draw = ImageDraw.Draw(image)
        for y in range(40, 81, 10):
            draw.line((10, y, 229, y), fill=0)
        return image, draw, [{'staff': 0, 'box': [10, 10, 230, 110]}]

    def test_square_center_from_pixels_no_source_centers_or_counts(self):
        image, draw, windows = self.staff()
        draw.rectangle((55, 50, 65, 60), fill=0)
        draw.line((55, 55, 55, 90), fill=0, width=2)
        before = image.tobytes()
        result = detector.propose(image, windows)
        self.assertEqual(image.tobytes(), before)
        self.assertEqual(len(result['proposals']), 1)
        row = result['proposals'][0]
        self.assertAlmostEqual(row['x'], 60, delta=1)
        self.assertAlmostEqual(row['y'], 55, delta=1)
        self.assertEqual(row['interline'], 10)

    def test_proposals_follow_translated_image_not_annotation(self):
        centers = []
        for x in (65, 115):
            image, draw, windows = self.staff()
            draw.rectangle((x-5, 50, x+5, 60), fill=0)
            centers.append(detector.propose(image, windows)['proposals'][0]['x'])
        self.assertEqual(centers[1]-centers[0], 50)

    def test_gray_background_thin_barlines_and_extended_beam_not_heads(self):
        image, draw, windows = self.staff()
        draw.rectangle((20, 17, 95, 26), fill=0)  # Dense but too extended.
        draw.rectangle((140, 20, 142, 95), fill=0)
        draw.rectangle((175, 52, 188, 62), fill=150)
        result = detector.propose(image, windows)
        self.assertEqual(result['proposals'], [])
        self.assertGreater(len(result['geometricVetoes']), 0)

    def test_open_head_is_not_claimed_by_filled_core_detector(self):
        image, draw, windows = self.staff()
        draw.rectangle((55, 50, 65, 60), outline=0, width=1)
        self.assertEqual(detector.propose(image, windows)['proposals'], [])

    def test_missing_lattice_abstains_without_fabricated_spacing(self):
        image = Image.new('L', (100, 100), 255)
        ImageDraw.Draw(image).rectangle((30, 30, 45, 45), fill=0)
        result = detector.propose(image, [{'staff': 0, 'box': [10, 10, 90, 90]}])
        self.assertEqual(result['proposals'], [])
        self.assertEqual(result['staffLattices'][0]['status'], 'unresolved')

    def test_invalid_overlapping_or_duplicate_staff_windows_rejected(self):
        image, _, windows = self.staff()
        for rows in (windows*2, windows+[{'staff': 1, 'box': windows[0]['box']}],
                     [{'staff': 0, 'box': [-1, 0, 100, 100]}]):
            with self.assertRaises(ValueError):
                detector.propose(image, rows)


class FusionTests(unittest.TestCase):
    def row(self, id, x, staff=0):
        return {'id': id, 'x': x, 'y': 10, 'staff': staff, 'interline': 10}

    def test_native_immutable_priority_staff_restriction_and_no_chain_merging(self):
        native = [self.row('native', 10)]
        proposals = [self.row('near', 17), self.row('new', 24), self.row('other-staff', 10, 1)]
        before = copy.deepcopy((native, proposals))
        fused, suppressed = detector.fuse(native, proposals)
        self.assertEqual((native, proposals), before)
        self.assertEqual([r['id'] for r in fused], ['native', 'new', 'other-staff'])
        self.assertEqual(suppressed[0]['suppressedBy'], 'native')

    def test_duplicate_nonfinite_and_invalid_scale_rejected(self):
        row = self.row('a', 10)
        for native, proposals in (([row], [row]), ([], [dict(row, x=float('nan'))]),
                                  ([], [dict(row, interline=0)])):
            with self.assertRaises(ValueError): detector.fuse(native, proposals)


class StudyTests(unittest.TestCase):
    @unittest.skipIf(Image is None, 'Image dependency required')
    def test_classification_uses_only_automatic_centers(self):
        proposal = {'id': 'automatic', 'staff': 0, 'x': 53, 'y': 40, 'interline': 10}
        centers = []
        def crop(image, x, y, spacing):
            centers.append((x, y, spacing))
            return Image.new('L', (24, 20), 255)
        with patch.object(study.training.prior.classifier, 'crop', side_effect=crop), \
             patch.object(study.training, 'predict', return_value={'prediction': 'square/filled'}):
            rows = study.classify(Image.new('L', (100, 100), 255), [proposal], {})
        self.assertEqual(centers, [(53, 40, 10)])
        self.assertEqual((rows[0]['x'], rows[0]['y']), (53, 40))

    def test_evaluation_page_cannot_enter_reconstructed_bank(self):
        samples = [{'id': str(i), 'group': 'page', 'sourceSha256': 'evaluation',
                    'label': 'square/filled'} for i in range(373)]
        with self.assertRaisesRegex(ValueError, 'source leakage'):
            study.fit_bank(Path('/must-not-open'), {'samples': samples}, 'evaluation')

    def test_new_candidates_and_misses_stay_in_both_denominators(self):
        sources = [{'id': 's1', 'x': 10, 'y': 10, 'staff': 0, 'interline': 10, 'label': 'square/filled'},
                   {'id': 's2', 'x': 30, 'y': 10, 'staff': 0, 'interline': 10, 'label': 'round/filled'}]
        rows = [{'id': 'p', 'x': 10, 'y': 10, 'staff': 0, 'prediction': 'square/filled'},
                {'id': 'extra', 'x': 80, 'y': 10, 'staff': 0, 'prediction': 'square/filled'}]
        summary = study.summarize(sources, rows)['0.5']['summary']
        self.assertEqual((summary['candidatePredictions'], summary['matched'],
                          summary['missedSourceHeads'], summary['unmatchedPredictions']), (2, 1, 1, 1))
        self.assertEqual(summary['correctLiteralPerKnownSourceHead'], .5)
        self.assertNotIn('nativePredictions', summary)

    def test_immutable_bytes_and_completed_report_drift_rejected_before_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)/'new'
            study.immutable(out/'protocol.json', {'phase': 'development'})
            study.immutable(out/'protocol.json', {'phase': 'development'})
            with self.assertRaises(ValueError):
                study.immutable(out/'protocol.json', {'phase': 'changed'})
            study.immutable(out/'report.json', {'result': 1})
            study.immutable(out/'receipt.json', {'reportSha256': study.digest(out/'report.json')})
            with patch.object(study, 'protocol', return_value={'phase': 'development'}), \
                 patch.object(study, 'retained_evidence', side_effect=AssertionError('must reuse')):
                self.assertEqual(study.run(Path(directory), out), {'result': 1})
                (out/'report.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'report drift'):
                    study.run(Path(directory), out)

    def test_completed_protocol_drift_rejected_before_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)/'new'
            study.immutable(out/'protocol.json', {'version': 1})
            with patch.object(study, 'protocol', return_value={'version': 2}):
                with self.assertRaisesRegex(ValueError, 'drift'):
                    study.run(Path(directory), out)

    @unittest.skipIf(Image is None or numpy is None, 'Pinned dependencies required')
    def test_protocol_binds_raw_artifact_bytes_not_just_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative_paths = [study.SOURCE, Path('selection.json'), Path('train.png'),
                              Path('raw.bin')]
            relative_paths += [study.PRIOR/name for name in (
                'source-observations.json', 'report.json', 'population-manifest.json',
                'recognition.json', 'inference-lock.json', 'transfer-protocol.json',
                'development-protocol.json')]
            for relative in relative_paths:
                path = root/relative; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'fixture')
            (root/study.PRIOR/'recognition.json').write_text(json.dumps(
                {'artifactsSha256': {'raw.bin': study.digest(root/'raw.bin')}}))
            with patch.object(study, 'source_paths', return_value=(
                    {'train': root/'train.png'}, root/'selection.json')):
                first = study.protocol(root)
                (root/'raw.bin').write_bytes(b'drift')
                second = study.protocol(root)
            self.assertNotEqual(first['retainedInputsSha256']['raw.bin'],
                                second['retainedInputsSha256']['raw.bin'])

    def test_old_frozen_output_directory_is_never_writable(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'Never write'):
                study.run(Path(directory), Path(directory)/study.PRIOR/'nested')


if __name__ == '__main__':
    unittest.main()
