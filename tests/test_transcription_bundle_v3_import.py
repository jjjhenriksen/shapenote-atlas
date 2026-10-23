"""Synthetic v3 lyric observations; no source readings or recognition inputs."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import import_transcription_bundle as consumer
import transcription_bundle_v2 as v2
import transcription_bundle_v3 as v3
import test_transcription_bundle_import as legacy
from test_transcription_bundle_import import encoded, synthetic_v2_reading, synthetic_v2_xml


def synthetic_v3_reading(part_count=3):
    reading = synthetic_v2_reading()
    reading['schemaVersion'] = 3
    if part_count == 4:
        fourth = deepcopy(reading['parts'][2])
        fourth.update(id='P4', name='Explicit synthetic fourth part')
        reading['parts'].append(fourth)
        reading['header']['clefs'].append({'sign': 'G', 'line': 2})
        reading['profile'] = 'four-shape-four-monophonic'
    for part in reading['parts']:
        for measure_no, measure in enumerate(part['measures']):
            for event in measure['events']:
                event['lyrics'] = []
            measure['events'][0]['lyrics'] = [
                {'lineId': 'L1', 'text': 'sung', 'syllabic': 'single',
                 'printedLabel': {'state': 'present', 'text': ' 01 '}},
                {'lineId': 'L7', 'text': 'another', 'syllabic': 'begin',
                 'printedLabel': {'state': 'present', 'text': ' 01 '}}]
            measure['events'][1]['lyrics'] = [
                {'lineId': 'L1', 'text': ' next\rword ', 'syllabic': 'single', 'printedLabel': {'state': 'absent'}}]
            measure['events'][2]['lyrics'] = [
                {'lineId': '\u00e9:\u884c-7', 'text': 'Unicode', 'syllabic': 'single',
                 'printedLabel': {'state': 'present', 'text': ' II.\t\u00a0'}}]
            measure['events'][4]['lyrics'] = [
                {'lineId': 'L1', 'text': 'literal & word', 'syllabic': 'single',
                 'printedLabel': {'state': 'present', 'text': ' 1.\r\n '}}]
            if measure_no:
                measure['events'][0]['lyrics'] = [
                    {'lineId': 'L7', 'text': 'sparse', 'syllabic': 'end', 'printedLabel': {'state': 'absent'}}]
                measure['events'][4]['lyrics'][0]['printedLabel'] = {'state': 'absent'}
    return reading


def observation_table(reading):
    records = []
    for part in reading['parts']:
        for measure in part['measures']:
            for event_no, event in enumerate(measure['events']):
                for lyric in event['lyrics']:
                    records.append({'partId': part['id'], 'measureIndex': measure['index'],
                                    'eventIndex': event_no, 'lineId': lyric['lineId'],
                                    'printedLabel': deepcopy(lyric['printedLabel'])})
    return {'schemaVersion': 3, 'kind': 'shapenote-lyric-observations', 'records': records}


def serialized_xml(root):
    # Numeric references retain literal CR across XML end-of-line normalization.
    return ET.tostring(root, encoding='utf-8', xml_declaration=True).replace(b'\r', b'&#13;')


def synthetic_v3_xml(reading):
    projected = deepcopy(reading)
    for part in projected['parts']:
        for measure in part['measures']:
            for event in measure['events']:
                event['lyrics'] = [{'number': row['lineId'], 'text': row['text'], 'syllabic': row['syllabic']}
                                   for row in event['lyrics']]
    xml = ET.fromstring(synthetic_v2_xml(projected).replace(b'\r', b'&#13;'))
    miscellaneous = ET.SubElement(xml.find('identification'), 'miscellaneous')
    field = ET.SubElement(miscellaneous, 'miscellaneous-field', name=v3.FIELD_NAME)
    field.text = encoded(observation_table(reading)).decode()
    return serialized_xml(xml)


class TranscriptionV3Import(unittest.TestCase):
    write_manifest = legacy.TranscriptionImport.write_manifest
    write_payload = legacy.TranscriptionImport.write_payload
    write_archive = legacy.TranscriptionImport.write_archive
    update_reading = legacy.TranscriptionV2Import.update_reading

    def setUp(self):
        legacy.TranscriptionV2Import.setUp(self)
        self.install(3)

    def install(self, part_count):
        self.reading = synthetic_v3_reading(part_count)
        profile = self.reading['profile']
        self.manifest.update(schemaVersion=3, readingContractVersion=3, profile=profile,
                             literalPrintedLabelEngravingVerified=False)
        events = sum(len(m['events']) for p in self.reading['parts'] for m in p['measures'])
        for name in ('report.json', 'comparison.json'):
            value = json.loads((self.bundle / name).read_bytes())
            value.update(readingContractVersion=3, profile=profile, literalPrintedLabelEngravingVerified=False,
                         staffMeasures=part_count * 2, exactStaffMeasures=part_count * 2,
                         eventsA=events, eventsB=events, pitchRhythmEventAgreements=events, fullEventAgreements=events)
            if name == 'report.json':
                value['measureCounts'] = [2] * part_count
            self.write_payload(name, encoded(value))
        self.update_reading()
        self.pin = self.write_archive(synthetic_v3_xml(self.reading))

    def verify(self):
        return consumer.verify(self.bundle, self.pin, bundle_version=3)

    def reject(self, message='V3 profile|JSON|binding|version|candidate|unpromoted'):
        with self.assertRaisesRegex(ValueError, message):
            consumer.stage(self.bundle, self.pin, self.root / 'atlas', bundle_version=3)
        self.assertFalse((self.root / 'atlas').exists())

    def change_xml(self, mutation):
        root = ET.fromstring(synthetic_v3_xml(self.reading))
        mutation(root)
        self.pin = self.write_archive(serialized_xml(root))

    def change_table(self, mutation):
        def change(root):
            field = root.find('identification/miscellaneous/miscellaneous-field')
            table = json.loads(field.text)
            mutation(table)
            field.text = encoded(table).decode()
        self.change_xml(change)

    def test_explicit_three_and_four_part_roundtrip_exact_atomic_staging(self):
        for part_count in (3, 4):
            self.install(part_count)
            self.verify()
            receipt = consumer.stage(self.bundle, self.pin, self.root / ('atlas' + str(part_count)), bundle_version=3)
            self.assertEqual(receipt['readingContractVersion'], 3)
            self.assertEqual(receipt['profile'], self.reading['profile'])
            self.assertIs(receipt['literalPrintedLabelEngravingVerified'], False)
            self.assertIs(receipt['safeToPromote'], False)
            target = self.root / ('atlas' + str(part_count)) / 'work/transcription-imports' / self.pin
            for file in self.bundle.iterdir():
                self.assertEqual(file.read_bytes(), (target / 'bundle' / file.name).read_bytes())
            self.assertFalse((target.parents[2] / 'public').exists())
            with self.assertRaises(FileExistsError):
                consumer.stage(self.bundle, self.pin, self.root / ('atlas' + str(part_count)), bundle_version=3)

    def test_default_and_v2_reject_v3_and_explicit_cli_v3_verifies(self):
        for version in (1, 2):
            with self.assertRaisesRegex(ValueError, 'version'):
                consumer.verify(self.bundle, self.pin, bundle_version=version)
        command = [sys.executable, consumer.__file__, str(self.bundle),
                   '--expected-manifest-sha256', self.pin, '--verify-only']
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
        result = subprocess.run(command + ['--bundle-version', '3'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['verified'])

    def test_sparse_streams_duplicate_printed_labels_and_literal_cr_are_preserved(self):
        expected, records, unknown = v3.normalize_reading(self.reading)
        self.assertFalse(unknown)
        self.assertEqual(records[('P1', 0, 0, 'L1')], records[('P1', 0, 0, 'L7')])
        self.assertEqual(records[('P1', 0, 1, 'L1')], {'state': 'absent'})
        self.assertNotIn(('P1', 1, 0, 'L1'), records)
        actual, actual_records = v3.parse_xml(synthetic_v3_xml(self.reading), v3.PROFILES[self.reading['profile']])
        self.assertEqual(expected, actual)
        self.assertEqual(records, actual_records)
        self.assertEqual(actual['parts'][0]['measures'][0]['events'][1]['lyrics'][0][1], ' next\rword ')
        self.assertEqual(actual_records[('P1', 0, 4, 'L1')]['text'], ' 1.\r\n ')
        self.verify()

    def test_record_and_object_key_order_are_semantic_collections(self):
        self.change_table(lambda table: table['records'].reverse())
        self.verify()
        def reversed_keys(table):
            table['records'] = [dict(reversed(list(record.items()))) for record in table['records']]
            for record in table['records']:
                record['printedLabel'] = dict(reversed(list(record['printedLabel'].items())))
        self.change_table(reversed_keys)
        self.verify()

    def test_table_is_required_even_when_no_lyrics_exist(self):
        for part in self.reading['parts']:
            for measure in part['measures']:
                for event in measure['events']:
                    event['lyrics'] = []
        self.update_reading()
        self.pin = self.write_archive(synthetic_v3_xml(self.reading))
        self.verify()
        self.change_xml(lambda root: root.find('identification').remove(root.find('identification/miscellaneous')))
        self.reject('cardinality')

    def test_unknown_is_formal_reading_state_but_blocks_candidate_even_when_xml_agrees(self):
        self.reading['parts'][0]['measures'][0]['events'][0]['lyrics'][0]['printedLabel'] = {'state': 'unknown'}
        _, records, unknown = v3.normalize_reading(self.reading)
        self.assertTrue(unknown)
        self.assertEqual(records[('P1', 0, 0, 'L1')], {'state': 'unknown'})
        self.update_reading()
        self.pin = self.write_archive(synthetic_v3_xml(self.reading))
        self.reject('unknown printedLabel')

    def test_legacy_number_is_never_upgraded_or_used_as_line_id(self):
        lyric = self.reading['parts'][0]['measures'][0]['events'][0]['lyrics'][0]
        lyric['number'] = '01'
        del lyric['lineId']
        self.update_reading()
        self.reject('fields')

    def test_v3_exact_lyric_fields_and_printed_label_tagged_union_reject_malformed_values(self):
        original = deepcopy(self.reading)
        labels = [None, [], False, {}, {'state': 'present'}, {'state': 'present', 'text': ''},
                  {'state': 'present', 'text': ' \t'}, {'state': 'present', 'text': 1},
                  {'state': 'absent', 'text': '1'}, {'state': 'unknown', 'text': '1'},
                  {'state': 'other'}, {'state': []}, {'state': 'absent', 'extra': False}]
        for value in labels:
            self.reading = deepcopy(original)
            self.reading['parts'][0]['measures'][0]['events'][0]['lyrics'][0]['printedLabel'] = value
            self.update_reading()
            self.reject()
        for field in ('lineId', 'text', 'syllabic', 'printedLabel'):
            self.reading = deepcopy(original)
            del self.reading['parts'][0]['measures'][0]['events'][0]['lyrics'][0][field]
            self.update_reading()
            self.reject()

    def test_duplicate_event_line_id_rejects_but_part_scoped_reuse_is_valid(self):
        self.verify()  # L1/L7 repeat in every distinct part, retaining separate records.
        lyric = self.reading['parts'][0]['measures'][0]['events'][0]['lyrics'][0]
        self.reading['parts'][0]['measures'][0]['events'][0]['lyrics'].append(deepcopy(lyric))
        self.update_reading()
        self.reject('duplicate lineId')

    def test_full_unicode_nmtoken_vocabulary_and_invalid_tokens(self):
        original = deepcopy(self.reading)
        for identifier in ('01', '-line', '.line', '\u00e9:\u884c-7', '\u0301L', 'a\u00b7b', '\U00010000line', '\u1680'):
            self.reading = deepcopy(original)
            self.reading['parts'][0]['measures'][0]['events'][0]['lyrics'][0]['lineId'] = identifier
            self.update_reading()
            self.pin = self.write_archive(synthetic_v3_xml(self.reading))
            self.verify()
        for identifier in ('', 'line one', ' line', 'line\t', 'line\x00', '\u037e', '\ud800', '\U000f0000', 1, True, []):
            self.reading = deepcopy(original)
            self.reading['parts'][0]['measures'][0]['events'][0]['lyrics'][0]['lineId'] = identifier
            self.update_reading()
            self.reject('NMTOKEN')

    def test_unicode_stream_id_does_not_use_printed_label_blank_rules(self):
        self.reading['parts'][0]['measures'][0]['events'][0]['lyrics'][0]['lineId'] = '\u1680'
        self.update_reading()
        self.pin = self.write_archive(synthetic_v3_xml(self.reading))
        self.verify()
        target_root = self.root / 'unicode-atlas'
        consumer.stage(self.bundle, self.pin, target_root, bundle_version=3)
        staged = target_root / 'work/transcription-imports' / self.pin / 'bundle/candidate.musicxml'
        self.assertEqual(staged.read_bytes(), (self.bundle / 'candidate.musicxml').read_bytes())
        old_reading = synthetic_v2_reading()
        old_reading['parts'][0]['measures'][0]['events'][4]['lyrics'][0]['number'] = '\u1680'
        with self.assertRaisesRegex(ValueError, 'nonempty literal'):
            v2.normalize_reading(old_reading)

    def test_explicit_profile_versions_counts_and_ids_reject_without_guessing(self):
        original = deepcopy(self.reading)
        mutations = [lambda r: r.update(schemaVersion=2), lambda r: r.update(schemaVersion=True),
                     lambda r: r.update(profile='four-shape-four-monophonic'),
                     lambda r: r.update(profile='unknown'), lambda r: r['parts'].pop(),
                     lambda r: r['header']['clefs'].pop(), lambda r: r['parts'][0].update(id={}),
                     lambda r: r['parts'][0]['measures'].pop()]
        for mutation in mutations:
            self.reading = deepcopy(original)
            mutation(self.reading)
            self.update_reading()
            self.reject()

    def test_each_explicit_profile_rejects_changed_part_and_clef_counts(self):
        for part_count in (3, 4):
            self.install(part_count)
            original = deepcopy(self.reading)
            for mutate in (lambda r: r['parts'].pop(),
                           lambda r: r['parts'].append(deepcopy(r['parts'][0])),
                           lambda r: r['header']['clefs'].pop()):
                self.reading = deepcopy(original)
                mutate(self.reading)
                self.update_reading()
                self.reject()

    def test_missing_duplicate_orphan_tampered_and_unknown_observation_records_reject(self):
        mutations = [lambda t: t['records'].pop(),
                     lambda t: t['records'].append(deepcopy(t['records'][0])),
                     lambda t: t['records'][0].update(measureIndex=99),
                     lambda t: t['records'][0].update(eventIndex=99),
                     lambda t: t['records'][0].update(partId='P4'),
                     lambda t: t['records'][0].update(lineId='orphan'),
                     lambda t: t['records'][0].update(printedLabel={'state': 'present', 'text': 'different'}),
                     lambda t: t['records'][0].update(printedLabel={'state': 'absent'}),
                     lambda t: t['records'][0].update(printedLabel={'state': 'unknown'}),
                     lambda t: t['records'][0].update(measureIndex=True),
                     lambda t: t['records'][0].update(eventIndex=0.0),
                     lambda t: t['records'][0].update(extra=False),
                     lambda t: t.update(schemaVersion=2), lambda t: t.update(schemaVersion=True),
                     lambda t: t.update(kind='other'), lambda t: t.update(extra=[]),
                     lambda t: t.update(records={})]
        for mutate in mutations:
            self.change_table(mutate)
            self.reject()

    def test_exactly_one_named_metadata_field_and_supported_structure_are_required(self):
        mutations = [lambda x: x.find('identification').append(deepcopy(x.find('identification/miscellaneous'))),
                     lambda x: x.find('identification/miscellaneous').append(deepcopy(x.find('identification/miscellaneous/miscellaneous-field'))),
                     lambda x: x.find('identification/miscellaneous/miscellaneous-field').set('name', 'other'),
                     lambda x: x.find('identification/miscellaneous/miscellaneous-field').set('extra', 'x'),
                     lambda x: x.find('identification/miscellaneous').set('extra', 'x'),
                     lambda x: ET.SubElement(x.find('identification/miscellaneous/miscellaneous-field'), 'child')]
        for mutate in mutations:
            self.change_xml(mutate)
            self.reject()
        def bad_order(xml):
            ident = xml.find('identification')
            rights = ident.find('rights')
            ident.remove(rights)
            ident.append(rights)
        self.change_xml(bad_order)
        self.reject('sequence')

    def test_strict_json_table_rejects_duplicate_keys_nonfinite_and_nonobjects(self):
        for raw in ('{"schemaVersion":3,"schemaVersion":3}', '{"v":NaN}', '{"v":1e999}', '[]', 'null'):
            self.change_xml(lambda root: setattr(root.find('identification/miscellaneous/miscellaneous-field'), 'text', raw))
            self.reject('JSON')

    def test_xml_line_ids_sung_text_and_no_name_attribute_are_bound(self):
        mutations = [lambda x: x.find('part/measure/note/lyric').set('number', '01'),
                     lambda x: x.find('part/measure/note/lyric').set('name', ' 01 '),
                     lambda x: setattr(x.find('part/measure/note/lyric/text'), 'text', ' 01 sung'),
                     lambda x: setattr(x.find('part/measure/note/lyric/syllabic'), 'text', 'middle'),
                     lambda x: x.find('part/measure/note').append(deepcopy(x.find('part/measure/note/lyric')))]
        for mutate in mutations:
            self.change_xml(mutate)
            self.reject()

    def test_all_v3_metadata_profiles_versions_and_false_authority_flags_agree(self):
        for name in ('bundle.json', 'report.json', 'comparison.json'):
            original = deepcopy(self.manifest) if name == 'bundle.json' else json.loads((self.bundle / name).read_bytes())
            changes = [('readingContractVersion', 2), ('readingContractVersion', True),
                       ('profile', 'four-shape-four-monophonic'), ('sourceCertified', True),
                       ('safeToPromote', True), ('literalPrintedLabelEngravingVerified', True)]
            for field, value in changes:
                if name == 'bundle.json':
                    self.manifest = {**original, field: value}
                    self.pin = self.write_manifest()
                else:
                    self.pin = self.write_payload(name, encoded({**original, field: value}))
                self.reject()
            missing = deepcopy(original)
            del missing['literalPrintedLabelEngravingVerified']
            if name == 'bundle.json':
                self.manifest = missing
                self.pin = self.write_manifest()
                self.reject()
                self.manifest = original
                self.pin = self.write_manifest()
            else:
                self.pin = self.write_payload(name, encoded(missing))
                self.reject()
                self.pin = self.write_payload(name, encoded(original))

    def test_existing_numeric_dtd_ordering_and_count_guards_remain_strong(self):
        mutations = [lambda x: setattr(x.find('part/measure/note/pitch/alter'), 'text', '2/2'),
                     lambda x: setattr(x.find('part/measure/attributes/divisions'), 'text', '1e0'),
                     lambda x: setattr(x.find('part/measure/note/pitch/octave'), 'text', '4_0'),
                     lambda x: ET.SubElement(x.find('part/measure/note'), 'chord')]
        for mutation in mutations:
            self.change_xml(mutation)
            self.reject()
        raw = synthetic_v3_xml(self.reading).decode('utf-8').split('?>', 1)[1]
        raw = ('<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE score-partwise [<!ENTITY unused "x">]>' + raw).encode('utf-16')
        self.pin = self.write_archive(raw)
        self.reject('document types')
        self.pin = self.write_archive(synthetic_v3_xml(self.reading))
        container = ('<?xml version="1.0" encoding="UTF-16"?>'
                     '<!DOCTYPE container [<!ENTITY unused "x">]>'
                     '<container><rootfile full-path="score.musicxml"/></container>').encode('utf-16')
        self.pin = self.write_archive(container=container)
        self.reject('document types')


if __name__ == '__main__':
    unittest.main()
