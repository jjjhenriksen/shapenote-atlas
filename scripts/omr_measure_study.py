#!/usr/bin/env python3
"""Frozen measure/classification loop; prepare BEFORE inspecting reserved source.

Reuses original training labels and consumed development pages. Selects the next
originally ranked SH2025 source after Penn and 184, without an outcome-based
choice. Source observations stay local and provisional. No recognition rerun.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import omr_image_geometry as geometry
import omr_image_study as prior
import omr_measure_classifier as classifier
import omr_measure_worklist as worklist
import sh1991_agent_correction as archive
import sh1991_symbol_classifier as baseline

ROOT = prior.ROOT
WORK = ROOT/'work/model-pilot/sh1991-v1'
SELECTION = WORK/'accuracy-tracks-v1/sh2025-selection-final.json'
OUT = WORK/'measure-loop-v1'


def current_protocol():
    from PIL import __version__
    selection = prior.load(SELECTION)
    if [r['songNo'] for r in selection['eligible'][:3]] != ['501t', '184', '188']:
        raise ValueError('Original reserved selection order drift')
    selected = selection['eligible'][2]
    sources = list((ROOT/'work/source-images/2025').glob('188-*'))
    if len(sources) != 1:
        raise ValueError('Need exactly one preserved reserved source')
    inputs = [ROOT/p for p in baseline.INPUTS]
    inputs += [ROOT/r['path'] for r in prior.load(ROOT/baseline.INPUTS[1])['sourceImages'].values()]
    inputs += [WORK/'accuracy-tracks-v1/penn-symbol-observations-final.json',
               WORK/'image-transfer-v1/source-observations.json', SELECTION, sources[0]]
    for label_path in inputs[:]:
        if label_path.name == 'penn-symbol-observations-final.json':
            inputs.append(ROOT/prior.load(label_path)['source']['path'])
    inputs.append(ROOT/'work/source-images/2025/184-and-jesus-crucified-bb8d27f0da.jpg')
    inputs += [Path(m.__file__) for m in (classifier, classifier.ranking, worklist, baseline, archive, geometry, prior, worklist.alignment)]
    inputs.append(Path(__file__))
    return {'recipe': classifier.RECIPE, 'pillowVersion': __version__,
            'selected': selected, 'sourcePath': str(sources[0].relative_to(ROOT)),
            'sourceSha256': archive.digest(sources[0]),
            'scope': 'Opening system: first six pitched heads per staff, four staves (24); all internal boundaries.',
            'selectionRule': 'Third source in original hash-ranked eligible list; Penn and 184 consumed.',
            'sourceExposure': 'Generic archive recognition/metadata may exist. No earlier 188 XML opened as truth; new-to-this-run evaluation only.',
            'observer': 'Same-agent provisional source reading; not independent gold.',
            'boundaryTolerancePixels': 4, 'retuningAllowed': False,
            'inputsSha256': {str(p.relative_to(ROOT)): archive.digest(p) for p in sorted(set(inputs))}}


def check_protocol(out):
    protocol = current_protocol()
    frozen = prior.load(out/'protocol.json')
    if frozen != protocol:
        raise ValueError('Frozen inputs/code drift; retain old run and use a new protocol directory')
    return protocol


def load_targets(path, source, page):
    from PIL import Image
    labels = prior.load(path)
    if 'source' in labels:
        if archive.digest(source) != labels['source']['sha256']:
            raise ValueError('Source binding drift')
    elif archive.digest(source) != labels['sourceSha256']:
        raise ValueError('Source binding drift')
    with Image.open(source) as image:
        return [dict(r, songNo=page, pixels=classifier.crop(image, r['x'], r['y'], r['interline']))
                for r in labels['rows']]


def compare(rows, train, bank, permitted=None):
    predictions = []
    for row in rows:
        raw = baseline.nearest(row, train)['label']
        allowed = permitted is None or permitted[row['id']] is not None
        result = classifier.predict(row['pixels'], bank) if allowed else {
            'prediction': None, 'selectivePrediction': None, 'reason': 'measure-footprint-unresolved'}
        predictions.append({'id': row['id'], 'label': row['label'], 'baseline': raw, **result,
                            'spanIndex': permitted[row['id']] if permitted is not None else None})
    selective = [dict(r, prediction=r['selectivePrediction']) for r in predictions]
    return {'allProposals': classifier.metrics(predictions),
            'selective': classifier.metrics(selective), 'predictions': predictions}


def development(out):
    out = Path(out); check_protocol(out)
    target = out/'development.json'
    if target.exists():
        return prior.load(target)
    train = baseline.samples()
    folds = {}
    for page, fitting, testing in baseline.grouped_folds(train):
        folds[page] = compare(testing, fitting, classifier.fit(fitting))
    bank = classifier.fit(train)
    penn_path = WORK/'accuracy-tracks-v1/penn-symbol-observations-final.json'
    penn_source = ROOT/prior.load(penn_path)['source']['path']
    penn = load_targets(penn_path, penn_source, '501t')
    previous = WORK/'image-transfer-v1/source-observations.json'
    rows184 = load_targets(previous, ROOT/'work/source-images/2025/184-and-jesus-crucified-bb8d27f0da.jpg', '184')
    report = {'phase': 'consumed-development', 'pageBlocked': folds,
              'penn': compare(penn, train, bank), '184': compare(rows184, train, bank),
              'safeToPromote': False}
    check_protocol(out)
    archive.immutable(target, archive.json_bytes(report))
    return report


def transfer(out, labels_path):
    from PIL import Image
    out, labels_path = Path(out), Path(labels_path)
    protocol = check_protocol(out)
    labels = prior.load(labels_path)
    if labels['sourceSha256'] != protocol['sourceSha256']:
        raise ValueError('Reserved observations source mismatch')
    ids = {f'188-p{p}-n{n}' for p in range(1, 5) for n in range(1, 7)}
    if len(labels['rows']) != 24 or {r['id'] for r in labels['rows']} != ids:
        raise ValueError('Require all 24 predeclared targets exactly once')
    if any(r['label'] not in geometry.GLYPHS for r in labels['rows']):
        raise ValueError('Unresolved label; cannot invent source truth')
    if len(labels['bands']) != 4:
        raise ValueError('Require all four supplied staff bands')
    lock = {'protocolSha256': archive.digest(out/'protocol.json'), 'labelsSha256': archive.digest(labels_path)}
    archive.immutable(out/'inference-lock.json', archive.json_bytes(lock))
    target = out/'transfer.json'
    if target.exists():
        report = prior.load(target)
        if report['inferenceLockSha256'] != archive.digest(out/'inference-lock.json'):
            raise ValueError('Transfer report binding drift')
        return report
    train = baseline.samples()
    if protocol['sourceSha256'] in {r['sourceSha256'] for r in train}:
        raise ValueError('Reserved page leaked into training')
    source = ROOT/protocol['sourcePath']
    rows = load_targets(labels_path, source, '188')
    with Image.open(source) as image:
        bands = [geometry.checked_box(image, box) for box in labels['bands']]
        if any(bands[i][3] > bands[i+1][1] for i in range(3)):
            raise ValueError('Bands must be ordered and disjoint')
        grid = geometry.shared_bar_grid(image, bands)
    edges = [max(b[0] for b in bands), *[r['x'] for r in grid['proposals']], min(b[2] for b in bands)]
    permitted = {}
    for row in rows:
        staff = int(row['id'].split('-p')[1].split('-')[0])-1
        a, b, c, d = bands[staff]
        x, y, scale = row['x'], row['y'], row['interline']
        spans = [i for i, (left, right) in enumerate(zip(edges, edges[1:]))
                 if left <= x-.8*scale and x+.8*scale <= right
                 and b <= y-.65*scale and y+.65*scale <= d]
        permitted[row['id']] = spans[0] if len(spans) == 1 and grid['staffLattices'][staff]['status'] == 'proposal' else None
    report = {'inferenceLockSha256': archive.digest(out/'inference-lock.json'),
              'phase': 'reserved-source-first; consumed after this test',
              'symbols': compare(rows, train, classifier.fit(train), permitted),
              'grid': grid, 'measureAssignments': permitted,
              'boundaries': prior.match_boundaries(labels['internalBoundariesApproxX'],
                            [r['x'] for r in grid['proposals']], protocol['boundaryTolerancePixels']),
              'byClass': {label: sum(r['label'] == label for r in rows) for label in sorted({r['label'] for r in rows})},
              'independentSourceGold': False, 'recognizerChanged': False,
              'wholeScoresAccepted': 0, 'safeToPromote': False,
              'limits': ['24 supplied positive centers on one system, no detector recall/precision.',
                         'Same-agent provisional observations, not independently certified accuracy.',
                         'Oracle review-target counts are not measured human effort or an automatic error detector.',
                         'No pitch/rhythm, exported-event mapping, score repair or corpus admission.']}
    check_protocol(out)
    if archive.digest(labels_path) != lock['labelsSha256']:
        raise ValueError('Source observations changed during inference')
    archive.immutable(target, archive.json_bytes(report))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--development', action='store_true')
    mode.add_argument('--labels', type=Path)
    args = parser.parse_args()
    if args.prepare:
        archive.immutable(args.out/'protocol.json', archive.json_bytes(current_protocol()))
        print('Frozen protocol:', args.out/'protocol.json')
    elif args.development:
        report = development(args.out)
        print(json.dumps({k: ({page: r['allProposals'] for page, r in v.items()} if k == 'pageBlocked' else
                             {a: v[a] for a in ('allProposals', 'selective')})
                          for k, v in report.items() if k in ('pageBlocked', 'penn', '184')}, indent=2))
    else:
        report = transfer(args.out, args.labels)
        print(json.dumps({'symbols': {k: v for k, v in report['symbols'].items() if k != 'predictions'},
                          'boundaries': report['boundaries']}, indent=2))
