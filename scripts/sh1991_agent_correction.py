#!/usr/bin/env python3
"""Local agent-owned, source-observation-driven correction, never automatic acceptance.

Repairs *copies* of saved exports, not recognition/training or reference XML.
The first adapter consumes the pilot's top-staff observations. A separately
implemented semantic parser verifies the written archive; equality to the repair
input is a consistency check, not independent recognition of source pixels.
"""
from __future__ import annotations

import argparse
import copy
from fractions import Fraction
import io
import json
from pathlib import Path
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

import sh1991_pilot as pilot
from agent_03_semantic_musicxml import parse_source

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PILOT = pilot.DEFAULT_WORK / 'draft-pilot-v7-20261016'
DEFAULT_OUT = pilot.DEFAULT_WORK / 'agent-correction-v1-final-20261016'
TIMED = {'note', 'backup', 'forward'}
STATUS = {'safeToPromote': False, 'sourceCertified': False,
          'humanReviewRequired': False, 'owner': 'agent',
          'disposition': 'quarantined-partial-source-repair'}
EMBEDDED = {'atlas-agent-loop-status': 'quarantined-partial-source-repair',
            'atlas-agent-loop-safe-to-promote': 'false',
            'atlas-agent-loop-scope': 'opening top-staff pitch/rest/duration only; not whole-score acceptance'}
LIMITS = [
    'Observed scope only: top staff, first two opening segments; not full tunes.',
    'Source observations were previously reference-exposed, not independent gold.',
    'Repair-input agreement and a second parser do not prove source fidelity.',
    'Changed segments encode pitch/rest/duration only. Original note decorations '
    '(including shapes, lyrics, ties and slurs) are retained in the raw export and '
    'audit, but not guessed onto replacement events. These fields need agent verification.',
    'No held-out tuning, recognition reruns, publication, corpus admission or human queue.',
]


def digest(path):
    return pilot.digest(Path(path).read_bytes())


def canonical(element):
    return ET.canonicalize(ET.tostring(element, encoding='unicode'), strip_text=True)


def immutable(path, data):
    path = Path(path)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f'Immutable artifact differs; choose a NEW output directory: {path}')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def read_archive(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        container = ET.fromstring(archive.read('META-INF/container.xml'))
        members = [n.attrib['full-path'] for n in container.iter()
                   if n.tag.rsplit('}', 1)[-1] == 'rootfile']
        if len(members) != 1:
            raise ValueError('Require exactly one declared MusicXML rootfile')
        member = archive.getinfo(members[0])
        if member.file_size > 20_000_000:
            raise ValueError('Oversized score XML')
        root = ET.fromstring(archive.read(member))
        if root.tag != 'score-partwise':
            raise ValueError('Require unnamespaced score-partwise XML')
        return root, members[0]


def archive_copy(original, root, member):
    """Copy all non-score members verbatim, retaining their ZipInfo metadata."""
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(output, 'w') as target:
        for info in source.infolist():
            target.writestr(info, ET.tostring(root, encoding='utf-8', xml_declaration=True)
                            if info.filename == member else source.read(info.filename))
    return output.getvalue()


def expected_events(observations):
    events = []
    onset = Fraction(0)
    if not observations:
        raise ValueError('Empty observed segment is ambiguous; quarantine')
    for spelling, raw_duration in observations:
        duration = Fraction(raw_duration)
        if duration <= 0:
            raise ValueError('Nonpositive source duration')
        pitch = None
        if spelling != 'rest':
            match = re.fullmatch(r'([A-G])([#b]?)([0-9])', spelling)
            if not match:
                raise ValueError(f'Unsupported source pitch: {spelling}')
            pitch = [match[1], str({'': 0, '#': 1, 'b': -1}[match[2]]), int(match[3])]
        events.append({'pitch': pitch, 'duration': str(duration), 'onset': str(onset)})
        onset += duration
    return events


def segment_events(parsed, part_index, measure_index):
    return [{k: e[k] for k in ('pitch', 'duration', 'onset')}
            for e in parsed['parts'][part_index]['events'] if e['measure'] == measure_index]


def duration_type(duration):
    for name, base in [('breve', 8), ('whole', 4), ('half', 2), ('quarter', 1),
                       ('eighth', Fraction(1, 2)), ('16th', Fraction(1, 4)),
                       ('32nd', Fraction(1, 8)), ('64th', Fraction(1, 16))]:
        for dots in range(3):
            if duration == base * (2 - Fraction(1, 2 ** dots)):
                return name, dots
    raise ValueError('Unsupported duration (e.g. tuplet); needs source notation evidence')


def new_note(event, divisions):
    duration = Fraction(event['duration'])
    units = duration * divisions
    if units.denominator != 1:
        raise ValueError('Source duration not representable in existing divisions')
    kind, dots = duration_type(duration)
    note = ET.Element('note')
    if event['pitch'] is None:
        ET.SubElement(note, 'rest')
    else:
        step, alter, octave = event['pitch']
        pitch = ET.SubElement(note, 'pitch')
        ET.SubElement(pitch, 'step').text = step
        if Fraction(alter):
            ET.SubElement(pitch, 'alter').text = alter
        ET.SubElement(pitch, 'octave').text = str(octave)
    ET.SubElement(note, 'duration').text = str(units.numerator)
    ET.SubElement(note, 'voice').text = '1'
    ET.SubElement(note, 'type').text = kind
    for _ in range(dots):
        ET.SubElement(note, 'dot')
    return note


def direction_anchors(measure, initial_divisions):
    """Capture absolute anchors before/after event-layer rewrite, including offsets."""
    divisions = initial_divisions
    cursor = Fraction(0)
    anchors = []
    for child in measure:
        if child.tag == 'attributes' and child.find('divisions') is not None:
            divisions = Fraction(child.findtext('divisions'))
        elif child.tag in {'backup', 'forward'}:
            cursor += Fraction(child.findtext('duration')) / divisions * (-1 if child.tag == 'backup' else 1)
        elif child.tag == 'note' and child.find('chord') is None and child.find('grace') is None:
            cursor += Fraction(child.findtext('duration', '0')) / divisions
        elif child.tag == 'direction':
            anchors.append(cursor + Fraction(child.findtext('offset', '0')) / divisions)
        elif child.tag == 'sound':
            raise ValueError('Standalone sound timing requires richer source evidence')
    return anchors


def rewrite_segment(measure, events, divisions):
    # Mid-measure attribute changes and multiple staves are outside this adapter.
    seen_timing = False
    for child in measure:
        if child.tag in TIMED:
            seen_timing = True
        if seen_timing and child.tag == 'attributes':
            raise ValueError('Mid-measure attributes require an explicit source map')
        if child.tag == 'note' and child.findtext('staff', '1') != '1':
            raise ValueError('Multi-staff segment cannot be replaced from top-staff observations')
        if child.tag == 'attributes' and int(child.findtext('staves', '1')) != 1:
            raise ValueError('Multi-staff segment cannot be replaced from top-staff observations')
    anchors = direction_anchors(measure, divisions)
    old_nodes = [copy.deepcopy(child) for child in measure if child.tag in TIMED]
    original_xml = ET.tostring(measure, encoding='unicode')
    insertion = next((i for i, child in enumerate(measure) if child.tag in TIMED), len(measure))
    for child in list(measure):
        if child.tag in TIMED:
            measure.remove(child)
    notes = [new_note(e, divisions) for e in events]
    for index, note in enumerate(notes):
        measure.insert(insertion + index, note)
    # Keep candidate directions' absolute anchors rather than silently moving
    # dynamics to the end of the newly written event sequence. Still unverified.
    current_anchors = direction_anchors(measure, divisions)
    for direction, old_anchor, current_anchor in zip(measure.findall('direction'), anchors, current_anchors):
        delta = (old_anchor - current_anchor) * divisions
        if delta:
            offset = direction.find('offset')
            if offset is None:
                offset = ET.Element('offset')
                direction.insert(1, offset)
            units = Fraction(offset.text or '0') + delta
            if units.denominator != 1:
                raise ValueError('Nonintegral direction offset requires a richer timing adapter')
            offset.text = str(units.numerator)
    if direction_anchors(measure, divisions) != anchors:
        raise ValueError('Direction anchors changed')
    annotations = sorted({n.tag for child in old_nodes if child.tag == 'note' for n in child
                          if n.tag not in {'pitch', 'rest', 'duration', 'voice', 'type', 'dot', 'chord'}})
    return {'originalMeasureXml': original_xml, 'removedNoteFields': annotations,
            'candidateDirectionAnchors': [str(x) for x in anchors],
            'replacementScope': 'monophonic pitch/rest/duration only; note decorations unverified'}


def mask_targets(root, targets):
    result = copy.deepcopy(root)
    identification = result.find('identification')
    if identification is not None:
        misc = identification.find('miscellaneous')
        if misc is not None:
            for item in list(misc):
                if item.tag == 'miscellaneous-field' and item.get('name') in EMBEDDED:
                    misc.remove(item)
            if not len(misc):
                identification.remove(misc)
        if not len(identification) and not identification.attrib:
            result.remove(identification)
    for part_index, measure_index in targets:
        measure = result.findall('part')[part_index].findall('measure')[measure_index]
        # Target internals are checked separately. Everything else must survive.
        for child in list(measure):
            measure.remove(child)
    return canonical(result)


def stamp_quarantine(root):
    identification = root.find('identification')
    if identification is None:
        identification = ET.Element('identification')
        index = next((i for i, e in enumerate(root) if e.tag not in
                      {'work', 'movement-number', 'movement-title'}), 0)
        root.insert(index, identification)
    misc = identification.find('miscellaneous')
    if misc is None:
        misc = ET.SubElement(identification, 'miscellaneous')
    for field in list(misc):
        if field.get('name') in EMBEDDED:
            misc.remove(field)
    for name, value in EMBEDDED.items():
        ET.SubElement(misc, 'miscellaneous-field', name=name).text = value


def repair_archive(data, observations, part_index=0):
    root, member = read_archive(data)
    before = pilot.score(data)
    parts = root.findall('part')
    if not 0 <= part_index < len(parts):
        raise ValueError('Source part index out of range')
    measures = parts[part_index].findall('measure')
    if len(observations) > len(measures):
        raise ValueError('Source segments exceed draft measure count; need boundary mapping')
    divisions = Fraction(1)
    receipts = []
    for index, raw_events in enumerate(observations):
        measure = measures[index]
        for attributes in measure.findall('attributes'):
            if attributes.find('divisions') is not None:
                divisions = Fraction(attributes.findtext('divisions'))
        if divisions <= 0:
            raise ValueError('Nonpositive divisions')
        expected = expected_events(raw_events)
        actual = segment_events(before, part_index, index)
        receipt = {'partIndex': part_index, 'partId': parts[part_index].get('id'),
                   'measureIndex': index, 'measureNumber': measure.get('number'),
                   'before': actual, 'expected': expected, 'changed': actual != expected}
        if receipt['changed']:
            receipt['rewrite'] = rewrite_segment(measure, expected, divisions)
        receipts.append(receipt)
    stamp_quarantine(root)
    output = archive_copy(data, root, member)
    verify_structure(data, output, receipts)
    return output, receipts


def verify_structure(original, output, receipts):
    left, member = read_archive(original)
    right, output_member = read_archive(output)
    if member != output_member:
        raise ValueError('Archive rootfile changed')
    fields = {e.get('name'): e.text for e in right.findall('./identification/miscellaneous/miscellaneous-field')}
    if any(fields.get(k) != v for k, v in EMBEDDED.items()):
        raise ValueError('Missing embedded quarantine/scope labels')
    targets = [(r['partIndex'], r['measureIndex']) for r in receipts if r['changed']]
    if mask_targets(left, targets) != mask_targets(right, targets):
        raise ValueError('Out-of-scope score content changed')
    with zipfile.ZipFile(io.BytesIO(original)) as a, zipfile.ZipFile(io.BytesIO(output)) as b:
        if a.namelist() != b.namelist() or any(a.read(n) != b.read(n) for n in a.namelist() if n != member):
            raise ValueError('Non-score archive members changed')
    for r in receipts:
        index, number = r['partIndex'], r['measureIndex']
        a = left.findall('part')[index].findall('measure')[number]
        b = right.findall('part')[index].findall('measure')[number]
        if a.attrib != b.attrib:
            raise ValueError('Target measure attributes changed')
        # All non-event elements survive; only a direction offset can change to
        # keep its absolute musical anchor fixed during note replacement.
        def context(measure):
            nodes = []
            for child in measure:
                if child.tag not in TIMED:
                    node = copy.deepcopy(child)
                    if node.tag == 'direction':
                        for offset in node.findall('offset'):
                            node.remove(offset)
                    nodes.append(canonical(node))
            return nodes
        if context(a) != context(b):
            raise ValueError('Target non-event context changed')
        if r['changed']:
            divisions = Fraction(1)
            for m in left.findall('part')[index].findall('measure')[:number+1]:
                for attr in m.findall('attributes'):
                    divisions = Fraction(attr.findtext('divisions', str(divisions)))
            if direction_anchors(a, divisions) != direction_anchors(b, divisions):
                raise ValueError('Target direction timing changed')
    return True


def verify_semantics(path, receipts):
    """Second implementation: the pre-existing semantic audit, not repair's writer."""
    parsed = parse_source(Path(path))
    for r in receipts:
        events = parsed['parts'][r['partIndex']]['events']
        # Select by the original measure's position, not its printed number:
        # number 0/implicit measures are legal and must never shift the target.
        part = parsed['parts'][r['partIndex']]
        numbers = part['measureNumbers']
        if len(set(numbers)) != len(numbers):
            raise ValueError('Ambiguous duplicate measure numbers in verification')
        actual = [e for e in events if e['measure'] == numbers[r['measureIndex']]]
        expected = r['expected']
        if len(actual) != len(expected):
            raise ValueError('Verifier event count mismatch')
        for a, e in zip(actual, expected):
            pitch = None if a['rest'] else [a['step'], str(a['alter']), a['octave']]
            if (pitch != e['pitch'] or abs(a['beats'] - float(Fraction(e['duration']))) > 0.0005
                    or abs(a['measureOnset'] - float(Fraction(e['onset']))) > 0.0005):
                raise ValueError('Verifier pitch/duration/onset mismatch')
    return {'parser': 'agent_03_semantic_musicxml.parse_source', 'segmentsChecked': len(receipts),
            'inputAgreement': True, 'independentSourceRecognition': False}


def resolve_local(root, relative):
    path = (Path(root) / relative).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('Evidence path escapes local source root')
    return path


def bind_inputs(pilot_work, root=ROOT):
    pilot_work = Path(pilot_work)
    source_path = pilot_work / 'source-observations.json'
    source = pilot.load(source_path)
    selection = pilot.load(pilot_work / 'review-selection.json')
    if source['sourceCards'] != selection['cards']:
        raise ValueError('Source-card selection drift')
    dataset = pilot.load(pilot_work / 'candidate/dataset.json')
    results_path = pilot_work / 'candidate/baseline-results.json'
    results = pilot.load(results_path)
    inputs = []
    records = {r['songNo']: r for r in dataset['records']}
    outputs = {r['songNo']: r for r in results['records']}
    cards = {r['songNo']: r for r in source['sourceCards']}
    if (len(records) != len(dataset['records']) or len(outputs) != len(results['records'])
            or len(cards) != len(source['sourceCards'])
            or set(records) != set(outputs) or set(records) != set(cards)
            or set(records) != set(source['expectedTopStaffMeasures'])):
        raise ValueError('Source/draft cohort is not an exact one-to-one mapping')
    for song_no, observations in source['expectedTopStaffMeasures'].items():
        row, receipt, card = records[song_no], outputs[song_no], cards[song_no]
        draft = resolve_local(root, receipt['output'])
        image = resolve_local(root, row['image']['path'])
        crop = resolve_local(root, card['card'])
        if (digest(draft) != receipt['outputSha256'] or digest(image) != row['image']['sha256']
                or digest(image) != card['sourceSha256'] or digest(crop) != card['cardSha256']):
            raise ValueError(f'Source/draft evidence hash drift: {song_no}')
        inputs.append({'songNo': song_no, 'title': row['title'],
                       'draft': str(draft), 'draftSha256': digest(draft),
                       'source': str(image), 'sourceSha256': digest(image),
                       'card': str(crop), 'cardSha256': digest(crop),
                       'observations': observations})
    return {'sourceObservationSha256': digest(source_path),
            'selectionSha256': digest(pilot_work/'review-selection.json'),
            'datasetSha256': digest(pilot_work/'candidate/dataset.json'),
            'recognitionReceiptSha256': digest(results_path), 'records': inputs,
            'referenceXmlRead': False, 'sourceObservationExposure': source.get('reviewerExposure')}


def run(pilot_work, output_dir):
    output_dir = Path(output_dir)
    # A pinned input receipt is also checked on replay. Changed evidence cannot
    # silently replace the predecessor of existing corrections.
    inputs = bind_inputs(pilot_work)
    if (output_dir.resolve().is_relative_to(Path(pilot_work).resolve())
            or Path(pilot_work).resolve().is_relative_to(output_dir.resolve())):
        raise ValueError('Output must be separate from historical evidence')
    immutable(output_dir/'inputs.json', json_bytes(inputs))
    pages = []
    for row in inputs['records']:
        result = {'songNo': row['songNo'], 'title': row['title'], **STATUS}
        try:
            corrected, receipts = repair_archive(Path(row['draft']).read_bytes(), row['observations'])
            path = output_dir / (row['songNo'] + '-partial-repair.mxl')
            immutable(path, corrected)
            check = verify_semantics(path, receipts)
            result.update(output=str(path), outputSha256=digest(path), segments=receipts,
                          verification=check, repairStatus='verified-against-input-observations')
        except (ValueError, KeyError, IndexError, zipfile.BadZipFile, ET.ParseError) as error:
            result.update(repairStatus='blocked-quarantined', blocker=str(error))
        pages.append(result)
    segments = [s for page in pages for s in page.get('segments', [])]
    changed = sum(s['changed'] for s in segments)
    report = {'schemaVersion': 1, **STATUS, 'limits': LIMITS,
              'verificationScope': 'repair-input consistency, two parsers, archive/scope preservation; not source certification',
              'implementationSha256': digest(__file__), 'inputManifestSha256': digest(output_dir/'inputs.json'),
              'summary': {'drafts': len(pages), 'blocked': sum(p['repairStatus']=='blocked-quarantined' for p in pages),
                          'observedSegments': len(segments), 'mismatchingSegmentsBefore': changed,
                          'inputMatchingSegmentsAfter': len(segments), 'wholeScoresAccepted': 0,
                          'humanTasksCreated': 0}, 'pages': pages}
    immutable(output_dir/'report.json', json_bytes(report))
    page_states = {p['songNo']: p['repairStatus'] for p in pages}
    tasks = [{'songNo': r['songNo'], 'owner': 'agent', 'status': 'pending',
              'action': 'Read remaining staves/measures directly from the retained scan; '
                        'record explicit scoped evidence before repairing. Verify note decorations, '
                        'lyrics and repeat/tie boundaries independently; do not copy reference XML.',
              'source': r['source'], 'sourceSha256': r['sourceSha256'],
              'predecessor': r['draft'], 'predecessorSha256': r['draftSha256'],
              'completedScope': ('pitch/rest/duration of opening top-staff segments only'
                                 if page_states[r['songNo']] != 'blocked-quarantined' else None),
              'safeToPromote': False, 'humanReviewRequired': False} for r in inputs['records']]
    immutable(output_dir/'agent-tasks.json', json_bytes({'owner': 'agent', 'tasks': tasks}))
    print(json.dumps(report['summary'], sort_keys=True))
    return report


def verify(pilot_work, output_dir):
    output_dir = Path(output_dir)
    report = pilot.load(output_dir/'report.json')
    inputs = bind_inputs(pilot_work)
    if json_bytes(inputs) != (output_dir/'inputs.json').read_bytes():
        raise ValueError('Input manifest drift')
    if report['inputManifestSha256'] != digest(output_dir/'inputs.json'):
        raise ValueError('Report manifest binding drift')
    if report['implementationSha256'] != digest(__file__):
        raise ValueError('Implementation changed; use a new output directory')
    if any(report.get(k) != v for k, v in STATUS.items()):
        raise ValueError('Report admission/ownership policy drift')
    rows = {r['songNo']: r for r in inputs['records']}
    if len(report['pages']) != len(rows) or {p['songNo'] for p in report['pages']} != set(rows):
        raise ValueError('Report page cohort drift')
    for page in report['pages']:
        if any(page.get(k) != v for k, v in STATUS.items()):
            raise ValueError('Admission/ownership policy drift')
        if page['repairStatus'] == 'blocked-quarantined':
            continue
        path = Path(page['output'])
        if digest(path) != page['outputSha256']:
            raise ValueError('Corrected archive drift')
        row = rows[page['songNo']]
        expected, receipts = repair_archive(Path(row['draft']).read_bytes(), row['observations'])
        if path.read_bytes() != expected or page['segments'] != receipts:
            raise ValueError('Correction is not reproducible from bound source observations')
        verify_structure(Path(row['draft']).read_bytes(), path.read_bytes(), receipts)
        verify_semantics(path, receipts)
    segments = [s for page in report['pages'] for s in page.get('segments', [])]
    expected_summary = {'drafts': len(rows),
                        'blocked': sum(p['repairStatus']=='blocked-quarantined' for p in report['pages']),
                        'observedSegments': len(segments),
                        'mismatchingSegmentsBefore': sum(s['changed'] for s in segments),
                        'inputMatchingSegmentsAfter': len(segments),
                        'wholeScoresAccepted': 0, 'humanTasksCreated': 0}
    if report['summary'] != expected_summary:
        raise ValueError('Report summary drift')
    tasks = pilot.load(output_dir/'agent-tasks.json')
    if (tasks.get('owner') != 'agent' or len(tasks['tasks']) != len(rows)
            or {t['songNo'] for t in tasks['tasks']} != set(rows)
            or any(t.get('owner') != 'agent' or t.get('safeToPromote') is not False
                   or t.get('humanReviewRequired') is not False for t in tasks['tasks'])):
        raise ValueError('Agent task ownership/cohort drift')
    print(json.dumps({'verifiedDrafts': sum('output' in p for p in report['pages']),
                      'wholeScoresAccepted': 0, 'humanTasksCreated': 0}, sort_keys=True))
    return report


def excerpts(pilot_work, output_dir):
    """Extract exactly the repaired scope for an offline notation import check.

    No time-signature, pickup or implicit flags are guessed to make import pass.
    The renderer must expose source-segment / MusicXML-measure disagreements.
    """
    report = verify(pilot_work, output_dir)
    output_dir = Path(output_dir)
    inputs = []
    for page in report['pages']:
        if 'output' not in page:
            continue
        root, _ = read_archive(Path(page['output']).read_bytes())
        part = root.find('part')
        part_id = part.get('id')
        for other in root.findall('part')[1:]:
            root.remove(other)
        part_list = root.find('part-list')
        for other in list(part_list):
            if other.tag != 'score-part' or other.get('id') != part_id:
                part_list.remove(other)
        for measure in part.findall('measure')[len(page['segments']):]:
            part.remove(measure)
        # Page layout is not musical evidence. Let the renderer lay out this
        # isolated excerpt rather than retaining the full scanned page width.
        defaults = root.find('defaults')
        if defaults is not None:
            root.remove(defaults)
        for pr in part.findall('.//print'):
            for child in list(pr):
                pr.remove(child)
        path = output_dir/'render'/(page['songNo']+'-excerpt.musicxml')
        immutable(path, ET.tostring(root, encoding='utf-8', xml_declaration=True))
        inputs.append({'songNo': page['songNo'], 'title': page['title'],
                       'path': str(path.resolve()), 'sha256': digest(path),
                       'expectedQuarterDurations': [sum(float(Fraction(e['duration']))
                                                       for e in s['expected']) for s in page['segments']]})
    immutable(output_dir/'render-inputs.json', json_bytes({'inputManifestSha256': report['inputManifestSha256'],
                                                         'records': inputs}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['run', 'verify', 'excerpts'])
    parser.add_argument('--pilot-work', type=Path, default=DEFAULT_PILOT)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    try:
        result = {'run': run, 'verify': verify, 'excerpts': excerpts}[args.action](args.pilot_work, args.out)
        sys.exit(1 if result['summary']['blocked'] else 0)
    except (ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as error:
        parser.exit(1, f'Quarantined: {error}\n')
