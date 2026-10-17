#!/usr/bin/env python3
"""Generate a standalone, hash-bound cross-staff grid proposal from a scan.

Bands JSON: {"sourceSha256": "...", "bands": [[x0,y0,x1,y1], ...]}.
Choose music-only x bounds; clefs, meter and closing double bars are not ordinary
internal barlines. Supplied bands are localization, not autonomous layout.
Never edits an image, saved recognition, or MusicXML score.
"""
import argparse
import json
from pathlib import Path

import omr_image_geometry as geometry
import sh1991_agent_correction as archive


def run(image_path, bands_path, out):
    from PIL import Image
    image_path, bands_path, out = map(Path, (image_path, bands_path, out))
    bands = json.loads(bands_path.read_text())
    image_hash = archive.digest(image_path)
    if bands['sourceSha256'] != image_hash:
        raise ValueError('Staff-band source binding differs')
    protocol = {'sourceSha256': image_hash, 'bandsSha256': archive.digest(bands_path),
                'runnerSha256': archive.digest(__file__),
                'geometrySha256': archive.digest(geometry.__file__), 'recipe': geometry.RECIPE}
    archive.immutable(out/'protocol.json', archive.json_bytes(protocol))
    report_path = out/'grid.json'
    if report_path.exists():
        report = json.loads(report_path.read_text())
        if report['protocolSha256'] != archive.digest(out/'protocol.json'):
            raise ValueError('Grid result binding differs')
        return report
    with Image.open(image_path) as image:
        report = geometry.shared_bar_grid(image, bands['bands'])
    if archive.digest(image_path) != image_hash or archive.digest(bands_path) != protocol['bandsSha256']:
        raise ValueError('Grid input changed during analysis')
    report.update(protocolSha256=archive.digest(out/'protocol.json'),
                  sourceCertified=False, safeToPromote=False,
                  scope='internal-barline proposals from supplied music-only staff regions')
    archive.immutable(report_path, archive.json_bytes(report))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--bands', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = run(args.image, args.bands, args.out)
    print(json.dumps({'proposals': len(result['proposals']), 'unresolved': len(result['unresolved']),
                      'result': str(args.out/'grid.json'), 'safeToPromote': False}))
