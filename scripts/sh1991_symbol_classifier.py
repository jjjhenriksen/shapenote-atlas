#!/usr/bin/env python3
"""Local 1-nearest-neighbor symbol prototype on provisional SOURCE labels.

Fixed recipe, no parameter search, no test-page use. Leave-one-PAGE-out
diagnostics keep nearby crops from leaking across folds. This classifies
source-centered crops, not detected objects; it cannot establish detector
recall or full-score accuracy. Pillow + standard library only.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path

import sh1991_agent_correction as archive

ROOT = archive.ROOT
INPUTS = ['docs/experiments/sh1991-head-shape-audit-20261015.json',
          'docs/experiments/sh1991-eval-review-selection-20261015.json',
          'docs/experiments/sh1991-eval-source-review-20261015.json']
RECIPE = {'model': '1-nearest-neighbor squared grayscale distance; ID tie-break',
          'cropHalfWidthInterlines': .8, 'cropHalfHeightInterlines': .65,
          'resize': [24, 20], 'resizeFilter': 'bilinear',
          'split': 'leave-one-source-page-out, no crop/random split',
          'parameterSearch': False, 'labels': 'provisional single-agent visual labels, not source-certified gold',
          'deployment': 'shadow-only; NEVER used to alter recognizer or scores in this study'}


def grouped_folds(rows):
    ids = [r['id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate source sample ID')
    hashes = {r['songNo']: r['sourceSha256'] for r in rows}
    if len(set(hashes.values())) != len(hashes):
        raise ValueError('Different page IDs share identical source bytes')
    for page in sorted(hashes):
        train = [r for r in rows if r['songNo'] != page]
        test = [r for r in rows if r['songNo'] == page]
        if not train or not test:
            raise ValueError('Need at least two source pages')
        yield page, train, test


def samples():
    from PIL import Image
    positive, selection, review = [json.loads((ROOT/p).read_text()) for p in INPUTS]
    if review['selectionSha256'] != archive.digest(ROOT/INPUTS[1]):
        raise ValueError('Negative review selection binding drift')
    chosen = {r['id']: r for r in selection['rows']}
    if set(chosen) != {r['id'] for r in review['rows']}:
        raise ValueError('Incomplete negative review')
    windows = {p['windowId']: p for p in positive['sourcePointers']}
    interlines = {r['windowId']: r['interline'] for r in positive['observations']}
    sources = selection['sourceImages']
    for page, source in sources.items():
        if archive.digest(ROOT/source['path']) != source['sha256']:
            raise ValueError('Training source image drift')
    rows = []
    for r in positive['observations']:
        if r['shape'] == 'unknown' or r['fill'] == 'unknown':
            raise ValueError('Unknown positive label must not become a class')
        if windows[r['windowId']]['sourceSha256'] != sources[r['songNo']]['sha256']:
            raise ValueError('Positive source binding drift')
        rows.append({k: r[k] for k in ('id', 'songNo', 'x', 'y', 'interline')}
                    | {'label': r['shape']+'/'+r['fill']})
    for label in review['rows']:
        if label['label'] != 'non_head':
            # The two true-head overlaps have no independent shape/fill label
            # and may duplicate a positive footprint; do not invent a label.
            continue
        r = chosen[label['id']]
        rows.append({k: r[k] for k in ('id', 'songNo', 'x', 'y')}
                    | {'interline': interlines[r['windowId']], 'label': 'non_head'})
    images = {page: Image.open(ROOT/s['path']).convert('L') for page, s in sources.items()}
    for r in rows:
        scale = r['interline']
        box = [math.floor(r['x']-.8*scale), math.floor(r['y']-.65*scale),
               math.ceil(r['x']+.8*scale), math.ceil(r['y']+.65*scale)]
        im = images[r['songNo']]
        if box[0] < 0 or box[1] < 0 or box[2] > im.width or box[3] > im.height:
            raise ValueError('Crop outside training source')
        r.update(cropBox=box, sourceSha256=sources[r['songNo']]['sha256'],
                 pixels=im.crop(box).resize(tuple(RECIPE['resize']), Image.Resampling.BILINEAR))
    return rows


def nearest(row, train):
    from PIL import ImageChops, ImageStat
    def distance(other):
        delta = ImageChops.difference(row['pixels'], other['pixels'])
        return ImageStat.Stat(delta).sum2[0], other['id']
    return min(train, key=distance)


def experiment(out):
    out = Path(out)
    lock = {'recipe': RECIPE, 'inputsSha256': {p: archive.digest(ROOT/p) for p in INPUTS},
            'runnerSha256': archive.digest(__file__), 'noSH2025OrHeldoutPages': True}
    # Freeze before extracting features, fitting exemplars or evaluating folds.
    archive.immutable(out/'protocol.json', archive.json_bytes(lock))
    archive.immutable(out/'runner.py', Path(__file__).read_bytes())
    rows = samples()
    folds, predictions = [], []
    for page, train, test in grouped_folds(rows):
        majority = sorted(Counter(r['label'] for r in train).items(), key=lambda v: (-v[1], v[0]))[0][0]
        known = {r['label'] for r in train}
        fold = {'page': page, 'train': len(train), 'test': len(test), 'correct': 0, 'majorityCorrect': 0,
                'unseenClassTestExamples': 0}
        for row in test:
            neighbor = nearest(row, train)
            fold['correct'] += neighbor['label'] == row['label']
            fold['majorityCorrect'] += majority == row['label']
            fold['unseenClassTestExamples'] += row['label'] not in known
            predictions.append({'id': row['id'], 'page': page, 'label': row['label'],
                                'prediction': neighbor['label'], 'neighborId': neighbor['id'],
                                'neighborPage': neighbor['songNo']})
        folds.append(fold)
    labels = sorted({r['label'] for r in rows})
    confusion = {a: {b: sum(r['label'] == a and r['prediction'] == b for r in predictions)
                     for b in labels} for a in labels}
    report = {'protocolSha256': archive.digest(out/'protocol.json'), 'sampleCount': len(rows),
              'pageCount': len(folds), 'byClass': dict(Counter(r['label'] for r in rows)),
              'correct': sum(r['correct'] for r in folds),
              'majorityCorrect': sum(r['majorityCorrect'] for r in folds),
              'folds': folds, 'confusion': confusion, 'predictions': predictions,
              'classifierAccuracyOnFreshPages': None, 'detectorAccuracy': None,
              'endToEndAccuracy': None, 'sourceCertified': False, 'safeToPromote': False,
              'limits': ['Only three consumed training pages; page-blocked diagnostics, not a fresh test.',
                         '19 error-directed non-head centers are not an unbiased negative population.',
                         'Source-centered crops assume localization; no new detector or engine integration.',
                         'Historical audit labels were NOT training-eligible certified gold; explicitly reused here only as provisional local research labels.']}
    archive.immutable(out/'report.json', archive.json_bytes(report))
    # Retain a concrete local fitted exemplar model; no pixels are published.
    model = {'protocolSha256': report['protocolSha256'], 'samples': []}
    for r in rows:
        model['samples'].append({k: v for k, v in r.items() if k != 'pixels'} |
                                {'pixels': list(r['pixels'].getdata())})
    archive.immutable(out/'model.json', archive.json_bytes(model))
    print(json.dumps({k: report[k] for k in ('sampleCount', 'pageCount', 'correct', 'majorityCorrect', 'folds')}))
    return report


def test_model(model_path, label_path, out):
    """One fixed cross-edition inference; never adds test exemplars to model."""
    from PIL import Image
    model_path, label_path, out = Path(model_path), Path(label_path), Path(out)
    model = json.loads(model_path.read_text())
    protocol_path = model_path.parent/'protocol.json'
    if model['protocolSha256'] != archive.digest(protocol_path):
        raise ValueError('Fitted model protocol drift')
    protocol = json.loads(protocol_path.read_text())
    if protocol['runnerSha256'] != archive.digest(__file__):
        raise ValueError('Frozen classifier code drift')
    if protocol['recipe'] != RECIPE:
        raise ValueError('Inference recipe differs from fitted model')
    labels = json.loads(label_path.read_text())
    source_path = ROOT/labels['source']['path']
    source_hash = archive.digest(source_path)
    if source_hash != labels['source']['sha256'] or source_hash in {s['sourceSha256'] for s in model['samples']}:
        raise ValueError('Test source drift or source-image training leakage')
    train = []
    for row in model['samples']:
        row = dict(row)
        row['pixels'] = Image.frombytes('L', tuple(RECIPE['resize']), bytes(row['pixels']))
        train.append(row)
    lock = {'modelSha256': archive.digest(model_path), 'labelsSha256': archive.digest(label_path),
            'sourceSha256': source_hash, 'runnerSha256': archive.digest(__file__),
            'recipe': RECIPE, 'noRefit': True}
    archive.immutable(out/'protocol.json', archive.json_bytes(lock))
    image = Image.open(source_path).convert('L')
    predictions = []
    seen = set()
    for label in labels['rows']:
        if label['id'] in seen:
            raise ValueError('Duplicate test symbol')
        seen.add(label['id'])
        x, y, scale = label['x'], label['y'], label['interline']
        box = [math.floor(x-.8*scale), math.floor(y-.65*scale),
               math.ceil(x+.8*scale), math.ceil(y+.65*scale)]
        if box[0] < 0 or box[1] < 0 or box[2] > image.width or box[3] > image.height:
            raise ValueError('Test crop outside source')
        row = {'pixels': image.crop(box).resize(tuple(RECIPE['resize']), Image.Resampling.BILINEAR)}
        predicted = nearest(row, train)
        predictions.append({'id': label['id'], 'label': label['label'], 'prediction': predicted['label'],
                            'neighborId': predicted['id'], 'cropBox': box})
    vocabulary = sorted({r['label'] for r in predictions} | {r['prediction'] for r in predictions})
    report = {'protocolSha256': archive.digest(out/'protocol.json'), 'samples': len(predictions),
              'correct': sum(r['label'] == r['prediction'] for r in predictions),
              'confusion': {a: {b: sum(r['label'] == a and r['prediction'] == b for r in predictions)
                               for b in vocabulary} for a in vocabulary}, 'predictions': predictions,
              'freshFit': False, 'sourceCertified': False, 'safeToPromote': False,
              'independentHumanGold': False, 'recognizerChanged': False,
              'limits': ['Single SH2025 scan; 48 source-centered positive noteheads, not all song symbols.',
                         'No SH2025 non-head negatives; cannot measure false-positive rate or detector recall.',
                         'Provisional same-agent source labels; prior generic OMR processing disclosed.']}
    archive.immutable(out/'report.json', archive.json_bytes(report))
    print(json.dumps({k: report[k] for k in ('samples', 'correct', 'recognizerChanged')}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--model', type=Path)
    parser.add_argument('--test-labels', type=Path)
    args = parser.parse_args()
    if args.model and args.test_labels:
        test_model(args.model, args.test_labels, args.out)
    elif args.model or args.test_labels:
        parser.error('--model and --test-labels must be supplied together')
    else:
        experiment(args.out)
