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
import transcription_bundle_v2 as v2


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

    def test_corrupt_compressed_zip_members_have_controlled_cli_errors(self):
        xml = (self.bundle / 'candidate.musicxml').read_bytes()
        for dependency, compression, offset in (
                ('zlib', zipfile.ZIP_DEFLATED, 0),
                ('bz2', zipfile.ZIP_BZIP2, 0),
                ('lzma', zipfile.ZIP_LZMA, 4)):
            try:
                __import__(dependency)
            except ImportError:
                continue
            with self.subTest(compression=dependency):
                stream = io.BytesIO()
                with zipfile.ZipFile(stream, 'w', compression=compression) as archive:
                    archive.writestr('score.musicxml', xml)
                    archive.writestr('META-INF/container.xml',
                                    '<container><rootfile full-path="score.musicxml"/></container>')
                    info = archive.getinfo('score.musicxml')
                raw = bytearray(stream.getvalue())
                # Corrupt the compression header/properties in the first member.
                start = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
                raw[start + offset] = 255
                pin = self.write_payload('candidate.mxl', bytes(raw), 'archiveSha256')
                self.assert_rejected_without_staging(pin, 'Invalid MXL/XML')
                self.assert_cli_error(pin)

    def test_mismatched_score_size_is_rejected_without_decompression(self):
        try:
            __import__('zlib')
        except ImportError:
            self.skipTest('DEFLATE backend unavailable')
        xml = (self.bundle / 'candidate.musicxml').read_bytes()
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('score.musicxml', xml + b' ' * (1024 * 1024))
            archive.writestr('META-INF/container.xml',
                            '<container><rootfile full-path="score.musicxml"/></container>')
        pin = self.write_payload('candidate.mxl', stream.getvalue(), 'archiveSha256')
        with patch.object(zipfile.ZipFile, 'read',
                          side_effect=AssertionError('Mismatched score must not be decompressed')) as read:
            self.assert_rejected_without_staging(pin, 'MXL score size')
            read.assert_not_called()
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


def synthetic_v2_reading():
    """Invented notation only: exercise every supported shape and rhythm field."""
    def note(shape, note_type='quarter', dots=0, **overrides):
        from fractions import Fraction
        duration = v2.TYPES[note_type] * sum(Fraction(1, 2 ** d) for d in range(dots + 1))
        row = {'onset': '0', 'duration': str(duration), 'pitch': ['C', '2/2', 4],
               'type': note_type, 'dots': dots, 'shape': shape, 'fill': 'filled',
               'tieStart': False, 'tieStop': False, 'lyrics': [], 'beams': [], 'uncertainties': []}
        row.update(overrides)
        return row

    events = [note('triangle', tieStart=True, fill='open'), note('triangle', tieStop=True),
              note('round', '16th', 2, beams=[{'number': 1, 'value': 'begin'},
                                            {'number': 2, 'value': 'forward hook'}]),
              note('square', 'eighth', beams=[{'number': 1, 'value': 'end'}]),
              note('diamond', 'half', 1, lyrics=[{'number': '01', 'text': ' literal & text ',
                                                'syllabic': 'single'}]),
              note(None, 'whole', pitch=None, fill=None)]
    from fractions import Fraction
    position = Fraction(0)
    for event in events:
        event['onset'] = str(position)
        position += Fraction(event['duration'])
    parts = []
    for index in range(3):
        measures = []
        for measure in range(2):
            measures.append({'index': measure, 'bbox': [0, 10 * index, 100, 10 * index + 9],
                             'events': deepcopy(events), 'uncertainties': [],
                             'barlines': [{'location': 'left', 'barStyle': 'heavy-light',
                                           'repeat': {'direction': 'forward', 'times': None},
                                           'ending': {'number': '01', 'type': 'start'}},
                                          {'location': 'right', 'barStyle': 'light-heavy',
                                           'repeat': {'direction': 'backward', 'times': 2},
                                           'ending': {'number': 1, 'type': 'stop'}}],
                             'endingLabel': 'literal 2.' if measure else '',
                             'unavailableSemantics': ['stem direction unrepresented']})
        parts.append({'id': 'P' + str(index + 1), 'name': 'Synthetic ' + str(index + 1), 'measures': measures})
    return {'schemaVersion': 2, 'profile': v2.PROFILE, 'sourceSha256': '1' * 64,
            'title': 'Synthetic v2 & literal title',
            'header': {'fifths': -1, 'time': [4, 4],
                       'clefs': [{'sign': 'G', 'line': 2}, {'sign': 'C', 'line': 3}, {'sign': 'F', 'line': 4}]},
            'parts': parts, 'uncertainties': [], 'unavailableSemantics': ['triangle orientation unrepresented']}


def synthetic_v2_xml(reading):
    """Test-only wire fixture builder, independent of the producer runtime."""
    from fractions import Fraction
    from xml.etree import ElementTree as ET
    root = ET.Element('score-partwise', version='4.0')

    def add(parent, tag, value=None, **attrs):
        node = ET.SubElement(parent, tag, attrs)
        if value is not None:
            node.text = str(value)
        return node

    add(add(root, 'work'), 'work-title', reading.get('title', 'Image-first research candidate'))
    add(add(root, 'identification'), 'rights',
        'Local research candidate; not source-certified or approved for publication.')
    listing = add(root, 'part-list')
    for part in reading['parts']:
        add(add(listing, 'score-part', id=part['id']), 'part-name', part['name'])
    for number, part in enumerate(reading['parts']):
        part_node = add(root, 'part', id=part['id'])
        for measure in part['measures']:
            node = add(part_node, 'measure', number=str(measure['index'] + 1))
            if measure['index'] == 0:
                attrs = add(node, 'attributes')
                add(attrs, 'divisions', 16)
                add(add(attrs, 'key'), 'fifths', reading['header']['fifths'])
                time = add(attrs, 'time')
                add(time, 'beats', reading['header']['time'][0])
                add(time, 'beat-type', reading['header']['time'][1])
                clef = add(attrs, 'clef')
                add(clef, 'sign', reading['header']['clefs'][number]['sign'])
                add(clef, 'line', reading['header']['clefs'][number]['line'])
            if measure.get('endingLabel'):
                add(add(add(node, 'direction', placement='above'), 'direction-type'), 'words', measure['endingLabel'])
            for event in measure['events']:
                note = add(node, 'note')
                if event['pitch'] is None:
                    add(note, 'rest')
                else:
                    pitch = add(note, 'pitch')
                    for tag, value in zip(('step', 'alter', 'octave'), event['pitch']):
                        add(pitch, tag, int(Fraction(str(value))) if tag == 'alter' else value)
                add(note, 'duration', int(Fraction(event['duration']) * 16))
                for key, kind in (('tieStop', 'stop'), ('tieStart', 'start')):
                    if event[key]:
                        add(note, 'tie', type=kind)
                add(note, 'voice', 1)
                add(note, 'type', event['type'])
                for _ in range(event['dots']):
                    add(note, 'dot')
                if event['pitch'] is not None:
                    add(note, 'notehead', v2.SHAPES[event['shape']],
                        filled='yes' if event['fill'] == 'filled' else 'no')
                for beam in event.get('beams', []):
                    add(note, 'beam', beam['value'], number=str(beam['number']))
                if event['tieStart'] or event['tieStop']:
                    notations = add(note, 'notations')
                    for key, kind in (('tieStop', 'stop'), ('tieStart', 'start')):
                        if event[key]:
                            add(notations, 'tied', type=kind)
                for lyric in event['lyrics']:
                    lyric_node = add(note, 'lyric', number=str(lyric['number']))
                    add(lyric_node, 'syllabic', lyric['syllabic'])
                    add(lyric_node, 'text', lyric['text'])
            for bar in measure.get('barlines', []):
                bar_node = add(node, 'barline', location=bar['location'])
                add(bar_node, 'bar-style', bar['barStyle'])
                if bar.get('ending'):
                    add(bar_node, 'ending', **{k: str(v) for k, v in bar['ending'].items()})
                if bar.get('repeat'):
                    add(bar_node, 'repeat', **{k: str(v) for k, v in bar['repeat'].items() if v is not None})
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


class TranscriptionV2Import(unittest.TestCase):
    write_manifest = TranscriptionImport.write_manifest
    write_payload = TranscriptionImport.write_payload
    write_archive = TranscriptionImport.write_archive

    def setUp(self):
        TranscriptionImport.setUp(self)
        self.reading = synthetic_v2_reading()
        self.manifest.update(schemaVersion=2, readingContractVersion=2, profile=v2.PROFILE)
        stats = {'staffMeasures': 6, 'exactStaffMeasures': 6, 'eventsA': 36, 'eventsB': 36,
                 'pitchRhythmEventAgreements': 36, 'fullEventAgreements': 36,
                 'independentSourceAccuracy': None, 'sourceCertified': False, 'safeToPromote': False,
                 'readingSha256': ['2' * 64, '3' * 64], 'sourceSha256': '1' * 64,
                 'readingContractVersion': 2, 'profile': v2.PROFILE}
        report = json.loads((self.bundle / 'report.json').read_bytes())
        report.update(stats, secondParserProfileSemanticsPassed=True, measureCounts=[2, 2, 2],
                      adjudicatedUnits=0, structureFindings=[], unavailableSemantics=[],
                      repeatTraversalVerified=False, adjudicationSha256=None)
        self.write_payload('report.json', encoded(report))
        self.write_payload('comparison.json', encoded({**stats, 'issues': []}))
        self.update_reading()
        self.pin = self.write_archive(synthetic_v2_xml(self.reading))

    def update_reading(self):
        self.pin = self.write_payload('resolved-reading.json', encoded(self.reading), 'resolvedReadingSha256')

    def verify(self):
        return consumer.verify(self.bundle, self.pin, bundle_version=2)

    def reject(self, message='V2 profile|JSON|binding|version|candidate|unpromoted'):
        with self.assertRaisesRegex(ValueError, message):
            consumer.stage(self.bundle, self.pin, self.root / 'atlas', bundle_version=2)
        self.assertFalse((self.root / 'atlas').exists())

    def test_opt_in_roundtrip_and_exact_atomic_staging(self):
        self.verify()
        with self.assertRaisesRegex(ValueError, 'version'):
            consumer.verify(self.bundle, self.pin)
        receipt = consumer.stage(self.bundle, self.pin, self.root / 'atlas', bundle_version=2)
        self.assertEqual(receipt['schemaVersion'], 2)
        self.assertEqual(receipt['readingContractVersion'], 2)
        self.assertEqual(receipt['profile'], v2.PROFILE)
        self.assertFalse(receipt['safeToPromote'])
        for path in self.bundle.iterdir():
            target = self.root / 'atlas/work/transcription-imports' / self.pin / 'bundle' / path.name
            self.assertEqual(path.read_bytes(), target.read_bytes())
        self.assertFalse((self.root / 'atlas/public').exists())

    def test_cli_requires_explicit_version(self):
        args = [sys.executable, consumer.__file__, str(self.bundle),
                '--expected-manifest-sha256', self.pin, '--verify-only']
        default = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(default.returncode, 2)
        selected = subprocess.run(args + ['--bundle-version', '2'], capture_output=True, text=True)
        self.assertEqual(selected.returncode, 0, selected.stderr)
        self.assertTrue(json.loads(selected.stdout)['verified'])

    def test_unknown_reading_fields_at_every_supported_level_fail(self):
        original = deepcopy(self.reading)
        selectors = [lambda r: r, lambda r: r['header'], lambda r: r['header']['clefs'][0],
                     lambda r: r['parts'][0], lambda r: r['parts'][0]['measures'][0],
                     lambda r: r['parts'][0]['measures'][0]['events'][0],
                     lambda r: r['parts'][0]['measures'][0]['events'][4]['lyrics'][0],
                     lambda r: r['parts'][0]['measures'][0]['events'][2]['beams'][0],
                     lambda r: r['parts'][0]['measures'][0]['barlines'][0],
                     lambda r: r['parts'][0]['measures'][0]['barlines'][0]['repeat'],
                     lambda r: r['parts'][0]['measures'][0]['barlines'][0]['ending']]
        for select in selectors:
            self.reading = deepcopy(original)
            select(self.reading)['unsupported'] = 'cannot silently drop'
            self.update_reading()
            self.reject('unsupported fields')

    def test_versions_part_counts_order_and_measure_coverage_fail(self):
        original = deepcopy(self.reading)
        mutations = [lambda r: r.update(schemaVersion=1), lambda r: r.update(schemaVersion=True),
                     lambda r: r.update(profile='seven-shape'), lambda r: r['parts'].pop(),
                     lambda r: r['parts'].append(deepcopy(r['parts'][0])),
                     lambda r: r['parts'][0].update(id='P3'), lambda r: r['header']['clefs'].pop(),
                     lambda r: r['parts'][0]['measures'].pop(),
                     lambda r: r['parts'][0].update(measures=[]),
                     lambda r: r['parts'][0]['measures'][0].update(index=1)]
        for mutation in mutations:
            self.reading = deepcopy(original)
            mutation(self.reading)
            self.update_reading()
            self.reject()

    def test_unsupported_rhythm_shapes_pitch_uncertainty_and_labels_fail(self):
        original = deepcopy(self.reading)
        changes = [('shape', 'pentagon'), ('shape', ['triangle']), ('type', '32nd'), ('type', []),
                   ('onset', '1/2'), ('duration', '1/3'), ('dots', True),
                   ('pitch', ['C', '1/2', 4]), ('pitch', ['C', 0, True]),
                   ('lyrics', [{'number': True, 'text': 'x', 'syllabic': 'single'}]),
                   ('uncertainties', ['not resolved']), ('beams', [{'number': 1, 'value': 'tremolo'}])]
        for key, value in changes:
            self.reading = deepcopy(original)
            self.reading['parts'][0]['measures'][0]['events'][0][key] = value
            self.update_reading()
            self.reject()

    def test_rehashed_xml_semantic_mutations_and_unsupported_nodes_fail(self):
        from xml.etree import ElementTree as ET
        original = synthetic_v2_xml(self.reading)
        mutations = [lambda x: x.find('part-list/score-part/part-name').__setattr__('text', 'different'),
                     lambda x: x.find('work/work-title').__setattr__('text', 'different'),
                     lambda x: x.find('part/measure/attributes/key/fifths').__setattr__('text', '0'),
                     lambda x: x.find('part/measure/attributes/time/beats').__setattr__('text', '3'),
                     lambda x: x.find('part/measure/attributes/clef/sign').__setattr__('text', 'F'),
                     lambda x: x.find('part/measure/note/notehead').__setattr__('text', 'so'),
                     lambda x: x.find('part/measure/note/notehead').set('filled', 'yes'),
                     lambda x: x.find('part/measure/note/duration').__setattr__('text', '8'),
                     lambda x: x.find('part/measure/note/tie').set('type', 'stop'),
                     lambda x: x.find('part/measure/note/voice').__setattr__('text', '2'),
                     lambda x: x.find('part/measure/note/lyric/text').__setattr__('text', 'changed'),
                     lambda x: x.find('part/measure/note/beam').__setattr__('text', 'end'),
                     lambda x: x.find('part/measure/barline/repeat').set('direction', 'backward'),
                     lambda x: x.find('part/measure/barline/ending').set('number', '2'),
                     lambda x: x.findall('part/measure')[1].find('direction/direction-type/words').__setattr__('text', 'changed'),
                     lambda x: ET.SubElement(x.find('part/measure/note'), 'chord'),
                     lambda x: ET.SubElement(x.find('part/measure/note'), 'time-modification'),
                     lambda x: ET.SubElement(x.find('part/measure/note'), 'grace'),
                     lambda x: ET.SubElement(x.find('part/measure'), 'backup'),
                     lambda x: move_first_attributes_after_notes(x)]
        def move_first_attributes_after_notes(xml):
            measure = xml.find('part/measure')
            attrs = measure.find('attributes')
            measure.remove(attrs)
            measure.append(attrs)

        for mutate in mutations:
            xml = ET.fromstring(original)
            mutate(xml)
            self.pin = self.write_archive(ET.tostring(xml))
            self.reject()

    def test_envelope_metadata_counts_authority_and_unknown_fields_fail(self):
        for name in ('bundle.json', 'report.json', 'comparison.json'):
            original = self.manifest if name == 'bundle.json' else json.loads((self.bundle / name).read_bytes())
            for field, value in [('profile', 'other'), ('readingContractVersion', True),
                                 ('readingContractVersion', 1), ('sourceCertified', True),
                                 ('safeToPromote', True), ('unsupported', False)]:
                changed = {**original, field: value}
                if name == 'bundle.json':
                    self.manifest = changed
                    self.pin = self.write_manifest()
                else:
                    self.pin = self.write_payload(name, encoded(changed))
                self.reject()
            if name == 'bundle.json':
                self.manifest = original
                self.pin = self.write_manifest()
            else:
                self.pin = self.write_payload(name, encoded(original))
        original = json.loads((self.bundle / 'report.json').read_bytes())
        for field, value in [('measureCounts', [2, 2, 2, 2]), ('measureCounts', [True, 2, 2]),
                             ('staffMeasures', 8), ('adjudicatedUnits', 1),
                             ('secondParserProfileSemanticsPassed', False),
                             ('secondParserPitchRhythmPassed', False), ('independentSourceAccuracy', 1.0)]:
            self.pin = self.write_payload('report.json', encoded({**original, field: value}))
            self.reject()

    def test_duplicate_keys_nonfinite_json_and_malformed_types_have_controlled_errors(self):
        for raw in (b'{"schemaVersion":2,"schemaVersion":2}', b'{"value":NaN}', b'{"value":Infinity}', b'{"value":1e999}'):
            self.pin = self.write_payload('resolved-reading.json', raw, 'resolvedReadingSha256')
            self.reject('Invalid JSON')
            result = subprocess.run([sys.executable, consumer.__file__, str(self.bundle),
                                     '--expected-manifest-sha256', self.pin, '--verify-only', '--bundle-version', '2'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('Traceback', result.stderr)

    def test_missing_optional_uncertainties_beams_and_title_defaults_are_preserved(self):
        self.reading.pop('title')
        self.reading.pop('uncertainties')
        for part in self.reading['parts']:
            for measure in part['measures']:
                measure.pop('uncertainties')
                for event in measure['events']:
                    event.pop('uncertainties')
                    if not event['beams']:
                        event.pop('beams')
        self.update_reading()
        self.pin = self.write_archive(synthetic_v2_xml(self.reading))
        self.verify()

    def test_v1_opt_in_selection_and_invalid_api_versions_are_rejected(self):
        for value in (0, 3, True, '2', None):
            with self.assertRaises(ValueError):
                consumer.verify(self.bundle, self.pin, bundle_version=value)
        self.manifest['schemaVersion'] = 1
        self.pin = self.write_manifest()
        self.reject()


if __name__ == '__main__':
    unittest.main()
