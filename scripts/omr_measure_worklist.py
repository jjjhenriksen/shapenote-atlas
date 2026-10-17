#!/usr/bin/env python3
"""Assign native head boxes to image spans; ambiguity is a review task.

Output refers to native IDs, not exported MusicXML events. Crop footprints must
fit entirely inside one proposed staff/measure region. No score is rewritten.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET

import omr_grid_alignment as alignment
import omr_measure_classifier as classifier
import sh1991_agent_correction as archive


def assign(heads, spans, bands, staff_ids, lattices):
    if len(staff_ids) != len(set(staff_ids)) or len(staff_ids) != len(bands) or len(lattices) != len(bands):
        raise ValueError('Ambiguous staff registration')
    if len({h['id'] for h in heads}) != len(heads):
        raise ValueError('Duplicate native head ID')
    result = []
    for head in heads:
        row = dict(head, spanIndex=None, cropBox=None)
        if head['staffId'] not in staff_ids:
            row['status'] = 'unknown-staff-review'
            result.append(row); continue
        i = staff_ids.index(head['staffId']); band = bands[i]; lattice = lattices[i]
        x, y, w, h = head['bounds']
        if not all(alignment.finite(v) == v for v in (x, y, w, h)) or w <= 0 or h <= 0:
            raise ValueError('Invalid native head bounds')
        cx, cy = x+w/2, y+h/2
        if not band[0] <= cx < band[2] or not band[1] <= cy < band[3]:
            row['status'] = 'outside-supplied-region'
        elif lattice['status'] != 'proposal':
            row['status'] = 'unresolved-staff-lattice'
        else:
            interline = alignment.finite(lattice['interline'])
            # Full classifier footprint, not merely its center, must fit.
            box = [cx-.8*interline, cy-.65*interline, cx+.8*interline, cy+.65*interline]
            candidates = [s for s in spans if s['left'] <= min(x, box[0])
                          and max(x+w, box[2]) <= s['right']
                          and band[1] <= min(y, box[1]) and max(y+h, box[3]) <= band[3]]
            if len(candidates) != 1:
                row['status'] = 'boundary-or-band-crossing-review'
            else:
                span = candidates[0]
                row.update(spanIndex=span['spanIndex'], cropBox=box, x=cx, y=cy,
                           interline=interline, spanStatus=span['status'],
                           status='localized-proposal')
        result.append(row)
    return {'heads': result, 'counts': dict(Counter(r['status'] for r in result)),
            'nativeHeads': len(heads), 'measureMap': None, 'exportEventMap': None,
            'detectorRecall': None, 'sourceCertified': False, 'scoreChanged': False,
            'safeToPromote': False}


def native_heads(graph, sheet_number, system_id):
    with zipfile.ZipFile(graph) as z:
        root = ET.fromstring(z.read(f'sheet#{sheet_number}/sheet#{sheet_number}.xml'))
    system = root.find(f'./page/system[@id="{system_id}"]')
    if system is None:
        raise ValueError('Missing native system')
    ids = [part.find('staff').get('id') for part in system.findall('part')]
    heads = []
    for head in system.iter('head'):
        box = head.find('bounds')
        if box is None:
            raise ValueError('Native head lacks localization')
        heads.append({'id': head.get('id'), 'staffId': head.get('staff'),
                      'nativeShape': head.get('shape'),
                      'bounds': [alignment.finite(box.get(k)) for k in ('x', 'y', 'w', 'h')]})
    return ids, heads


def run(manifest_path, score_path, out, bank=None, model_binding=None):
    manifest_path, out = Path(manifest_path), Path(out)
    manifest = json.loads(manifest_path.read_text())
    # Existing adapter validates source path, dimensions, staff order and hashes.
    aligned = alignment.run(manifest_path, score_path, out/'grid')
    def path(name):
        p = Path(manifest[name]['path'])
        return p if p.is_absolute() else manifest_path.parent/p
    protocol = {'alignmentSha256': archive.digest(out/'grid/alignment.json'),
                'codeSha256': {Path(p).name: archive.digest(p)
                               for p in (__file__, classifier.__file__, classifier.ranking.__file__)},
                'modelBinding': model_binding, 'classifierRecipe': classifier.RECIPE,
                'classificationRequested': bank is not None}
    if bank is not None and not model_binding:
        raise ValueError('Classification requires frozen model binding')
    archive.immutable(out/'protocol.json', archive.json_bytes(protocol))
    target = out/'worklist.json'
    if target.exists():
        result = json.loads(target.read_text())
        if result['protocolSha256'] != archive.digest(out/'protocol.json'):
            raise ValueError('Worklist binding drift')
        return result
    staff_ids, heads = native_heads(path('graph'), manifest['sheetNumber'], manifest['systemId'])
    bands = json.loads(path('bands').read_text())['bands']
    result = assign(heads, aligned['proposedSpans'], bands, staff_ids, aligned['imageGrid']['staffLattices'])
    if bank is not None:
        from PIL import Image
        with Image.open(path('source')) as image:
            for row in result['heads']:
                if row['status'] == 'localized-proposal':
                    row['shadowClassification'] = classifier.predict(
                        classifier.crop(image, row['x'], row['y'], row['interline']), bank)
    for name in ('source', 'graph', 'bands'):
        if archive.digest(path(name)) != manifest[name]['sha256']:
            raise ValueError('Worklist input drift: '+name)
    result.update(protocolSha256=archive.digest(out/'protocol.json'),
                  association='Native boxes only; no source truth or exported event correspondence.',
                  sourceAccuracy=None, measuredHumanEdits=None, measuredHumanMinutes=None)
    archive.immutable(target, archive.json_bytes(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score', type=Path)
    parser.add_argument('--grid-manifest', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = run(args.grid_manifest, args.score, args.out)
    print(json.dumps({'nativeHeads': result['nativeHeads'], 'counts': result['counts']}))
