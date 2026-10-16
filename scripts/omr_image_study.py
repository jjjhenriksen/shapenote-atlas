#!/usr/bin/env python3
"""Development-only, read-only comparison of image-grounded OMR proposals.

Freeze inputs/code before running, keep raw examples local, reuse exact outputs
only when their protocol matches. Does NOT rerun recognition or edit scores.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import omr_image_geometry as geometry
import sh1991_symbol_classifier as baseline
import sh1991_agent_correction as archive

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT/'work/model-pilot/sh1991-v1/accuracy-tracks-v1'
DEFAULT_OUT = ROOT/'work/model-pilot/sh1991-v1/image-geometry-v2'
CONDITIONS = ['clean', 'staff-line', 'staff-space', 'stem-up', 'stem-down',
              'blur', 'skew', 'ink-spread', 'low-resolution']


def load(path):
    return json.loads(Path(path).read_text())


def compare_predictions(rows):
    """Keep denominator, abstentions, fixes and regressions explicit."""
    return {'samples': len(rows), 'baselineCorrect': sum(r['label'] == r['baseline'] for r in rows),
            'candidateCorrect': sum(r['label'] == r['prediction'] for r in rows),
            'abstained': sum(r['prediction'] is None for r in rows),
            'fixed': sum(r['baseline'] != r['label'] == r['prediction'] for r in rows),
            'regressed': sum(r['baseline'] == r['label'] != r['prediction'] for r in rows),
            'wrongProposals': sum(r['prediction'] is not None and r['prediction'] != r['label'] for r in rows)}


def render_bank(fonts):
    bank = []
    for name, path in fonts.items():
        for label, variants in geometry.GLYPHS.items():
            for i in range(len(variants)):
                try:
                    image = geometry.render_head(path, label, variant=i)
                except ValueError as error:
                    if str(error) != 'Missing or empty music-font glyph':
                        raise
                    continue
                bank.append({'id': f'{name}:{label}:{i}', 'label': label,
                             'pixels': geometry.note_crop(image, 32, 32, 12)})
        # A font with a missing literal class cannot enter the comparison.
    for name in fonts:
        available = {r['label'] for r in bank if r['id'].startswith(name+':')}
        if available != set(geometry.GLYPHS):
            raise ValueError('Music font lacks required literal classes: '+name)
    return bank


def add_features(rows, images):
    for row in rows:
        raw, masked = geometry.analysis_mask(images[row['songNo']], row['x'], row['y'], row['interline'])
        row['features'] = geometry.geometry_features(raw)
        row['maskedFeatures'] = geometry.geometry_features(masked)
        row['analysisPixels'] = masked


def fit_rows(rows, field):
    return [{'id': r['id'], 'label': r['label'], 'features': r[field]} for r in rows]


def geometry_arms(rows, train, baseline_predictions):
    output = {}
    for name, field in [('raw-contour', 'features'), ('staff-masked-contour', 'maskedFeatures')]:
        fitted = fit_rows(train, field)
        predictions = [{'id': r['id'], 'label': r['label'], 'baseline': baseline_predictions[r['id']],
                        **geometry.geometry_predict(r[field], fitted)} for r in rows]
        output[name] = {'summary': compare_predictions(predictions), 'predictions': predictions}
    return output


def source_study(fonts):
    from PIL import Image
    selection = load(ROOT/baseline.INPUTS[1])
    images = {song: Image.open(ROOT/src['path']).convert('L') for song, src in selection['sourceImages'].items()}
    rows = baseline.samples()
    add_features(rows, images)
    page_arms = {}
    for page, train, test in baseline.grouped_folds(rows):
        initial = {r['id']: baseline.nearest(r, train)['label'] for r in test}
        page_arms[page] = geometry_arms(test, train, initial)
    source = load(WORK/'penn-symbol-observations-final.json')
    image = Image.open(ROOT/source['source']['path']).convert('L')
    penn = [dict(r, songNo='penn') for r in source['rows']]
    add_features(penn, {'penn': image})
    for r in penn:
        box = [math.floor(r['x']-.8*r['interline']), math.floor(r['y']-.65*r['interline']),
               math.ceil(r['x']+.8*r['interline']), math.ceil(r['y']+.65*r['interline'])]
        r['pixels'] = image.crop(box).resize((24, 20), Image.Resampling.BILINEAR)
    initial = {r['id']: baseline.nearest(r, rows)['label'] for r in penn}
    penn_arms = geometry_arms(penn, rows, initial)
    bank = render_bank(fonts)
    rendered = [{'id': r['id'], 'label': r['label'], 'baseline': initial[r['id']],
                 **geometry.rank_rendered(r['analysisPixels'], bank)} for r in penn]
    penn_arms['local-render-back'] = {'summary': compare_predictions(rendered), 'predictions': rendered}
    return {'sh1991PageBlocked': page_arms, 'pennConsumedDevelopment': penn_arms}


def synthetic_study(fonts):
    """Train on clean font A, test font B with nuisance variation, then reverse."""
    from PIL import Image, ImageDraw
    folds = {}
    for test_name, test_font in fonts.items():
        train_fonts = {k: v for k, v in fonts.items() if k != test_name}
        bank = render_bank(train_fonts)
        training = [{'id': r['id'], 'label': r['label'],
                     'pixels': r['pixels'].resize((24, 20), Image.Resampling.BILINEAR),
                     'features': geometry.geometry_features(r['pixels'])} for r in bank]
        output = []
        contact = Image.new('L', (9*64, 10*64), 255)
        row_index = 0
        for label, variants in geometry.GLYPHS.items():
            for variant in range(len(variants)):
                try:
                    original = geometry.render_head(test_font, label, variant=variant)
                except ValueError as error:
                    if str(error) != 'Missing or empty music-font glyph':
                        raise
                    continue
                for column, condition in enumerate(CONDITIONS):
                    image = geometry.perturb_head(original, condition)
                    contact.paste(image, (column*64, row_index*64))
                    raw, masked = geometry.analysis_mask(image, 32, 32, 12)
                    initial = baseline.nearest({'pixels': raw.resize((24, 20), Image.Resampling.BILINEAR)}, training)['label']
                    prediction = geometry.geometry_predict(geometry.geometry_features(masked), training)['prediction']
                    render = geometry.rank_rendered(masked, bank)
                    output.append({'id': f'{test_name}:{label}:{variant}:{condition}', 'condition': condition,
                                   'label': label, 'baseline': initial, 'prediction': prediction,
                                   'renderPrediction': render['prediction']})
                row_index += 1
        render_rows = [dict(r, prediction=r['renderPrediction']) for r in output]
        # Matched non-head controls, not a detector false-positive-rate estimate.
        negatives = []
        for condition in CONDITIONS:
            blank = Image.new('L', (64, 64), 255)
            im = geometry.perturb_head(blank, condition)
            _, masked = geometry.analysis_mask(im, 32, 32, 12)
            negatives.append({'condition': condition, 'prediction': geometry.rank_rendered(masked, bank)['prediction']})
        folds[test_name] = {'summary': compare_predictions(output),
                            'renderSummary': compare_predictions(render_rows),
                            'byCondition': {c: compare_predictions([r for r in output if r['condition'] == c]) for c in CONDITIONS},
                            'renderByCondition': {c: compare_predictions([r for r in render_rows if r['condition'] == c]) for c in CONDITIONS},
                            'negativeControls': negatives, 'predictions': output, 'contact': contact}
    return folds


def match_boundaries(expected, predicted, tolerance):
    """Maximum one-to-one cardinality within tolerance, order-preserving in 1D."""
    expected = sorted(expected); predicted = sorted(predicted)
    i = j = 0; pairs = []
    while i < len(expected) and j < len(predicted):
        if predicted[j] < expected[i]-tolerance:
            j += 1
        elif predicted[j] > expected[i]+tolerance:
            i += 1
        else:
            pairs.append([expected[i], predicted[j]]); i += 1; j += 1
    return {'observedInternalBoundaries': len(expected), 'proposedInternalBoundaries': len(predicted),
            'matched': len(pairs), 'missed': len(expected)-len(pairs),
            'extra': len(predicted)-len(pairs), 'pairs': pairs, 'tolerancePixels': tolerance}


def bar_study(source_name):
    from PIL import Image
    source = load(WORK/source_name)
    im = Image.open(ROOT/source['source']['path']).convert('L')
    bands = []
    # Existing source crop bounds localize staffs; labels never enter detector.
    for part in range(4):
        boxes = [s['cropBox'] for s in source['segments'] if s['part'] == part]
        bands.append([min(b[0] for b in boxes), min(b[1] for b in boxes),
                      max(b[2] for b in boxes), max(b[3] for b in boxes)])
    result = geometry.shared_bar_grid(im, bands)
    expected = sorted(set(s['cropBox'][0] for s in source['segments'] if s['part'] == 0 and s['measure'] > 0))
    lattices = [r['interline'] for r in result['staffLattices'] if r['status'] == 'proposal']
    spacing = sum(lattices)/len(lattices) if lattices else 1
    # Exclude only closing double/final bars, not internal false positives.
    right = bands[0][2]-1.5*spacing
    predicted = [r['x'] for r in result['proposals'] if bands[0][0] < r['x'] < right]
    comparison = match_boundaries(expected, predicted, spacing)
    comparison['labelLimit'] = 'Approximate existing crop edges, not exact independently audited barline centers; one-interline tolerance.'
    return {'geometry': result, 'internalBoundaryComparison': comparison,
            'closingBarExclusionPixels': 1.5*spacing}


def protocol_inputs(fonts):
    paths = [ROOT/p for p in baseline.INPUTS]
    paths += [WORK/n for n in ('penn-symbol-observations-final.json', 'penn-source-development.json', '303-source-observations.json')]
    selection = load(ROOT/baseline.INPUTS[1])
    paths += [ROOT/r['path'] for r in selection['sourceImages'].values()]
    for name in ('penn-symbol-observations-final.json', '303-source-observations.json'):
        source = load(WORK/name)['source']; p = ROOT/source['path']
        if archive.digest(p) != source['sha256']:
            raise ValueError('Source image binding drift')
        paths.append(p)
    paths += [Path(geometry.__file__), Path(__file__), Path(baseline.__file__), Path(archive.__file__)]
    paths += list(fonts.values())
    return {str(p.relative_to(ROOT)): archive.digest(p) for p in sorted(set(paths))}


def run(output, fonts):
    from PIL import __version__ as pillow_version
    output = Path(output)
    protocol = {'recipe': geometry.RECIPE, 'conditions': CONDITIONS,
                'inputsSha256': protocol_inputs(fonts), 'pillowVersion': pillow_version,
                'fontGlyphInventory': [r['id'] for r in render_bank(fonts)],
                'missingGlyphPolicy': 'Skip unavailable alternate orientations; require all eight literal shape/fill classes per font.',
                'phase': 'consumed-development; no fresh holdout opened',
                'exploration': 'Penn shared-grid geometry inspected before final strict-majority recipe; no independent validation claim.',
                'recognitionRerun': False, 'sourceScoreWrites': False}
    archive.immutable(output/'protocol.json', archive.json_bytes(protocol))
    completed = output/'report.json'
    if completed.exists():
        report = load(completed)
        if report['protocolSha256'] != archive.digest(output/'protocol.json'):
            raise ValueError('Completed report binding drift')
        print(json.dumps({'status': 'reused-completed-report', 'report': str(completed)})); return report
    bars = {name: bar_study(name) for name in ('penn-source-development.json', '303-source-observations.json')}
    source = source_study(fonts)
    synthetic = synthetic_study(fonts)
    for name, fold in synthetic.items():
        fold.pop('contact').save(output/f'synthetic-{name}.png')
    # Recheck inputs to detect edits while analysis was running.
    if protocol_inputs(fonts) != protocol['inputsSha256']:
        raise ValueError('Inputs changed during experiment')
    report = {'schemaVersion': 1, 'protocolSha256': archive.digest(output/'protocol.json'),
              'barlines': bars, 'symbols': source, 'syntheticCrossFont': synthetic,
              'safeToPromote': False, 'recognizerChanged': False,
              'freshHeldoutAccuracy': None, 'wholeSongAccuracy': None,
              'limits': ['Consumed development source observations, not independently audited gold.',
                         'Geometry and render-back use source-supplied note centers; no detector recall.',
                         'Cross-staff grid uses supplied staff bands, not automatic page/system layout.',
                         'Barline comparison uses approximate existing crop edges and excludes closing bars.',
                         'Synthetic font transfer and negative controls are not real scan accuracy.',
                         'Render-back is registered local notehead matching, not full-score search.',
                         'No MusicXML edits, fresh recognition, corpus admission, or acceptance.']}
    archive.immutable(completed, archive.json_bytes(report))
    summary = summarize(report)
    archive.immutable(output/'summary.json', archive.json_bytes(summary))
    print(json.dumps(summary, indent=2)); return report


def summarize(report):
    folds = report['symbols']['sh1991PageBlocked']
    aggregated = {}
    for arm in ('raw-contour', 'staff-masked-contour'):
        aggregate = Counter()
        for page in folds.values():
            aggregate.update(page[arm]['summary'])
        aggregated[arm] = dict(aggregate)
    return {'protocolSha256': report['protocolSha256'],
            'barlines': {name: {k: v for k, v in row['internalBoundaryComparison'].items() if k != 'pairs'} for name, row in report['barlines'].items()},
            'sh1991PageBlocked': aggregated,
            'pennConsumedDevelopment': {k: r['summary'] for k, r in report['symbols']['pennConsumedDevelopment'].items()},
            'syntheticCrossFont': {k: {key: row[key] for key in ('summary', 'renderSummary', 'byCondition', 'renderByCondition', 'negativeControls')} for k, row in report['syntheticCrossFont'].items()},
            'safeToPromote': False, 'recognizerChanged': False,
            'freshHeldoutAccuracy': None, 'wholeSongAccuracy': None, 'limits': report['limits']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--font-dir', type=Path, default=ROOT/'work/model-pilot/sh1991-v1/toolchain/audiveris-source/app/res')
    args = parser.parse_args()
    run(args.out, {name: args.font_dir/f'{name}.otf' for name in ('Bravura', 'Leland')})
