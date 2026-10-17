"""Meaningful localization, abstention and evidence-boundary contracts."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_measure_classifier as classifier
import omr_measure_study as study
import omr_measure_worklist as worklist

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = ImageDraw = None


class MetricTests(unittest.TestCase):
    def test_abstentions_cannot_inflate_accuracy_or_hide_review_targets(self):
        rows = [{'id': 'a', 'label': 'round/open', 'baseline': 'round/filled', 'prediction': 'round/open'},
                {'id': 'b', 'label': 'square/open', 'baseline': 'square/open', 'prediction': None},
                {'id': 'c', 'label': 'diamond/open', 'baseline': 'triangle/open', 'prediction': 'round/open'}]
        m = classifier.metrics(rows)
        self.assertEqual((m['targets'], m['correct'], m['proposed'], m['abstentions']), (3, 1, 2, 1))
        self.assertEqual((m['fixed'], m['regressed'], m['wrongProposals']), (1, 1, 1))
        self.assertEqual(m['accuracyAllTargets'], 1/3)
        self.assertEqual(m['accuracyAmongProposals'], 1/2)
        self.assertEqual(m['oracleReviewTargets'], 2)
        self.assertIsNone(m['measuredHumanEdits'])
        self.assertIsNone(m['detectorRecall'])

    def test_empty_metrics_and_duplicate_targets(self):
        m = classifier.metrics([])
        self.assertIsNone(m['proposalCoverage'])
        self.assertIsNone(m['accuracyAmongProposals'])
        row = {'id': 'x', 'label': 'round/open', 'baseline': None, 'prediction': None}
        with self.assertRaises(ValueError):
            classifier.metrics([row, row])


class LocalizationTests(unittest.TestCase):
    bands = [[10, 10, 190, 70], [10, 80, 190, 140]]
    lattices = [{'status': 'proposal', 'interline': 10}]*2
    spans = [{'spanIndex': 0, 'left': 10, 'right': 100, 'status': 'split-draft-measure-proposal'},
             {'spanIndex': 1, 'left': 100, 'right': 190, 'status': 'one-to-one-proposal'}]

    def head(self, id='h1', x=40, y=30, staff='s1'):
        return {'id': id, 'staffId': staff, 'nativeShape': 'NOTEHEAD_BLACK', 'bounds': [x, y, 12, 8]}

    def test_full_footprint_assigns_split_measure_without_export_mapping(self):
        heads = [self.head(), self.head('h2', x=130, y=100, staff='s2')]
        original = copy.deepcopy((heads, self.spans, self.bands))
        result = worklist.assign(heads, self.spans, self.bands, ['s1', 's2'], self.lattices)
        self.assertEqual([r['spanIndex'] for r in result['heads']], [0, 1])
        self.assertEqual(result['heads'][0]['spanStatus'], 'split-draft-measure-proposal')
        self.assertIsNone(result['exportEventMap'])
        self.assertFalse(result['scoreChanged'])
        self.assertEqual((heads, self.spans, self.bands), original)

    def test_center_alone_does_not_authorize_boundary_crossing(self):
        result = worklist.assign([self.head(x=90)], self.spans, self.bands, ['s1', 's2'], self.lattices)
        self.assertEqual(result['heads'][0]['status'], 'boundary-or-band-crossing-review')
        self.assertIsNone(result['heads'][0]['spanIndex'])

    def test_unresolved_lattice_staff_and_outside_heads_remain_counted(self):
        heads = [self.head(), self.head('h2', staff='unknown'), self.head('h3', x=0)]
        result = worklist.assign(heads, self.spans, self.bands, ['s1', 's2'],
                                 [{'status': 'unresolved'}, self.lattices[1]])
        self.assertEqual(result['nativeHeads'], 3)
        self.assertEqual(set(result['counts']), {'unresolved-staff-lattice', 'unknown-staff-review', 'outside-supplied-region'})

    def test_duplicate_native_id_or_staff_registration_rejected(self):
        for heads, staffs in [([self.head(), self.head()], ['s1', 's2']), ([self.head()], ['s1', 's1'])]:
            with self.assertRaises(ValueError):
                worklist.assign(heads, self.spans, self.bands, staffs, self.lattices)

    def test_nonfinite_geometry_is_not_a_valid_review_crop(self):
        with self.assertRaises(ValueError):
            worklist.assign([self.head(x=float('nan'))], self.spans, self.bands, ['s1', 's2'], self.lattices)


@unittest.skipIf(Image is None, 'Pillow required for image classification')
class ImageTests(unittest.TestCase):
    def stamp(self, shape):
        image = Image.new('L', (24, 20), 255)
        draw = ImageDraw.Draw(image)
        if shape == 'square':
            draw.rectangle((3, 3, 20, 16), fill=0)
        else:
            draw.ellipse((3, 3, 20, 16), fill=0)
        return image

    def test_smaller_shifted_shape_has_a_matching_scale_witness(self):
        square, circle = self.stamp('square'), self.stamp('round')
        bank = classifier.fit([{'id': 's', 'label': 'square/filled', 'pixels': square},
                               {'id': 'r', 'label': 'round/filled', 'pixels': circle}])
        query = Image.new('L', (24, 20), 255)
        query.paste(square.resize((18, 15), Image.Resampling.BILINEAR), (4, 1))
        result = classifier.predict(query, bank)
        self.assertEqual(result['prediction'], 'square/filled')
        self.assertEqual(result['scale'], .75)
        self.assertEqual(result['distance'], 0)

    def test_tied_classes_and_single_class_abstain_selectively(self):
        im = self.stamp('square')
        for rows in [[{'id': 's', 'label': 'square/filled', 'pixels': im}],
                     [{'id': 's', 'label': 'square/filled', 'pixels': im},
                      {'id': 'r', 'label': 'round/filled', 'pixels': im}]]:
            self.assertIsNone(classifier.predict(im, classifier.fit(rows))['selectivePrediction'])

    def test_out_of_source_crops_fail_instead_of_padding(self):
        with self.assertRaises(ValueError):
            classifier.crop(self.stamp('round'), 1, 1, 10)


@unittest.skipIf(Image is None, 'Pillow required for native worklist integration')
class WorklistRunnerTests(unittest.TestCase):
    def fixture(self, root):
        from test_omr_grid_alignment import RunnerTests
        manifest, score = RunnerTests().fixture(root)
        graph = root/'graph.omr'
        with zipfile.ZipFile(graph) as z:
            book = z.read('book.xml')
            sheet = ET.fromstring(z.read('sheet#1/sheet#1.xml'))
        system = sheet.find('./page/system')
        for index, staff in enumerate(system.findall('./part/staff'), 1):
            staff.set('id', str(index))
        for id, x, staff in [('one', 35, '1'), ('two', 65, '2')]:
            head = ET.SubElement(system, 'head', id=id, staff=staff, shape='NOTEHEAD_BLACK')
            ET.SubElement(head, 'bounds', x=str(x), y='30' if staff == '1' else '90', w='10', h='8')
        with zipfile.ZipFile(graph, 'w') as z:
            z.writestr('book.xml', book)
            z.writestr('sheet#1/sheet#1.xml', ET.tostring(sheet))
        m = json.loads(manifest.read_text())
        m['graph']['sha256'] = worklist.archive.digest(graph)
        manifest.write_text(json.dumps(m))
        return manifest, score

    def test_worklist_retains_crossing_and_reuses_without_graph_or_image_work(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest, score = self.fixture(root)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            result = worklist.run(manifest, score, root/'out')
            self.assertEqual(result['nativeHeads'], 2)
            self.assertEqual(result['counts'], {'localized-proposal': 1, 'boundary-or-band-crossing-review': 1})
            with patch.object(worklist, 'native_heads', side_effect=AssertionError('must reuse')):
                self.assertEqual(worklist.run(manifest, score, root/'out'), result)
            self.assertEqual(before, {name: (root/name).read_bytes() for name in before})

    def test_source_drift_rejected_on_completed_worklist(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest, score = self.fixture(root)
            worklist.run(manifest, score, root/'out')
            with (root/'source.png').open('ab') as f:
                f.write(b'drift')
            with self.assertRaises(ValueError):
                worklist.run(manifest, score, root/'out')

    def test_shared_ranker_drift_rejected_on_completed_worklist(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest, score = self.fixture(root)
            worklist.run(manifest, score, root/'out')
            digest = worklist.archive.digest
            def changed(path):
                if Path(path) == Path(worklist.classifier.ranking.__file__):
                    return 'changed-ranker'
                return digest(path)
            with patch.object(worklist.archive, 'digest', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'Immutable artifact differs'):
                    worklist.run(manifest, score, root/'out')


class FrozenProtocolTests(unittest.TestCase):
    def test_changed_input_or_code_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'protocol.json').write_text(json.dumps({'recipe': 1}))
            with patch.object(study, 'current_protocol', return_value={'recipe': 2}):
                with self.assertRaises(ValueError):
                    study.check_protocol(root)

    @unittest.skipIf(Image is None, 'Transfer runner requires Pillow')
    def test_completed_transfer_reuses_before_fitting_or_image_inference(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            labels = {'sourceSha256': 'source', 'bands': [[0, 0, 10, 10]]*4,
                      'rows': [{'id': f'188-p{p}-n{n}', 'label': 'round/filled'}
                               for p in range(1, 5) for n in range(1, 7)]}
            (root/'labels.json').write_text(json.dumps(labels))
            (root/'protocol.json').write_text('{}')
            lock = {'protocolSha256': study.archive.digest(root/'protocol.json'),
                    'labelsSha256': study.archive.digest(root/'labels.json')}
            study.archive.immutable(root/'inference-lock.json', study.archive.json_bytes(lock))
            report = {'inferenceLockSha256': study.archive.digest(root/'inference-lock.json')}
            (root/'transfer.json').write_text(json.dumps(report))
            with patch.object(study, 'check_protocol', return_value={'sourceSha256': 'source'}), \
                 patch.object(study.baseline, 'samples', side_effect=AssertionError('must reuse')):
                self.assertEqual(study.transfer(root, root/'labels.json'), report)


if __name__ == '__main__':
    unittest.main()
