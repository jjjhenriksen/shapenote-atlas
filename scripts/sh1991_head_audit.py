#!/usr/bin/env python3
"""Source-literal head audit versus retained OMR graph, not MusicXML gold labels."""
import argparse
from collections import defaultdict
import math
import json
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET

import sh1991_pilot as pilot

DEFAULT_WORK = pilot.DEFAULT_WORK / 'head-shape-audit-v1'


def sheet_for(song_no):
    files = list((pilot.DEFAULT_WORK / 'baseline' / song_no).glob('*.omr'))
    if len(files) != 1:
        raise ValueError('expected one retained raw OMR graph')
    with zipfile.ZipFile(files[0]) as archive:
        return ET.fromstring(archive.read('sheet#1/sheet#1.xml')), pilot.digest(files[0].read_bytes())


def at_x(points, x):
    points = sorted((float(p.attrib['x']), float(p.attrib['y'])) for p in points)
    if not points:
        raise ValueError('missing line geometry')
    if x <= points[0][0]:
        return points[0][1]
    for left, right in zip(points, points[1:]):
        if left[0] <= x <= right[0] and right[0] > left[0]:
            t = (x - left[0]) / (right[0] - left[0])
            return left[1] * (1 - t) + right[1] * t
    return points[-1][1]


def literal_point(staff, x, position):
    """Position is visually observed half-line distance below the top staff line."""
    lines = [at_x(line.findall('point'), x) for line in staff.findall('lines/line')]
    if len(lines) != 5 or any(b <= a for a, b in zip(lines, lines[1:])):
        raise ValueError('invalid five-line geometry')
    interline = (lines[-1] - lines[0]) / 4
    if position <= 0:
        y = lines[0] + position * (lines[1] - lines[0]) / 2
    elif position >= 8:
        y = lines[-1] + (position - 8) * (lines[-1] - lines[-2]) / 2
    else:
        i = int(position // 2); t = position / 2 - i
        y = lines[i] * (1 - t) + lines[i+1] * t
    return y, interline


def observations(work, frozen=True):
    design = pilot.load(work / 'design.json')
    annotations = pilot.load(work / ('annotations.json' if frozen else 'annotations-draft.json'))
    windows = {w['id']: w for w in design['selections']}
    if set(windows) != set(annotations['windows']):
        raise ValueError('annotation window coverage differs from frozen selection')
    result = []
    for name, window in windows.items():
        source = pilot.ROOT / window['sourceImage']['path']
        if pilot.digest(source.read_bytes()) != window['sourceImage']['sha256']:
            raise ValueError('original scan drift')
        sheet, sha = sheet_for(window['songNo'])
        if sha != window['layoutSha256']:
            raise ValueError('layout changed')
        staff = sheet.find(f"./page/system/part/staff[@id='{window['staffId']}']")
        if staff is None:
            raise ValueError('missing selected staff')
        prior_x = -math.inf
        for index, item in enumerate(annotations['windows'][name]):
            if item['shape'] not in ('round', 'square', 'triangle', 'diamond', 'unknown') or item['fill'] not in ('filled', 'open', 'unknown'):
                raise ValueError('unknown annotation vocabulary')
            if not window['cropBox'][0] <= item['x'] < window['cropBox'][2] or item['x'] <= prior_x:
                raise ValueError('out-of-window or unordered source centers')
            prior_x = item['x']
            y, interline = literal_point(staff, item['x'], item['staffPosition'])
            if not window['cropBox'][1] <= y < window['cropBox'][3]:
                raise ValueError('source center outside vertical review window')
            result.append({**item, 'id': name + '-n' + str(index+1), 'windowId': name,
                           'songNo': window['songNo'], 'staffId': window['staffId'],
                           'y': y, 'interline': interline})
    return design, annotations, result


def render(work):
    from PIL import Image, ImageDraw
    design, _, rows = observations(work, frozen=False)
    for window in design['selections']:
        card = Image.open(work / (window['id'] + '.png')).convert('RGB')
        if pilot.digest((work / (window['id'] + '.png')).read_bytes()) != window['cardSha256']:
            raise ValueError('source card drift')
        draw = ImageDraw.Draw(card)
        for row in rows:
            if row['windowId'] != window['id']:
                continue
            x = (row['x'] - window['cropBox'][0]) * 2
            y = (row['y'] - window['cropBox'][1]) * 2 + 50
            draw.ellipse((x-3,y-3,x+3,y+3), fill='red')
            draw.text((x+3,y+12),row['id'].rsplit('-n',1)[1],fill='blue')
        card.save(work / (window['id'] + '-source-points.png'))
    print('Rendered source-only point checks for', len(rows), 'heads')


def heads_in_graph(sheet):
    chords = {e.attrib['id'] for e in sheet.iter('head-chord')}
    memberships = set()
    for relation in sheet.iter('relation'):
        if relation.find('containment') is not None:
            a, b = relation.attrib['source'], relation.attrib['target']
            if a in chords: memberships.add(b)
            if b in chords: memberships.add(a)
    heads = []
    for head in sheet.iter('head'):
        bounds = head.find('bounds')
        if bounds is None:
            continue
        heads.append({'id': head.attrib['id'], 'x': float(bounds.attrib['x']) + float(bounds.attrib['w']) / 2,
                      'y': float(bounds.attrib['y']) + float(bounds.attrib['h']) / 2,
                      'shape': head.attrib.get('shape'), 'staffId': head.attrib.get('staff'),
                      'inHeadChord': head.attrib['id'] in memberships})
    return heads


def match(rows, heads, threshold):
    """Distance-only greedy one-to-one match; source shape/fill never enters cost."""
    pairs = []
    for i, row in enumerate(rows):
        for j, head in enumerate(heads):
            distance = math.hypot(row['x'] - head['x'], row['y'] - head['y']) / row['interline']
            if distance <= threshold:
                pairs.append((distance, i, j))
    used_rows = set(); used_heads = set(); matches = {}
    for distance, i, j in sorted(pairs):
        if i in used_rows or j in used_heads:
            continue
        used_rows.add(i); used_heads.add(j)
        matches[rows[i]['id']] = {**heads[j], 'distanceInInterlines': distance}
    return matches


def strata(rows, keys):
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row[k] for k in keys)].append(row)
    output = []
    for key, group in sorted(grouped.items()):
        detected = [r for r in group if r['match'] is not None]
        fill_judged = [r for r in detected if r['fill'] in ('filled', 'open') and r['match']['shape'] in ('NOTEHEAD_BLACK', 'NOTEHEAD_VOID')]
        output.append({**dict(zip(keys,key)), 'observed': len(group), 'retainedHead': len(detected),
                       'missingHead': len(group) - len(detected), 'retainedHeadRate': len(detected) / len(group),
                       'inHeadChord': sum(r['match']['inHeadChord'] for r in detected),
                       'staffAssignmentMatches': sum(r['staffId'] == r['match']['staffId'] for r in detected),
                       'fillJudgedAmongDetected': len(fill_judged),
                       'fillMatchesAmongDetected': sum((r['fill'] == 'filled') == (r['match']['shape'] == 'NOTEHEAD_BLACK') for r in fill_judged)})
    return output


def evaluate(rows, per_page):
    summaries = {}; primary = None
    for threshold in (.35, .5, .75):
        matches = {}
        for song, heads in per_page.items():
            matches.update(match([r for r in rows if r['songNo'] == song], heads, threshold))
        judged = [{**r, 'match': matches.get(r['id'])} for r in rows]
        summaries[str(threshold)] = {label: strata(judged, keys) for label, keys in
                                     [('byShape', ['shape']), ('byShapeFill', ['shape','fill']),
                                      ('byPageShapeFill', ['songNo','shape','fill']), ('byStaff', ['windowId'])]}
        if threshold == .5: primary = judged
    return summaries, primary


def adjudicate(rows, cases, per_page):
    revised = {r['id']: dict(r) for r in rows}; assigned = set()
    for case in cases:
        key = case['observationId']
        if key not in revised or key in assigned or revised[key]['match'] is not None:
            raise ValueError('adjudication must name a distinct automatic unmatched observation')
        assigned.add(key); row = revised[key]; head = case['retainedHead']
        found = [h for h in per_page[row['songNo']] if h['id'] == head['id']]
        if found != [head]:
            raise ValueError('adjudicated head differs from retained graph')
        if any(r['songNo'] == row['songNo'] and r['match'] and r['match']['id'] == head['id'] for r in revised.values()):
            raise ValueError('adjudication would reuse an assigned head')
        row['match'] = head
    return list(revised.values())


def write_report(path, value):
    """Keep data rows one-per-line so a numeric evidence diff remains reviewable."""
    def encode(item, level=0):
        pad = '  ' * level; child = '  ' * (level+1)
        if isinstance(item, dict):
            return '{\n' + ',\n'.join(child + json.dumps(k) + ': ' + encode(v, level+1) for k,v in item.items()) + '\n' + pad + '}'
        if isinstance(item, list):
            return '[\n' + ',\n'.join(child + json.dumps(v, ensure_ascii=False) for v in item) + '\n' + pad + ']'
        return json.dumps(item, ensure_ascii=False)
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(encode(value) + '\n')


def analyze(work, output):
    design, annotations, rows = observations(work)
    if annotations.get('reviewStatus') != 'source-only-point-review-complete':
        raise ValueError('finish source-only annotation review before matching graph heads')
    if annotations.get('designSha256') != pilot.digest((work / 'design.json').read_bytes()):
        raise ValueError('annotation design drift')
    per_page = {}
    for song in sorted({r['songNo'] for r in rows}):
        sheet, _ = sheet_for(song); per_page[song] = heads_in_graph(sheet)
    summaries, primary = evaluate(rows, per_page)
    cases = pilot.load(work / 'adjudications.json')['cases']
    revised = adjudicate(primary, cases, per_page)
    result = {'schemaVersion': 1, 'audit': 'sh1991-head-shape-v1', 'designSha256': pilot.digest((work/'design.json').read_bytes()),
              'annotationSha256': pilot.digest((work/'annotations.json').read_bytes()),
              'analysisScriptSha256': pilot.digest(Path(__file__).read_bytes()),
              'sourceEnumerationRule': design['sampleRule'], 'reviewer': design['reviewer'],
              'annotationFrozenAt': annotations['frozenAt'], 'annotationMethod': annotations['method'],
              'centerRefinement': annotations.get('centerRefinement'),
              'scope': design['scope'], 'matching': design['matching'], 'confounding': design['confounding'],
              'sourceCertified': False, 'trainingEligible': False, 'causalEffectEstablished': False,
              'primaryThresholdInInterlines': .5, 'sensitivity': summaries,
              'postMatchVisualAdjudications': cases,
              'adjudicatedSummary': {'byShape': strata(revised, ['shape']), 'byShapeFill': strata(revised, ['shape','fill'])},
              'sourcePointers': [{'windowId':w['id'], 'songNo':w['songNo'], 'staffId':w['staffId'],
                                  'cropBox':w['cropBox'], 'sourceUrl':w['sourceImage']['url'],
                                  'sourceSha256':w['sourceImage']['sha256'], 'layoutSha256':w['layoutSha256']} for w in design['selections']],
              'observations': primary}
    write_report(output, result)
    print('Wrote', output)
    for row in summaries['0.5']['byShapeFill']: print(row)


def replay(path):
    """Recheck graph/source hashes and recompute every match/count from saved labels."""
    report = pilot.load(path); pages = {}; expected = {}
    dataset = pilot.load(pilot.DEFAULT_WORK / 'dataset.json')
    for pointer in report['sourcePointers']:
        song = pointer['songNo']
        pair = (pointer['sourceSha256'], pointer['layoutSha256'])
        if song in expected and expected[song] != pair:
            raise ValueError('inconsistent source pointers')
        expected[song] = pair
    for song, (source_sha, layout_sha) in expected.items():
        row = next(r for r in dataset['records'] if r['songNo'] == song)
        if pilot.digest((pilot.ROOT / row['image']['path']).read_bytes()) != source_sha:
            raise ValueError('source image drift')
        sheet, sha = sheet_for(song)
        if sha != layout_sha: raise ValueError('retained graph drift')
        pages[song] = heads_in_graph(sheet)
    rows = [{k:v for k,v in r.items() if k != 'match'} for r in report['observations']]
    summaries, primary = evaluate(rows, pages)
    if summaries != report['sensitivity'] or primary != report['observations']:
        raise ValueError('automatic analysis differs from report')
    revised = adjudicate(primary, report['postMatchVisualAdjudications'], pages)
    if report['adjudicatedSummary'] != {'byShape': strata(revised,['shape']), 'byShapeFill': strata(revised,['shape','fill'])}:
        raise ValueError('adjudicated summary differs from report')
    print('Verified source/graph hashes and replayed',len(rows),'observations, three matching radii, and explicit adjudications. Literal labels still require independent source review.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['render', 'analyze', 'replay'])
    parser.add_argument('--work', type=Path, default=DEFAULT_WORK)
    parser.add_argument('--output', type=Path, default=pilot.ROOT / 'docs/experiments/sh1991-head-shape-audit-20261015.json')
    parser.add_argument('--report', type=Path, default=pilot.ROOT / 'docs/experiments/sh1991-head-shape-audit-20261015.json')
    args = parser.parse_args()
    if args.command == 'render': render(args.work)
    elif args.command == 'analyze': analyze(args.work, args.output)
    else: replay(args.report)
