#!/usr/bin/env python3
"""Label-blind max-cardinality/min-distance matching and detection accounting.

All source targets and all predicted centers in complete frozen windows stay in
their denominators. Spatial agreement is NOT an exported-note or musical proof.
"""
from __future__ import annotations

import math

RECIPE = {'version': 1, 'radiusInterlines': .5, 'sensitivityRadii': [.35, .5, .75],
          'matching': 'maximum cardinality, minimum summed Euclidean distance; no shape/fill in cost; frozen-window staff restriction',
          'distanceQuantization': 1000000,
          'scope': 'all native graph head centers in complete supplied source windows, not exported notes'}


def match(targets, predictions, radius=.5):
    """Successive shortest augmenting paths; reverse edges can reassign matches."""
    if not math.isfinite(radius) or radius < 0:
        raise ValueError('Invalid spatial radius')
    for rows in (targets, predictions):
        if len({r['id'] for r in rows}) != len(rows):
            raise ValueError('Duplicate localization ID')
        if any(not math.isfinite(float(r[k])) for r in rows for k in ('x', 'y')):
            raise ValueError('Nonfinite head center')
    if any(not math.isfinite(r['interline']) or r['interline'] <= 0 for r in targets):
        raise ValueError('Invalid source interline')
    n, m = len(targets), len(predictions)
    end = 1+n+m; graph = [[] for _ in range(end+1)]
    def edge(a, b, cost):
        forward = [b, 1, cost, len(graph[b])]
        backward = [a, 0, -cost, len(graph[a])]
        graph[a].append(forward); graph[b].append(backward)
        return forward
    links = []
    for i in range(n): edge(0, 1+i, 0)
    for j in range(m): edge(1+n+j, end, 0)
    for i, source in enumerate(targets):
        for j, prediction in enumerate(predictions):
            if source['staff'] != prediction['staff']:
                continue
            distance = math.hypot(source['x']-prediction['x'], source['y']-prediction['y'])/source['interline']
            if distance <= radius:
                link = edge(1+i, 1+n+j, round(distance*RECIPE['distanceQuantization']))
                links.append((i, j, distance, link))
    while True:
        distances = [math.inf]*len(graph); parents = [None]*len(graph); distances[0] = 0
        for _ in range(len(graph)-1):
            changed = False
            for a, neighbors in enumerate(graph):
                if math.isinf(distances[a]): continue
                for index, (b, capacity, cost, reverse) in enumerate(neighbors):
                    if capacity and distances[a]+cost < distances[b]:
                        distances[b] = distances[a]+cost; parents[b] = (a, index); changed = True
            if not changed: break
        if parents[end] is None: break
        b = end
        while b != 0:
            a, index = parents[b]; link = graph[a][index]
            link[1] -= 1; graph[b][link[3]][1] += 1; b = a
    return [{'sourceId': targets[i]['id'], 'predictionId': predictions[j]['id'],
             'distanceInInterlines': distance} for i, j, distance, link in links if link[1] == 0]


def summarize(targets, predictions, pairs, field='prediction'):
    source = {r['id']: r for r in targets}; output = {r['id']: r for r in predictions}
    if len({p['sourceId'] for p in pairs}) != len(pairs) or len({p['predictionId'] for p in pairs}) != len(pairs):
        raise ValueError('Matching is not one-to-one')
    correct = sum(source[p['sourceId']]['label'] == output[p['predictionId']].get(field)
                  for p in pairs if source[p['sourceId']]['label'] is not None)
    judged = sum(r['label'] is not None for r in targets)
    abstentions = sum(r.get(field) is None for r in predictions)
    return {'sourceHeads': len(targets), 'nativePredictions': len(predictions), 'matched': len(pairs),
            'missedSourceHeads': len(targets)-len(pairs), 'unmatchedPredictions': len(predictions)-len(pairs),
            'geometricRecall': len(pairs)/len(targets) if targets else None,
            'geometricPrecision': len(pairs)/len(predictions) if predictions else None,
            'knownLiteralTargets': judged, 'correctLiteralAtAutomaticCenters': correct,
            'correctLiteralPerKnownSourceHead': correct/judged if judged else None,
            'correctLiteralAmongMatchedKnown': correct/sum(source[p['sourceId']]['label'] is not None for p in pairs)
              if any(source[p['sourceId']]['label'] is not None for p in pairs) else None,
            'predictionAbstentions': abstentions, 'independentSourceGold': False,
            'exportedEventAccuracy': None, 'pitchRhythmAccuracy': None,
            'measuredHumanEdits': None, 'measuredHumanMinutes': None}
