"""Synthetic v1 consumer tests. Integrity/staging is not source acceptance."""
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
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

    def write_payload(self, name, raw, report_field=None):
        (self.bundle / name).write_bytes(raw)
        self.manifest['files'][name] = consumer.sha(raw)
        if report_field:
            report = json.loads((self.bundle / 'report.json').read_bytes())
            report[report_field] = consumer.sha(raw)
            report_raw = encoded(report)
            (self.bundle / 'report.json').write_bytes(report_raw)
            self.manifest['files']['report.json'] = consumer.sha(report_raw)
        return self.write_manifest()

    def write_archive(self, xml=None, container=None):
        if xml is None:
            xml = (self.bundle / 'candidate.musicxml').read_bytes()
        if container is None:
            container = '<container><rootfile full-path="score.musicxml"/></container>'
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('score.musicxml', xml)
            archive.writestr('META-INF/container.xml', container)
        self.write_payload('candidate.musicxml', xml, 'candidateSha256')
        return self.write_payload('candidate.mxl', stream.getvalue(), 'archiveSha256')

    def assert_rejected_without_staging(self, pin, message):
        with self.assertRaisesRegex(ValueError, message):
            consumer.stage(self.bundle, pin, self.root / 'atlas')
        self.assertFalse((self.root / 'atlas').exists())

    def assert_cli_error(self, pin):
        result = subprocess.run(
            [sys.executable, consumer.__file__, str(self.bundle),
             '--expected-manifest-sha256', pin, '--verify-only'],
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertTrue(result.stderr.startswith('error: '), result.stderr)
        self.assertNotIn('Traceback', result.stderr)

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

    def test_manifest_requires_an_object_and_typed_nested_objects(self):
        original = deepcopy(self.manifest)
        for value in (None, [], 'text', 1, True):
            with self.subTest(value=value):
                self.manifest = value
                self.assert_rejected_without_staging(self.write_manifest(), 'JSON object')
        for field in ('files', 'producer'):
            for value in (None, [], 'text', 1, True):
                with self.subTest(field=field, value=value):
                    self.manifest = {**original, field: value}
                    self.assert_rejected_without_staging(
                        self.write_manifest(), 'payload paths|producer provenance')

    def test_json_payloads_require_objects_before_reading_fields(self):
        for name, report_field in (('report.json', None), ('comparison.json', None),
                                   ('resolved-reading.json', 'resolvedReadingSha256')):
            original = (self.bundle / name).read_bytes()
            for value in (None, [], 'text', 1, True):
                with self.subTest(name=name, value=value):
                    pin = self.write_payload(name, encoded(value), report_field)
                    self.assert_rejected_without_staging(pin, 'JSON object: ' + name)
            self.write_payload(name, original, report_field)

    def test_malformed_json_and_invalid_utf8_have_controlled_cli_errors(self):
        for name, report_field in (('bundle.json', None), ('report.json', None),
                                   ('comparison.json', None),
                                   ('resolved-reading.json', 'resolvedReadingSha256')):
            original = (self.bundle / name).read_bytes()
            for raw in (b'{', b'\xff'):
                with self.subTest(name=name, raw=raw):
                    if name == 'bundle.json':
                        (self.bundle / name).write_bytes(raw)
                        pin = consumer.sha(raw)
                    else:
                        pin = self.write_payload(name, raw, report_field)
                    self.assert_rejected_without_staging(pin, 'Invalid JSON: ' + name)
                    self.assert_cli_error(pin)
            if name == 'bundle.json':
                (self.bundle / name).write_bytes(original)
            else:
                self.write_payload(name, original, report_field)

    def test_malformed_zip_and_xml_are_rejected_before_staging(self):
        pin = self.write_payload('candidate.mxl', b'not a zip archive', 'archiveSha256')
        self.assert_rejected_without_staging(pin, 'Invalid MXL/XML')
        self.assert_cli_error(pin)
        pin = self.write_archive(container='<container>')
        self.assert_rejected_without_staging(pin, 'Invalid MXL/XML')
        self.assert_cli_error(pin)
        pin = self.write_archive(xml=b'<score-partwise>')
        self.assert_rejected_without_staging(pin, 'Invalid MXL/XML')
        self.assert_cli_error(pin)

    def test_failed_staging_cleans_temporary_files_and_allows_retry(self):
        for method, filename in (('write_bytes', 'candidate.mxl'),
                                 ('write_text', 'atlas-import-receipt.json'),
                                 ('rename', None)):
            atlas = self.root / method
            original = getattr(Path, method)

            def fail(path, *args, **kwargs):
                if filename is None or path.name == filename:
                    raise OSError('injected staging failure')
                return original(path, *args, **kwargs)

            with self.subTest(method=method):
                with patch.object(Path, method, autospec=True, side_effect=fail):
                    with self.assertRaisesRegex(OSError, 'injected staging failure'):
                        consumer.stage(self.bundle, self.pin, atlas)
                base = atlas / 'work/transcription-imports'
                self.assertEqual(list(base.iterdir()), [])
                receipt = consumer.stage(self.bundle, self.pin, atlas)
                self.assertEqual(receipt['status'], 'staged-research-only')
                self.assertTrue((base / self.pin / 'atlas-import-receipt.json').is_file())

    def test_existing_empty_import_directory_is_not_replaced(self):
        atlas = self.root / 'atlas'
        destination = atlas / 'work/transcription-imports' / self.pin
        destination.mkdir(parents=True)
        with self.assertRaises(FileExistsError):
            consumer.stage(self.bundle, self.pin, atlas)
        self.assertEqual(list(destination.iterdir()), [])
        self.assertEqual(list(destination.parent.iterdir()), [destination])

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
