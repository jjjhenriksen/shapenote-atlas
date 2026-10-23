"""Independent Atlas lyric-observation v3 consumer; no producer runtime imports.

The landed Atlas music validator is shared internally. V3 validates its own
lyric vocabulary and observation table before projecting internal line IDs into
that music validator. No printed label is inferred, propagated or engraved.
"""
from copy import deepcopy
from functools import wraps

import transcription_bundle_v2 as music

PROFILES = {
    'four-shape-three-monophonic': ('P1', 'P2', 'P3'),
    'four-shape-four-monophonic': ('P1', 'P2', 'P3', 'P4'),
}
FIELD_NAME = 'shapenote-lyric-observations-v3'
BASE_METADATA = music.BASE_METADATA | {'literalPrintedLabelEngravingVerified'}
NAME_RANGES = ((0x41, 0x5A), (0x61, 0x7A), (0xC0, 0xD6), (0xD8, 0xF6),
               (0xF8, 0x2FF), (0x370, 0x37D), (0x37F, 0x1FFF), (0x200C, 0x200D),
               (0x2070, 0x218F), (0x2C00, 0x2FEF), (0x3001, 0xD7FF),
               (0xF900, 0xFDCF), (0xFDF0, 0xFFFD), (0x10000, 0xEFFFF),
               (0x30, 0x39), (0x300, 0x36F), (0x203F, 0x2040))


def v3_errors(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ValueError as exc:
            message = str(exc).replace('V2 profile:', 'V3 profile:', 1)
            raise ValueError(message) from exc
    return checked


def require(condition, message):
    if not condition:
        raise ValueError('V3 profile: ' + message)


def line_id(value):
    """XML 1.0 Fifth Edition NMTOKEN: one or more NameChar, at any position."""
    require(isinstance(value, str) and bool(value), 'lineId must be a nonempty XML NMTOKEN')
    require(all(char in ':_-.' or ord(char) == 0xB7
                or any(start <= ord(char) <= end for start, end in NAME_RANGES)
                for char in value), 'lineId must be an XML NMTOKEN')
    return value


def printed_label(value):
    music.fields(value, ('state', 'text'), ('state',), 'printedLabel')
    state = value['state']
    require(state in ('present', 'absent', 'unknown'), 'unsupported printedLabel state')
    if state == 'present':
        require(set(value) == {'state', 'text'} and isinstance(value['text'], str)
                and bool(value['text'].strip()), 'present printedLabel requires exact nonblank text')
    else:
        require(set(value) == {'state'}, 'absent/unknown printedLabel cannot contain text or other fields')
    return deepcopy(value)


def selected_profile(reading):
    require(isinstance(reading, dict), 'reading must be an object')
    require(type(reading.get('schemaVersion')) is int and reading['schemaVersion'] == 3,
            'reading schemaVersion must be 3')
    profile = reading.get('profile')
    require(isinstance(profile, str) and profile in PROFILES, 'unsupported explicit v3 reading profile')
    return profile, PROFILES[profile]


@v3_errors
def normalize_reading(reading):
    """Validate reading structure and observations, retaining formal unknown states.

    Returns music semantics, keyed observation records and whether any label is
    unknown. An assembled candidate must pass verify_profile, which blocks that
    unknown state even when uncertainty lists happen to be empty.
    """
    profile, part_ids = selected_profile(reading)
    projected = deepcopy(reading)
    require(isinstance(projected.get('parts'), list), 'parts must be a list')
    require(len(projected['parts']) == len(part_ids), 'part count must match the explicit profile')
    records = {}
    unknown = False
    for part_no, part in enumerate(projected['parts']):
        require(isinstance(part, dict) and isinstance(part.get('measures'), list), 'invalid part/measures')
        require(part.get('id') == part_ids[part_no], 'parts must match the explicit ordered profile IDs')
        for measure_no, measure in enumerate(part['measures']):
            require(isinstance(measure, dict) and isinstance(measure.get('events'), list), 'invalid measure/events')
            for event_no, event in enumerate(measure['events']):
                require(isinstance(event, dict) and isinstance(event.get('lyrics'), list), 'invalid event/lyrics')
                lyrics = []
                seen = set()
                for lyric in event['lyrics']:
                    music.fields(lyric, ('lineId', 'text', 'syllabic', 'printedLabel'),
                                 ('lineId', 'text', 'syllabic', 'printedLabel'), 'v3 lyric')
                    identifier = line_id(lyric['lineId'])
                    require(identifier not in seen, 'duplicate lineId on one event')
                    seen.add(identifier)
                    observation = printed_label(lyric['printedLabel'])
                    unknown = unknown or observation['state'] == 'unknown'
                    key = (part.get('id'), measure_no, event_no, identifier)
                    records[key] = observation
                    lyrics.append({'number': identifier, 'text': lyric['text'], 'syllabic': lyric['syllabic']})
                event['lyrics'] = lyrics
    expected = music.normalize_reading(projected, reading_version=3, profile=profile, part_ids=part_ids,
                                       lyric_identifier=lambda value, name: line_id(value))
    return expected, records, unknown


@v3_errors
def observation_records(table, part_ids):
    music.fields(table, ('schemaVersion', 'kind', 'records'), ('schemaVersion', 'kind', 'records'),
                 'lyric observation table')
    require(type(table['schemaVersion']) is int and table['schemaVersion'] == 3
            and table['kind'] == 'shapenote-lyric-observations', 'unsupported observation table version/kind')
    require(isinstance(table['records'], list), 'observation records must be a list')
    records = {}
    for record in table['records']:
        music.fields(record, ('partId', 'measureIndex', 'eventIndex', 'lineId', 'printedLabel'),
                     ('partId', 'measureIndex', 'eventIndex', 'lineId', 'printedLabel'), 'observation record')
        require(isinstance(record['partId'], str) and record['partId'] in part_ids, 'unsupported observation partId')
        measure = music.integer(record['measureIndex'], 'observation measureIndex', 0)
        event = music.integer(record['eventIndex'], 'observation eventIndex', 0)
        identifier = line_id(record['lineId'])
        key = (record['partId'], measure, event, identifier)
        require(key not in records, 'duplicate observation record')
        records[key] = printed_label(record['printedLabel'])
    return records


@v3_errors
def parse_xml(raw, part_ids):
    """Validate the sole v3 table and all remaining music in the same parsed tree."""
    root = music.parse_document(raw)
    identification = music.one(root, 'identification')
    music.xml_node(identification, 'identification', ('rights', 'miscellaneous'))
    music.one(identification, 'rights')
    miscellaneous = music.one(identification, 'miscellaneous')
    music.xml_node(miscellaneous, 'miscellaneous', ('miscellaneous-field',))
    field = music.one(miscellaneous, 'miscellaneous-field')
    raw_table = music.leaf(field, 'miscellaneous-field', ('name',))
    require(field.attrib == {'name': FIELD_NAME}, 'unsupported lyric observation field name/attributes')
    table = music.strict_json_object(raw_table, 'XML lyric observations')
    records = observation_records(table, part_ids)
    # Remove only metadata whose complete vocabulary and cardinality were checked.
    # Reuse the parsed tree so XML character references (notably CR) stay literal.
    identification.remove(miscellaneous)
    return music.parse_xml_tree(root, part_ids=part_ids), records


@v3_errors
def verify_profile(reading, xml_raw):
    expected, records, unknown = normalize_reading(reading)
    require(not unknown, 'unknown printedLabel observations quarantine the assembled candidate')
    _, part_ids = selected_profile(reading)
    actual, actual_records = parse_xml(xml_raw, part_ids)
    require(actual == expected, 'MusicXML semantics differ from resolved reading')
    require(actual_records == records, 'observation table differs from exact lyric attachments/labels')
    require(all(label['state'] != 'unknown' for label in actual_records.values()),
            'unknown printedLabel observations quarantine the assembled candidate')
    return expected


@v3_errors
def verify_metadata(manifest, report, reading, comparison, xml_raw):
    music.fields(manifest, ('schemaVersion', 'kind', 'status', 'sourceSha256', 'sourceCertified',
                           'safeToPromote', 'producer', 'files', 'readingContractVersion', 'profile',
                           'literalPrintedLabelEngravingVerified'),
                 ('schemaVersion', 'readingContractVersion', 'profile', 'literalPrintedLabelEngravingVerified'),
                 'manifest')
    require(type(manifest['schemaVersion']) is int and manifest['schemaVersion'] == 3,
            'manifest schemaVersion must be 3')
    music.fields(manifest['producer'], ('repository', 'revision', 'dirty', 'exporterSha256'),
                 ('repository', 'revision', 'dirty', 'exporterSha256'), 'producer')
    for name, value, allowed in (('report', report, music.REPORT_METADATA | {'literalPrintedLabelEngravingVerified'}),
                                  ('comparison', comparison, BASE_METADATA | {'issues'})):
        music.fields(value, allowed, BASE_METADATA, name)
        require(value['sourceCertified'] is False and value['safeToPromote'] is False,
                name + ' cannot assert source/promotion authority')
        require(value['independentSourceAccuracy'] is None, name + ' source accuracy must be unknown')
    profile, _ = selected_profile(reading)
    for name, value in (('manifest', manifest), ('report', report), ('comparison', comparison)):
        require(type(value.get('readingContractVersion')) is int and value['readingContractVersion'] == 3
                and value.get('profile') == profile, name + ' reading contract/profile differs')
    for name, value in (('manifest', manifest), ('report', report), ('comparison', comparison)):
        require(value.get('literalPrintedLabelEngravingVerified') is False,
                name + ' literal printed-label engraving remains unverified')
    require(report.get('secondParserProfileSemanticsPassed') is True, 'second parser profile semantics must pass')
    expected = verify_profile(reading, xml_raw)
    music.verify_comparison(report, comparison, expected)


@v3_errors
def strict_json_object(raw, name):
    return music.strict_json_object(raw, name)


@v3_errors
def parse_document(raw):
    return music.parse_document(raw)
