#!/usr/bin/env python3
"""Metadata-assisted layout probe; preserves scan pixels, never edits noteheads."""
import argparse
from collections import Counter
from copy import deepcopy
import io
import math
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET

import sh1991_pilot as pilot

TRAIN_IDS = ['26', '83t', '68b', '72b', '89']
METHOD = 'audiveris-staff-geometry-full-width-4-interline-margin-v1'


def xml_root(data):
    if data[:2] == b'PK':
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            container = ET.fromstring(archive.read('META-INF/container.xml'))
            target = next(x.attrib['full-path'] for x in container.iter()
                          if x.tag.rsplit('}', 1)[-1] == 'rootfile')
            if archive.getinfo(target).file_size > 20_000_000:
                raise ValueError('oversized score XML')
            data = archive.read(target)
    root = ET.fromstring(data)
    for item in root.iter():
        item.tag = item.tag.rsplit('}', 1)[-1]
    return root


def single_part(data, index):
    root = xml_root(data)
    parts = root.findall('part')
    selected = parts[index].attrib['id']
    for part in parts:
        if part.attrib['id'] != selected:
            root.remove(part)
    listing = root.find('part-list')
    for child in list(listing):
        if child.tag != 'score-part' or child.attrib['id'] != selected:
            listing.remove(child)
    result = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    if pilot.score(result)['parts'] != [pilot.score(data)['parts'][index]]:
        raise ValueError('part extraction changed musical events')
    return result


def staff_bounds(sheet, width, height, part_count):
    picture = sheet.find('picture')
    if (int(picture.attrib['width']), int(picture.attrib['height'])) != (width, height):
        raise ValueError('layout coordinate frame differs from original')
    systems = []
    for system in sheet.findall('./page/system'):
        staves = []
        for staff in system.findall('./part/staff'):
            lines = staff.findall('lines/line')
            if len(lines) != 5:
                raise ValueError('expected five-line staff')
            points = [[float(p.attrib['y']) for p in line.findall('point')] for line in lines]
            if any(not values for values in points):
                raise ValueError('missing staff geometry')
            top, bottom = min(points[0]), max(points[-1])
            spacing = (sum(points[-1]) / len(points[-1]) - sum(points[0]) / len(points[0])) / 4
            if not 4 <= spacing <= 40 or bottom <= top:
                raise ValueError('invalid interline geometry')
            staves.append((top, bottom, spacing))
        staves.sort()
        if len(staves) != part_count:
            raise ValueError('staff count differs from supplied part-count metadata')
        systems.append(staves)
    if not systems:
        raise ValueError('no detected systems')
    flattened = [s for system in systems for s in system]
    if flattened != sorted(flattened):
        raise ValueError('overlapping or unordered systems')
    bounds = []
    for i, (top, bottom, spacing) in enumerate(flattened):
        upper = max(0, math.floor(top - 4 * spacing))
        lower = min(height, math.ceil(bottom + 4 * spacing))
        if i:
            upper = max(upper, math.ceil((flattened[i-1][1] + top) / 2))
        if i + 1 < len(flattened):
            lower = min(lower, math.floor((bottom + flattened[i+1][0]) / 2))
        if not upper < top < bottom < lower:
            raise ValueError('crop would clip staff')
        bounds.append([0, upper, width, lower])
    return [bounds[v::part_count] for v in range(part_count)]


def prepare(work, phase='train'):
    from PIL import Image, ImageDraw, __version__ as pillow_version
    dataset = pilot.load(work / 'dataset.json')
    rows = [r for r in dataset['records'] if r['songNo'] in TRAIN_IDS] if phase == 'train' else [r for r in dataset['records'] if r['split'] == 'test']
    if phase == 'test' and not pilot.load(work / 'staff-probe-train/decision.json')['passesTrainingRule']:
        raise ValueError('training rule failed: no held-out evaluation authorized by protocol')
    destination = work / ('staff-probe-' + phase)
    destination.mkdir(parents=True, exist_ok=True)
    manifest = destination / 'dataset.json'
    if manifest.exists():
        raise ValueError('probe already frozen; reuse existing manifest, do not overwrite')
    design = {'method': METHOD, 'frozenAt': pilot.now(), 'phase': phase,
              'parentDatasetSha256': pilot.digest((work / 'dataset.json').read_bytes()),
              'pageIds': [r['songNo'] for r in rows], 'pillowVersion': pillow_version,
              'geometry': 'raw Audiveris OMR staff detection; full x extent; vertical four-interline margins clamped at adjacent staff midpoints; 64 white pixels between systems',
              'pixelChanges': 'none within crops; RGB copy/paste only, no deskew, scale, threshold, staff removal, or head replacement',
              'metadataAssistance': 'reference part count and top-to-bottom part order; not fully autonomous transcription',
              'selectionRule': {'pitchRecallGainAtLeast': .02, 'durationRecallLossAtMost': .01, 'noFewerExportedPages': True},
              'heldOutRule': 'evaluate unchanged method on test only if train rule passes; no tuning on held-out results'}
    pilot.write(destination / 'design.json', design)
    records = []; provenance = []
    for row in rows:
        image_path = pilot.ROOT / row['image']['path']; label_path = pilot.ROOT / row['label']['path']
        if pilot.digest(image_path.read_bytes()) != row['image']['sha256'] or pilot.digest(label_path.read_bytes()) != row['label']['sha256']:
            raise ValueError('parent source drift')
        omrs = list((work / 'baseline' / row['songNo']).glob('*.omr'))
        if len(omrs) != 1:
            raise ValueError('expected one retained raw layout file')
        with zipfile.ZipFile(omrs[0]) as archive:
            sheet = ET.fromstring(archive.read('sheet#1/sheet#1.xml'))
        source = Image.open(image_path).convert('RGB')
        crops = staff_bounds(sheet, source.width, source.height, row['label']['parts'])
        overlay = source.copy(); draw = ImageDraw.Draw(overlay)
        for index, boxes in enumerate(crops):
            for box in boxes:
                draw.rectangle(box, outline=['red','blue','green','purple'][index % 4], width=3)
            height = sum(box[3] - box[1] for box in boxes) + 64 * (len(boxes) - 1)
            composite = Image.new('RGB', (source.width, height), 'white'); offset = 0
            for box in boxes:
                composite.paste(source.crop(box), (0, offset)); offset += box[3] - box[1] + 64
            name = row['songNo'] + '-p' + str(index + 1)
            image_out = destination / 'inputs' / (name + '.png'); image_out.parent.mkdir(exist_ok=True)
            composite.save(image_out)
            label_out = image_out.with_suffix('.musicxml'); label_out.write_bytes(single_part(label_path.read_bytes(), index))
            records.append({**deepcopy(row), 'songNo': name, 'parentSongNo': row['songNo'], 'partIndex': index,
                            'image': {'path': str(image_out.relative_to(pilot.ROOT)), 'sha256': pilot.digest(image_out.read_bytes()), 'width': source.width, 'height': height},
                            'label': {'path': str(label_out.relative_to(pilot.ROOT)), 'sha256': pilot.digest(label_out.read_bytes()), 'parts': 1},
                            'derivation': {'originalImageSha256': row['image']['sha256'], 'originalLabelSha256': row['label']['sha256'],
                                           'layoutSha256': pilot.digest(omrs[0].read_bytes()), 'cropBoxes': boxes, 'method': METHOD}})
        overlay.thumbnail((1100, 1100)); overlay.save(destination / (row['songNo'] + '-crop-overlay.png'))
        provenance.append({'songNo': row['songNo'], 'partCropBoxes': crops})
    pilot.write(manifest, {**dataset, 'records': records, 'parentDatasetSha256': design['parentDatasetSha256'],
                          'splits': {phase: len(records)}, 'derivation': design, 'safeToPromote': False})
    pilot.write(destination / 'crop-provenance.json', provenance)
    print(destination, len(rows), 'pages', len(records), 'part images')


def summarize(work, phase='train'):
    probe = work / ('staff-probe-' + phase)
    results = pilot.load(probe / 'baseline-results.json')
    dataset = pilot.load(probe / 'dataset.json')
    expected = {r['songNo'] for r in dataset['records']}
    if len(results['records']) != len(expected) or {r['songNo'] for r in results['records']} != expected:
        raise ValueError('incomplete or duplicate probe results; retain failed parts, not missing receipts')
    if results['datasetSha256'] != pilot.digest((probe / 'dataset.json').read_bytes()):
        raise ValueError('probe dataset drift')
    parents = {r['parentSongNo'] for r in dataset['records']}
    raw = [r for r in pilot.load(work / 'baseline-results.json')['records'] if r['songNo'] in parents]
    if len(raw) != len(parents) or {r['songNo'] for r in raw} != parents:
        raise ValueError('missing or duplicate raw comparator')
    raw_counts = Counter()
    for row in raw:
        if row.get('metrics'):
            raw_counts.update(row['metrics']['counts'])
        else:
            parent = next(r for r in pilot.load(work / 'dataset.json')['records'] if r['songNo'] == row['songNo'])
            parsed = pilot.score((pilot.ROOT / parent['label']['path']).read_bytes())
            raw_counts['referenceEvents'] += sum(len(p['events']) for p in parsed['parts'])
            raw_counts['referencePitched'] += sum(e['pitch'] is not None for p in parsed['parts'] for e in p['events'])
    candidate = results['summary']['all']
    full_pages = sum(all(r['status'] == 'exported' for r in results['records'] if r['songNo'].rsplit('-p', 1)[0] == parent) for parent in parents)
    raw_pitch = raw_counts['pitchMatches'] / raw_counts['referencePitched']
    raw_duration = raw_counts['durationMatches'] / raw_counts['referenceEvents']
    rule = pilot.load(probe / 'design.json')['selectionRule']
    decision = {'phase': phase, 'pages': len(parents), 'rawPitchRecall': raw_pitch,
                'probePitchRecall': candidate['candidatePitchRecall'], 'rawDurationRecall': raw_duration,
                'probeDurationRecall': candidate['candidateDurationRecall'], 'completeExportedPages': full_pages,
                'rawExportedPages': sum(r['status'] == 'exported' for r in raw),
                'probeCounts': candidate['counts'], 'rawCounts': dict(raw_counts),
                'candidateReferencesOnly': True, 'modelFineTuned': False}
    decision['passesTrainingRule'] = phase == 'train' and candidate['candidatePitchRecall'] >= raw_pitch + rule['pitchRecallGainAtLeast'] and candidate['candidateDurationRecall'] >= raw_duration - rule['durationRecallLossAtMost'] and full_pages >= decision['rawExportedPages']
    pilot.write(probe / 'decision.json', decision)
    print(decision)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'summarize'])
    parser.add_argument('--work', type=Path, default=pilot.DEFAULT_WORK)
    parser.add_argument('--phase', choices=['train', 'test'], default='train')
    args = parser.parse_args()
    (prepare if args.command == 'prepare' else summarize)(args.work, args.phase)
