#!/usr/bin/env python3
"""Full-written-grid evidence audit, not a corpus admission decision.

Compare actual MusicXML to explicit source observations; missing annotation
layers stay unavailable. A repaired score agreeing with its own repair inputs
is not independent source accuracy. No source inference or score modification.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

import omr_head_proposal_study as evidence
import omr_score_audit as audit

load, digest, immutable = evidence.load, evidence.digest, evidence.immutable
LAYERS = ('literalHeads', 'lyrics', 'slurs', 'repeatsEndings')


def projection(node):
    """Exact semantic tree; ignore serializer whitespace, not attributes/text."""
    return {'tag': node.tag, 'attributes': dict(sorted(node.attrib.items())),
            'text': (node.text or '').strip(), 'children': [projection(n) for n in node]}


def measure_layers(measure):
    notes = [n for n in measure.findall('note') if n.find('grace') is None]
    return {
        # Explicit notation, not shape inferred from pitch, nor fill from duration.
        'literalHeads': [projection(n.find('notehead')) if n.find('notehead') is not None else None
                         for n in notes],
        'lyrics': [[projection(l) for l in n.findall('lyric')] for n in notes],
        'slurs': [[projection(l) for l in n.findall('notations/slur')] for n in notes],
        'repeatsEndings': [{'location': b.get('location', 'right'),
                           'children': [projection(n) for n in b if n.tag in {'repeat', 'ending'}]}
                          for b in measure.findall('barline')
                          if b.find('repeat') is not None or b.find('ending') is not None],
    }


def gate(status, **values):
    return {'status': status, **values}


def compare_headers(observed, root):
    headers = observed.get('headers')
    parts = root.findall('part')
    if headers is None:
        return gate('unavailable', reason='No complete source header observations')
    if len(headers) != len(parts):
        raise ValueError('Header source coverage differs from part grid')
    mismatches = []
    for pi, (header, part) in enumerate(zip(headers, parts)):
        attrs = part.find('measure/attributes')
        if attrs is None:
            mismatches.append({'part': pi, 'actual': None}); continue
        actual = {'fifths': attrs.findtext('key/fifths'),
                  'beats': attrs.findtext('time/beats'),
                  'beatType': attrs.findtext('time/beat-type'),
                  'clef': {'sign': attrs.findtext('clef/sign'), 'line': attrs.findtext('clef/line')}}
        wanted = {'fifths': str(header['fifths']), 'beats': str(header['beats']),
                  'beatType': str(header['beatType']),
                  'clef': {'sign': header['clef']['sign'], 'line': str(header['clef']['line'])}}
        if actual != wanted:
            mismatches.append({'part': pi, 'expected': wanted, 'actual': actual})
    return gate('pass' if not mismatches else 'fail', checkedParts=len(parts), mismatches=mismatches,
                scope='Opening key, clef and meter only; later changes are not verified')


def validate_grid(observed):
    expected = observed['expectedMeasuresPerPart']
    if not expected or any(type(n) is not int or n < 1 for n in expected):
        raise ValueError('Positive complete source measure counts required')
    if not observed.get('observer') or not observed.get('scope'):
        raise ValueError('Source observer and scope required')
    grid = observed.get('writtenGrid')
    if grid is not None:
        edges, bands = grid['edges'], grid['staffBands']
        if (len(edges) < 2 or any(type(n) is not int for n in edges)
                or edges != sorted(set(edges)) or edges[0] < 0
                or len(bands) != len(expected)
                or expected != [len(edges)-1]*len(expected)
                or any(len(b) != 2 or not 0 <= b[0] < b[1] for b in bands)):
            raise ValueError('Explicit full source grid coverage differs')
    return expected


def compare(observed, root, mapping=None):
    expected = validate_grid(observed)
    actual = audit.inspect(root)
    result = {'sourceGrid': gate('pass' if expected == actual['measureCounts'] else 'fail',
                                expected=expected, actual=actual['measureCounts'])}
    result['openingHeader'] = compare_headers(observed, root)
    # Do not let an alignment failure erase other independently known failures.
    aligned = None
    alignment_error = None
    try:
        aligned = audit.measure_map(observed, actual['measureCounts'], mapping)
    except ValueError as exc:
        alignment_error = str(exc)
    result['measureAlignment'] = gate('pass' if aligned is not None else 'blocked',
                                      reason=alignment_error,
                                      method='Explicit supplied map, or index agreement on equal declared grids; not independent alignment proof')
    grace_count = actual['findingCounts'].get('grace-event-unscored', 0)
    result['unscoredGraceEvents'] = gate('blocked' if grace_count else 'pass',
                                        count=grace_count,
                                        scope='Source event schema cannot evaluate grace notes')
    if 'segments' in observed:
        audit.validate_observations(observed)
        segments = observed['segments']
    else:
        segments = []
    actual_segments = {(s['part'], s['measure']): s for s in actual['segments']}
    actual_xml = {(pi, mi): m for pi, p in enumerate(root.findall('part'))
                  for mi, m in enumerate(p.findall('measure'))}
    if segments and aligned is not None:
        matched = missing = extra = source_events = 0
        details = []
        for segment in segments:
            pi, mi = segment['part'], segment['measure']
            old = aligned[pi][mi]
            wanted = audit.source_events(segment)
            got = actual_segments[(pi, old)]['events'] if old is not None else []
            counts = audit.errors(wanted, got)
            miss = sum(n for (kind, _), n in counts.items() if kind == 'missing')
            ext = sum(n for (kind, _), n in counts.items() if kind == 'extra')
            source_events += len(wanted); matched += len(wanted)-miss
            missing += miss; extra += ext
            if miss or ext:
                details.append({'part': pi, 'measure': mi, 'draftMeasure': old,
                                'missingEventUnits': miss, 'extraEventUnits': ext})
        for pi, indices in enumerate(audit.orphan_indices(mapping, len(expected))):
            for mi in indices:
                ext = len(actual_segments[(pi, mi)]['events']); extra += ext
                details.append({'part': pi, 'orphanDraftMeasure': mi, 'extraEventUnits': ext})
        result['pitchRhythm'] = gate('pass' if missing+extra == 0 else 'fail',
                                     sourceEvents=source_events, matched=matched,
                                     missingEventUnits=missing, extraEventUnits=extra,
                                     checkedStaffMeasures=len(segments), differences=details)
    else:
        result['pitchRhythm'] = gate('blocked' if alignment_error else 'unavailable',
                                     reason=alignment_error or 'No complete source event inventory')
    # Each optional layer must explicitly cover EVERY source measure; empty
    # inventories are evidence of absence only when explicitly source-observed.
    for layer in LAYERS:
        covered = [s for s in segments if layer in s]
        if len(covered) != sum(expected):
            result[layer] = gate('unavailable', observedStaffMeasures=len(covered),
                                 requiredStaffMeasures=sum(expected)); continue
        if any(s[layer] is None for s in covered):
            result[layer] = gate('unavailable', reason='Null source annotation is unknown, not absence'); continue
        if layer == 'literalHeads':
            incomplete = False
            for s in covered:
                if len(s[layer]) != len(s['events']):
                    raise ValueError('Per-event annotation coverage differs: '+layer)
                for event, head in zip(audit.source_events(s), s[layer]):
                    if event['pitch'] is not None and (head is None or
                            head.get('attributes', {}).get('filled') not in {'yes', 'no'}):
                        incomplete = True
            if incomplete:
                result[layer] = gate('unavailable', reason='Pitched heads require directly observed shape and explicit fill; no duration-derived fill'); continue
        if aligned is None:
            result[layer] = gate('blocked', reason=alignment_error); continue
        differences = []
        for s in covered:
            pi, mi = s['part'], s['measure']; old = aligned[pi][mi]
            if layer != 'repeatsEndings' and len(s[layer]) != len(s['events']):
                raise ValueError('Per-event annotation coverage differs: '+layer)
            got = measure_layers(actual_xml[(pi, old)])[layer] if old is not None else None
            if got != s[layer]:
                differences.append({'part': pi, 'measure': mi, 'draftMeasure': old})
        # Orphan measures cannot escape an annotation layer's denominator.
        orphan_count = sum(len(v) for v in audit.orphan_indices(mapping, len(expected)))
        result[layer] = gate('pass' if not differences and not orphan_count else 'fail',
                             differences=differences, orphanDraftMeasures=orphan_count,
                             checkedStaffMeasures=len(covered))
    ties = audit.expected_ties(observed) if segments else None
    if ties is None:
        result['ties'] = gate('unavailable', reason='No complete source tie inventory')
    elif aligned is None:
        result['ties'] = gate('blocked', reason=alignment_error)
    else:
        wanted, got = Counter(ties), audit.score_ties(root, aligned)
        result['ties'] = gate('pass' if wanted == got else 'fail',
                              observedEndpoints=sum(wanted.values()),
                              matchedEndpoints=sum((wanted & got).values()),
                              missingEndpoints=sum((wanted-got).values()),
                              extraEndpoints=sum((got-wanted).values()),
                              scope='Playback tie elements; visual tied notation is separately unverified')
    # Existing absence observations cover these three families, not every kind
    # of printed mark. Keep a separate unavailable gate for all other markings.
    covered = [s for s in segments if set(s.get('absentMarkings', [])) == audit.MARKINGS]
    if len(covered) == sum(expected) and aligned is not None:
        unsupported = sum(sum(actual_segments[(s['part'], aligned[s['part']][s['measure']])]['markings'].values())
                          for s in covered if aligned[s['part']][s['measure']] is not None)
        unsupported += sum(sum(actual_segments[(pi, mi)]['markings'].values())
                           for pi, indices in enumerate(audit.orphan_indices(mapping, len(expected))) for mi in indices)
        result['observedAbsentMarkings'] = gate('pass' if unsupported == 0 else 'fail',
                                                unsupported=unsupported, families=sorted(audit.MARKINGS))
    else:
        result['observedAbsentMarkings'] = gate('unavailable', reason='Complete mapped absence observations unavailable')
    result['otherMarkingsAndHeaderChanges'] = gate('unavailable', reason='No complete source inventory/comparator for remaining printed markings and later attribute changes')
    result['visualTieNotation'] = gate('unavailable', reason='Playback ties do not verify printed tied/slur glyphs')
    result['independentSourceVerification'] = gate('unavailable', reason='No separate blinded source-reader adjudication receipt; source independent flag alone is insufficient')
    return {'gates': result, 'structureFindings': actual['findingCounts'],
            'status': 'blocked' if any(v['status'] in {'fail', 'blocked'} for v in result.values()) else 'incomplete',
            'wholeScoresAccepted': 0, 'safeToPromote': False, 'sourceCertified': False,
            'interpretation': 'Agreement with declared source observations only. This audit cannot authorize promotion.'}


def run(manifest_path, out):
    manifest_path, out = Path(manifest_path).resolve(), Path(out).resolve()
    manifest = load(manifest_path)
    refs = {k: manifest[k] for k in ('source', 'score', 'observations')}
    if 'mapping' in manifest:
        refs['mapping'] = manifest['mapping']
    paths = {k: (manifest_path.parent/v['path']).resolve() for k, v in refs.items()}
    if any(out == p or out in p.parents for p in [manifest_path, *paths.values()]):
        raise ValueError('Never write into an input evidence directory')
    inputs = {str(manifest_path): digest(manifest_path)}
    for key, path in paths.items():
        if digest(path) != refs[key]['sha256']:
            raise ValueError('Manifest input drift: '+key)
        inputs[str(path)] = digest(path)
    observed = load(paths['observations'])
    if observed['source']['sha256'] != refs['source']['sha256']:
        raise ValueError('Observation/source image hash mismatch')
    # Verify source extents whenever a full source grid was supplied.
    if 'writtenGrid' in observed:
        from PIL import Image
        with Image.open(paths['source']) as im:
            grid = observed['writtenGrid']
            if grid['edges'][-1] > im.width or any(b[1] > im.height for b in grid['staffBands']):
                raise ValueError('Full source grid exceeds image')
    mapping = load(paths['mapping']) if 'mapping' in paths else None
    root = audit.read(paths['score'])
    report = compare(observed, root, mapping)
    code = {str(Path(m.__file__).resolve()): digest(m.__file__)
            for m in (audit, audit.archive, audit.archive.pilot, evidence)}
    code[str(Path(__file__).resolve())] = digest(__file__)
    report.update(schemaVersion=1, source=manifest['identity'],
                  observer=observed['observer'], sourceScope=observed['scope'],
                  inputsSha256=inputs, codeSha256=code)
    if any(digest(p) != sha for p, sha in {**inputs, **code}.items()):
        raise ValueError('Input/code drift during audit')
    immutable(out/'report.json', report)
    immutable(out/'receipt.json', {'reportSha256': digest(out/'report.json'),
                                 'inputsSha256': inputs, 'codeSha256': code})
    return report


if __name__ == '__main__':
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    r = run(args.manifest, args.out)
    print(json.dumps({'source': r['source'], 'status': r['status'],
                      'gates': {k: v['status'] for k, v in r['gates'].items()}}, indent=2))
