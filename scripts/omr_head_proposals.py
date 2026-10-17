#!/usr/bin/env python3
"""Image-only dense-core head proposals in supplied staff windows.

Research only. No source head centers, labels, expected counts, XML or graph
nodes enter detection. This deliberately targets filled heads, not open heads.
Staff/window localization is supplied; full-page detection is not measured.
"""
from __future__ import annotations

import math

import omr_image_geometry as geometry

RECIPE = {
    'version': 1, 'inkThreshold': 110,
    'coreInterlines': [.7, .6], 'minimumCoreCoverage': .9,
    'maximumResponseSpanInterlines': [1.5, 1.2],
    'mergeRadiusInterlines': .75,
    'classifierGate': 'selective square/filled only; expanded bank unchanged',
    'fusion': 'add-only; retain every native prediction; suppress proposals near native or earlier proposal',
    'scope': 'consumed SH2025/219 complete windows; development only',
    'sourceCertified': False, 'safeToPromote': False,
}


def components(mask):
    """Eight-connected response islands, deterministic row-major traversal."""
    import numpy as np
    remaining = set(zip(*np.nonzero(mask)))
    while remaining:
        start = min(remaining); remaining.remove(start)
        stack = [start]; group = []
        while stack:
            y, x = stack.pop(); group.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    neighbor = (y+dy, x+dx)
                    if neighbor in remaining:
                        remaining.remove(neighbor); stack.append(neighbor)
        yield group


def propose(image, windows):
    """Return all dense-core islands and explicit geometric vetoes.

    A threshold on the original grayscale rejects pale marks, not watermark
    removal. All operations are on an in-memory copy; source bytes stay intact.
    """
    import numpy as np
    if len({w['staff'] for w in windows}) != len(windows):
        raise ValueError('Duplicate staff window')
    boxes = [geometry.checked_box(image, w['box']) for w in windows]
    for i, (a, b, c, d) in enumerate(boxes):
        if any(max(a, e) < min(c, g) and max(b, f) < min(d, h)
               for e, f, g, h in boxes[:i]):
            raise ValueError('Overlapping staff windows')
    gray = image.convert('L'); proposals, rejected, lattices = [], [], []
    for window, box in zip(windows, boxes):
        staff = window['staff']; lattice = geometry.staff_lines(gray, box)
        lattices.append(dict(lattice, staff=staff))
        if lattice['status'] != 'proposal':
            continue  # Unavailable lattice: no invented spacing or truth fallback.
        spacing = lattice['interline']; a, b, c, d = box
        width, height = [max(1, round(v*spacing)) for v in RECIPE['coreInterlines']]
        ink = (np.asarray(gray.crop(box)) < RECIPE['inkThreshold']).astype(np.int64)
        if width > c-a or height > d-b:
            continue
        summed = np.pad(ink, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        counts = (summed[height:, width:] - summed[:-height, width:]
                  - summed[height:, :-width] + summed[:-height, :-width])
        response = counts >= RECIPE['minimumCoreCoverage']*width*height
        for index, island in enumerate(components(response)):
            ys, xs = zip(*island)
            span = [max(xs)-min(xs)+1, max(ys)-min(ys)+1]
            row = {'id': f'image:{staff}:{index}', 'staff': staff,
                   'x': float(a+(min(xs)+max(xs)+width-1)/2),
                   'y': float(b+(min(ys)+max(ys)+height-1)/2),
                   'interline': float(spacing), 'responsePixels': len(island),
                   'responseSpanPixels': list(map(int, span)),
                   'origin': 'image-dense-core'}
            if any(v > limit*spacing for v, limit in
                   zip(span, RECIPE['maximumResponseSpanInterlines'])):
                rejected.append(dict(row, reason='extended-ink-response'))
            else:
                proposals.append(row)
    return {'proposals': proposals, 'geometricVetoes': rejected, 'staffLattices': lattices}


def fuse(native, proposals):
    """Add proposals without moving/deleting native centers; no truth inputs.

    Stable input order breaks ties; all suppression decisions remain auditable.
    No chain merging: distance is always to an actual retained center.
    """
    rows = [dict(r) for r in native]; suppressed = []
    if len({r['id'] for r in [*native, *proposals]}) != len(native)+len(proposals):
        raise ValueError('Duplicate native/proposal ID')
    for r in [*native, *proposals]:
        if not all(math.isfinite(r[k]) for k in ('x', 'y')):
            raise ValueError('Nonfinite proposal center')
    for row in proposals:
        if not math.isfinite(row['interline']) or row['interline'] < 3:
            raise ValueError('Invalid proposal interline')
        nearby = [r for r in rows if r['staff'] == row['staff'] and
                  math.hypot(r['x']-row['x'], r['y']-row['y']) <=
                  RECIPE['mergeRadiusInterlines']*row['interline']]
        if nearby:
            suppressed.append(dict(row, suppressedBy=nearby[0]['id']))
        else:
            rows.append(dict(row))
    return rows, suppressed
