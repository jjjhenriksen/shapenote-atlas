#!/usr/bin/env python3
"""Vectorized shadow scoring ablations on the unchanged real-exemplar bank.

NumPy is a research-only optional dependency. Raw SSD uses exact integer sums,
checked against the original Pillow implementation. Variants are collapsed by
exemplar before multi-exemplar class scoring; they never become extra votes.
"""
from __future__ import annotations

import omr_measure_classifier as previous

RECIPE = {'version': 1, 'baseRecipe': previous.RECIPE,
          'arms': ['raw-ssd', 'gradient-half', 'class-top3', 'contrast-normalized'],
          'gradientMix': .5, 'classTopK': 3,
          'contrastMinimumStd': 1., 'selectiveMinimumRelativeMargin': .08,
          'selection': 'No net all-target loss on any consumed cohort; maximize total correct, arm order breaks ties; otherwise retain raw-ssd.',
          'deployment': 'shadow-only; no new training source or score writes'}


def features(pixels):
    import numpy as np
    image = np.asarray(pixels, dtype=np.int32)
    gradient = np.concatenate((np.diff(image, axis=-1).reshape(-1),
                               np.diff(image, axis=-2).reshape(-1)))
    flat = image.reshape(-1)
    centered = flat-flat.mean()
    normalized = centered/max(RECIPE['contrastMinimumStd'], flat.std())
    return flat, gradient, normalized


def fit(rows):
    import numpy as np
    variants = previous.fit(rows)
    extracted = [features(r['pixels']) for r in variants]
    return {'rows': variants,
            'pixels': np.stack([r[0] for r in extracted]),
            'gradients': np.stack([r[1] for r in extracted]),
            'normalized': np.stack([r[2] for r in extracted])}


def rank(distances, bank, *, top_k=1):
    # Same tie-break as the predecessor, including exemplar and transform.
    by_class = {}
    for score, row in zip(distances, bank['rows']):
        key = (float(score), row['id'], row['scale'], *row['offset'])
        exemplars = by_class.setdefault(row['label'], {})
        if row['id'] not in exemplars or key < exemplars[row['id']][0]:
            exemplars[row['id']] = (key, row)
    classes = []
    for label, exemplars in by_class.items():
        ordered = sorted(exemplars.values(), key=lambda r: r[0])[:top_k]
        score = sum(r[0][0] for r in ordered)/len(ordered)
        classes.append((score, ordered[0][0][1:], label, ordered[0][1], len(ordered)))
    classes.sort()
    first = classes[0]
    margin = (classes[1][0]-first[0])/max(classes[1][0], 1e-12) if len(classes) > 1 else None
    return {'prediction': first[2],
            'selectivePrediction': first[2] if margin is not None and margin >= RECIPE['selectiveMinimumRelativeMargin'] else None,
            'relativeMargin': margin, 'neighborId': first[3]['id'],
            'scale': first[3]['scale'], 'offset': first[3]['offset'],
            'distance': first[0], 'distinctExemplarsScored': first[4]}


def predict(pixels, bank):
    import numpy as np
    if pixels.size != tuple(previous.RECIPE['size']):
        raise ValueError('Invalid query dimensions')
    query, gradient, normalized = features(pixels.convert('L').crop(previous.RECIPE['distanceBox']))
    def squared(matrix, vector):
        delta = matrix-vector
        return np.sum(delta*delta, axis=1, dtype=np.int64)/matrix.shape[1]
    raw = squared(bank['pixels'], query)
    grad = squared(bank['gradients'], gradient)
    contrast = np.mean((bank['normalized']-normalized)**2, axis=1)
    # Both raw and gradient normalization are label-independent fixed choices.
    mix = RECIPE['gradientMix']
    return {'raw-ssd': rank(raw, bank),
            'gradient-half': rank((1-mix)*raw/65025+mix*grad/260100, bank),
            'class-top3': rank(raw, bank, top_k=RECIPE['classTopK']),
            'contrast-normalized': rank(contrast, bank)}
