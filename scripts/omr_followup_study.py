#!/usr/bin/env python3
"""Consumed-page ablations, then a separately frozen next-source check.

The next original ranked page is 80t. Never view it before --freeze-transfer.
All previous sources, including Ephesus, are development for this iteration.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import omr_crop_scoring as scoring
import omr_terminal_grid as terminal
import omr_measure_study as prior

ROOT, WORK = prior.ROOT, prior.WORK
OUT = WORK/'terminal-loop-v1'


def protocol():
    import numpy
    from PIL import __version__ as pillow
    base = prior.current_protocol()
    eligible = prior.prior.load(prior.SELECTION)['eligible']
    if [r['songNo'] for r in eligible[:4]] != ['501t', '184', '188', '80t']:
        raise ValueError('Original ranked selection drift')
    sources = list((ROOT/'work/source-images/2025').glob('80t-*'))
    if len(sources) != 1:
        raise ValueError('Need exactly one retained 80t source')
    inputs = dict(base['inputsSha256'])
    paths = [Path(__file__), Path(scoring.__file__), Path(terminal.__file__),
             prior.OUT/'source-observations.json', prior.OUT/'development.json', prior.OUT/'transfer.json',
             WORK/'image-geometry-v2/postrun-source-review.json', sources[0]]
    paths += [WORK/f'image-geometry-v2/{name}-music-bands.json' for name in ('penn', '303')]
    for p in paths:
        inputs[str(p.relative_to(ROOT))] = prior.archive.digest(p)
    return {'classifierRecipe': scoring.RECIPE, 'terminalRecipe': terminal.RECIPE,
            'numpyVersion': numpy.__version__, 'pillowVersion': pillow,
            'selected': eligible[3], 'sourcePath': str(sources[0].relative_to(ROOT)),
            'sourceSha256': prior.archive.digest(sources[0]), 'inputsSha256': inputs,
            'scope': 'Opening-system internal boundaries; first 12 pitched heads per staff, or all if fewer, on each of four staves.',
            'observer': 'Same-agent provisional source observations, not independently audited gold.',
            'sourceExposure': 'Generic archive recognition/metadata may exist; no earlier 80t score/reference XML opened as truth in this run.',
            'selectionRule': 'Fourth originally hash-ranked eligible source; first three are consumed.',
            'retuningAfterSourceInspection': False, 'boundaryTolerancePixels': 4}


def check(out):
    current = protocol()
    if prior.prior.load(Path(out)/'development-protocol.json') != current:
        raise ValueError('Frozen code/input drift; use a new versioned directory')
    return current


def arms(rows, train):
    bank = scoring.fit(train)
    predictions = {name: [] for name in scoring.RECIPE['arms']}
    for row in rows:
        for name, result in scoring.predict(row['pixels'], bank).items():
            predictions[name].append({'id': row['id'], 'label': row['label'], **result})
    for index in range(len(rows)):
        baseline = predictions['raw-ssd'][index]['prediction']
        for values in predictions.values():
            values[index]['baseline'] = baseline
    return {name: {'metrics': prior.classifier.metrics(values),
                   'selective': prior.classifier.metrics([dict(r, prediction=r['selectivePrediction']) for r in values]),
                   'predictions': values} for name, values in predictions.items()}


def grid_study():
    from PIL import Image
    pages = prior.prior.load(WORK/'image-geometry-v2/postrun-source-review.json')['pages']
    for name, file, source in [
        ('184', WORK/'image-transfer-v1/source-observations.json', ROOT/'work/source-images/2025/184-and-jesus-crucified-bb8d27f0da.jpg'),
        ('188', prior.OUT/'source-observations.json', ROOT/prior.current_protocol()['sourcePath'])]:
        labels = prior.prior.load(file)
        pages[name] = {'source': {'path': str(source.relative_to(ROOT)), 'sha256': labels['sourceSha256']},
                       'bands': labels['bands'], 'internalBoundariesApproxX': labels['internalBoundariesApproxX']}
    results = {}
    for name, page in pages.items():
        source = ROOT/page['source']['path']
        if prior.archive.digest(source) != page['source']['sha256']:
            raise ValueError('Development grid source drift')
        bands = page.get('bands')
        if bands is None:
            bands = prior.prior.load(ROOT/page['bandsPath'])['bands']
        with Image.open(source) as image:
            refined = terminal.shared_bar_grid(image, bands)
        results[name] = {'raw': prior.prior.match_boundaries(page['internalBoundariesApproxX'],
                                [r['x'] for r in refined['rawGrid']['proposals']], 4),
                         'candidate': prior.prior.match_boundaries(page['internalBoundariesApproxX'],
                                [r['x'] for r in refined['proposals']], 4), 'grid': refined}
    return results


def develop(out):
    out = Path(out); check(out)
    target = out/'development.json'
    if target.exists():
        return prior.prior.load(target)
    train = prior.baseline.samples(); cohorts = {}
    for page, fitting, testing in prior.baseline.grouped_folds(train):
        cohorts['sh1991-'+page] = arms(testing, fitting)
    penn = WORK/'accuracy-tracks-v1/penn-symbol-observations-final.json'
    for name, path, source in [('penn', penn, ROOT/prior.prior.load(penn)['source']['path']),
                              ('184', WORK/'image-transfer-v1/source-observations.json', ROOT/'work/source-images/2025/184-and-jesus-crucified-bb8d27f0da.jpg'),
                              ('188', prior.OUT/'source-observations.json', ROOT/prior.current_protocol()['sourcePath'])]:
        cohorts[name] = arms(prior.load_targets(path, source, name), train)
    # Enforce exact reproduction of the predecessor's all-target outcomes.
    old = prior.prior.load(prior.OUT/'development.json')
    expected = {'sh1991-'+page: value['allProposals']['correct'] for page, value in old['pageBlocked'].items()}
    expected.update({name: old[name]['allProposals']['correct'] for name in ('penn', '184')})
    expected['188'] = prior.prior.load(prior.OUT/'transfer.json')['symbols']['allProposals']['correct']
    if any(cohorts[name]['raw-ssd']['metrics']['correct'] != value for name, value in expected.items()):
        raise ValueError('Raw integer kernel did not reproduce prior outcomes')
    eligible = [arm for arm in scoring.RECIPE['arms'] if all(
        cohort[arm]['metrics']['correct'] >= cohort['raw-ssd']['metrics']['correct'] for cohort in cohorts.values())]
    chosen = min(eligible, key=lambda arm: (-sum(c[arm]['metrics']['correct'] for c in cohorts.values()), scoring.RECIPE['arms'].index(arm)))
    report = {'protocolSha256': prior.archive.digest(out/'development-protocol.json'),
              'phase': 'all consumed development; 188 is not held out again',
              'cohorts': cohorts, 'eligibleArms': eligible, 'selectedArm': chosen,
              'rawKernelReproducesPriorCounts': True, 'grid': grid_study(),
              'safeToPromote': False}
    check(out)
    prior.archive.immutable(target, prior.archive.json_bytes(report))
    return report


def freeze(out):
    out = Path(out); current = check(out); dev = prior.prior.load(out/'development.json')
    if dev['protocolSha256'] != prior.archive.digest(out/'development-protocol.json'):
        raise ValueError('Development report protocol drift')
    frozen = {'developmentProtocolSha256': prior.archive.digest(out/'development-protocol.json'),
              'developmentReportSha256': prior.archive.digest(out/'development.json'),
              'selectedArm': dev['selectedArm'], 'reserved': current['selected'],
              'sourceSha256': current['sourceSha256'], 'scope': current['scope']}
    prior.archive.immutable(out/'transfer-protocol.json', prior.archive.json_bytes(frozen))
    return frozen


def transfer(out, labels_path):
    from PIL import Image
    out, labels_path = Path(out), Path(labels_path)
    current = check(out)
    if not (out/'transfer-protocol.json').exists():
        raise ValueError('Freeze selected arm BEFORE source observation')
    frozen = freeze(out)
    labels = prior.prior.load(labels_path)
    if labels['sourceSha256'] != current['sourceSha256']:
        raise ValueError('Reserved source binding drift')
    counts = labels['headCounts']; rows = labels['rows']
    if len(counts) != 4 or any(type(n) is not int or not 1 <= n <= 12 for n in counts):
        raise ValueError('Need first twelve or all available heads in each staff')
    expected = {f'80t-p{p+1}-n{n+1}' for p, count in enumerate(counts) for n in range(count)}
    if len(rows) != len(expected) or {r['id'] for r in rows} != expected or any(r['label'] not in prior.geometry.GLYPHS for r in rows):
        raise ValueError('Incomplete or unresolved reserved label set')
    lock = {'transferProtocolSha256': prior.archive.digest(out/'transfer-protocol.json'),
            'labelsSha256': prior.archive.digest(labels_path)}
    prior.archive.immutable(out/'inference-lock.json', prior.archive.json_bytes(lock))
    target = out/'transfer.json'
    if target.exists():
        report = prior.prior.load(target)
        if report['inferenceLockSha256'] != prior.archive.digest(out/'inference-lock.json'):
            raise ValueError('Reserved result binding drift')
        return report
    source = ROOT/current['sourcePath']; train = prior.baseline.samples()
    if current['sourceSha256'] in {r['sourceSha256'] for r in train}:
        raise ValueError('Training/source overlap')
    targets = prior.load_targets(labels_path, source, '80t')
    with Image.open(source) as image:
        bands = [prior.geometry.checked_box(image, b) for b in labels['bands']]
        if len(bands) != 4 or any(bands[i][3] > bands[i+1][1] for i in range(3)):
            raise ValueError('Require four ordered, disjoint bands')
        grid = terminal.shared_bar_grid(image, bands)
    bank = scoring.fit(train); selected, raw = [], []
    edges = [max(b[0] for b in bands), *[r['x'] for r in grid['proposals']], min(b[2] for b in bands)]
    for row in targets:
        result = scoring.predict(row['pixels'], bank)
        base = result['raw-ssd']['prediction']
        raw.append({'id': row['id'], 'label': row['label'], 'baseline': base, **result['raw-ssd']})
        staff = int(row['id'].split('-p')[1].split('-')[0])-1
        x, y, scale = row['x'], row['y'], row['interline']; band = bands[staff]
        spans = [i for i, (a, b) in enumerate(zip(edges, edges[1:])) if a <= x-.8*scale and x+.8*scale <= b
                 and band[1] <= y-.65*scale and y+.65*scale <= band[3]]
        allowed = len(spans) == 1 and grid['staffLattices'][staff]['status'] == 'proposal'
        prediction = result[frozen['selectedArm']] if allowed else {'prediction': None, 'selectivePrediction': None}
        selected.append({'id': row['id'], 'label': row['label'], 'baseline': base, **prediction,
                         'spanIndex': spans[0] if allowed else None})
    report = {'inferenceLockSha256': prior.archive.digest(out/'inference-lock.json'),
              'selectedArm': frozen['selectedArm'], 'phase': 'reserved-source-first; now consumed',
              'symbols': prior.classifier.metrics(selected),
              'selective': prior.classifier.metrics([dict(r, prediction=r['selectivePrediction']) for r in selected]),
              'ungatedRawClassifier': prior.classifier.metrics(raw), 'predictions': selected,
              'rawPredictions': raw, 'grid': grid,
              'boundaries': {name: prior.prior.match_boundaries(labels['internalBoundariesApproxX'],
                                 [r['x'] for r in g['proposals']], 4) for name, g in [('raw', grid['rawGrid']), ('candidate', grid)]},
              'byClass': {label: sum(r['label'] == label for r in rows) for label in sorted({r['label'] for r in rows})},
              'independentSourceGold': False, 'recognizerChanged': False,
              'safeToPromote': False, 'wholeScoresAccepted': 0}
    check(out)
    if prior.archive.digest(labels_path) != lock['labelsSha256']:
        raise ValueError('Observations changed during inference')
    prior.archive.immutable(target, prior.archive.json_bytes(report))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--development', action='store_true')
    mode.add_argument('--freeze-transfer', action='store_true')
    mode.add_argument('--labels', type=Path)
    args = parser.parse_args()
    if args.prepare:
        prior.archive.immutable(args.out/'development-protocol.json', prior.archive.json_bytes(protocol()))
        print('Development protocol frozen; reserved source NOT opened.')
    elif args.development:
        r = develop(args.out)
        print(json.dumps({'selectedArm': r['selectedArm'], 'eligibleArms': r['eligibleArms'],
                          'cohorts': {p: {a: v['metrics']['correct'] for a, v in c.items()} for p, c in r['cohorts'].items()},
                          'grid': {p: {a: g[a] for a in ('raw', 'candidate')} for p, g in r['grid'].items()}}, indent=2))
    elif args.freeze_transfer:
        print(json.dumps(freeze(args.out), indent=2))
    else:
        r = transfer(args.out, args.labels)
        print(json.dumps({k: r[k] for k in ('selectedArm', 'symbols', 'selective', 'boundaries', 'byClass')}, indent=2))
