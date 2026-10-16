#!/usr/bin/env python3
"""Read-only image-grounded OMR proposals. Pillow is needed only for image work.

No MusicXML mutations or acceptance decisions. Source pixels are never saved
in tracked reports. Staff bands and note centers are supplied localization,
not detector recall. All thresholds are explicit, fixed development choices.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations
import math
from statistics import median

RECIPE = {
    'version': 1, 'inkThreshold': 170, 'staffRowCoverage': .40,
    'staffGapTolerance': .16, 'barColumnCoverage': .86,
    'barClusterInterlines': .35, 'barMinimumStaves': 2,
    'barConsensus': 'strict majority of all supplied staves',
    'cropHalfInterlines': [.8, .65], 'normalizedSize': [48, 40],
    'geometry': 'binary contour profiles + interior occupancy; 3-neighbor vote',
    'staffMask': 'long-run horizontal pixels only; preserve crossing vertical ink',
    'renderMaxDistance': .30, 'renderMinimumMargin': .025,
    'status': 'development-shadow-only; no score edits or source certification',
}


def checked_box(image, box):
    if len(box) != 4 or any(not math.isfinite(v) for v in box):
        raise ValueError('Invalid image box')
    a, b, c, d = map(int, box)
    if not (0 <= a < c <= image.width and 0 <= b < d <= image.height):
        raise ValueError('Image box outside source')
    return a, b, c, d


def runs(values):
    groups = []
    for value in sorted(set(values)):
        if not groups or value > groups[-1][-1] + 1:
            groups.append([value])
        else:
            groups[-1].append(value)
    return groups


def staff_lines(image, box):
    """Find a five-line lattice within a supplied one-staff band, or abstain."""
    a, b, c, d = checked_box(image, box)
    gray = image.convert('L'); pix = gray.load()
    rows = [y for y in range(b, d)
            if sum(pix[x, y] < RECIPE['inkThreshold'] for x in range(a, c))/(c-a)
            >= RECIPE['staffRowCoverage']]
    centers = [sum(group)/len(group) for group in runs(rows)]
    candidates = []
    for lines in combinations(centers, 5):
        gaps = [v-u for u, v in zip(lines, lines[1:])]; spacing = median(gaps)
        if spacing < 3:
            continue
        error = max(abs(g/spacing-1) for g in gaps)
        if error <= RECIPE['staffGapTolerance']:
            candidates.append((error, lines, spacing))
    if not candidates:
        return {'status': 'unresolved', 'reason': 'no-five-line-lattice'}
    candidates.sort()
    if len(candidates) > 1 and candidates[1][0]-candidates[0][0] < .02:
        return {'status': 'unresolved', 'reason': 'ambiguous-five-line-lattice'}
    error, lines, spacing = candidates[0]
    return {'status': 'proposal', 'lines': list(lines), 'interline': spacing,
            'maximumRelativeGapError': error}


def shared_bar_grid(image, bands):
    """Cross-staff bar proposals, with separate unsupported single-staff marks.

    No expected count, source bar labels, XML measures, or pitches are inputs.
    Aligned stems and brackets may still be false positives: evidence, not gold.
    """
    if len(bands) < 2:
        raise ValueError('Cross-staff evidence requires at least two staff bands')
    gray = image.convert('L'); pix = gray.load()
    lattices = [staff_lines(gray, band) for band in bands]
    marks = []
    for index, (band, lattice) in enumerate(zip(bands, lattices)):
        if lattice['status'] != 'proposal':
            continue
        a, _, c, _ = checked_box(image, band)
        top, bottom = map(round, (lattice['lines'][0], lattice['lines'][-1]))
        coverage = {}
        for x in range(a, c):
            coverage[x] = sum(pix[x, y] < RECIPE['inkThreshold']
                              for y in range(top, bottom+1))/(bottom-top+1)
        columns = [x for x, v in coverage.items() if v >= RECIPE['barColumnCoverage']]
        for group in runs(columns):
            # Thick double/final bars can span more than one ordinary bar.
            if len(group) > lattice['interline']:
                continue
            marks.append({'x': sum(group)/len(group), 'staff': index,
                          'coverage': max(coverage[x] for x in group),
                          'width': len(group), 'interline': lattice['interline']})
    spacing = median([l['interline'] for l in lattices if l['status'] == 'proposal']) if marks else 1
    clusters = []
    for mark in sorted(marks, key=lambda m: m['x']):
        # Complete-link range avoids transitive chains merging unrelated marks.
        if not clusters or mark['x']-clusters[-1][0]['x'] > spacing*RECIPE['barClusterInterlines']:
            clusters.append([mark])
        else:
            clusters[-1].append(mark)
    supported, unresolved = [], []
    required = max(RECIPE['barMinimumStaves'], len(bands)//2+1)
    for group in clusters:
        by_staff = {}
        for mark in group:
            if mark['staff'] not in by_staff or mark['coverage'] > by_staff[mark['staff']]['coverage']:
                by_staff[mark['staff']] = mark
        row = {'x': median([m['x'] for m in by_staff.values()]),
               'supportStaves': sorted(by_staff), 'evidence': list(by_staff.values())}
        (supported if len(by_staff) >= required else unresolved).append(row)
    return {'staffLattices': lattices, 'minimumSupportStaves': required,
            'proposals': supported, 'unresolved': unresolved,
            'acceptedMeasures': None, 'recognizerChanged': False}


def note_crop(image, x, y, interline):
    from PIL import Image
    if not math.isfinite(interline) or interline < 3:
        raise ValueError('Invalid staff interline')
    box = [math.floor(x-.8*interline), math.floor(y-.65*interline),
           math.ceil(x+.8*interline), math.ceil(y+.65*interline)]
    checked_box(image, box)
    return image.convert('L').crop(box).resize(tuple(RECIPE['normalizedSize']), Image.Resampling.BILINEAR)


def analysis_mask(image, x, y, interline):
    """Suppress only long horizontal runs in a COPY; retain original elsewhere.

    Staff removal is intentionally conservative and may leave residual lines.
    It is neither watermark removal nor a reconstructed source image.
    """
    from PIL import Image
    crop = note_crop(image, x, y, interline)
    size = tuple(RECIPE['normalizedSize'])
    box = [max(0, math.floor(x-2.5*interline)), math.floor(y-.65*interline),
           min(image.width, math.ceil(x+2.5*interline)), math.ceil(y+.65*interline)]
    checked_box(image, box)
    wide = image.convert('L').crop(box)
    pixels = wide.load(); radius = max(1, round(.12*interline))
    horizontal = set()
    for yy in range(wide.height):
        if sum(pixels[xx, yy] < RECIPE['inkThreshold'] for xx in range(wide.width))/wide.width >= .65:
            horizontal.add(yy)
    base = image.convert('L')
    original = base.crop((math.floor(x-.8*interline), box[1], math.ceil(x+.8*interline), box[3]))
    cleaned = original.copy(); src = original.load(); dst = cleaned.load()
    for yy in horizontal:
        for xx in range(cleaned.width):
            above = yy-radius; below = yy+radius
            crossing = (above >= 0 and below < cleaned.height
                        and src[xx, above] < RECIPE['inkThreshold']
                        and src[xx, below] < RECIPE['inkThreshold'])
            if not crossing:
                dst[xx, yy] = 255
    return crop, cleaned.resize(size, Image.Resampling.BILINEAR)


def geometry_features(crop):
    """Fixed-size outer contour (fill-insensitive) and interior density features."""
    from PIL import Image
    crop = crop.convert('L').resize((32, 24), Image.Resampling.BILINEAR)
    p = crop.load(); threshold = RECIPE['inkThreshold']
    # Exclude upper/lower stem extensions, retaining the head's central 80%.
    mask = [[int(p[x, y] < threshold) for x in range(32)] for y in range(3, 21)]
    features = []
    for row in mask:
        xs = [x for x, v in enumerate(row) if v]
        features.extend(([xs[0]/32, xs[-1]/32, (xs[-1]-xs[0]+1)/32] if xs else [1, 0, 0]))
    for x in range(2, 30, 2):
        ys = [y for y in range(18) if mask[y][x]]
        features.extend(([ys[0]/18, ys[-1]/18] if ys else [1, 0]))
    for by in range(0, 18, 6):
        for bx in range(0, 32, 8):
            features.append(sum(mask[y][x] for y in range(by, by+6)
                                for x in range(bx, bx+8))/48)
    return features


def geometry_predict(features, train):
    if not train:
        raise ValueError('Empty geometry training population')
    if any(len(row['features']) != len(features) for row in train):
        raise ValueError('Geometry feature dimensions differ')
    distances = sorted((sum((a-b)**2 for a, b in zip(features, row['features']))/len(features),
                        row['id'], row['label']) for row in train)
    weights = Counter()
    for distance, _, label in distances[:3]:
        weights[label] += 1/(.001+distance)
    label = min(weights, key=lambda k: (-weights[k], k))
    return {'prediction': label, 'neighbors': [r[1] for r in distances[:3]],
            'distance': distances[0][0]}


# SMuFL glyphs; triangle orientations are variants of the same literal class.
GLYPHS = {'round/open': [0xE0A3], 'round/filled': [0xE0A4],
          'square/open': [0xE0B8], 'square/filled': [0xE0B9],
          'diamond/open': [0xE0D9], 'diamond/filled': [0xE0DB],
          'triangle/open': [0xE0BF, 0xE0C8], 'triangle/filled': [0xE0C0, 0xE0C9]}


def render_head(font_path, label, interline=12, variant=0, size=(64, 64)):
    """Render actual music-font glyph, preserving native proportions."""
    from PIL import Image, ImageDraw, ImageFont
    if label not in GLYPHS:
        raise ValueError('Unsupported literal shape/fill label')
    scale = 4
    canvas = Image.new('L', (size[0]*scale, size[1]*scale), 255)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(font_path), round(4*interline*scale))
    char = chr(GLYPHS[label][variant % len(GLYPHS[label])])
    bounds = draw.textbbox((0, 0), char, font=font)
    if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
        raise ValueError('Missing or empty music-font glyph')
    draw.text(((canvas.width-bounds[2]-bounds[0])/2,
               (canvas.height-bounds[3]-bounds[1])/2), char, font=font, fill=0)
    return canvas.resize(size, Image.Resampling.LANCZOS)


def perturb_head(image, condition, interline=12):
    """Deterministic synthetic controls. Never called on a source scan."""
    from PIL import Image, ImageDraw, ImageFilter
    out = image.copy(); draw = ImageDraw.Draw(out); cx, cy = out.width/2, out.height/2
    if condition in ('staff-line', 'staff-space', 'stem-up', 'stem-down', 'blur', 'skew', 'ink-spread', 'low-resolution'):
        offset = interline/2 if condition == 'staff-space' else 0
        for i in range(-2, 3):
            y = round(cy+i*interline+offset)
            draw.line((0, y, out.width-1, y), fill=0, width=1)
    if condition in ('stem-up', 'stem-down'):
        direction = -1 if condition == 'stem-up' else 1
        x = round(cx+direction*.55*interline)
        draw.line((x, round(cy), x, round(cy+direction*2.8*interline)), fill=0)
    if condition == 'blur':
        out = out.filter(ImageFilter.GaussianBlur(.65))
    elif condition == 'skew':
        out = out.rotate(2, Image.Resampling.BICUBIC, fillcolor=255)
    elif condition == 'ink-spread':
        out = out.filter(ImageFilter.MinFilter(3))
    elif condition == 'low-resolution':
        out = out.resize((32, 32), Image.Resampling.BILINEAR).resize(out.size, Image.Resampling.BILINEAR)
    elif condition not in ('clean', 'staff-line', 'staff-space', 'stem-up', 'stem-down'):
        raise ValueError('Unknown synthetic condition')
    return out


def edge_points(crop):
    from PIL import Image
    im = crop.convert('L').resize((24, 20), Image.Resampling.BILINEAR)
    p = im.load(); points = set()
    for y in range(1, 19):
        for x in range(1, 23):
            if p[x, y] < RECIPE['inkThreshold'] and any(p[x+dx, y+dy] >= RECIPE['inkThreshold']
                                                     for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))):
                points.add((x, y))
    return points


def render_distance(observed, candidate):
    """Symmetric edge distance; penalizes missing AND extra marks."""
    a, b = edge_points(observed), edge_points(candidate)
    if not a or not b:
        return None
    # Bounded distance map avoids O(edges^2) per candidate on noisy crops.
    def directed(first, second):
        return sum(min(6, min(abs(x-u)+abs(y-v) for u, v in second))
                   for x, y in first)/(6*len(first))
    return (directed(a, b)+directed(b, a))/2


def rank_rendered(observed, candidates):
    """Rank supplied registered render crops; abstain if weak or ambiguous.

    Translation/scale registration belongs to the caller. This local scorer is
    not a full-page engraving alignment or an independent source observer.
    """
    scores = []
    seen = set()
    for candidate in candidates:
        if candidate['id'] in seen:
            raise ValueError('Duplicate rendered candidate ID')
        seen.add(candidate['id'])
        score = render_distance(observed, candidate['pixels'])
        if score is not None:
            scores.append({'id': candidate['id'], 'label': candidate['label'], 'distance': score})
    # Collapse font/orientation variants before calculating class ambiguity.
    by_label = {}
    for row in sorted(scores, key=lambda r: (r['distance'], r['id'])):
        by_label.setdefault(row['label'], row)
    ranked = list(by_label.values())
    if len(ranked) < 2:
        return {'prediction': None, 'reason': 'insufficient-nonempty-alternatives', 'ranking': ranked}
    margin = ranked[1]['distance']-ranked[0]['distance']
    accepted = (ranked[0]['distance'] <= RECIPE['renderMaxDistance']
                and margin >= RECIPE['renderMinimumMargin'])
    return {'prediction': ranked[0]['label'] if accepted else None,
            'reason': 'proposal' if accepted else 'weak-or-ambiguous-image-evidence',
            'margin': margin, 'ranking': ranked}
