"""Frozen-transfer orchestration contracts; fixtures do not prove OMR accuracy."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_image_transfer as transfer
try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = ImageDraw = None


@unittest.skipIf(Image is None, 'Pillow optional')
class TransferTests(unittest.TestCase):
    def labels(self, source_hash):
        return {'sourceSha256': source_hash, 'rows': [
            {'id': f'184-p{part}-n{note}', 'x': 32, 'y': 32, 'interline': 12, 'label': 'square/filled'}
            for part in range(1, 5) for note in range(1, 7)],
            'bands': [], 'internalBoundariesApproxX': []}

    def test_binding_and_incomplete_population_fail_before_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); labels_path = root/'labels.json'
            protocol = {'sourceSha256': 'frozen'}
            for index, labels in enumerate([self.labels('wrong'), self.labels('frozen')]):
                if index:
                    labels['rows'].pop()
                labels_path.write_text(json.dumps(labels))
                with patch.object(transfer, 'current_protocol', return_value=protocol), \
                     patch.object(transfer.baseline, 'samples', side_effect=AssertionError('not allowed')):
                    with self.assertRaises(ValueError):
                        transfer.run(root/str(index), labels_path)

    def test_runner_reads_training_paths_runs_and_reuses_without_predictions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); image_path = root/'source.png'; train_path = root/'train.png'
            image = Image.new('L', (64, 64), 255)
            ImageDraw.Draw(image).rectangle((25, 27, 39, 37), fill=0)
            image.save(image_path); image.save(train_path)
            labels_path = root/'labels.json'
            source_hash = transfer.archive.digest(image_path)
            labels_path.write_text(json.dumps(self.labels(source_hash)))
            protocol = {'sourceSha256': source_hash, 'boundaryTolerancePixels': 4}
            source_index = root/transfer.baseline.INPUTS[1]
            source_index.parent.mkdir(parents=True)
            source_index.write_text(json.dumps({'sourceImages': {'train': {'path': 'train.png'}}}))
            samples = [{'id': 'train', 'songNo': 'train', 'sourceSha256': 'not-test-source',
                        'x': 32, 'y': 32, 'interline': 12, 'label': 'square/filled',
                        'pixels': transfer.geometry.note_crop(image, 32, 32, 12).resize((24, 20))}]
            with patch.object(transfer, 'ROOT', root), patch.object(transfer, 'SOURCE', image_path), \
                 patch.object(transfer, 'current_protocol', return_value=protocol), \
                 patch.object(transfer.baseline, 'samples', return_value=samples), \
                 patch.object(transfer.study, 'render_bank', return_value=[]), \
                 patch.object(transfer.geometry, 'shared_bar_grid', return_value={'proposals': []}):
                result = transfer.run(root/'out', labels_path)
                self.assertEqual(result['symbols']['raw-contour']['summary']['samples'], 24)
                self.assertFalse(result['safeToPromote'])
                with patch.object(transfer.baseline, 'samples', side_effect=AssertionError('must not rerun')):
                    self.assertEqual(transfer.run(root/'out', labels_path), result)
                labels = self.labels(source_hash); labels['rows'][0]['x'] = 33
                labels_path.write_text(json.dumps(labels))
                with self.assertRaisesRegex(ValueError, 'Immutable artifact differs'):
                    transfer.run(root/'out', labels_path)

    def test_test_source_cannot_be_in_training(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root/'labels.json'
            path.write_text(json.dumps(self.labels('source')))
            with patch.object(transfer, 'current_protocol', return_value={'sourceSha256': 'source'}), \
                 patch.object(transfer.baseline, 'samples', return_value=[{'sourceSha256': 'source'}]):
                with self.assertRaisesRegex(ValueError, 'training population'):
                    transfer.run(root/'out', path)


if __name__ == '__main__':
    unittest.main()
