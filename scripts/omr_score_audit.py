#!/usr/bin/env python3
"""Exact written-score diagnostics; contradictions are not automatic repairs.

No playback expansion, reference search, or inferred source notation. Fractions
are quarter-note units. A source-to-draft measure map is mandatory when grids
differ: silently zipping measures after a missed bar is not evaluation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import sh1991_agent_correction as archive

TYPES = {'breve': 8, 'whole': 4, 'half': 2, 'quarter': 1,
         'eighth': Fraction(1, 2), '16th': Fraction(1, 4),
         '32nd': Fraction(1, 8), '64th': Fraction(1, 16)}
MARKINGS = {'dynamics', 'articulations', 'ornaments'}


def read(path):
    data = Path(path).read_bytes()
    root = archive.read_archive(data)[0] if data[:2] == b'PK' else ET.fromstring(data)
    if root.tag != 'score-partwise':
        raise ValueError('Require unnamespaced score-partwise MusicXML')
    return root


def pitch(note):
    if note.find('rest') is not None:
        return None
    node = note.find('pitch')
    if node is None:
        raise ValueError('Unpitched/unknown event: source-specific adapter required')
    return [node.findtext('step'), str(Fraction(node.findtext('alter', '0'))),
            int(node.findtext('octave'))]


def inspect(root):
    rows, findings, counts = [], [], []
    for pi, part in enumerate(root.findall('part')):
        divisions, capacity = Fraction(1), None
        measures = part.findall('measure')
        counts.append(len(measures))
        open_ties = {}
        for mi, measure in enumerate(measures):
            cursor, previous = Fraction(0), None
            events, lanes = [], defaultdict(Fraction)
            location = {'part': pi, 'measure': mi}

            def flag(kind, **extra):
                findings.append({**location, 'kind': kind, **extra})

            for child in measure:
                if child.tag == 'attributes':
                    if child.find('divisions') is not None:
                        divisions = Fraction(child.findtext('divisions'))
                        if divisions <= 0:
                            raise ValueError('Nonpositive divisions')
                    time = child.find('time')
                    if time is not None:
                        beats, units = time.findall('beats'), time.findall('beat-type')
                        if len(beats) != len(units) or not beats:
                            capacity = None
                            flag('unavailable-meter')
                        else:
                            capacity = sum((sum(Fraction(x) for x in b.text.split('+')) *
                                            4 / Fraction(u.text) for b, u in zip(beats, units)), Fraction(0))
                elif child.tag in {'backup', 'forward'}:
                    amount = Fraction(child.findtext('duration')) / divisions
                    if amount < 0:
                        raise ValueError('Negative backup/forward duration')
                    cursor += amount * (-1 if child.tag == 'backup' else 1)
                    previous = None
                    if cursor < 0:
                        flag('negative-cursor', onset=str(cursor))
                elif child.tag == 'note':
                    if child.find('grace') is not None:
                        flag('grace-event-unscored')
                        continue
                    duration = Fraction(child.findtext('duration', '0')) / divisions
                    if duration <= 0:
                        flag('nonpositive-duration')
                    lane = (child.findtext('staff', '1'), child.findtext('voice', '1'))
                    chord = child.find('chord') is not None
                    if chord and (previous is None or previous[0] != lane):
                        raise ValueError('Chord without a preceding event in the same lane')
                    onset = previous[1] if chord else cursor
                    event = {'pitch': pitch(child), 'duration': str(duration),
                             'onset': str(onset), 'staff': lane[0], 'voice': lane[1]}
                    events.append(event)
                    if not chord:
                        if onset < lanes[lane]:
                            flag('same-voice-overlap', voice=lane[1], staff=lane[0], onset=str(onset))
                        cursor += duration
                        previous = (lane, onset)
                    lanes[lane] = max(lanes[lane], onset + duration)
                    kind = child.findtext('type')
                    if kind in TYPES and child.find('rest[@measure="yes"]') is None:
                        declared = Fraction(TYPES[kind]) * (2 - Fraction(1, 2 ** len(child.findall('dot'))))
                        mod = child.find('time-modification')
                        if mod is not None:
                            declared *= Fraction(mod.findtext('normal-notes')) / Fraction(mod.findtext('actual-notes'))
                        if declared != duration:
                            flag('symbol-duration-conflict', encoded=str(duration), declared=str(declared))
                    tie_key = (lane, tuple(event['pitch'] or ()))
                    tie_types = {t.get('type') for t in child.findall('tie')}
                    if tie_types and event['pitch'] is None:
                        flag('tie-on-rest')
                    if 'stop' in tie_types:
                        if tie_key not in open_ties:
                            flag('orphan-tie-stop', pitch=event['pitch'])
                        else:
                            del open_ties[tie_key]
                    if 'start' in tie_types:
                        if tie_key in open_ties:
                            flag('duplicate-tie-start', pitch=event['pitch'])
                        open_ties[tie_key] = mi
            for (staff, voice), extent in lanes.items():
                if capacity is not None and extent != capacity:
                    # A short measure can be a legitimate pickup or repeat
                    # boundary. Review it; never pad it from meter alone.
                    flag('overfull-voice' if extent > capacity else 'short-measure-review',
                         staff=staff, voice=voice, extent=str(extent), capacity=str(capacity),
                         partialHint=measure.get('implicit') == 'yes' or mi in (0, len(measures)-1)
                         or measure.find('barline/repeat') is not None)
            if capacity is None:
                flag('meter-unavailable')
            rows.append({**location, 'number': measure.get('number'), 'events': events,
                         'capacity': str(capacity) if capacity is not None else None,
                         'markings': {tag: sum(len(list(n)) for n in measure.iter(tag)) for tag in MARKINGS}})
        for (lane, value), mi in open_ties.items():
            findings.append({'part': pi, 'measure': mi, 'kind': 'unclosed-tie-start',
                             'staff': lane[0], 'voice': lane[1], 'pitch': list(value)})
    if len(set(counts)) > 1:
        findings.append({'kind': 'part-measure-count-disagreement', 'counts': counts})
    return {'measureCounts': counts, 'segments': rows, 'findings': findings,
            'findingCounts': dict(sorted(Counter(r['kind'] for r in findings).items())),
            'sourceFidelityEstablished': False}


def event_key(event):
    return (tuple(event['pitch']) if event['pitch'] is not None else None,
            str(Fraction(event['duration'])), str(Fraction(event['onset'])),
            event.get('staff', '1'), event.get('voice', '1'))


def source_events(segment):
    result = archive.expected_events(segment['events'])
    return [{**r, 'voice': segment.get('voice', '1'), 'staff': segment.get('staff', '1')} for r in result]


def measure_map(observations, actual_counts, mapping=None):
    expected = observations['expectedMeasuresPerPart']
    orphans = orphan_indices(mapping, len(expected))
    if isinstance(mapping, dict):
        mapping = mapping['mapping']
    if mapping is None:
        if expected != actual_counts:
            raise ValueError('Source/draft measure grids differ; explicit reviewed measure map required')
        mapping = [list(range(n)) for n in expected]
    if len(mapping) != len(expected) or len(actual_counts) != len(expected):
        raise ValueError('Part coverage differs from source')
    for count, actual, row, extra in zip(expected, actual_counts, mapping, orphans):
        present = [x for x in row if x is not None]
        if (len(row) != count or any(type(x) is not int for x in present)
                or any(type(x) is not int for x in extra) or len(extra) != len(set(extra))
                or present != sorted(set(present)) or set(present) & set(extra)
                or set(present) | set(extra) != set(range(actual))):
            raise ValueError('Map must account for every draft measure once: ordered source map or explicit orphan; null is source-only')
    return mapping


def orphan_indices(mapping, part_count):
    result = mapping.get('orphanDraftMeasures', [[] for _ in range(part_count)]) if isinstance(mapping, dict) else [[] for _ in range(part_count)]
    if len(result) != part_count or any(not isinstance(row, list) for row in result):
        raise ValueError('Orphan map part coverage differs')
    return result


def validate_observations(observations):
    keys = [(s['part'], s['measure']) for s in observations['segments']]
    wanted = {(p, m) for p, n in enumerate(observations['expectedMeasuresPerPart']) for m in range(n)}
    if len(keys) != len(set(keys)) or set(keys) != wanted:
        raise ValueError('Full declared source coverage required; duplicate/missing source segment')
    for segment in observations['segments']:
        source_events(segment)
        if set(segment.get('absentMarkings', [])) - MARKINGS:
            raise ValueError('Unknown absent-marking vocabulary')
        box = segment['cropBox']
        if len(box) != 4 or not (0 <= box[0] < box[2] and 0 <= box[1] < box[3]):
            raise ValueError('Invalid source crop')
    expected_ties(observations)


def expected_ties(observations):
    """If present, ties is the complete source-observed tie endpoint inventory."""
    if 'ties' not in observations:
        return None
    segments = {(s['part'], s['measure']): s for s in observations['segments']}
    endpoints = set()
    for tie in observations['ties']:
        pi, fm, fn, tm, tn = (tie[k] for k in ('part', 'fromMeasure', 'fromNote', 'toMeasure', 'toNote'))
        if any(type(x) is not int or x < 0 for x in (pi, fm, fn, tm, tn)) or (fm, fn) >= (tm, tn):
            raise ValueError('Invalid source tie order')
        try:
            a, b = source_events(segments[(pi, fm)])[fn], source_events(segments[(pi, tm)])[tn]
        except (KeyError, IndexError) as exc:
            raise ValueError('Source tie endpoint outside coverage') from exc
        if a['pitch'] is None or a['pitch'] != b['pitch']:
            raise ValueError('Source tie pitches disagree')
        for key in [(pi, fm, fn, 'start'), (pi, tm, tn, 'stop')]:
            if key in endpoints:
                raise ValueError('Duplicate source tie endpoint')
            endpoints.add(key)
    return endpoints


def score_ties(root, mapping=None):
    result = Counter()
    for pi, part in enumerate(root.findall('part')):
        inverse = {old: new for new, old in enumerate(mapping[pi]) if old is not None} if mapping else None
        for mi, measure in enumerate(part.findall('measure')):
            for ni, note in enumerate(measure.findall('note')):
                for tie in note.findall('tie'):
                    result[(pi, inverse.get(mi, -mi-1) if inverse is not None else mi, ni, tie.get('type'))] += 1
    return result


def errors(gold, candidate):
    g, c = Counter(map(event_key, gold)), Counter(map(event_key, candidate))
    return Counter({('missing', key): n for key, n in (g-c).items()}) + Counter(
        {('extra', key): n for key, n in (c-g).items()})


def evaluate(observations, before, after, mapping=None):
    validate_observations(observations)
    orphans = orphan_indices(mapping, len(observations['expectedMeasuresPerPart']))
    mapping = measure_map(observations, before['measureCounts'], mapping)
    if after['measureCounts'] != observations['expectedMeasuresPerPart']:
        raise ValueError('Corrected score must cover the complete source measure grid')
    b = {(r['part'], r['measure']): r for r in before['segments']}
    a = {(r['part'], r['measure']): r for r in after['segments']}
    rows = []
    for s in observations['segments']:
        pi, mi = s['part'], s['measure']
        old_index = mapping[pi][mi]
        old = b[(pi, old_index)] if old_index is not None else {'events': [], 'markings': {}}
        new = a[(pi, mi)]
        gold = source_events(s)
        e0, e1 = errors(gold, old['events']), errors(gold, new['events'])
        g = Counter(map(event_key, gold))
        c0, c1 = Counter(map(event_key, old['events'])), Counter(map(event_key, new['events']))
        rows.append({'part': pi, 'measure': mi, 'draftMeasure': old_index, 'sourceEvents': len(gold),
                     'beforeEvents': len(old['events']), 'afterEvents': len(new['events']),
                     'beforeMatching': sum((g & c0).values()), 'afterMatching': sum((g & c1).values()),
                     'beforeErrors': sum(e0.values()), 'afterErrors': sum(e1.values()),
                     'errorsRemoved': sum((e0-e1).values()), 'errorsIntroduced': sum((e1-e0).values()),
                     'beforeUnsupportedMarkings': sum(old['markings'].get(k, 0) for k in s.get('absentMarkings', [])),
                     'afterUnsupportedMarkings': sum(new['markings'].get(k, 0) for k in s.get('absentMarkings', []))})
    total_keys = [k for k in rows[0] if k not in {'part', 'measure', 'draftMeasure'}]
    summary = {k: sum(r[k] for r in rows) for k in total_keys}
    orphan_rows = []
    for pi, indices in enumerate(orphans):
        for mi in indices:
            row = b[(pi, mi)]
            count = len(row['events'])
            orphan_rows.append({'part': pi, 'draftMeasure': mi, 'beforeEvents': count,
                                'extraEventsRemoved': count, 'candidateMarkings': row['markings']})
            summary['beforeEvents'] += count
            summary['beforeErrors'] += count
            summary['errorsRemoved'] += count
    return {'summary': summary, 'segments': rows, 'orphanDraftMeasures': orphan_rows,
            'checkedStaffMeasures': len(rows), 'independentSourceGold': observations.get('independent') is True,
            'interpretation': 'Agreement with provisional source observations used by repair; not independent accuracy.',
            'unmeasured': ['lyrics', 'literal shape/fill', 'repeat playback', 'unobserved markings'],
            'safeToPromote': False, 'sourceCertified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    archive.immutable(args.output, archive.json_bytes(inspect(read(args.score))))
