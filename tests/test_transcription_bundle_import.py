"""Synthetic v1 consumer tests. Integrity/staging is not source acceptance."""
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import import_transcription_bundle as consumer


def encoded(value):
    return (json.dumps(value, sort_keys=True) + '\n').encode()


class TranscriptionImport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / 'input'
        self.bundle.mkdir()
        source = '1' * 64
        reading_hashes = ['2' * 64, '3' * 64]
        xml = b'<score-partwise version="4.0"/>'
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('META-INF/container.xml',
                            '<container><rootfile full-path="score.musicxml"/></container>')
            archive.writestr('score.musicxml', xml)
        reading = encoded({'sourceSha256': source})
        report = {'status': 'assembled-research-candidate', 'unresolvedMeasures': [],
                  'sourceSha256': source, 'readingSha256': reading_hashes,
                  'writerSha256': '4' * 64, 'secondParserPitchRhythmPassed': True,
                  'sourceCertified': False, 'safeToPromote': False,
                  'independentSourceAccuracy': None, 'candidateSha256': consumer.sha(xml),
                  'archiveSha256': consumer.sha(stream.getvalue()),
                  'resolvedReadingSha256': consumer.sha(reading)}
        payload = {'candidate.musicxml': xml, 'candidate.mxl': stream.getvalue(),
                   'report.json': encoded(report), 'resolved-reading.json': reading,
                   'comparison.json': encoded({'sourceSha256': source, 'readingSha256': reading_hashes})}
        self.manifest = {'schemaVersion': 1, 'kind': 'shapenote-transcription-bundle',
                         'status': 'research-candidate', 'sourceSha256': source,
                         'sourceCertified': False, 'safeToPromote': False,
                         'producer': {'repository': 'fixture://producer', 'revision': 'a' * 40,
                                      'dirty': False, 'exporterSha256': '5' * 64},
                         'files': {n: consumer.sha(raw) for n, raw in payload.items()}}
        for name, raw in payload.items():
            (self.bundle / name).write_bytes(raw)
        self.pin = self.write_manifest()

    def write_manifest(self):
        raw = encoded(self.manifest)
        (self.bundle / 'bundle.json').write_bytes(raw)
        return consumer.sha(raw)

    def test_stage_is_confined_to_ignored_research_with_exact_bytes(self):
        receipt = consumer.stage(self.bundle, self.pin, self.root / 'atlas')
        target = self.root / 'atlas/work/transcription-imports' / self.pin
        self.assertTrue((target / 'atlas-import-receipt.json').exists())
        for path in self.bundle.iterdir():
            self.assertEqual(path.read_bytes(), (target / 'bundle' / path.name).read_bytes())
        self.assertFalse(receipt['safeToPromote'])
        self.assertFalse(receipt['publicAssetsModified'])
        self.assertFalse((self.root / 'atlas/public').exists())
        with self.assertRaises(FileExistsError):
            consumer.stage(self.bundle, self.pin, self.root / 'atlas')

    def test_manifest_pin_and_payload_drift_both_fail_before_staging(self):
        with self.assertRaisesRegex(ValueError, 'manifest hash'):
            consumer.stage(self.bundle, '0' * 64, self.root / 'atlas')
        (self.bundle / 'candidate.musicxml').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Payload hash'):
            consumer.stage(self.bundle, self.pin, self.root / 'atlas')
        self.assertFalse((self.root / 'atlas').exists())

    def test_unknown_version_promotion_and_payload_paths_are_rejected(self):
        original = deepcopy(self.manifest)
        cases = [('schemaVersion', 2), ('status', 'accepted'), ('safeToPromote', True),
                 ('sourceCertified', True), ('files', {'../escape': '0' * 64})]
        for key, value in cases:
            self.manifest = {**original, key: value}
            pin = self.write_manifest()
            with self.subTest(key=key), self.assertRaises(ValueError):
                consumer.verify(self.bundle, pin)

    def test_rehashed_but_internally_unbound_report_is_rejected(self):
        path = self.bundle / 'report.json'
        report = json.loads(path.read_bytes())
        report['candidateSha256'] = '0' * 64
        path.write_bytes(encoded(report))
        self.manifest['files']['report.json'] = consumer.sha(path.read_bytes())
        pin = self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'report hash drift'):
            consumer.verify(self.bundle, pin)

    def test_missing_accuracy_claim_is_not_treated_as_unknown(self):
        path = self.bundle / 'report.json'
        report = json.loads(path.read_bytes())
        del report['independentSourceAccuracy']
        path.write_bytes(encoded(report))
        self.manifest['files']['report.json'] = consumer.sha(path.read_bytes())
        with self.assertRaisesRegex(ValueError, 'research candidate'):
            consumer.verify(self.bundle, self.write_manifest())

    def test_rehashed_mxl_cannot_redirect_the_score(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('score.musicxml', (self.bundle / 'candidate.musicxml').read_bytes())
            archive.writestr('META-INF/container.xml',
                            '<container><rootfile full-path="other.xml"/></container>')
        (self.bundle / 'candidate.mxl').write_bytes(stream.getvalue())
        digest = consumer.sha(stream.getvalue())
        self.manifest['files']['candidate.mxl'] = digest
        report_path = self.bundle / 'report.json'
        report = json.loads(report_path.read_bytes())
        report['archiveSha256'] = digest
        report_path.write_bytes(encoded(report))
        self.manifest['files']['report.json'] = consumer.sha(report_path.read_bytes())
        with self.assertRaisesRegex(ValueError, 'container rootfile'):
            consumer.verify(self.bundle, self.write_manifest())

    def test_symlink_payload_or_output_storage_is_rejected(self):
        atlas = self.root / 'atlas'
        atlas.mkdir()
        (atlas / 'work').symlink_to(self.root / 'input', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'storage'):
            consumer.stage(self.bundle, self.pin, atlas)
        path = self.bundle / 'candidate.musicxml'
        external = self.root / 'external.xml'
        path.rename(external)
        path.symlink_to(external)
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            consumer.verify(self.bundle, self.pin)


if __name__ == '__main__':
    unittest.main()
