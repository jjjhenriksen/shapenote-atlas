#!/usr/bin/env python3
"""Shadow-only scale/position-tolerant crop classifier, never a pitch decoder.

Supplied centers remain a prerequisite. Training variants are not independent
examples. No labels enter the image transform or the distance calculation.
"""
from __future__ import annotations

import math

RECIPE = {'version': 1, 'size': [24, 20], 'scales': [.6, .75, .9, 1., 1.15, 1.3],
          'offsets': [-1, 0, 1], 'distanceBox': [2, 2, 22, 18],
          'selectiveMinimumRelativeMargin': .08,
          'distance': 'mean squared grayscale, best exemplar variant per literal class',
          'deployment': 'shadow-only; source centers supplied; no score writes'}


def crop(image, x, y, interline):
    from PIL import Image
    if not all(math.isfinite(v) for v in (x, y, interline)) or interline < 3:
        raise ValueError('Invalid note location/interline')
    box = [math.floor(x-.8*interline), math.floor(y-.65*interline),
           math.ceil(x+.8*interline), math.ceil(y+.65*interline)]
    if not (0 <= box[0] < box[2] <= image.width and 0 <= box[1] < box[3] <= image.height):
        raise ValueError('Note crop outside source')
    return image.convert('L').crop(box).resize(tuple(RECIPE['size']), Image.Resampling.BILINEAR)


def fit(rows):
    from PIL import Image
    if not rows or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Need nonempty, uniquely identified training examples')
    bank = []
    for row in rows:
        original = row['pixels'].convert('L')
        if original.size != tuple(RECIPE['size']):
            raise ValueError('Unexpected training crop size')
        for scale in RECIPE['scales']:
            w, h = [max(1, round(v*scale)) for v in original.size]
            resized = original.resize((w, h), Image.Resampling.BILINEAR)
            for dx in RECIPE['offsets']:
                for dy in RECIPE['offsets']:
                    canvas = Image.new('L', original.size, 255)
                    canvas.paste(resized, ((24-w)//2+dx, (20-h)//2+dy))
                    bank.append({'id': row['id'], 'label': row['label'],
                                 'scale': scale, 'offset': [dx, dy],
                                 'pixels': canvas.crop(RECIPE['distanceBox'])})
    return bank


def predict(pixels, bank):
    from PIL import ImageChops, ImageStat
    if pixels.size != tuple(RECIPE['size']) or not bank:
        raise ValueError('Invalid prediction crop or empty model')
    query = pixels.convert('L').crop(RECIPE['distanceBox'])
    classes = {}
    for row in bank:
        delta = ImageChops.difference(query, row['pixels'])
        distance = ImageStat.Stat(delta).sum2[0]/(query.width*query.height)
        key = (distance, row['id'], row['scale'], *row['offset'])
        if row['label'] not in classes or key < classes[row['label']][0]:
            classes[row['label']] = (key, row)
    ranked = sorted((key, label, row) for label, (key, row) in classes.items())
    first = ranked[0]
    margin = ((ranked[1][0][0]-first[0][0])/max(ranked[1][0][0], 1)
              if len(ranked) > 1 else None)
    # Ties and a single-class model provide no discriminative confidence.
    selected = (first[1] if margin is not None and margin >= RECIPE['selectiveMinimumRelativeMargin'] else None)
    return {'prediction': first[1], 'selectivePrediction': selected,
            'relativeMargin': margin, 'neighborId': first[2]['id'],
            'scale': first[2]['scale'], 'offset': first[2]['offset'],
            'distance': first[0][0]}


def metrics(rows):
    """All known targets remain in the denominator, including abstentions.

    Review targets are a retrospective oracle count, NOT measured human edits,
    minutes, or a claim that the system knows which wrong proposals to review.
    """
    ids = [r['id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate evaluation ID')
    total = len(rows)
    correct = sum(r['prediction'] == r['label'] for r in rows)
    proposed = sum(r['prediction'] is not None for r in rows)
    baseline_correct = sum(r['baseline'] == r['label'] for r in rows)
    return {'targets': total, 'baselineCorrect': baseline_correct,
            'correct': correct, 'wrongProposals': proposed-correct,
            'abstentions': total-proposed, 'proposed': proposed,
            'accuracyAllTargets': correct/total if total else None,
            'proposalCoverage': proposed/total if total else None,
            'accuracyAmongProposals': correct/proposed if proposed else None,
            'fixed': sum(r['baseline'] != r['label'] == r['prediction'] for r in rows),
            'regressed': sum(r['baseline'] == r['label'] != r['prediction'] for r in rows),
            'oracleReviewTargets': total-correct,
            'baselineOracleReviewTargets': total-baseline_correct,
            'measuredHumanEdits': None, 'measuredHumanMinutes': None,
            'endToEndAccuracy': None, 'detectorRecall': None}
