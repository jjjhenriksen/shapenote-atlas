"""Engine-independent, source-point OMR diagnostics (not score certification).

Input predictions are spatially assigned upstream without using source labels.
Missing observations never silently become correct negatives or zero accuracy.
"""
from collections import Counter
from fractions import Fraction
import math


def ratio(numerator, denominator):
    if not 0 <= numerator <= denominator:
        raise ValueError('invalid ratio counts')
    return {'numerator': numerator, 'denominator': denominator,
            'value': numerator / denominator if denominator else None}


def threshold_check(numerator, denominator, minimum):
    """Compare counts exactly; an empty denominator is not a pass."""
    result = ratio(numerator, denominator)
    return {**result, 'minimum': str(minimum),
            'status': ('not_evaluable' if not denominator else
                       'pass' if Fraction(numerator, denominator) >= Fraction(str(minimum)) else 'fail')}


def summarize_points(points):
    """Report conditional and all-source denominators separately, by stratum.

    Each point: id, group, shape, fill, prediction (null or an engine-native
    label plus decoded fill and stage booleans). Native labels are NOT mapped
    to source shapes unless an engine actually distinguishes those shapes.
    """
    identities = set()
    for point in points:
        identity = (point['group'], point['id'])
        if identity in identities:
            raise ValueError('duplicate source identity')
        identities.add(identity)
        if point['fill'] not in ('filled', 'open', 'unknown'):
            raise ValueError('invalid source fill')
        prediction = point['prediction']
        if prediction is not None:
            if not prediction.get('nativeLabel') or prediction['fill'] not in ('filled', 'open', None):
                raise ValueError('invalid prediction')
            if any(value is not None and not isinstance(value, bool)
                   for value in prediction.get('stages', {}).values()):
                raise ValueError('stage state must be boolean or unavailable')
    strata = []
    keys = sorted({(p['group'], p['shape'], p['fill']) for p in points})
    for group, shape, fill in keys:
        selected = [p for p in points if (p['group'], p['shape'], p['fill']) == (group, shape, fill)]
        retained = [p for p in selected if p['prediction'] is not None]
        judged = [p for p in retained if fill != 'unknown' and p['prediction']['fill'] is not None]
        correct = sum(p['prediction']['fill'] == fill for p in judged)
        stages = sorted({s for p in retained for s in p['prediction'].get('stages', {})})
        strata.append({'group': group, 'shape': shape, 'fill': fill,
            'sourceHeads': len(selected), 'retained': ratio(len(retained), len(selected)),
            'fillCorrectAmongJudgedRetained': ratio(correct, len(judged)),
            'retainedWithCorrectFillAmongSource': ratio(correct, len(selected)) if fill != 'unknown' else None,
            'unjudgedRetainedFill': len(retained) - len(judged),
            'nativeLabelCounts': dict(sorted(Counter(p['prediction']['nativeLabel'] for p in retained).items())),
            'stages': {s: {'knownRetained': sum(p['prediction'].get('stages', {}).get(s) is not None for p in retained),
                'presentAmongSource': ratio(sum(p['prediction'].get('stages', {}).get(s) is True for p in retained), len(selected)),
                'unavailableRetained': sum(p['prediction'].get('stages', {}).get(s) is None for p in retained)} for s in stages},
            'missingSourceIds': [p['id'] for p in selected if p['prediction'] is None],
            'wrongFillSourceIds': [p['id'] for p in judged if p['prediction']['fill'] != fill]})
    return strata


def negative_diagnostic(counts_by_arm):
    """Do not infer discrimination improvement from an all-zero final set."""
    lengths = {len(v) for v in counts_by_arm.values()}
    if len(lengths) != 1 or not counts_by_arm:
        raise ValueError('negative cohorts must be identical in size')
    if any(not isinstance(n, int) or n < 0 for v in counts_by_arm.values() for n in v):
        raise ValueError('invalid retained negative count')
    size = next(iter(lengths))
    floor = bool(size) and all(not any(v) for v in counts_by_arm.values())
    return {'pointsPerArm': size, 'allArmsAtFinalDetectionFloor': floor,
            'finalReductionMeasurable': bool(size) and not floor,
            'populationPrecision': None,
            'reason': 'Error-directed point negatives do not supply a population precision denominator.'}


def paired_proposals(events):
    """Compare only observed pairs with same point, orientation, logged center,
    anchor and seed path. These are not forced source-center evaluations:
    templates can have different bounds/anchor offsets despite equal centers.
    """
    groups = {}
    for event in events:
        if any(not math.isfinite(event[k]) for k in ('x', 'y', 'distance')):
            raise ValueError('nonfinite proposal')
        shape = event['shape']
        if not shape.startswith('NOTEHEAD_FA_') or not shape.endswith(('_FILLED', '_VOID')):
            continue
        base, fill = shape.rsplit('_', 1)
        key = (event['pointId'], base, event['x'], event['y'], event['anchor'], event['seed'])
        # Duplicates are counted, not resolved by selecting a favorable distance.
        groups.setdefault(key, {}).setdefault(fill, []).append(event)
    points = {}
    for key, variants in sorted(groups.items()):
        row = points.setdefault(key[0], Counter())
        if set(variants) != {'FILLED', 'VOID'}:
            row['unpairedGroups'] += 1
            continue
        if any(len(v) != 1 for v in variants.values()):
            row['duplicateGroupsExcluded'] += 1
            continue
        filled, opened = variants['FILLED'][0], variants['VOID'][0]
        row['pairedGroups'] += 1
        row['filledLower'] += filled['distance'] < opened['distance']
        row['openLower'] += opened['distance'] < filled['distance']
        row['ties'] += filled['distance'] == opened['distance']
        row['bothAllowed'] += not filled['veto'] and not opened['veto']
    return {key: dict(value) for key, value in sorted(points.items())}
