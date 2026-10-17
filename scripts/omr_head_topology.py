#!/usr/bin/env python3
"""Default-off image proposals: enclosed white regions and thick filled cores.

No source centers, counts, labels, native nodes or XML enter this detector.
Supplied windows remain a localization dependency. Topology is evidence, not
source certification: staff/bar cells, damaged outlines and text can confuse it.
Historical detector modules and their frozen protocols are never modified.
"""
from __future__ import annotations

import omr_head_proposals as dense

RECIPE = {
    'version': 1, 'inkThreshold': 110,
    'holeConnectivity': 4,
    'holeWidthInterlines': [.1, 1.25],
    'holeHeightInterlines': [.08, .95],
    'minimumHoleAreaInterlinesSquared': .04,
    'staffCellBoundaryToleranceInterlines': .2,
    'staffCellMinimumOccupancy': .75,
    'staffCellRequiresDistinctLines': True,
    'fragmentMinimumHorizontalOverlap': .5,
    'fragmentMaximumGapInterlines': .35,
    'mergedMaximumHeightInterlines': 1.15,
    'filledCentralWidthInterlines': .6,
    'filledCentralInkFraction': .65,
    'minimumFilledThicknessInterlines': .72,
    'classifier': 'unchanged 373-exemplar bank; no forced shape or fill',
    'gate': 'selective open labels for holes; selective square/filled for thick cores',
    'fusion': 'unchanged native-priority add-only; never move or relabel native',
    'sourceCertified': False, 'safeToPromote': False,
}


def white_components(mask):
    """Four-connected components so diagonal black outlines remain barriers."""
    import numpy as np
    seen = np.zeros(mask.shape, dtype=bool)
    height, width = mask.shape
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        seen[y, x] = True
        stack, group = [(int(y), int(x))], []
        while stack:
            y, x = stack.pop(); group.append((y, x))
            for v, u in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                if 0 <= v < height and 0 <= u < width and mask[v, u] and not seen[v, u]:
                    seen[v, u] = True; stack.append((v, u))
        yield group


def merge_fragments(holes, spacing):
    """Join hole halves bisected by a staff line; cap each resulting box."""
    groups = []
    for hole in sorted(holes, key=lambda h: (h['box'][1], h['box'][0])):
        a, b, c, d = hole['box']
        for group in groups:
            e, f, g, h = group['box']
            overlap = min(c, g)-max(a, e)
            if (overlap >= RECIPE['fragmentMinimumHorizontalOverlap']*min(c-a, g-e)
                    and 0 <= b-h <= RECIPE['fragmentMaximumGapInterlines']*spacing
                    and max(d, h)-min(b, f) <= RECIPE['mergedMaximumHeightInterlines']*spacing
                    and max(c, g)-min(a, e) <= RECIPE['holeWidthInterlines'][1]*spacing):
                group['box'] = [min(a, e), min(b, f), max(c, g), max(d, h)]
                group['holePixels'] += hole['holePixels']
                group['fragments'] += 1
                break
        else:
            groups.append(dict(hole, fragments=1))
    return groups


def filled_thickness(gray, row):
    """Longest central ink run around an automatic center; stems don't suffice."""
    import numpy as np
    import math
    x, y, spacing = row['x'], row['y'], row['interline']
    half = RECIPE['filledCentralWidthInterlines']/2*spacing
    box = (max(0, math.floor(x-half)), max(0, math.floor(y-.85*spacing)),
           min(gray.width, math.ceil(x+half)), min(gray.height, math.ceil(y+.85*spacing)))
    ink = np.asarray(gray.crop(box)) < RECIPE['inkThreshold']
    occupied = ink.mean(axis=1) >= RECIPE['filledCentralInkFraction']
    return max((len(g) for g in dense.geometry.runs(np.nonzero(occupied)[0])), default=0)/spacing


def propose(image, windows):
    import numpy as np
    baseline = dense.propose(image, windows)  # Validates windows before any crop.
    gray = image.convert('L')
    holes, vetoes, filled = [], [], []
    for row in baseline['proposals']:
        row = dict(row, centralThicknessInterlines=filled_thickness(gray, row))
        if row['centralThicknessInterlines'] >= RECIPE['minimumFilledThicknessInterlines']:
            filled.append(row)
        else:
            vetoes.append(dict(row, reason='thin-central-ink'))
    for window, lattice in zip(windows, baseline['staffLattices']):
        if lattice['status'] != 'proposal':
            continue
        a, b, c, d = dense.geometry.checked_box(image, window['box'])
        spacing = lattice['interline']; fragments = []
        for group in white_components(np.asarray(gray.crop((a, b, c, d))) >= RECIPE['inkThreshold']):
            ys, xs = zip(*group)
            left, top, right, bottom = min(xs), min(ys), max(xs)+1, max(ys)+1
            if left == 0 or top == 0 or right == c-a or bottom == d-b:
                continue  # An unbounded/background region is not a closed hole.
            width, height = right-left, bottom-top
            if (not RECIPE['holeWidthInterlines'][0]*spacing <= width <= RECIPE['holeWidthInterlines'][1]*spacing
                    or not RECIPE['holeHeightInterlines'][0]*spacing <= height <= RECIPE['holeHeightInterlines'][1]*spacing
                    or len(group) < RECIPE['minimumHoleAreaInterlinesSquared']*spacing**2):
                continue
            hole = {'box': [left+a, top+b, right+a, bottom+b], 'holePixels': len(group)}
            nearest = lambda y: min(range(5), key=lambda index: abs(y-lattice['lines'][index]))
            upper, lower = nearest(top+b), nearest(bottom+b-1)
            tolerance = RECIPE['staffCellBoundaryToleranceInterlines']*spacing
            if (upper != lower and abs(top+b-lattice['lines'][upper]) <= tolerance
                    and abs(bottom+b-1-lattice['lines'][lower]) <= tolerance
                    and len(group)/(width*height) >= RECIPE['staffCellMinimumOccupancy']):
                vetoes.append(dict(hole, staff=window['staff'], reason='rectangular-staff-cell'))
            else:
                fragments.append(hole)
        for index, group in enumerate(merge_fragments(fragments, spacing)):
            left, top, right, bottom = group['box']
            holes.append(dict(group, id=f"hole:{window['staff']}:{index}",
                              staff=window['staff'], x=(left+right-1)/2, y=(top+bottom-1)/2,
                              interline=spacing, origin='image-enclosed-white'))
    return {'filled': filled, 'holes': holes, 'vetoes': vetoes,
            'denseGeometricVetoes': baseline['geometricVetoes'],
            'staffLattices': baseline['staffLattices']}


def select(filled, holes):
    return ([r for r in filled if r.get('selectivePrediction') == 'square/filled']
            + [r for r in holes if (r.get('selectivePrediction') or '').endswith('/open')])
