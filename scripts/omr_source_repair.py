#!/usr/bin/env python3
"""Full-grid, source-bound repair copies, never corpus promotion.

The observer explicitly supplies every monophonic source measure, plus a
reviewed map when recognition lost measures. Exact matching note nodes survive
(lyrics/shape/notations included). Changed/new events get only observed pitch
and rhythm. Every discarded candidate field is retained in the audit; missing
annotation verification remains agent-owned. No meter-based note invention.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from difflib import SequenceMatcher
from fractions import Fraction
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import sh1991_agent_correction as archive
import omr_score_audit as audit


def remove_absent(measure, tags):
    removed = []
    for parent in list(measure.iter()):
        for child in list(parent):
            if child.tag in tags:
                removed.append(ET.tostring(child, encoding='unicode'))
                parent.remove(child)
    if 'dynamics' in tags:
        for sound in measure.iter('sound'):
            if 'dynamics' in sound.attrib:
                removed.append('sound@dynamics=' + sound.attrib.pop('dynamics'))
    return removed


def replace_events(measure, expected, divisions):
    original = copy.deepcopy(measure)
    # Parse in a wrapper carrying inherited divisions; never assume divisions=1.
    wrapper = ET.Element('score-partwise')
    part = ET.SubElement(wrapper, 'part')
    stub = ET.SubElement(part, 'measure')
    attrs = ET.SubElement(stub, 'attributes')
    ET.SubElement(attrs, 'divisions').text = str(divisions)
    part.append(copy.deepcopy(measure))
    parsed = audit.inspect(wrapper)['segments'][1]['events']
    old_notes = [n for n in measure.findall('note') if n.find('grace') is None]
    # This adapter replaces the source-observed complete event layer, so extra
    # candidate voices are removed too. It is not a top-voice-only observation.
    reusable = {}
    if len(old_notes) == len(parsed) and all(n.find('chord') is None for n in old_notes):
        def musical_key(e):
            return tuple(e['pitch'] or ()), e['duration'], e['staff'], e['voice']
        matcher = SequenceMatcher(None, list(map(musical_key, parsed)), list(map(musical_key, expected)), autojunk=False)
        for block in matcher.get_matching_blocks():
            for offset in range(block.size):
                reusable[block.b+offset] = copy.deepcopy(old_notes[block.a+offset])
    anchors = archive.direction_anchors(measure, divisions)
    insertion = next((i for i, n in enumerate(measure) if n.tag in archive.TIMED), len(measure))
    for node in list(measure):
        if node.tag in archive.TIMED:
            measure.remove(node)
    for index, event in enumerate(expected):
        note = reusable.get(index)
        if note is None:
            note = archive.new_note(event, divisions)
        elif note.find('time-modification') is None and note.find('rest[@measure="yes"]') is None:
            kind, dots = archive.duration_type(Fraction(event['duration']))
            if note.findtext('type') != kind or len(note.findall('dot')) != dots:
                for child in list(note):
                    if child.tag in {'type', 'dot'}:
                        note.remove(child)
                position = next((i for i, child in enumerate(note) if child.tag in
                                 {'accidental', 'stem', 'notehead', 'staff', 'beam', 'notations', 'lyric'}), len(note))
                node = ET.Element('type')
                node.text = kind
                note.insert(position, node)
                for dot in range(dots):
                    note.insert(position+1+dot, ET.Element('dot'))
        measure.insert(insertion+index, note)
    # Preserve absolute candidate direction anchors, not inferred source timing.
    current = archive.direction_anchors(measure, divisions)
    for node, before, after in zip(measure.findall('direction'), anchors, current):
        delta = (before-after)*divisions
        if delta:
            offset = node.find('offset')
            if offset is None:
                offset = ET.Element('offset')
                node.insert(1, offset)
            value = Fraction(offset.text or '0')+delta
            if value.denominator != 1:
                raise ValueError('Nonintegral direction timing; richer source evidence required')
            offset.text = str(value.numerator)
    if archive.direction_anchors(measure, divisions) != anchors:
        raise ValueError('Candidate direction anchor drift')
    return {'originalMeasureXml': ET.tostring(original, encoding='unicode'),
            'retainedExactNoteNodes': len(reusable), 'newSourceEventNodes': len(expected)-len(reusable),
            'unverifiedFields': ['lyrics', 'literal shape/fill', 'ties/slurs on replaced or inserted notes']}


def write_source_ties(root, expected):
    if expected is None:
        return
    for pi, part in enumerate(root.findall('part')):
        for mi, measure in enumerate(part.findall('measure')):
            for ni, note in enumerate(measure.findall('note')):
                for child in list(note.findall('tie')):
                    note.remove(child)
                for notations in note.findall('notations'):
                    for child in list(notations.findall('tied')):
                        notations.remove(child)
                for kind in ('stop', 'start'):
                    if (pi, mi, ni, kind) not in expected:
                        continue
                    tie = ET.Element('tie', type=kind)
                    # MusicXML tie follows duration, before voice/type.
                    at = next(i for i, n in enumerate(note) if n.tag == 'duration')+1
                    note.insert(at, tie)
                    notations = note.find('notations')
                    if notations is None:
                        notations = ET.Element('notations')
                        at = next((i for i, n in enumerate(note) if n.tag in {'lyric', 'play', 'listen'}), len(note))
                        note.insert(at, notations)
                    ET.SubElement(notations, 'tied', type=kind)


def source_header(measure, header, divisions):
    """Opening attributes must be observed from source, never guessed from notes."""
    fifths, beats, beat_type = header['fifths'], header['beats'], header['beatType']
    if type(fifths) is not int or not -7 <= fifths <= 7 or Fraction(beats) <= 0 or Fraction(beat_type) <= 0:
        raise ValueError('Unsupported source header')
    clef = header['clef']
    if clef['sign'] not in {'G', 'F', 'C'} or type(clef['line']) is not int or not 1 <= clef['line'] <= 5:
        raise ValueError('Unsupported source clef')
    original = [ET.tostring(a, encoding='unicode') for a in measure.findall('attributes')]
    attributes = measure.find('attributes')
    if attributes is None:
        attributes = ET.Element('attributes')
        measure.insert(0, attributes)
    for node in measure.findall('attributes'):
        for child in list(node):
            if child.tag in {'divisions', 'key', 'time', 'clef'}:
                node.remove(child)
    declaration = ET.Element('divisions')
    declaration.text = str(divisions)
    attributes.insert(0, declaration)
    key = ET.Element('key')
    ET.SubElement(key, 'fifths').text = str(fifths)
    attributes.insert(1, key)
    time = ET.Element('time')
    ET.SubElement(time, 'beats').text = str(beats)
    ET.SubElement(time, 'beat-type').text = str(beat_type)
    attributes.insert(2, time)
    node = ET.Element('clef')
    ET.SubElement(node, 'sign').text = clef['sign']
    ET.SubElement(node, 'line').text = str(clef['line'])
    attributes.append(node)
    return original


def repair(root, observations, mapping=None):
    audit.validate_observations(observations)
    before = audit.inspect(root)
    mapping_spec = mapping
    mapping = audit.measure_map(observations, before['measureCounts'], mapping)
    orphans = audit.orphan_indices(mapping_spec, len(mapping))
    corrected = copy.deepcopy(root)
    source = {(s['part'], s['measure']): s for s in observations['segments']}
    changes = []
    orphan_xml = []
    for pi, part in enumerate(corrected.findall('part')):
        original = part.findall('measure')
        orphan_xml.extend({'part': pi, 'draftMeasure': i, 'originalMeasureXml': ET.tostring(original[i], encoding='unicode')}
                          for i in orphans[pi])
        inherited, division_at = Fraction(1), []
        for measure in original:
            if measure.find('attributes/divisions') is not None:
                inherited = Fraction(measure.findtext('attributes/divisions'))
            division_at.append(inherited)
        if not original:
            raise ValueError('No draft part attributes to preserve')
        if mapping[pi][0] is None:
            raise ValueError('Missing opening measure requires an explicit source attribute map')
        for measure in original:
            part.remove(measure)
        divisions = division_at[0]
        for mi, old_index in enumerate(mapping[pi]):
            observation = source[(pi, mi)]
            expected = audit.source_events(observation)
            if any(e['staff'] != '1' or e['voice'] != '1' for e in expected):
                raise ValueError('Only source-observed single-staff monophonic segments supported')
            if old_index is None:
                measure = ET.Element('measure', number=str(mi+1))
            else:
                measure = copy.deepcopy(original[old_index])
                divisions = division_at[old_index]
            for attributes in measure.findall('attributes'):
                if int(attributes.findtext('staves', '1')) != 1:
                    raise ValueError('Multi-staff part needs a richer adapter')
            if any(n.findtext('staff', '1') != '1' for n in measure.findall('note')):
                raise ValueError('Multi-staff draft cannot be repaired by this adapter')
            # Mid-measure attributes, grace timing and unsupported notes must
            # not be silently discarded by the event-layer rewrite.
            seen_timing = False
            for node in measure:
                if node.tag in archive.TIMED:
                    seen_timing = True
                if node.tag == 'attributes' and seen_timing:
                    raise ValueError('Mid-measure attribute change needs a source map')
                if node.tag == 'note' and node.find('grace') is not None:
                    raise ValueError('Grace note source scope is unavailable')
            old_events = before['segments'][sum(before['measureCounts'][:pi])+old_index]['events'] if old_index is not None else []
            record = {'part': pi, 'measure': mi, 'draftMeasure': old_index,
                      'insertedMeasure': old_index is None, 'cropBox': observation['cropBox']}
            symbol_conflict = any(r['kind'] == 'symbol-duration-conflict' and r['part'] == pi
                                  and r['measure'] == old_index for r in before['findings'])
            if symbol_conflict or list(map(audit.event_key, old_events)) != list(map(audit.event_key, expected)):
                record.update(replace_events(measure, expected, divisions))
            removed = remove_absent(measure, observation.get('absentMarkings', []))
            if removed:
                record['sourceUnsupportedMarkingsRemoved'] = removed
            measure.set('number', str(mi+1))
            if mi == 0 and 'headers' in observations:
                if len(observations['headers']) != len(mapping):
                    raise ValueError('Source header part coverage differs')
                record['originalOpeningAttributes'] = source_header(measure, observations['headers'][pi], divisions)
            if old_index is None or len(record) > 5:
                changes.append(record)
            part.append(measure)
    archive.stamp_quarantine(corrected)
    # Replace the old opening-only scope, without implying other annotations
    # have become verified just because event coverage is complete.
    for field in corrected.findall('./identification/miscellaneous/miscellaneous-field'):
        if field.get('name') == 'atlas-agent-loop-scope':
            field.text = 'source-observed full written grid pitch/rest/duration; other annotations unresolved'
    source_ties = audit.expected_ties(observations)
    before_tie_xml = [[ET.tostring(n, encoding='unicode') for n in p.iter('note')]
                      for p in corrected.findall('part')] if source_ties is not None else None
    write_source_ties(corrected, source_ties)
    after = audit.inspect(corrected)
    result = audit.evaluate(observations, before, after, mapping_spec)
    result['orphanMeasureXml'] = orphan_xml
    if source_ties is not None:
        g = Counter(source_ties)
        b, a = audit.score_ties(root, mapping), audit.score_ties(corrected)
        e0, e1 = (g-b)+(b-g), (g-a)+(a-g)
        result['ties'] = {'sourceEndpoints': sum(g.values()), 'beforeMatching': sum((g & b).values()),
                          'afterMatching': sum((g & a).values()), 'errorsRemoved': sum((e0-e1).values()),
                          'errorsIntroduced': sum((e1-e0).values())}
        result['tieNoteEdits'] = [{'part': pi, 'noteIndex': ni, 'originalNoteXml': old,
                                  'repairedNoteXml': ET.tostring(new, encoding='unicode')}
                                 for pi, part in enumerate(corrected.findall('part'))
                                 for ni, (old, new) in enumerate(zip(before_tie_xml[pi], part.iter('note')))
                                 if old != ET.tostring(new, encoding='unicode')]
    result.update(changes=changes, beforeStructure=before['findingCounts'], afterStructure=after['findingCounts'],
                  humanReviewRequired=False, nextOwner='agent', wholeScoreAcceptance=False)
    return corrected, result


def run(score, observation_path, out, map_path=None):
    score, observation_path, out = Path(score).resolve(), Path(observation_path).resolve(), Path(out).resolve()
    if out == score or score in out.parents or out in score.parents:
        raise ValueError('Repair output must be a separate file/directory')
    observations = json.loads(observation_path.read_text())
    source_path = Path(observations['source']['path'])
    if not source_path.is_absolute():
        source_path = archive.ROOT/source_path
    if archive.digest(source_path) != observations['source']['sha256']:
        raise ValueError('Frozen source image drift')
    from PIL import Image
    with Image.open(source_path) as image:
        width, height = image.size
    if any(s['cropBox'][2] > width or s['cropBox'][3] > height for s in observations['segments']):
        raise ValueError('Source crop outside original image')
    mapping = None
    if map_path:
        map_data = json.loads(Path(map_path).read_text())
        if (map_data['sourceObservationsSha256'] != archive.digest(observation_path)
                or map_data['draftSha256'] != archive.digest(score)):
            raise ValueError('Measure map evidence binding drift')
        mapping = map_data if 'orphanDraftMeasures' in map_data else map_data['mapping']
    root = audit.read(score)
    corrected, result = repair(root, observations, mapping)
    raw = score.read_bytes()
    if raw[:2] != b'PK':
        raise ValueError('Archive copy output currently requires MXL')
    _, member = archive.read_archive(raw)
    data = archive.archive_copy(raw, corrected, member)
    # Reparse the serialized archive, not merely the in-memory object.
    reparsed = audit.inspect(archive.read_archive(data)[0])
    if reparsed != audit.inspect(corrected):
        raise ValueError('Serialized score semantics drift')
    result['evidenceSha256'] = {'input': archive.digest(score), 'sourceObservations': archive.digest(observation_path),
                               'sourceImage': archive.digest(source_path), 'measureMap': archive.digest(map_path) if map_path else None,
                               'writer': archive.digest(__file__), 'evaluator': archive.digest(audit.__file__),
                               'correctedMxl': archive.pilot.digest(data)}
    archive.immutable(out/'repaired.mxl', data)
    # Different existing parser implementation, reading the written archive.
    # This checks serialization/semantics, NOT an independent source reading.
    from agent_03_semantic_musicxml import parse_source
    second = parse_source(out/'repaired.mxl')
    if [len(p['measureNumbers']) for p in second['parts']] != observations['expectedMeasuresPerPart']:
        raise ValueError('Second parser measure coverage differs')
    for segment in observations['segments']:
        rows = [e for e in second['parts'][segment['part']]['events'] if e['measure'] == str(segment['measure']+1)]
        observed = [{'pitch': None if e['rest'] else [e['step'], str(e['alter']), e['octave']],
                     'duration': str(Fraction(str(e['beats']))), 'onset': str(Fraction(str(e['measureOnset']))),
                     'voice': e['voice'], 'staff': e['staff']} for e in rows]
        if list(map(audit.event_key, observed)) != list(map(audit.event_key, audit.source_events(segment))):
            raise ValueError('Second parser pitch/rhythm disagreement')
    result['secondParser'] = {'implementation': 'agent_03_semantic_musicxml.parse_source',
                              'implementationSha256': archive.digest(archive.ROOT/'scripts/agent_03_semantic_musicxml.py'),
                              'checkedStaffMeasures': len(observations['segments']), 'passed': True,
                              'independentSourceRecognition': False}
    archive.immutable(out/'report.json', archive.json_bytes(result))
    print(json.dumps({'checkedStaffMeasures': result['checkedStaffMeasures'], **result['summary']}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score', type=Path)
    parser.add_argument('observations', type=Path)
    parser.add_argument('--map', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.score, args.observations, args.out, args.map)
