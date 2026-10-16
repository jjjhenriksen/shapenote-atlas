"""Population leakage, complete-window denominators and inference guards."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_localization_eval as evaluation
import omr_localization_study as study
import omr_training_population as training

try:
    from PIL import Image, ImageDraw
    import numpy
except ImportError:
    Image = ImageDraw = numpy = None


class MatchingTests(unittest.TestCase):
    def source(self, id, x, staff=0, label='square/filled'):
        return {'id': id, 'x': x, 'y': 0, 'interline': 1, 'staff': staff, 'label': label}

    def prediction(self, id, x, staff=0, label='square/filled'):
        return {'id': id, 'x': x, 'y': 0, 'staff': staff, 'prediction': label}

    def test_augmenting_path_recovers_match_that_greedy_distance_loses(self):
        sources = [self.source('s1', 0), self.source('s2', 1.5)]
        predictions = [self.prediction('p1', .5), self.prediction('p2', -1)]
        pairs = evaluation.match(sources, predictions, 1)
        self.assertEqual({(r['sourceId'], r['predictionId']) for r in pairs}, {('s1', 'p2'), ('s2', 'p1')})

    def test_minimum_distance_among_maximum_cardinality_matchings(self):
        sources = [self.source('s1', 0), self.source('s2', 5)]
        predictions = [self.prediction('p1', .1), self.prediction('p2', 5.1)]
        pairs = evaluation.match(sources, predictions, 6)
        self.assertAlmostEqual(sum(r['distanceInInterlines'] for r in pairs), .2)

    def test_labels_never_enter_cost_and_staff_windows_do(self):
        sources = [self.source('s', 0)]; predictions = [self.prediction('p', .1)]
        before = copy.deepcopy((sources, predictions))
        first = evaluation.match(sources, predictions)
        self.assertEqual((sources, predictions), before)
        sources[0]['label'] = 'round/open'; predictions[0]['prediction'] = 'non_head'
        self.assertEqual(evaluation.match(sources, predictions), first)
        predictions[0]['staff'] = 1
        self.assertEqual(evaluation.match(sources, predictions), [])

    def test_invalid_radius_duplicate_id_and_nonfinite_center_rejected(self):
        with self.assertRaises(ValueError): evaluation.match([], [], -1)
        source = self.source('s', 0)
        with self.assertRaises(ValueError): evaluation.match([source, source], [])
        with self.assertRaises(ValueError): evaluation.match([self.source('s', float('nan'))], [])

    def test_misses_and_unmatched_predictions_stay_in_both_denominators(self):
        sources = [self.source('a', 0), self.source('b', 5), self.source('c', 10)]
        predictions = [self.prediction('p', 0), self.prediction('q', 5, label='round/open'),
                       self.prediction('r', 30, label=None)]
        pairs = evaluation.match(sources, predictions)
        summary = evaluation.summarize(sources, predictions, pairs)
        self.assertEqual((summary['sourceHeads'], summary['nativePredictions'], summary['matched']), (3, 3, 2))
        self.assertEqual((summary['missedSourceHeads'], summary['unmatchedPredictions']), (1, 1))
        self.assertEqual(summary['correctLiteralPerKnownSourceHead'], 1/3)
        self.assertEqual(summary['correctLiteralAmongMatchedKnown'], 1/2)
        self.assertIsNone(summary['exportedEventAccuracy'])
        self.assertIsNone(summary['measuredHumanMinutes'])

    def test_unresolved_truth_remains_in_detection_not_literal_denominator(self):
        sources = [self.source('a', 0, label=None)]; predictions = [self.prediction('p', 0)]
        summary = evaluation.summarize(sources, predictions, evaluation.match(sources, predictions))
        self.assertEqual(summary['geometricRecall'], 1)
        self.assertEqual(summary['knownLiteralTargets'], 0)
        self.assertIsNone(summary['correctLiteralPerKnownSourceHead'])

    def test_empty_prediction_denominator_is_unavailable_not_perfect(self):
        summary = evaluation.summarize([self.source('a', 0)], [], [])
        self.assertEqual(summary['geometricRecall'], 0)
        self.assertIsNone(summary['geometricPrecision'])
        self.assertEqual(summary['correctLiteralPerKnownSourceHead'], 0)


class PopulationTests(unittest.TestCase):
    def row(self, id, group, sha, edition='SH2025'):
        return {'id': id, 'group': group, 'sourceSha256': sha, 'edition': edition, 'label': 'square/open'}

    def test_whole_source_group_removed_and_population_routing_explicit(self):
        rows = [self.row('a', 'modern-a', 'sha-a'), self.row('b', 'modern-a', 'sha-a'),
                self.row('c', 'modern-b', 'sha-b'), self.row('old', 'legacy', 'old', 'SH1991')]
        fitting = training.population(rows, 'expanded', 'modern-a')
        self.assertEqual({r['id'] for r in fitting}, {'c', 'old'})
        self.assertEqual([r['id'] for r in training.population(rows, 'sh2025-only', 'modern-a')], ['c'])

    def test_duplicate_source_alias_or_unknown_truth_cannot_enter_model(self):
        with self.assertRaises(ValueError):
            training.validate([self.row('a', 'page-a', 'same'), self.row('b', 'page-b', 'same')])
        row = self.row('a', 'page', 'sha'); row['label'] = None
        with self.assertRaises(ValueError): training.validate([row])

    @unittest.skipIf(Image is None or numpy is None, 'Pinned image/NumPy dependencies required in CI')
    def test_new_population_kernel_matches_original_on_fixed_crops(self):
        rows = []
        for index, label in enumerate(('square/filled', 'round/open')):
            image = Image.new('L', (24, 20), 255); draw = ImageDraw.Draw(image)
            if index: draw.ellipse((4, 4, 19, 15), outline=0, width=2)
            else: draw.rectangle((3, 3, 20, 16), fill=0)
            rows.append({**self.row(str(index), str(index), str(index)), 'label': label, 'pixels': image})
        bank = training.fit(rows); old = training.prior.classifier.fit(rows)
        for row in rows:
            result = training.predict(row['pixels'], bank)
            previous = training.prior.classifier.predict(row['pixels'], old)
            for field in ('prediction', 'selectivePrediction', 'neighborId', 'distance', 'scale', 'offset'):
                self.assertEqual(result[field], previous[field])


class InferenceGuardTests(unittest.TestCase):
    @unittest.skipIf(Image is None, 'Image dependency required for evaluation wiring')
    def test_actual_automatic_centers_used_and_missing_source_not_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); out = root/'out'; out.mkdir()
            Image.new('L', (200, 420), 255).save(root/'source.png')
            labels_path = root/'labels.json'; labels_path.write_text('{}')
            for name in ('inference-lock.json', 'recognition.json'): (out/name).write_text('{}')
            windows = [{'staff': i, 'box':[10, 10+i*100, 190, 90+i*100]} for i in range(4)]
            labels = {'windows': windows, 'rows':[
                {'id':'a','x':50,'y':40,'interline':10,'staff':0,'label':'square/filled'},
                {'id':'b','x':100,'y':40,'interline':10,'staff':0,'label':'round/filled'}]}
            current = {'sourcePath':'source.png','sourceSha256':'fresh'}
            crop_centers = []
            def crop(image, x, y, spacing):
                crop_centers.append((x,y)); return Image.new('L',(24,20),255)
            prediction = {'prediction':'square/filled','selectivePrediction':'square/filled'}
            head = {'id':'native','x':53,'y':40,'staffId':'1','inHeadChord':True}
            with patch.object(study,'ROOT',root), \
                 patch.object(study,'observations',return_value=(current,{'selectedPopulation':'expanded'},labels,{'labelsSha256':study.archive.digest(labels_path)})), \
                 patch.object(study,'recognize',return_value={'status':'graph-ready','graph':'graph.omr'}), \
                 patch.object(study,'check',return_value=current), \
                 patch.object(study,'graph_heads',return_value=[head]), \
                 patch.object(study.training,'samples',return_value=[{'sourceSha256':'train'}]), \
                 patch.object(study.training,'population',return_value=[{'sourceSha256':'train'}]), \
                 patch.object(study.training,'fit',return_value={}), \
                 patch.object(study.training,'predict',return_value=prediction), \
                 patch.object(study.training.prior.classifier,'crop',side_effect=crop), \
                 patch.object(study.training.prior.geometry,'staff_lines',return_value={'status':'proposal','interline':10}):
                report = study.evaluate(out,labels_path)
            self.assertIn((50,40),crop_centers)  # Source-centered diagnostic only.
            self.assertIn((53,40),crop_centers)  # Actual automatic-center inference.
            self.assertEqual(report['nativeHeadsInWindows'],1)
            summary = report['models']['expanded']['automatic']['0.5']['summary']
            self.assertEqual(summary['missedSourceHeads'],1)
            self.assertEqual(summary['correctLiteralPerKnownSourceHead'],.5)

    def test_missing_pre_source_population_freeze_stops_before_reading_labels(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(study, 'check', return_value={}):
                with self.assertRaisesRegex(ValueError, 'BEFORE'):
                    study.observations(Path(d), Path(d)/'must-not-read.json')

    def test_recognition_receipt_reuses_before_launch_and_rejects_artifact_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'inference-lock.json').write_text('{}')
            artifact = root/'graph.omr'; artifact.write_bytes(b'graph')
            current = {'engine': {}, 'settings': {}, 'sourceSha256': 'source'}
            execution = {'inferenceLockSha256': study.archive.digest(root/'inference-lock.json'), **current}
            study.archive.immutable(root/'execution.json', study.archive.json_bytes(execution))
            receipt = {'executionSha256': study.archive.digest(root/'execution.json'), 'artifactsSha256': {'graph.omr':study.archive.digest(artifact)}}
            (root/'recognition.json').write_text(json.dumps(receipt))
            with patch.object(study, 'ROOT', root), patch.object(study.subprocess, 'Popen', side_effect=AssertionError('must reuse')):
                self.assertEqual(study.recognize(root, current), receipt)
                artifact.write_bytes(b'drift')
                with self.assertRaises(ValueError): study.recognize(root, current)

    def test_started_recognition_never_blindly_retries(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'inference-lock.json').write_text('{}'); (root/'started.json').write_text('{}')
            with patch.object(study.subprocess, 'Popen', side_effect=AssertionError('must not rerun')):
                with self.assertRaisesRegex(ValueError, 'never silently retry'):
                    study.recognize(root, {'engine':{},'settings':{},'sourceSha256':'source'})

    def test_graph_registration_and_complete_native_coordinate_accounting(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); graph = root/'graph.omr'; source = root/'source.png'
            def write(path, width=200, missing=False):
                with zipfile.ZipFile(graph, 'w') as z:
                    z.writestr('book.xml', f'<book><sheet number="1"><input><number>1</number><path>{path}</path></input></sheet></book>')
                    bounds = '' if missing else '<bounds x="20" y="30" w="10" h="8"/>'
                    z.writestr('sheet#1/sheet#1.xml', f'<sheet><picture width="{width}" height="100"/><page><system id="1"><head id="a" staff="1">{bounds}</head></system></page></sheet>')
            write(source)
            rows = study.graph_heads(graph, source, (200, 100))
            self.assertEqual((rows[0]['id'], rows[0]['x'], rows[0]['y']), ('1:a', 25, 34))
            for options in ({'path':root/'other.png'}, {'path':source, 'width':300}, {'path':source, 'missing':True}):
                write(**options)
                with self.assertRaises(ValueError): study.graph_heads(graph, source, (200, 100))


if __name__ == '__main__':
    unittest.main()
