#!/usr/bin/env python3
"""One source-first SH2025 transfer check after the development image study.

Preparation freezes code, training inputs, fonts, selection and source hash.
Then an observer records the first six heads in each opening-system staff and
internal barlines WITHOUT running predictions. Run locks those observations
before inference, makes no tuning changes, and reuses completed results.
"""
import argparse
import json
from pathlib import Path

import omr_image_geometry as geometry
import omr_image_study as study
import sh1991_symbol_classifier as baseline
import sh1991_agent_correction as archive

ROOT = study.ROOT
OUT = ROOT/'work/model-pilot/sh1991-v1/image-transfer-v2'
SOURCE = ROOT/'work/source-images/2025/184-and-jesus-crucified-bb8d27f0da.jpg'
SELECTION = study.WORK/'sh2025-selection-final.json'
FONTS = {name: ROOT/f'work/model-pilot/sh1991-v1/toolchain/audiveris-source/app/res/{name}.otf'
         for name in ('Bravura', 'Leland')}


def current_protocol():
    selection = study.load(SELECTION)
    selected = next(r for r in selection['eligible'] if r['songNo'] != '501t')
    if selected['songNo'] != '184':
        raise ValueError('Reserved next-song selection drift')
    inputs = study.protocol_inputs(FONTS)
    for path in [Path(__file__), SOURCE, SELECTION, ROOT/'scripts/omr_bar_grid.py']:
        inputs[str(path.relative_to(ROOT))] = archive.digest(path)
    return {'selection': selected, 'selectionRule': 'Next SHA256-ranked eligible SH2025 record after consumed Penn in original selection; no outcome-based choice.',
            'sourcePath': str(SOURCE.relative_to(ROOT)), 'sourceSha256': archive.digest(SOURCE),
            'scope': 'Opening system internal barlines and first six pitched heads per staff, all four staves; 24 source-centered positives.',
            'sourceExposure': 'Generic archive recognition and metadata already exist; no earlier 184 score/reference XML opened in this run. No pretraining or other-agent novelty claim.',
            'observer': 'Single agent; source-first frozen provisional labels, not independent certified gold.',
            'recipe': geometry.RECIPE, 'inputsSha256': inputs,
            'expectedSymbolSamples': 24, 'boundaryTolerancePixels': 4,
            'recognitionRerun': False, 'retuningAllowed': False}


def run(out, labels_path):
    from PIL import Image
    out = Path(out); labels_path = Path(labels_path)
    protocol = current_protocol()
    archive.immutable(out/'protocol.json', archive.json_bytes(protocol))
    labels = study.load(labels_path)
    if labels['sourceSha256'] != protocol['sourceSha256']:
        raise ValueError('Transfer label source binding differs')
    rows = labels['rows']
    expected_ids = {f'184-p{part}-n{note}' for part in range(1, 5) for note in range(1, 7)}
    if len(rows) != 24 or {r['id'] for r in rows} != expected_ids:
        raise ValueError('Require all predeclared 24 source-centered noteheads exactly once')
    if any(r['label'] not in geometry.GLYPHS for r in rows):
        raise ValueError('Unresolved literal labels; do not invent a truth class')
    frozen = {'protocolSha256': archive.digest(out/'protocol.json'), 'labelsSha256': archive.digest(labels_path)}
    archive.immutable(out/'inference-lock.json', archive.json_bytes(frozen))
    result_path = out/'report.json'
    if result_path.exists():
        result = study.load(result_path)
        if result['inferenceLockSha256'] != archive.digest(out/'inference-lock.json'):
            raise ValueError('Transfer report binding drift')
        return result
    train = baseline.samples()
    if protocol['sourceSha256'] in {r['sourceSha256'] for r in train}:
        raise ValueError('Transfer page is in training population')
    sources = study.load(ROOT/baseline.INPUTS[1])['sourceImages']
    images = {song: Image.open(ROOT/src['path']).convert('L') for song, src in sources.items()}
    study.add_features(train, images)
    image = Image.open(SOURCE).convert('L')
    test = [dict(r, songNo='184') for r in rows]
    study.add_features(test, {'184': image})
    # Use exact original crop recipe, not a second resize of new-arm pixels.
    import math
    for row in test:
        x, y, spacing = row['x'], row['y'], row['interline']
        box = [math.floor(x-.8*spacing), math.floor(y-.65*spacing),
               math.ceil(x+.8*spacing), math.ceil(y+.65*spacing)]
        row['pixels'] = image.crop(box).resize((24, 20), Image.Resampling.BILINEAR)
    initial = {r['id']: baseline.nearest(r, train)['label'] for r in test}
    arms = study.geometry_arms(test, train, initial)
    bank = study.render_bank(FONTS)
    rendered = [{'id': r['id'], 'label': r['label'], 'baseline': initial[r['id']],
                 **geometry.rank_rendered(r['analysisPixels'], bank)} for r in test]
    arms['local-render-back'] = {'summary': study.compare_predictions(rendered), 'predictions': rendered}
    bars = geometry.shared_bar_grid(image, labels['bands'])
    result = {'inferenceLockSha256': archive.digest(out/'inference-lock.json'),
              'symbols': arms, 'grid': bars,
              'boundaryComparison': study.match_boundaries(labels['internalBoundariesApproxX'],
                  [r['x'] for r in bars['proposals']], protocol['boundaryTolerancePixels']),
              'freshForThisRun': True, 'independentSourceGold': False,
              'wholeSongAccuracy': None, 'recognizerChanged': False, 'safeToPromote': False,
              'limits': ['Only one selected new-to-run source page, opening system and 24 positive crops.',
                         'Source localization supplied; detector recall and false-positive rate unmeasured.',
                         'Same-agent provisional observations; not independently audited source accuracy.',
                         'Frozen code but no full recognition/repair pipeline or whole-song acceptance.']}
    if current_protocol() != protocol or archive.digest(labels_path) != frozen['labelsSha256']:
        raise ValueError('Transfer inputs changed during analysis')
    archive.immutable(result_path, archive.json_bytes(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--labels', type=Path)
    args = parser.parse_args()
    if args.prepare:
        archive.immutable(args.out/'protocol.json', archive.json_bytes(current_protocol()))
        print('Frozen before source reading/predictions:', args.out/'protocol.json')
    elif args.labels:
        report = run(args.out, args.labels)
        print(json.dumps({'symbols': {k: r['summary'] for k, r in report['symbols'].items()},
                          'barlines': report['boundaryComparison'], 'safeToPromote': False}, indent=2))
    else:
        parser.error('Choose --prepare or --labels PATH')
