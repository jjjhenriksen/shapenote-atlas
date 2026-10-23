"""Synthetic declaration/bundle byte consistency; no source or policy approval."""
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_transcription_acceptance_provenance as checker

consumer = checker.bundle_consumer


def encoded(value):
    return (json.dumps(value, sort_keys=True) + '\n').encode()


class AcceptanceProvenance(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bundle = self.root / 'bundle'
        self.bundle.mkdir()
        self.path = self.root / 'declaration.json'
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
            'producer': {'repository': 'fixture://synthetic-producer', 'revision': 'a' * 40,
                         'dirty': False, 'exporterSha256': '5' * 64},
            'files': {name: consumer.sha(raw) for name, raw in payload.items()}}
        for name, raw in payload.items():
            (self.bundle / name).write_bytes(raw)
        self.pin = self.write_manifest()
        self.declaration = json.loads((ROOT / 'tests/fixtures/transcription-acceptance/synthetic-accepted-declaration.json').read_text())
        self.declaration['bundle'] = {'schemaVersion': 1, 'manifestSha256': self.pin,
            'sourceSha256': source, 'producer': deepcopy(self.manifest['producer']),
            'actualWriterSha256': report['writerSha256'], 'payloadSha256': deepcopy(self.manifest['files']),
            'researchFlags': {'sourceCertified': False, 'safeToPromote': False}}
        self.write_declaration()

    def write_manifest(self):
        raw = encoded(self.manifest)
        (self.bundle / 'bundle.json').write_bytes(raw)
        return consumer.sha(raw)

    def write_declaration(self):
        declared = self.declaration['bundle']
        self.declaration['humanImageReview']['sourceSha256'] = declared['sourceSha256']
        for evidence in self.declaration['evidence']:
            kind = evidence['kind']
            pin = declared['manifestSha256']
            if kind in ('sourceFidelity', 'humanImage'):
                pin = declared['sourceSha256']
            elif kind in ('xmlDownload', 'mxlDownload'):
                pin = declared['payloadSha256']['candidate.musicxml' if kind == 'xmlDownload' else 'candidate.mxl']
            evidence['subjectSha256'] = pin
        self.path.write_bytes(encoded(self.declaration))

    def check(self, pin=None):
        return checker.check(self.path, self.bundle, self.pin if pin is None else pin)

    def snapshot(self):
        return {str(path.relative_to(self.root)): path.read_bytes()
                for path in self.root.rglob('*') if path.is_file()}

    def test_matching_pins_preserve_declared_claims_without_granting_acceptance(self):
        before = self.snapshot()
        with patch.object(consumer, 'stage', side_effect=AssertionError('must never stage')):
            result = self.check()
        self.assertEqual(result['status'], 'consistent')
        self.assertTrue(result['bundleIntegrityVerified'])
        self.assertTrue(result['declarationValid'])
        self.assertEqual(result['declarationSha256'], consumer.sha(self.path.read_bytes()))
        self.assertEqual(result['verifiedBundleManifestSha256'], self.pin)
        self.assertNotEqual(self.declaration['bundle']['actualWriterSha256'], self.manifest['producer']['exporterSha256'])
        self.assertEqual(result['declaredDispositions']['decision'], 'accept')
        self.assertEqual(result['declaredDispositions']['publication'], 'blocked')
        self.assertEqual(result['declaredDispositions']['assessments']['publicationRights'], 'unknown')
        for field in ('acceptance', 'authorityVerified', 'evidenceVerified', 'sourceCertified', 'safeToPromote'):
            self.assertIs(result[field], False)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.root / 'work').exists())
        self.assertFalse((self.root / 'public').exists())

    def test_rejected_and_blocked_unknown_declarations_are_not_upgraded(self):
        for outcome in ('reject', 'blocked'):
            self.declaration['decision'] = outcome
            self.declaration['remainingBlockers']['admission'] = ['Human review remains pending.']
            self.declaration['uncertainties'] = ['Literal reading is unknown.']
            self.declaration['humanImageReview'].update(disposition='unreviewed', reviewer=None,
                                                       reviewedAt=None, evidence=[])
            self.declaration['assessments']['sourceFidelity'].update(disposition='unknown', evidence=[])
            self.write_declaration()
            result = self.check()
            with self.subTest(outcome=outcome):
                self.assertEqual(result['status'], 'consistent')
                self.assertEqual(result['declaredDispositions']['decision'], outcome)
                self.assertEqual(result['declaredDispositions']['humanImageReview'], 'unreviewed')
                self.assertEqual(result['declaredDispositions']['assessments']['sourceFidelity'], 'unknown')
                self.assertEqual(result['declaredDispositions']['uncertainties'], self.declaration['uncertainties'])

    def test_every_declared_provenance_pin_reports_its_precise_mismatch(self):
        original = deepcopy(self.declaration)
        cases = [('manifestSha256', 'b' * 64), ('sourceSha256', 'b' * 64),
                 ('actualWriterSha256', 'b' * 64)]
        cases += [('producer.' + key, value) for key, value in (
            ('repository', 'fixture://other-producer'), ('revision', 'b' * 40),
            ('dirty', True), ('exporterSha256', 'b' * 64))]
        cases += [('payloadSha256.' + name, 'b' * 64) for name in sorted(consumer.FILES)]
        for path, value in cases:
            self.declaration = deepcopy(original)
            target = self.declaration['bundle']
            keys = path.split('.') if not path.startswith('payloadSha256.') else ['payloadSha256', path[len('payloadSha256.'):]]
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = value
            self.write_declaration()
            result = self.check()
            with self.subTest(path=path):
                self.assertEqual(result['status'], 'blocked')
                self.assertTrue(result['declarationValid'])
                self.assertTrue(result['bundleIntegrityVerified'])
                self.assertEqual([row['field'] for row in result['mismatches']], ['bundle.' + path])
                self.assertEqual(result['blockers'][0]['code'], 'provenance-mismatch')

    def test_wrong_external_manifest_pin_cannot_be_replaced_by_declared_or_computed_pin(self):
        result = self.check('0' * 64)
        self.assertEqual(result['status'], 'blocked')
        self.assertFalse(result['bundleIntegrityVerified'])
        self.assertIn('Pinned bundle manifest hash mismatch', result['blockers'][0]['detail'])

    def test_malformed_declaration_and_bundle_inputs_are_explicit_blockers(self):
        original = self.path.read_bytes()
        for raw in (b'{', b'\xff', b'{"schemaVersion":1,"schemaVersion":1}', b'{}'):
            self.path.write_bytes(raw)
            result = self.check()
            self.assertEqual(result['declarationSha256'], consumer.sha(raw))
            self.assertEqual(result['blockers'][0]['code'], 'invalid-declaration')
            self.assertFalse(result['declarationValid'])
        self.path.write_bytes(original)
        (self.bundle / 'candidate.musicxml').write_bytes(b'changed')
        result = self.check()
        self.assertEqual(result['blockers'][0]['code'], 'bundle-verification-failed')
        self.assertIn('Payload hash drift', result['blockers'][0]['detail'])

    def test_ambiguous_duplicate_bundle_or_report_provenance_is_blocked(self):
        for name in ('bundle.json', 'report.json'):
            with self.subTest(name=name):
                path = self.bundle / name
                original = path.read_bytes()
                raw = original.rstrip()[:-1] + b',"schemaVersion":1,"schemaVersion":1}'
                path.write_bytes(raw)
                if name == 'report.json':
                    self.manifest['files'][name] = consumer.sha(raw)
                    self.pin = self.write_manifest()
                else:
                    self.pin = consumer.sha(raw)
                result = self.check()
                self.assertEqual(result['status'], 'blocked')
                self.assertIn('duplicate JSON key', result['blockers'][0]['detail'])
                path.write_bytes(original)
                self.manifest['files']['report.json'] = consumer.sha((self.bundle / 'report.json').read_bytes())
                self.pin = self.write_manifest()

    def test_exact_declaration_bytes_are_bound_and_extra_bundle_metadata_is_allowed(self):
        first = self.check()
        self.path.write_bytes(self.path.read_bytes() + b'\n')
        second = self.check()
        self.assertEqual(second['status'], 'consistent')
        self.assertNotEqual(first['declarationSha256'], second['declarationSha256'])
        self.manifest['producer']['note'] = 'Harmless producer extension.'
        self.manifest['note'] = 'Harmless manifest extension.'
        self.pin = self.write_manifest()
        self.declaration['bundle']['manifestSha256'] = self.pin
        self.write_declaration()
        self.assertEqual(self.check()['status'], 'consistent')

    def test_only_verified_snapshots_are_used_after_bundle_capture(self):
        captured = consumer.verify(self.bundle, self.pin)
        shutil.rmtree(self.bundle)
        with patch.object(consumer, 'verify', return_value=captured):
            self.assertEqual(self.check()['status'], 'consistent')

    def test_cli_requires_external_pin_and_never_creates_local_import_caches_or_stage(self):
        tools = self.root / 'tools'
        tools.mkdir()
        for name in ('check_transcription_acceptance_provenance.py',
                     'import_transcription_bundle.py', 'validate_transcription_acceptance.py'):
            shutil.copyfile(ROOT / 'scripts' / name, tools / name)
        command = [sys.executable, str(tools / 'check_transcription_acceptance_provenance.py'),
                   str(self.path), str(self.bundle)]
        missing = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2)
        before = self.snapshot()
        result = subprocess.run(command + ['--expected-manifest-sha256', self.pin],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'consistent')
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((tools / '__pycache__').exists())
        blocked = subprocess.run(command + ['--expected-manifest-sha256', '0' * 64],
                                 cwd=self.root, capture_output=True, text=True)
        self.assertEqual(blocked.returncode, 2)
        self.assertEqual(json.loads(blocked.stdout)['status'], 'blocked')


if __name__ == '__main__':
    unittest.main()
