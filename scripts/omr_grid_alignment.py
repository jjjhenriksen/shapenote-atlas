#!/usr/bin/env python3
"""Connect image-grid proposals to saved Audiveris measure geometry.

Review-only segmentation, never a MusicXML index map or a score correction.
Requires supplied music-only bands in original source pixels; no rescaling,
deskew registration, source labels, or expected measure counts are inferred.
"""
from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET

import omr_image_geometry as geometry
import sh1991_agent_correction as archive

RECIPE = {'version': 2, 'boundaryTolerancePixels': 4,
          'matching': 'mutually unique within tolerance; collisions abstain',
          'nativeJoinTolerancePixels': 1,
          'coordinates': 'original-source-pixels; no registration transform',
          'scope': 'one supplied system; review-only clipped segmentation'}


def finite(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('Nonfinite source coordinate')
    return result


def saved_system(graph_path, image_path, image_size, sheet_number, system_id, bands):
    """Read the native stack layout, including special/duplicate display IDs."""
    if type(sheet_number) is not int or sheet_number < 1:
        raise ValueError('Require positive integer sheet number')
    with zipfile.ZipFile(graph_path) as saved:
        book = ET.fromstring(saved.read('book.xml'))
        sheets = [s for s in book.findall('sheet') if s.get('number') == str(sheet_number)]
        if len(sheets) != 1 or sheets[0].findtext('input/number') != '1':
            raise ValueError('Only an explicitly bound single-image input is supported')
        recorded = sheets[0].findtext('input/path')
        if not recorded or Path(recorded).resolve() != Path(image_path).resolve():
            raise ValueError('Saved graph input path differs from source; registration required')
        root = ET.fromstring(saved.read(f'sheet#{sheet_number}/sheet#{sheet_number}.xml'))
    picture = root.find('picture')
    if picture is None or (int(picture.get('width')), int(picture.get('height'))) != tuple(image_size):
        raise ValueError('Graph/source dimensions differ; registration required')
    systems = [s for s in root.findall('./page/system') if s.get('id') == str(system_id)]
    if len(systems) != 1:
        raise ValueError('Require exactly one saved system')
    system = systems[0]
    parts = system.findall('part')
    if len(parts) != len(bands) or len({p.get('id') for p in parts}) != len(parts):
        raise ValueError('Part/band coverage differs')
    for part, band in zip(parts, bands):
        staves = part.findall('staff')
        if len(staves) != 1:
            raise ValueError('Only one staff per part supported')
        staff = staves[0]
        lines = staff.findall('./lines/line')
        points = staff.findall('./lines/line/point')
        if len(lines) != 5 or not points:
            raise ValueError('Missing saved five-line staff geometry')
        ys = [finite(p.get('y')) for p in points]
        if not (band[1] <= min(ys) <= max(ys) < band[3]
                and finite(staff.get('left')) <= band[0] < band[2] <= finite(staff.get('right'))):
            raise ValueError('Bands do not localize saved staves in supplied order')
    stacks = []
    for index, stack in enumerate(system.findall('stack')):
        left, right = finite(stack.get('left')), finite(stack.get('right'))
        if not 0 <= left < right <= image_size[0]:
            raise ValueError('Invalid saved measure extent')
        if stacks and abs(left-stacks[-1]['right']) > RECIPE['nativeJoinTolerancePixels']:
            raise ValueError('Noncontiguous saved measure grid')
        stacks.append({'stackIndex': index, 'displayId': stack.get('id'),
                       'special': stack.get('special'), 'left': left, 'right': right})
    if not stacks or any(len(p.findall('measure')) != len(stacks) for p in parts):
        raise ValueError('Saved part/stack coverage differs')
    return stacks


def align(grid, stacks, bands, tolerance=4):
    """Retain many-to-many overlap instead of fabricating a one-to-one map."""
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError('Invalid boundary tolerance')
    left, right = max(b[0] for b in bands), min(b[2] for b in bands)
    if left >= right:
        raise ValueError('Staff bands have no common music region')
    findings = []
    for staff, lattice in enumerate(grid['staffLattices']):
        if lattice['status'] != 'proposal':
            findings.append({'kind': 'unresolved-staff-lattice', 'staff': staff})
    bars = [finite(row['x']) for row in grid['proposals'] if left < finite(row['x']) < right]
    if bars != sorted(set(bars)):
        raise ValueError('Image boundaries must be unique and ordered')
    draft = [s['right'] for s in stacks[:-1] if left < s['right'] < right]
    possibilities = [[j for j, x in enumerate(draft) if abs(x-bar) <= tolerance] for bar in bars]
    reverse = [[i for i, bar in enumerate(bars) if abs(x-bar) <= tolerance] for x in draft]
    pairs = [(i, js[0]) for i, js in enumerate(possibilities)
             if len(js) == 1 and len(reverse[js[0]]) == 1]
    for i, js in enumerate(possibilities):
        if not js:
            findings.append({'kind': 'image-boundary-missing-in-draft', 'x': bars[i]})
        elif len(js) != 1 or len(reverse[js[0]]) != 1:
            findings.append({'kind': 'ambiguous-boundary-match', 'x': bars[i],
                             'draftCandidates': [draft[j] for j in js]})
    for j, candidates in enumerate(reverse):
        if not candidates:
            findings.append({'kind': 'draft-boundary-without-image-consensus', 'x': draft[j]})
    # Snap only mutually unique matches, avoiding tiny overlap slivers. All raw
    # coordinates and unsupported marks remain in the image-grid evidence.
    snapped = {draft[j]: bars[i] for i, j in pairs}
    extents = []
    for index, stack in enumerate(stacks):
        # Native stack left/right joins can differ by a rounding pixel. Treat
        # each saved shared join once, retaining raw coordinates in draftStacks.
        a = stack['left']
        if index and abs(a-stacks[index-1]['right']) <= RECIPE['nativeJoinTolerancePixels']:
            a = stacks[index-1]['right']
        a, b = snapped.get(a, a), snapped.get(stack['right'], stack['right'])
        if a >= b:
            raise ValueError('Aligned draft extent collapsed; registration requires review')
        extents.append({'stackIndex': stack['stackIndex'], 'left': a, 'right': b})
    edges = [left, *bars, right]
    spans = []
    for i, (a, b) in enumerate(zip(edges, edges[1:])):
        ids = [s['stackIndex'] for s in extents if min(b, s['right']) > max(a, s['left'])]
        overlaps = [s for s in stacks if s['stackIndex'] in ids]
        spans.append({'spanIndex': i, 'left': a, 'right': b,
                      'edgeClipped': i in (0, len(edges)-2),
                      'draftStacks': [s['stackIndex'] for s in overlaps],
                      'specialDraftStacks': [s['stackIndex'] for s in overlaps if s['special']],
                      'cropBoxes': [[a, band[1], b, band[3]] for band in bands]})
    usage = Counter(index for row in spans for index in row['draftStacks'])
    for row in spans:
        ids = row['draftStacks']
        if row['specialDraftStacks']:
            status = 'special-stack-review'
        elif not ids:
            status = 'no-draft-coverage'
        elif len(ids) == 1:
            status = 'split-draft-measure-proposal' if usage[ids[0]] > 1 else 'one-to-one-proposal'
        else:
            status = 'complex-overlap-review' if any(usage[i] > 1 for i in ids) else 'merge-draft-measures-proposal'
        row['status'] = status
        if status != 'one-to-one-proposal':
            findings.append({'kind': status, 'spanIndex': row['spanIndex'], 'draftStacks': ids})
    if not bars:
        findings.append({'kind': 'no-internal-grid-evidence'})
    return {'imageGrid': grid, 'draftStacks': stacks, 'alignedDraftExtents': extents,
            'proposedSpans': spans,
            'boundaryComparison': {'image': len(bars), 'draft': len(draft), 'matched': len(pairs),
                                   'pairs': [[bars[i], draft[j]] for i, j in pairs]},
            'findings': findings, 'findingCounts': dict(Counter(f['kind'] for f in findings)),
            'status': 'review-required' if findings else 'geometry-consistent-proposal',
            'scope': 'Supplied music-only system region; first/last spans are clipped, not complete measures.',
            'measureMap': None, 'recognizerChanged': False, 'scoreChanged': False,
            'sourceCertified': False, 'safeToPromote': False}


def run(manifest_path, score_path, out):
    """Hash-bound optional audit stage; exact completed runs skip image work."""
    from PIL import Image
    manifest_path, score_path, out = map(Path, (manifest_path, score_path, out))
    manifest = json.loads(manifest_path.read_text())
    if manifest['coordinates'] != RECIPE['coordinates']:
        raise ValueError('Unsupported coordinate registration')
    paths = {'score': score_path, 'manifest': manifest_path}
    for name in ('source', 'graph', 'bands'):
        path = Path(manifest[name]['path'])
        paths[name] = path if path.is_absolute() else manifest_path.parent/path
    hashes = {name: archive.digest(path) for name, path in paths.items()}
    for name in ('source', 'graph', 'bands'):
        if hashes[name] != manifest[name]['sha256']:
            raise ValueError('Manifest input hash differs: '+name)
    if hashes['score'] != manifest['scoreSha256']:
        raise ValueError('Manifest score binding differs')
    bands = json.loads(paths['bands'].read_text())
    if bands['sourceSha256'] != hashes['source']:
        raise ValueError('Staff-band source binding differs')
    protocol = {'inputsSha256': hashes, 'recipe': RECIPE, 'geometryRecipe': geometry.RECIPE,
                'codeSha256': {Path(p).name: archive.digest(p)
                               for p in (__file__, geometry.__file__, archive.__file__)}}
    archive.immutable(out/'protocol.json', archive.json_bytes(protocol))
    result_path = out/'alignment.json'
    if result_path.exists():
        result = json.loads(result_path.read_text())
        if result['protocolSha256'] != archive.digest(out/'protocol.json'):
            raise ValueError('Alignment report binding differs')
        return result
    with Image.open(paths['source']) as image:
        boxes = [geometry.checked_box(image, b) for b in bands['bands']]
        if len(boxes) < 2 or any(boxes[i][3] > boxes[i+1][1] for i in range(len(boxes)-1)):
            raise ValueError('Require ordered, disjoint staff bands')
        stacks = saved_system(paths['graph'], paths['source'], image.size,
                              manifest['sheetNumber'], manifest['systemId'], boxes)
        grid = geometry.shared_bar_grid(image, boxes)
        result = align(grid, stacks, boxes, RECIPE['boundaryTolerancePixels'])
    if hashes != {name: archive.digest(path) for name, path in paths.items()}:
        raise ValueError('Alignment inputs changed during analysis')
    result.update(protocolSha256=archive.digest(out/'protocol.json'),
                  association='Caller hash-bound score/graph pair; no exported-note or musical correspondence inferred.')
    archive.immutable(result_path, archive.json_bytes(result))
    return result
