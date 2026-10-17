"""Deterministic nearest-variant ranking shared by research crop backends.

Distance extraction stays with each backend. This module only collapses variants
by literal class and retains the winning exemplar/transform as a witness.
"""
from __future__ import annotations


def nearest_class(scored_rows, *, minimum_relative_margin):
    """Rank (distance, variant) pairs with the original recipe's tie-breaks."""
    classes = {}
    for distance, row in scored_rows:
        key = (float(distance), row['id'], row['scale'], *row['offset'])
        if row['label'] not in classes or key < classes[row['label']][0]:
            classes[row['label']] = (key, row)
    if not classes:
        raise ValueError('Cannot rank an empty exemplar bank')
    ranked = sorted((key, label, row) for label, (key, row) in classes.items())
    first = ranked[0]
    margin = ((ranked[1][0][0]-first[0][0])/max(ranked[1][0][0], 1)
              if len(ranked) > 1 else None)
    return {'prediction': first[1],
            'selectivePrediction': first[1] if margin is not None and margin >= minimum_relative_margin else None,
            'relativeMargin': margin, 'neighborId': first[2]['id'],
            'scale': first[2]['scale'], 'offset': first[2]['offset'],
            'distance': first[0][0]}
