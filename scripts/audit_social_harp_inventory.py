#!/usr/bin/env python3
"""Read frozen source-only readings and emit an aggregate, non-certifying audit."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys

DISPOSITIONS = ('opening-present', 'continuation-only', 'mixed', 'non-music', 'uncertain')
ROLES = ('opening', 'continuation', 'other', 'uncertain')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'Duplicate JSON key')
        value[key] = item
    return value


def pinned_json(path, expected):
    require(isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected), 'Invalid expected SHA-256')
    raw = Path(path).read_bytes()
    require(digest(raw) == expected, 'Pinned input SHA-256 mismatch')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object)
    require(type(value) is dict, 'Expected JSON object')
    return value


def strings(value):
    require(type(value) is list and all(type(v) is str and v.strip() for v in value), 'Expected string list')


def validate_protocol(packet, protocol):
    require(type(protocol.get('schemaVersion')) is int and protocol['schemaVersion'] == 1 and
            protocol.get('kind') == 'social-harp-source-only-inventory-protocol', 'Unsupported protocol')
    coordinates = protocol.get('coordinates')
    require(type(coordinates) is dict and type(coordinates.get('pdfLeafBase')) is int and
            coordinates['pdfLeafBase'] == 1 and type(coordinates.get('pdfIndexBase')) is int and
            coordinates['pdfIndexBase'] == 0, 'Unsupported coordinate convention')
    count = protocol.get('sourcePageCount')
    require(type(count) is int and count > 0, 'Invalid source page count')
    raw = (packet / 'source.pdf').read_bytes()
    require(digest(raw) == protocol.get('sourceSha256') and type(protocol.get('sourceBytes')) is int and
            len(raw) == protocol['sourceBytes'],
            'Source PDF snapshot mismatch')
    require(type(protocol.get('pages')) is list and bool(protocol['pages']), 'Missing protocol pages')
    leaves = []
    for page in protocol['pages']:
        require(type(page) is dict, 'Invalid protocol page')
        leaf = page.get('pdfLeaf')
        require(type(leaf) is int and 1 <= leaf <= count and type(page.get('pdfIndex')) is int and
                page['pdfIndex'] == leaf - 1, 'PDF leaf/index mismatch')
        name = page.get('imageFile')
        require(type(name) is str and re.fullmatch(r'leaf-[0-9]+\.png', name), 'Unsafe image filename')
        require(digest((packet / name).read_bytes()) == page.get('imageSha256'), 'Source image snapshot mismatch')
        leaves.append(leaf)
    require(len(set(leaves)) == len(leaves), 'Duplicate protocol leaf')
    targets = protocol.get('targetPdfLeaves')
    require(type(targets) is list and bool(targets) and all(type(v) is int and v in leaves for v in targets)
            and len(set(targets)) == len(targets), 'Invalid target leaves')
    return leaves


def validate_reading(reading, protocol, protocol_pin, leaves):
    require(type(reading.get('schemaVersion')) is int and reading['schemaVersion'] == 1 and
            reading.get('kind') == 'social-harp-source-only-inventory-reading', 'Unsupported reading')
    require(reading.get('protocolSha256') == protocol_pin and
            reading.get('sourceSha256') == protocol['sourceSha256'], 'Reading source/protocol binding mismatch')
    require(type(reading.get('readerId')) is str and bool(reading['readerId'].strip()), 'Missing reader identity')
    require(type(reading.get('pages')) is list, 'Missing reading pages')
    strings(reading.get('notes'))
    by_leaf = {}
    for page in reading['pages']:
        require(type(page) is dict, 'Invalid reading page')
        leaf = page.get('pdfLeaf')
        require(type(leaf) is int and leaf in leaves and leaf not in by_leaf and
                type(page.get('pdfIndex')) is int and page['pdfIndex'] == leaf - 1, 'Reading leaf coverage/index mismatch')
        require(page.get('printedPageLabel') is None or
                (type(page['printedPageLabel']) is str and bool(page['printedPageLabel'].strip())), 'Invalid printed label')
        require(page.get('pageDisposition') in DISPOSITIONS, 'Invalid page disposition')
        strings(page.get('uncertainties'))
        require(type(page.get('continuationEvidence')) is str and bool(page['continuationEvidence'].strip()),
                'Missing visual continuation evidence/uncertainty')
        require(type(page.get('headings')) is list, 'Missing heading enumeration')
        opening_count = 0
        for heading in page['headings']:
            require(type(heading) is dict and type(heading.get('text')) is str and heading['text'].strip()
                    and heading.get('role') in ROLES, 'Invalid heading observation')
            box = heading.get('bbox')
            require(type(box) is list and len(box) == 4 and
                    all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in box)
                    and box[0] < box[2] and box[1] < box[3], 'Invalid normalized heading coordinates')
            opening_count += heading['role'] == 'opening'
        if page['pageDisposition'] in ('opening-present', 'mixed'):
            require(opening_count > 0, 'Opening disposition lacks an opening heading')
        if page['pageDisposition'] in ('continuation-only', 'non-music'):
            require(opening_count == 0, 'Disposition contradicts opening heading')
        by_leaf[leaf] = page
    require(set(by_leaf) == set(leaves), 'Incomplete reading coverage')
    return by_leaf


def compare(packet, protocol_pin, reader_a_path, reader_a_pin, reader_b_path, reader_b_pin):
    packet = Path(packet)
    protocol = pinned_json(packet / 'protocol.json', protocol_pin)
    leaves = validate_protocol(packet, protocol)
    reader_a = pinned_json(reader_a_path, reader_a_pin)
    reader_b = pinned_json(reader_b_path, reader_b_pin)
    a = validate_reading(reader_a, protocol, protocol_pin, leaves)
    b = validate_reading(reader_b, protocol, protocol_pin, leaves)
    require(reader_a['readerId'] != reader_b['readerId'], 'Reader identities must differ')
    targets = set(protocol['targetPdfLeaves'])
    rows = []
    target_counts = Counter()
    for leaf in sorted(leaves):
        first, second = a[leaf], b[leaf]
        headings = lambda page: sorted((h['role'], ' '.join(h['text'].split()).casefold()) for h in page['headings'])
        disagreements = []
        for field, same in (('pageDisposition', first['pageDisposition'] == second['pageDisposition']),
                            ('printedPageLabel', first['printedPageLabel'] == second['printedPageLabel']),
                            ('headings', headings(first) == headings(second))):
            if not same:
                disagreements.append(field)
        agreed_disposition = first['pageDisposition'] if first['pageDisposition'] == second['pageDisposition'] else None
        if leaf in targets and agreed_disposition is not None:
            target_counts[agreed_disposition] += 1
        rows.append({'pdfLeaf': leaf, 'pdfIndex': leaf - 1, 'target': leaf in targets,
                     'agreedDisposition': agreed_disposition, 'disagreements': disagreements,
                     'headingCounts': [len(first['headings']), len(second['headings'])],
                     'uncertaintyCounts': [len(first['uncertainties']), len(second['uncertainties'])]})
    return {'schemaVersion': 1, 'kind': 'social-harp-bounded-visual-inventory-audit', 'status': 'compared',
            'sourceSha256': protocol['sourceSha256'], 'protocolSha256': protocol_pin,
            'readerSha256': [reader_a_pin, reader_b_pin], 'targetLeafCount': len(targets),
            'contextLeafCount': len(leaves) - len(targets), 'reviewedLeafCount': len(leaves),
            'agreedTargetDispositionCounts': dict(sorted(target_counts.items())), 'pages': rows,
            'unresolvedLeaves': [row['pdfLeaf'] for row in rows if row['disagreements'] or
                                 any(row['uncertaintyCounts']) or row['agreedDisposition'] == 'uncertain'],
            'headingsAndLyricsOmitted': True, 'readerIndependenceVerified': False,
            'wholeBookReviewed': False, 'inventoryReconciled': False,
            'sourceCertified': False, 'safeToPromote': False, 'humanReviewRequired': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('--expected-protocol-sha256', required=True)
    parser.add_argument('--reader-a', type=Path, required=True)
    parser.add_argument('--expected-reader-a-sha256', required=True)
    parser.add_argument('--reader-b', type=Path, required=True)
    parser.add_argument('--expected-reader-b-sha256', required=True)
    args = parser.parse_args(argv)
    try:
        receipt = compare(args.packet, args.expected_protocol_sha256, args.reader_a,
                          args.expected_reader_a_sha256, args.reader_b, args.expected_reader_b_sha256)
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        print(json.dumps({'schemaVersion': 1, 'status': 'blocked', 'error': str(error),
                          'inventoryReconciled': False, 'sourceCertified': False, 'safeToPromote': False}))
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
