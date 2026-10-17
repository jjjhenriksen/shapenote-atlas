#!/usr/bin/env python3
"""Experimental bar proposals with ink evidence near BOTH staff terminals.

Raw candidates and rejected evidence are retained. This can reject aligned short
stems; it does not prove that a full-height vertical stroke is a barline.
"""
from __future__ import annotations

from statistics import median

import omr_image_geometry as geometry

RECIPE = {'version': 1, 'terminalInnerInterlines': .2,
          'terminalOuterInterlines': .65, 'minimumTerminalCoverage': .75,
          'consensus': 'same strict-majority denominator as raw grid; both terminals on the same column',
          'status': 'shadow-only; no repeat semantics or acceptance'}


def refine(image, raw):
    gray = image.convert('L'); pixels = gray.load()
    proposals, unresolved = [], []
    for row in sorted(raw['proposals']+raw['unresolved'], key=lambda r: r['x']):
        evidence = []
        for mark in row['evidence']:
            lattice = raw['staffLattices'][mark['staff']]
            top, bottom = lattice['lines'][0], lattice['lines'][-1]
            scale = lattice['interline']
            ends = [range(round(top+RECIPE['terminalInnerInterlines']*scale),
                          round(top+RECIPE['terminalOuterInterlines']*scale)+1),
                    range(round(bottom-RECIPE['terminalOuterInterlines']*scale),
                          round(bottom-RECIPE['terminalInnerInterlines']*scale)+1)]
            if any(not rr or min(rr) < 0 or max(rr) >= gray.height for rr in ends):
                raise ValueError('Invalid terminal inspection region')
            # Original mark width is a contiguous integer column group.
            left = round(mark['x']-(mark['width']-1)/2)
            columns = range(left, left+mark['width'])
            if min(columns) < 0 or max(columns) >= gray.width:
                raise ValueError('Invalid bar column')
            choices = []
            for x in columns:
                scores = [sum(pixels[x, y] < geometry.RECIPE['inkThreshold'] for y in rr)/len(rr)
                          for rr in ends]
                choices.append((min(scores), x, scores))
            weakest, x, scores = max(choices, key=lambda r: (r[0], -r[1]))
            evidence.append({**mark, 'terminalColumn': x, 'terminalCoverage': scores,
                             'terminalSupported': weakest >= RECIPE['minimumTerminalCoverage']})
        supported = [m for m in evidence if m['terminalSupported']]
        result = {**row, 'rawX': row['x'], 'rawSupportStaves': row['supportStaves'],
                  'supportStaves': sorted(m['staff'] for m in supported), 'evidence': evidence}
        if len(supported) >= raw['minimumSupportStaves']:
            result['x'] = median(m['x'] for m in supported)
            proposals.append(result)
        else:
            result['reason'] = 'insufficient-both-terminal-staff-support'
            unresolved.append(result)
    return {'staffLattices': raw['staffLattices'], 'minimumSupportStaves': raw['minimumSupportStaves'],
            'proposals': proposals, 'unresolved': unresolved, 'rawGrid': raw,
            'acceptedMeasures': None, 'recognizerChanged': False, 'recipe': RECIPE}


def shared_bar_grid(image, bands):
    return refine(image, geometry.shared_bar_grid(image, bands))
