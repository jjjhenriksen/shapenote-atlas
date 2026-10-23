#!/usr/bin/env python3
"""Atlas consumer for opt-in research bundle versions 1 and 2. Stage private research only; never publish."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
from xml.etree import ElementTree as ET
import zipfile

# ZIP's optional compression backends raise their own parser exceptions.
try:
    from lzma import LZMAError
except ImportError:
    LZMAError = RuntimeError
try:
    from zlib import error as ZlibError
except ImportError:
    ZlibError = RuntimeError

ROOT = Path(__file__).resolve().parents[1]
FILES = frozenset(('candidate.musicxml', 'candidate.mxl', 'report.json',
                   'resolved-reading.json', 'comparison.json'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def valid_hash(value, size=64):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{' + str(size) + '}', value)


def json_object(raw, name):
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError('Invalid JSON: ' + name) from exc
    if not isinstance(value, dict):
        raise ValueError('Expected JSON object: ' + name)
    return value


def verify_archive(payload):
    try:
        # Well-formed XML is a format check, not semantic/source acceptance.
        ET.fromstring(payload['candidate.musicxml'])
        with zipfile.ZipFile(io.BytesIO(payload['candidate.mxl'])) as archive:
            if (len(archive.namelist()) != 2 or set(archive.namelist()) !=
                    {'META-INF/container.xml', 'score.musicxml'}):
                raise ValueError('MXL does not match the candidate XML')
            if archive.getinfo('score.musicxml').file_size != len(payload['candidate.musicxml']):
                raise ValueError('MXL score size differs from candidate XML')
            if archive.read('score.musicxml') != payload['candidate.musicxml']:
                raise ValueError('MXL does not match the candidate XML')
            container = ET.fromstring(archive.read('META-INF/container.xml'))
            rootfiles = [n.get('full-path') for n in container.iter()
                         if n.tag.rsplit('}', 1)[-1] == 'rootfile']
            if rootfiles != ['score.musicxml']:
                raise ValueError('MXL container rootfile differs from candidate XML')
    except (zipfile.BadZipFile, ET.ParseError, LookupError, RuntimeError,
            NotImplementedError, OSError, EOFError, ZlibError, LZMAError) as exc:
        raise ValueError('Invalid MXL/XML payload') from exc


def verify(directory, expected_manifest_sha256, bundle_version=1):
    """Independent stdlib-only consumer; no transcriber runtime imports."""
    if type(bundle_version) is not int or bundle_version not in (1, 2):
        raise ValueError('Unsupported requested bundle version')
    if bundle_version == 2:
        import transcription_bundle_v2 as v2
        parse_json = v2.strict_json_object
    else:
        parse_json = json_object
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
    manifest = parse_json(raw, 'bundle.json')
    if (type(manifest.get('schemaVersion')) is not int or manifest['schemaVersion'] != bundle_version
            or manifest.get('kind') != 'shapenote-transcription-bundle'
            or manifest.get('status') != 'research-candidate'):
        raise ValueError('Unsupported bundle version/kind/status')
    if any(manifest.get(k) is not False for k in ('sourceCertified', 'safeToPromote')):
        raise ValueError('Only unpromoted research bundles are supported')
    files = manifest.get('files')
    if not isinstance(files, dict) or set(files) != FILES:
        raise ValueError('Unsupported payload paths')
    payload = {name: (directory / name).read_bytes() for name in FILES}
    for name, data in payload.items():
        if not valid_hash(manifest['files'][name]) or sha(data) != manifest['files'][name]:
            raise ValueError('Payload hash drift: ' + name)
    producer = manifest.get('producer', {})
    if (not isinstance(producer, dict)
            or not isinstance(producer.get('repository'), str) or not producer['repository']
            or not valid_hash(producer.get('revision'), 40)
            or type(producer.get('dirty')) is not bool
            or not valid_hash(producer.get('exporterSha256'))):
        raise ValueError('Missing pinned producer provenance')
    report = parse_json(payload['report.json'], 'report.json')
    reading = parse_json(payload['resolved-reading.json'], 'resolved-reading.json')
    comparison = parse_json(payload['comparison.json'], 'comparison.json')
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
    verify_archive(payload)
    if bundle_version == 2:
        v2.verify_metadata(manifest, report, reading, comparison, payload['candidate.musicxml'])
    return manifest, {**payload, 'bundle.json': raw}


def stage(directory, expected_manifest_sha256, root=ROOT, bundle_version=1):
    manifest, payload = verify(directory, expected_manifest_sha256, bundle_version=bundle_version)
    # Never offer a destination override into public/catalogue data.
    root = Path(root).resolve()
    work = root / 'work'
    base = work / 'transcription-imports'
    if work.is_symlink() or base.is_symlink():
        raise ValueError('Research storage cannot be symlinked')
    base.mkdir(parents=True, exist_ok=True)
    destination = base / expected_manifest_sha256
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Research bundle already staged: ' + str(destination))
    receipt = {'schemaVersion': bundle_version, 'bundleManifestSha256': expected_manifest_sha256,
               'producer': manifest['producer'], 'sourceSha256': manifest['sourceSha256'],
               'status': 'staged-research-only', 'sourceCertified': False,
               'safeToPromote': False, 'catalogueModified': False, 'publicAssetsModified': False}
    if bundle_version == 2:
        receipt.update(readingContractVersion=2, profile=manifest['profile'])
    # Publish only a complete bundle and receipt. A failed write removes the
    # temporary sibling, allowing the same pinned bundle to be retried.
    with tempfile.TemporaryDirectory(prefix='.bundle-', dir=base) as temporary:
        staged = Path(temporary)
        bundle_dir = staged / 'bundle'
        bundle_dir.mkdir()
        # Copy the exact bytes already verified, not a second mutable source read.
        for name, raw in payload.items():
            (bundle_dir / name).write_bytes(raw)
        (staged / 'atlas-import-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        staged.rename(destination)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--expected-manifest-sha256', required=True)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--bundle-version', type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    try:
        if args.verify_only:
            manifest, _ = verify(args.directory, args.expected_manifest_sha256, bundle_version=args.bundle_version)
            print(json.dumps({'verified': True, 'staged': False, 'status': manifest['status']}))
        else:
            print(json.dumps(stage(args.directory, args.expected_manifest_sha256, bundle_version=args.bundle_version), indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, 'error: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
