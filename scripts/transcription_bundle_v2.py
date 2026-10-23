"""Independent, stdlib-only reading/MusicXML verifier for the opt-in v2 profile.

This module consumes the wire contract only. It neither imports a producer
implementation nor recognizes source images or grants acceptance authority.
"""
from fractions import Fraction
import math
import re
from xml.etree import ElementTree as ET

XML_SPACE = ' \t\r\n'
XML_DECIMAL = r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)'
PROFILE = 'four-shape-three-monophonic'
PART_IDS = ['P1', 'P2', 'P3']
SHAPES = {'triangle': 'fa', 'round': 'so', 'square': 'la', 'diamond': 'mi'}
TYPES = {'whole': 4, 'half': 2, 'quarter': 1,
         'eighth': Fraction(1, 2), '16th': Fraction(1, 4)}
BAR_STYLES = {'regular', 'light-heavy', 'light-light', 'heavy-light', 'heavy', 'heavy-heavy'}
BEAMS = {'begin', 'continue', 'end', 'forward hook', 'backward hook'}


def require(condition, message):
    if not condition:
        raise ValueError('V2 profile: ' + message)


def fields(value, allowed, required, name):
    require(isinstance(value, dict), name + ' must be an object')
    require(set(value) <= set(allowed), name + ' has unsupported fields')
    require(set(required) <= set(value), name + ' is missing required fields')


def integer(value, name, minimum=None, maximum=None):
    require(type(value) is int, name + ' must be an integer')
    require(minimum is None or value >= minimum, name + ' is too small')
    require(maximum is None or value <= maximum, name + ' is too large')
    return value


def rational(value, name):
    require(type(value) in (int, float, str), name + ' must be rational')
    try:
        result = Fraction(str(value))
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError('V2 profile: ' + name + ' must be rational') from exc
    return result


def text(value, name, nonempty=False):
    require(isinstance(value, str), name + ' must be a string')
    require(not nonempty or bool(value), name + ' must be nonempty')
    return value


def label(value, name):
    require(type(value) is int or isinstance(value, str) and bool(value.strip()),
            name + ' must be a nonempty literal string or integer')
    return str(value)


def uncertainties(value, name):
    require(value == [] and isinstance(value, list), name + ' must be empty')


def unavailable(value, name):
    require(isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value),
            name + ' must be a list of nonempty strings')


def normalize_reading(reading):
    """Validate the complete resolved-reading v2 vocabulary and normalize music."""
    fields(reading, ('schemaVersion', 'profile', 'sourceSha256', 'title', 'header',
                     'parts', 'uncertainties', 'unavailableSemantics'),
           ('schemaVersion', 'profile', 'sourceSha256', 'header', 'parts'),
           'reading')
    require(type(reading['schemaVersion']) is int and reading['schemaVersion'] == 2,
            'reading schemaVersion must be 2')
    require(reading['profile'] == PROFILE, 'unsupported reading profile')
    require(reading.get('title') is None or isinstance(reading['title'], str),
            'title must be a string or null')
    uncertainties(reading.get('uncertainties', []), 'reading uncertainties')
    if 'unavailableSemantics' in reading:
        unavailable(reading['unavailableSemantics'], 'reading unavailableSemantics')
    header = reading['header']
    fields(header, ('fifths', 'time', 'clefs'), ('fifths', 'time', 'clefs'), 'header')
    integer(header['fifths'], 'fifths', -7, 7)
    require(isinstance(header['time'], list) and len(header['time']) == 2, 'time must have two values')
    for value in header['time']:
        integer(value, 'time value', 1)
    require(isinstance(header['clefs'], list) and len(header['clefs']) == 3,
            'exactly three ordered clefs are required')
    clefs = []
    for clef in header['clefs']:
        fields(clef, ('sign', 'line'), ('sign', 'line'), 'clef')
        require(clef['sign'] in ('G', 'F', 'C'), 'unsupported clef sign')
        clefs.append((clef['sign'], integer(clef['line'], 'clef line', 1, 5)))
    require(isinstance(reading['parts'], list) and len(reading['parts']) == 3,
            'exactly three parts are required')
    result = {'title': reading.get('title', 'Image-first research candidate') or '', 'fifths': header['fifths'],
              'time': tuple(header['time']), 'clefs': clefs, 'parts': []}
    measure_count = None
    for part_no, part in enumerate(reading['parts']):
        fields(part, ('id', 'name', 'measures'), ('id', 'name', 'measures'), 'part')
        require(part['id'] == PART_IDS[part_no], 'parts must be ordered P1/P2/P3')
        text(part['name'], 'part name')
        measures = part['measures']
        require(isinstance(measures, list) and bool(measures), 'measure coverage must be nonempty')
        if measure_count is None:
            measure_count = len(measures)
        require(len(measures) == measure_count, 'parts must have equal measure coverage')
        normalized = {'id': part['id'], 'name': part['name'], 'measures': []}
        for measure_no, measure in enumerate(measures):
            fields(measure, ('index', 'bbox', 'events', 'uncertainties', 'barlines',
                             'endingLabel', 'unavailableSemantics'),
                   ('index', 'bbox', 'events'), 'measure')
            integer(measure['index'], 'measure index', 0)
            require(measure['index'] == measure_no, 'measure indexes must be contiguous from zero')
            bbox = measure['bbox']
            require(isinstance(bbox, list) and len(bbox) == 4
                    and all(type(v) in (int, float) and (type(v) is int or math.isfinite(v)) for v in bbox)
                    and 0 <= bbox[0] < bbox[2] and 0 <= bbox[1] < bbox[3], 'invalid measure bbox')
            uncertainties(measure.get('uncertainties', []), 'measure uncertainties')
            if 'unavailableSemantics' in measure:
                unavailable(measure['unavailableSemantics'], 'measure unavailableSemantics')
            if measure.get('endingLabel') is not None:
                require(isinstance(measure['endingLabel'], str) and bool(measure['endingLabel'].strip()),
                        'endingLabel must be a nonblank string or null')
            require(isinstance(measure['events'], list) and bool(measure['events']),
                    'measure events must be nonempty')
            events = []
            position = Fraction(0)
            for event in measure['events']:
                fields(event, ('onset', 'duration', 'pitch', 'type', 'dots', 'shape', 'fill',
                               'tieStart', 'tieStop', 'lyrics', 'beams', 'uncertainties'),
                       ('onset', 'duration', 'pitch', 'type', 'dots', 'shape', 'fill',
                        'tieStart', 'tieStop', 'lyrics'), 'event')
                uncertainties(event.get('uncertainties', []), 'event uncertainties')
                onset = rational(event['onset'], 'onset')
                duration = rational(event['duration'], 'duration')
                require(onset == position and duration > 0, 'events must be contiguous and positive')
                require(isinstance(event['type'], str) and event['type'] in TYPES, 'unsupported event type')
                dots = integer(event['dots'], 'dots', 0, 2)
                require(duration == TYPES[event['type']] * sum(Fraction(1, 2 ** d) for d in range(dots + 1)),
                        'duration does not match type/dots')
                position += duration
                require(type(event['tieStart']) is bool and type(event['tieStop']) is bool,
                        'ties must be booleans')
                pitch = event['pitch']
                if pitch is None:
                    require(event['shape'] is None and event['fill'] is None
                            and not event['tieStart'] and not event['tieStop'], 'rest notation is invalid')
                else:
                    require(isinstance(pitch, list) and len(pitch) == 3, 'invalid pitch')
                    require(isinstance(pitch[0], str) and pitch[0] in 'ABCDEFG' and len(pitch[0]) == 1,
                            'unsupported pitch step')
                    alter = rational(pitch[1], 'pitch alter')
                    require(alter.denominator == 1, 'pitch alter must be integral')
                    pitch = (pitch[0], int(alter), integer(pitch[2], 'pitch octave'))
                    require(isinstance(event['shape'], str) and event['shape'] in SHAPES, 'unsupported literal shape')
                    require(event['fill'] in ('open', 'filled'), 'unsupported notehead fill')
                require(isinstance(event['lyrics'], list), 'lyrics must be a list')
                lyrics = []
                for lyric in event['lyrics']:
                    fields(lyric, ('number', 'text', 'syllabic'), ('number', 'text', 'syllabic'), 'lyric')
                    require(lyric['syllabic'] in ('single', 'begin', 'middle', 'end'), 'unsupported syllabic')
                    lyrics.append((label(lyric['number'], 'lyric number'),
                                   text(lyric['text'], 'lyric text', True), lyric['syllabic']))
                beams = event.get('beams', [])
                require(isinstance(beams, list), 'beams must be a list')
                normalized_beams = []
                for beam in beams:
                    fields(beam, ('number', 'value'), ('number', 'value'), 'beam')
                    number = integer(beam['number'], 'beam number', 1)
                    require(isinstance(beam['value'], str) and beam['value'] in BEAMS, 'unsupported beam value')
                    normalized_beams.append((number, beam['value']))
                events.append({'onset': onset, 'duration': duration, 'pitch': pitch,
                               'type': event['type'], 'dots': dots, 'shape': event['shape'],
                               'fill': event['fill'], 'tieStart': event['tieStart'],
                               'tieStop': event['tieStop'], 'lyrics': lyrics, 'beams': normalized_beams})
            bars = measure.get('barlines', [])
            require(isinstance(bars, list), 'barlines must be a list')
            barlines = []
            for bar in bars:
                fields(bar, ('location', 'barStyle', 'repeat', 'ending', 'uncertainties'),
                       ('location', 'barStyle'), 'barline')
                uncertainties(bar.get('uncertainties', []), 'barline uncertainties')
                require(bar['location'] in ('left', 'right'), 'unsupported barline location')
                require(isinstance(bar['barStyle'], str) and bar['barStyle'] in BAR_STYLES, 'unsupported barline style')
                repeat = bar.get('repeat')
                if repeat is not None:
                    fields(repeat, ('direction', 'times'), ('direction',), 'repeat')
                    require(repeat['direction'] in ('forward', 'backward'), 'unsupported repeat direction')
                    if repeat.get('times') is not None:
                        integer(repeat['times'], 'repeat times', 2)
                    repeat = (repeat['direction'], repeat.get('times'))
                ending = bar.get('ending')
                if ending is not None:
                    fields(ending, ('number', 'type'), ('number', 'type'), 'ending')
                    require(ending['type'] in ('start', 'stop', 'discontinue'), 'unsupported ending type')
                    ending = (label(ending['number'], 'ending number'), ending['type'])
                barlines.append((bar['location'], bar['barStyle'], repeat, ending))
            normalized['measures'].append({'events': events, 'barlines': sorted(barlines, key=repr),
                                           'endingLabel': measure.get('endingLabel') or ''})
        result['parts'].append(normalized)
    return result


def xml_node(node, tag, allowed_children=(), attributes=(), ordered=True):
    require(node.tag == tag, 'unsupported XML element ' + str(node.tag))
    require(set(node.attrib) <= set(attributes), 'unsupported XML attributes on ' + tag)
    require(all(child.tag in allowed_children for child in node), 'unsupported XML children in ' + tag)
    require(not allowed_children or not (node.text or '').strip(XML_SPACE), 'mixed XML content in ' + tag)
    require(all(not (child.tail or '').strip(XML_SPACE) for child in node), 'mixed XML tail in ' + tag)
    if ordered:
        ranks = [allowed_children.index(child.tag) for child in node]
        require(ranks == sorted(ranks), 'invalid XML child sequence in ' + tag)
    return node


def one(node, tag, required=True):
    matches = node.findall(tag)
    require(len(matches) == 1 if required else len(matches) <= 1, 'XML cardinality for ' + tag)
    return matches[0] if matches else None


def leaf(node, tag, attributes=()):
    xml_node(node, tag, (), attributes)
    return node.text or ''


def xml_integer(value, name, minimum=None):
    require(isinstance(value, str) and re.fullmatch(r'[+-]?[0-9]+', value.strip(XML_SPACE)) is not None,
            'invalid XML integer ' + name)
    try:
        result = int(value.strip(XML_SPACE))
    except ValueError as exc:
        raise ValueError('V2 profile: invalid XML integer ' + name) from exc
    return integer(result, 'XML ' + name, minimum)


def xml_decimal(value, name, positive=False):
    require(isinstance(value, str) and re.fullmatch(XML_DECIMAL, value.strip(XML_SPACE)) is not None,
            'XML ' + name + ' must use decimal syntax')
    result = rational(value.strip(XML_SPACE), 'XML ' + name)
    require(not positive or result > 0, 'XML ' + name + ' must be positive')
    return result


class NoDocumentTypes(ET.TreeBuilder):
    def doctype(self, name, public_id, system_id):
        raise ValueError('V2 profile: XML document types/entities are unsupported')


def parse_document(raw):
    """Reject DTDs through the XML parser, regardless of input encoding."""
    try:
        return ET.fromstring(raw, parser=ET.XMLParser(target=NoDocumentTypes()))
    except (ET.ParseError, ValueError, RecursionError) as exc:
        raise ValueError('V2 profile: invalid XML: ' + str(exc)) from exc


def parse_xml(raw):
    """Parse only the supported three-monophonic-part MusicXML wire subset."""
    root = parse_document(raw)
    xml_node(root, 'score-partwise', ('work', 'identification', 'part-list', 'part'), ('version',))
    require(root.attrib == {'version': '4.0'}, 'MusicXML version must be 4.0')
    work = one(root, 'work')
    xml_node(work, 'work', ('work-title',))
    title = leaf(one(work, 'work-title'), 'work-title')
    identification = one(root, 'identification')
    xml_node(identification, 'identification', ('rights',))
    rights = leaf(one(identification, 'rights'), 'rights')
    require(rights == 'Local research candidate; not source-certified or approved for publication.',
            'XML research rights statement differs')
    part_list = one(root, 'part-list')
    xml_node(part_list, 'part-list', ('score-part',))
    score_parts = list(part_list)
    parts = root.findall('part')
    require(len(score_parts) == len(parts) == 3, 'XML must have exactly three parts')
    result = {'title': title, 'clefs': [], 'parts': []}
    for part_no, (score_part, part) in enumerate(zip(score_parts, parts)):
        xml_node(score_part, 'score-part', ('part-name',), ('id',))
        xml_node(part, 'part', ('measure',), ('id',))
        require(score_part.attrib == part.attrib == {'id': PART_IDS[part_no]},
                'XML parts must be ordered P1/P2/P3')
        name = leaf(one(score_part, 'part-name'), 'part-name')
        measures = list(part)
        require(bool(measures), 'XML measure coverage must be nonempty')
        normalized = {'id': PART_IDS[part_no], 'name': name, 'measures': []}
        divisions = None
        for measure_no, measure in enumerate(measures):
            xml_node(measure, 'measure', ('attributes', 'note', 'barline', 'direction'), ('number',), ordered=False)
            require(measure.attrib == {'number': str(measure_no + 1)}, 'XML measure numbers must be contiguous')
            attributes = one(measure, 'attributes', required=measure_no == 0)
            if measure_no > 0:
                require(attributes is None, 'XML mid-score attribute changes are unsupported')
            else:
                require(list(measure)[0] is attributes, 'XML attributes must precede events')
                xml_node(attributes, 'attributes', ('divisions', 'key', 'time', 'clef'))
                divisions = xml_decimal(leaf(one(attributes, 'divisions'), 'divisions'), 'divisions', positive=True)
                key = one(attributes, 'key')
                xml_node(key, 'key', ('fifths',))
                fifths = xml_integer(leaf(one(key, 'fifths'), 'fifths'), 'fifths')
                meter = one(attributes, 'time')
                xml_node(meter, 'time', ('beats', 'beat-type'))
                time = (xml_integer(leaf(one(meter, 'beats'), 'beats'), 'beats', 1),
                        xml_integer(leaf(one(meter, 'beat-type'), 'beat-type'), 'beat-type', 1))
                clef = one(attributes, 'clef')
                xml_node(clef, 'clef', ('sign', 'line'))
                result['clefs'].append((leaf(one(clef, 'sign'), 'sign'),
                                        xml_integer(leaf(one(clef, 'line'), 'line'), 'clef line')))
                if part_no == 0:
                    result.update(fifths=fifths, time=time)
                require(result['fifths'] == fifths and result['time'] == time,
                        'XML key/time differs between parts')
            events = []
            position = Fraction(0)
            for note in measure.findall('note'):
                xml_node(note, 'note', ('pitch', 'rest', 'duration', 'tie', 'voice', 'type',
                                        'dot', 'notehead', 'beam', 'notations', 'lyric'))
                pitch = one(note, 'pitch', False)
                rest = one(note, 'rest', False)
                require((pitch is None) != (rest is None), 'XML note must have pitch or rest')
                if pitch is not None:
                    xml_node(pitch, 'pitch', ('step', 'alter', 'octave'))
                    alter = xml_decimal(leaf(one(pitch, 'alter'), 'alter'), 'alter')
                    require(alter.denominator == 1, 'XML alter must be integral')
                    pitch_value = (leaf(one(pitch, 'step'), 'step'), int(alter),
                                   xml_integer(leaf(one(pitch, 'octave'), 'octave'), 'octave'))
                else:
                    require(leaf(rest, 'rest') == '', 'XML rest must be empty')
                    pitch_value = None
                duration = xml_decimal(leaf(one(note, 'duration'), 'duration'), 'duration', positive=True) / divisions
                require(leaf(one(note, 'voice'), 'voice') == '1', 'XML voice must be 1')
                note_type = leaf(one(note, 'type'), 'type')
                dots = note.findall('dot')
                for dot in dots:
                    require(leaf(dot, 'dot') == '', 'XML dots must be empty')
                head = one(note, 'notehead', False)
                shape, fill = None, None
                if pitch_value is not None:
                    require(head is not None, 'XML pitched note requires a literal notehead')
                    alias = leaf(head, 'notehead', ('filled',))
                    require(alias in SHAPES.values() and head.get('filled') in ('yes', 'no')
                            and len(head.attrib) == 1, 'unsupported XML shape/fill')
                    shape = next(s for s, a in SHAPES.items() if a == alias)
                    fill = 'filled' if head.get('filled') == 'yes' else 'open'
                else:
                    require(head is None, 'XML rest cannot have notehead')
                ties = []
                for tie in note.findall('tie'):
                    require(leaf(tie, 'tie', ('type',)) == '' and set(tie.attrib) == {'type'}
                            and tie.get('type') in ('start', 'stop'), 'unsupported XML tie')
                    ties.append(tie.get('type'))
                require(len(ties) == len(set(ties)), 'duplicate XML ties')
                notations = one(note, 'notations', False)
                tied = []
                if notations is not None:
                    xml_node(notations, 'notations', ('tied',))
                    for item in notations:
                        require(leaf(item, 'tied', ('type',)) == '' and set(item.attrib) == {'type'}
                                and item.get('type') in ('start', 'stop'), 'unsupported XML tied')
                        tied.append(item.get('type'))
                require(sorted(ties) == sorted(tied), 'XML tie/notation disagreement')
                require(pitch_value is not None or not ties, 'XML rest cannot have ties')
                lyrics = []
                for lyric in note.findall('lyric'):
                    xml_node(lyric, 'lyric', ('syllabic', 'text'), ('number',))
                    require(set(lyric.attrib) == {'number'} and bool(lyric.get('number')), 'invalid XML lyric number')
                    lyrics.append((lyric.get('number'), leaf(one(lyric, 'text'), 'text'),
                                   leaf(one(lyric, 'syllabic'), 'syllabic')))
                beams = []
                for beam in note.findall('beam'):
                    value = leaf(beam, 'beam', ('number',))
                    require(set(beam.attrib) == {'number'}, 'invalid XML beam attributes')
                    beams.append((xml_integer(beam.get('number'), 'beam number', 1), value))
                events.append({'onset': position, 'duration': duration, 'pitch': pitch_value,
                               'type': note_type, 'dots': len(dots), 'shape': shape, 'fill': fill,
                               'tieStart': 'start' in ties, 'tieStop': 'stop' in ties,
                               'lyrics': lyrics, 'beams': beams})
                position += duration
            barlines = []
            for bar in measure.findall('barline'):
                xml_node(bar, 'barline', ('bar-style', 'ending', 'repeat'), ('location',))
                require(set(bar.attrib) == {'location'}, 'invalid XML barline location')
                style = leaf(one(bar, 'bar-style'), 'bar-style')
                repeat = one(bar, 'repeat', False)
                repeat_value = None
                if repeat is not None:
                    require(leaf(repeat, 'repeat', ('direction', 'times')) == ''
                            and 'direction' in repeat.attrib, 'invalid XML repeat')
                    repeat_value = (repeat.get('direction'),
                                    xml_integer(repeat.get('times'), 'repeat times', 2)
                                    if 'times' in repeat.attrib else None)
                ending = one(bar, 'ending', False)
                ending_value = None
                if ending is not None:
                    require(leaf(ending, 'ending', ('number', 'type')) == ''
                            and set(ending.attrib) == {'number', 'type'}, 'invalid XML ending')
                    ending_value = (ending.get('number'), ending.get('type'))
                barlines.append((bar.get('location'), style, repeat_value, ending_value))
            directions = measure.findall('direction')
            require(len(directions) <= 1, 'unsupported XML directions')
            ending_label = ''
            if directions:
                direction = directions[0]
                require(not events or list(measure).index(direction) < list(measure).index(measure.find('note')),
                        'XML endingLabel must precede events')
                xml_node(direction, 'direction', ('direction-type',), ('placement',))
                require(direction.attrib == {'placement': 'above'}, 'unsupported XML direction placement')
                direction_type = one(direction, 'direction-type')
                xml_node(direction_type, 'direction-type', ('words',))
                ending_label = leaf(one(direction_type, 'words'), 'words')
            normalized['measures'].append({'events': events, 'barlines': sorted(barlines, key=repr), 'endingLabel': ending_label})
        result['parts'].append(normalized)
    return result


def verify_profile(reading, xml_raw):
    """Raise ValueError unless reading and independent XML semantics agree."""
    expected = normalize_reading(reading)
    actual = parse_xml(xml_raw)
    require(actual == expected, 'MusicXML semantics differ from resolved reading')
    return expected


BASE_METADATA = {'staffMeasures', 'exactStaffMeasures', 'eventsA', 'eventsB',
                 'pitchRhythmEventAgreements', 'fullEventAgreements',
                 'independentSourceAccuracy', 'sourceCertified', 'safeToPromote',
                 'readingSha256', 'sourceSha256', 'readingContractVersion', 'profile'}
REPORT_METADATA = BASE_METADATA | {
    'unresolvedMeasures', 'status', 'adjudicatedUnits', 'writerSha256',
    'adjudicationSha256', 'unavailableSemantics', 'repeatTraversalVerified',
    'secondParserProfileSemanticsPassed', 'candidateSha256', 'archiveSha256',
    'measureCounts', 'structureFindings', 'secondParserPitchRhythmPassed', 'resolvedReadingSha256'}


def strict_json_object(raw, name):
    """V2 JSON disallows duplicate keys and JavaScript nonfinite constants."""
    import json

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key in ' + name)
            result[key] = value
        return result

    def constant(value):
        raise ValueError('V2 profile: nonfinite JSON value in ' + name)

    def finite_float(value):
        result = float(value)
        require(math.isfinite(result), 'nonfinite JSON value in ' + name)
        return result

    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite_float)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError('Invalid JSON: ' + name + ': ' + str(exc)) from exc
    require(isinstance(result, dict), name + ' must be a JSON object')
    return result


def verify_metadata(manifest, report, reading, comparison, xml_raw):
    """Check v2 envelope vocabulary, profile agreement, counts and XML music."""
    fields(manifest, ('schemaVersion', 'kind', 'status', 'sourceSha256', 'sourceCertified',
                      'safeToPromote', 'producer', 'files', 'readingContractVersion', 'profile'),
           ('schemaVersion', 'readingContractVersion', 'profile'), 'manifest')
    fields(manifest['producer'], ('repository', 'revision', 'dirty', 'exporterSha256'),
           ('repository', 'revision', 'dirty', 'exporterSha256'), 'producer')
    for name, value, allowed in (('report', report, REPORT_METADATA),
                                  ('comparison', comparison, BASE_METADATA | {'issues'})):
        fields(value, allowed, BASE_METADATA, name)
        require(value['sourceCertified'] is False and value['safeToPromote'] is False,
                name + ' cannot assert source/promotion authority')
        require(value['independentSourceAccuracy'] is None, name + ' source accuracy must be unknown')
    for name, value in (('manifest', manifest), ('report', report), ('comparison', comparison)):
        require(type(value.get('readingContractVersion')) is int and value['readingContractVersion'] == 2
                and value.get('profile') == PROFILE, name + ' reading contract/profile differs')
    require(report.get('secondParserProfileSemanticsPassed') is True,
            'second parser profile semantics must pass')
    expected = verify_profile(reading, xml_raw)
    measure_counts = [len(part['measures']) for part in expected['parts']]
    require(isinstance(report.get('measureCounts'), list)
            and all(type(value) is int for value in report['measureCounts'])
            and report['measureCounts'] == measure_counts, 'report measureCounts differs')
    staff_measures = sum(measure_counts)
    for name, value in (('report', report), ('comparison', comparison)):
        for key in ('staffMeasures', 'exactStaffMeasures', 'eventsA', 'eventsB',
                    'pitchRhythmEventAgreements', 'fullEventAgreements'):
            integer(value[key], name + ' ' + key, 0)
        require(min(value['eventsA'], value['eventsB']) >= staff_measures,
                name + ' events must cover every nonempty staff measure')
        require(value['staffMeasures'] == staff_measures, name + ' staffMeasures differs')
        require(value['exactStaffMeasures'] <= staff_measures, name + ' exactStaffMeasures exceeds coverage')
        require(value['fullEventAgreements'] <= value['pitchRhythmEventAgreements']
                <= min(value['eventsA'], value['eventsB']), name + ' agreement counts are inconsistent')
    for key in BASE_METADATA:
        require(report[key] == comparison[key], 'report/comparison metadata differs: ' + key)
    require(isinstance(comparison.get('issues'), list)
            and all(isinstance(issue, dict) for issue in comparison['issues']), 'comparison issues must be objects')
    if not comparison['issues']:
        event_count = sum(len(measure['events']) for part in expected['parts'] for measure in part['measures'])
        require(all(report[key] == event_count for key in
                    ('eventsA', 'eventsB', 'pitchRhythmEventAgreements', 'fullEventAgreements'))
                and report['exactStaffMeasures'] == staff_measures,
                'unadjudicated comparison counts differ from resolved score')
    integer(report.get('adjudicatedUnits'), 'adjudicatedUnits', 0)
    require(report['adjudicatedUnits'] == len(comparison['issues']), 'adjudicatedUnits differs from resolved issues')
    require(isinstance(report.get('structureFindings'), list)
            and all(isinstance(finding, dict) for finding in report['structureFindings']),
            'structureFindings must be objects')
    adjudication = report.get('adjudicationSha256')
    require(adjudication is None or isinstance(adjudication, str)
            and len(adjudication) == 64 and all(c in '0123456789abcdef' for c in adjudication),
            'invalid adjudication provenance')
    if 'unavailableSemantics' in report:
        unavailable(report['unavailableSemantics'], 'report unavailableSemantics')
    require(report.get('repeatTraversalVerified') is False, 'repeat traversal remains unverified')
