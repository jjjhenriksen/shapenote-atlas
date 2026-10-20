#!/usr/bin/env python3
"""Atlas consumer for bundle v1. Stage private research only; never publish."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = frozenset(('candidate.musicxml', 'candidate.mxl', 'report.json',
                   'resolved-reading.json', 'comparison.json'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def valid_hash(value, size=64):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{' + str(size) + '}', value)


def verify(directory, expected_manifest_sha256):
    """Independent stdlib-only consumer; no transcriber runtime imports."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('Bundle must be a real directory')
    names = {p.name for p in directory.iterdir()}
    if names != FILES | {'bundle.json'}:
        raise ValueError('Unexpected/missing bundle files')
    if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
        raise ValueError('Bundle symlinks/directories are not supported')
    raw = (directory / 'bundle.json').read_bytes()
    if not valid_hash(expected_manifest_sha256) or sha(raw) != expected_manifest_sha256:
        raise ValueError('Pinned bundle manifest hash mismatch')
    manifest = json.loads(raw)
    if (type(manifest.get('schemaVersion')) is not int or manifest['schemaVersion'] != 1
            or manifest.get('kind') != 'shapenote-transcription-bundle'
            or manifest.get('status') != 'research-candidate'):
        raise ValueError('Unsupported bundle version/kind/status')
    if any(manifest.get(k) is not False for k in ('sourceCertified', 'safeToPromote')):
        raise ValueError('Only unpromoted research bundles are supported')
    if set(manifest.get('files', {})) != FILES:
        raise ValueError('Unsupported payload paths')
    payload = {name: (directory / name).read_bytes() for name in FILES}
    for name, data in payload.items():
        if not valid_hash(manifest['files'][name]) or sha(data) != manifest['files'][name]:
            raise ValueError('Payload hash drift: ' + name)
    producer = manifest.get('producer', {})
    if (not isinstance(producer.get('repository'), str) or not producer['repository']
            or not valid_hash(producer.get('revision'), 40)
            or type(producer.get('dirty')) is not bool
            or not valid_hash(producer.get('exporterSha256'))):
        raise ValueError('Missing pinned producer provenance')
    report = json.loads(payload['report.json'])
    reading = json.loads(payload['resolved-reading.json'])
    comparison = json.loads(payload['comparison.json'])
    if (report.get('status') != 'assembled-research-candidate'
            or report.get('unresolvedMeasures') != []
            or report.get('secondParserPitchRhythmPassed') is not True
            or 'independentSourceAccuracy' not in report
            or report['independentSourceAccuracy'] is not None
            or any(report.get(k) is not False for k in ('sourceCertified', 'safeToPromote'))):
        raise ValueError('Assembly report is not an unresolved-free research candidate')
    source = manifest.get('sourceSha256')
    if not valid_hash(source) or any(row.get('sourceSha256') != source
                                     for row in (report, reading, comparison)):
        raise ValueError('Source binding drift')
    hashes = report.get('readingSha256')
    if (not isinstance(hashes, list) or len(hashes) != 2
            or not all(valid_hash(h) for h in hashes) or comparison.get('readingSha256') != hashes
            or not valid_hash(report.get('writerSha256'))):
        raise ValueError('Reading/writer provenance drift')
    for field, name in (('candidateSha256', 'candidate.musicxml'),
                        ('archiveSha256', 'candidate.mxl'),
                        ('resolvedReadingSha256', 'resolved-reading.json')):
        if report.get(field) != sha(payload[name]):
            raise ValueError('Assembly report hash drift: ' + name)
    with zipfile.ZipFile(io.BytesIO(payload['candidate.mxl'])) as archive:
        if (len(archive.namelist()) != 2 or set(archive.namelist()) !=
                {'META-INF/container.xml', 'score.musicxml'}
                or archive.read('score.musicxml') != payload['candidate.musicxml']):
            raise ValueError('MXL does not match the candidate XML')
        container = ET.fromstring(archive.read('META-INF/container.xml'))
        rootfiles = [n.get('full-path') for n in container.iter()
                     if n.tag.rsplit('}', 1)[-1] == 'rootfile']
        if rootfiles != ['score.musicxml']:
            raise ValueError('MXL container rootfile differs from candidate XML')
    return manifest, {**payload, 'bundle.json': raw}


def stage(directory, expected_manifest_sha256, root=ROOT):
    manifest, payload = verify(directory, expected_manifest_sha256)
    # Never offer a destination override into public/catalogue data.
    root = Path(root).resolve()
    work = root / 'work'
    base = work / 'transcription-imports'
    if work.is_symlink() or base.is_symlink():
        raise ValueError('Research storage cannot be symlinked')
    base.mkdir(parents=True, exist_ok=True)
    destination = base / expected_manifest_sha256
    destination.mkdir(exist_ok=False)
    bundle_dir = destination / 'bundle'
    bundle_dir.mkdir()
    # Copy the exact bytes already verified, not a second mutable source read.
    for name, raw in payload.items():
        (bundle_dir / name).write_bytes(raw)
    receipt = {'schemaVersion': 1, 'bundleManifestSha256': expected_manifest_sha256,
               'producer': manifest['producer'], 'sourceSha256': manifest['sourceSha256'],
               'status': 'staged-research-only', 'sourceCertified': False,
               'safeToPromote': False, 'catalogueModified': False, 'publicAssetsModified': False}
    (destination / 'atlas-import-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--expected-manifest-sha256', required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if args.verify_only:
        manifest, _ = verify(args.directory, args.expected_manifest_sha256)
        print(json.dumps({'verified': True, 'staged': False, 'status': manifest['status']}))
    else:
        print(json.dumps(stage(args.directory, args.expected_manifest_sha256), indent=2))
