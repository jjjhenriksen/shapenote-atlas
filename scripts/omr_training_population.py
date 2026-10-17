#!/usr/bin/env python3
"""Explicit provisional research populations, grouped by complete source page.

Uses consumed SH2025 labels only in NEW models. Never rewrites or silently
refits the earlier SH1991 model; no source-certified corpus admission.
"""
from __future__ import annotations

from collections import Counter

import omr_measure_study as prior

ROOT, WORK = prior.ROOT, prior.WORK
RECIPE = {'version': 1, 'classifier': prior.classifier.RECIPE,
          'populations': ['legacy', 'expanded', 'sh2025-only'],
          'sourceGroups': 'canonical edition/tune ID; whole source page held out',
          'selection': 'SH2025 target edition explicit; no net correct-target loss on any of four consumed SH2025 page-held-out cohorts, maximize total correct, listed order breaks ties; SH1991 keeps legacy.',
          'labels': 'same-agent provisional research labels, never certified gold'}


def modern_inputs():
    return [('501t', WORK/'accuracy-tracks-v1/penn-symbol-observations-final.json', ROOT/'work/source-images/2025/501t-penn-8a2061599c.jpg'),
            ('184', WORK/'image-transfer-v1/source-observations.json', ROOT/'work/source-images/2025/184-and-jesus-crucified-bb8d27f0da.jpg'),
            ('188', WORK/'measure-loop-v1/source-observations.json', ROOT/'work/source-images/2025/188-ephesus-aa1817a576.jpg'),
            ('80t', WORK/'terminal-loop-v2/source-observations.json', ROOT/'work/source-images/2025/80t-troubles-over-604fc47469.jpg')]


def validate(rows):
    if not rows or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Empty or duplicate research sample IDs')
    groups = {}
    for row in rows:
        if row['label'] not in prior.geometry.GLYPHS and row['label'] != 'non_head':
            raise ValueError('Unresolved truth cannot enter a fitted exemplar bank')
        groups.setdefault(row['group'], set()).add(row['sourceSha256'])
    if any(len(hashes) != 1 for hashes in groups.values()):
        raise ValueError('Group has multiple source hashes; supply a reviewed family grouping')
    hashes = [next(iter(h)) for h in groups.values()]
    if len(hashes) != len(set(hashes)):
        raise ValueError('Source bytes duplicated across page groups')


def samples():
    rows = [dict(r, group='SH1991/'+r['songNo'], edition='SH1991') for r in prior.baseline.samples()]
    for song, labels, image in modern_inputs():
        sha = prior.archive.digest(image)
        targets = prior.load_targets(labels, image, song)
        rows.extend(dict(r, group='SH2025/'+song, edition='SH2025', sourceSha256=sha,
                         observationPath=str(labels.relative_to(ROOT))) for r in targets)
    validate(rows)
    return rows


def population(rows, name, exclude=None):
    if name not in RECIPE['populations']:
        raise ValueError('Unknown training population')
    fitting = [r for r in rows if r['group'] != exclude and
               (name == 'expanded' or r['edition'] == ('SH1991' if name == 'legacy' else 'SH2025'))]
    validate(fitting)
    return fitting


def fit(rows):
    import numpy as np
    validate(rows)
    variants = prior.classifier.fit(rows)
    return {'variants': variants,
            'matrix': np.stack([np.asarray(r['pixels'], dtype=np.int32).reshape(-1) for r in variants]),
            'groupById': {r['id']: r['group'] for r in rows},
            'sourceHashes': sorted({r['sourceSha256'] for r in rows}),
            'populationCounts': dict(Counter(r['group'] for r in rows))}


def predict(pixels, bank):
    import numpy as np
    if pixels.size != tuple(prior.classifier.RECIPE['size']):
        raise ValueError('Invalid automatic/query crop size')
    query = np.asarray(pixels.convert('L').crop(prior.classifier.RECIPE['distanceBox']), dtype=np.int32).reshape(-1)
    delta = bank['matrix']-query
    distances = np.sum(delta*delta, axis=1, dtype=np.int64)/len(query)
    classes = {}
    for distance, row in zip(distances, bank['variants']):
        key = (float(distance), row['id'], row['scale'], *row['offset'])
        if row['label'] not in classes or key < classes[row['label']][0]:
            classes[row['label']] = (key, row)
    ranked = sorted((key, label, row) for label, (key, row) in classes.items())
    first = ranked[0]
    margin = ((ranked[1][0][0]-first[0][0])/max(ranked[1][0][0], 1) if len(ranked) > 1 else None)
    return {'prediction': first[1],
            'selectivePrediction': first[1] if margin is not None and margin >= prior.classifier.RECIPE['selectiveMinimumRelativeMargin'] else None,
            'relativeMargin': margin, 'neighborId': first[2]['id'],
            'neighborGroup': bank['groupById'][first[2]['id']],
            'distance': first[0][0], 'scale': first[2]['scale'], 'offset': first[2]['offset']}
