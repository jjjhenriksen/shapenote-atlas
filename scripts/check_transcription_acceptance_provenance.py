#!/usr/bin/env python3
"""Compare declaration pins with a verified bundle snapshot, without staging."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

# The standalone read-only command must not create sibling bytecode caches.
_previous_bytecode_setting = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True
    import import_transcription_bundle as bundle_consumer
    import validate_transcription_acceptance as declarations
finally:
    sys.dont_write_bytecode = _previous_bytecode_setting


def check(declaration_path: Path, bundle_directory: Path,
          expected_manifest_sha256: str) -> dict[str, Any]:
    """Bind a receipt to captured bytes; never infer human approval from consistency."""
    result = {
        'schemaVersion': 1, 'kind': 'shapenote-transcription-provenance-check',
        'status': 'blocked', 'declarationSha256': None,
        'expectedBundleManifestSha256': expected_manifest_sha256,
        'verifiedBundleManifestSha256': None,
        'declarationValid': False, 'bundleIntegrityVerified': False,
        'declaredDispositions': None, 'mismatches': [], 'blockers': [],
        'acceptance': False, 'authorityVerified': False, 'evidenceVerified': False,
        'sourceCertified': False, 'safeToPromote': False,
    }
    declaration = None
    manifest = None
    payload = None
    try:
        raw = Path(declaration_path).read_bytes()
        result['declarationSha256'] = bundle_consumer.sha(raw)
        declaration = json.loads(raw.decode('utf-8'), object_pairs_hook=declarations.unique_object)
        declarations.validate(declaration)
        result['declarationValid'] = True
        result['declaredDispositions'] = {
            'decision': declaration['decision'], 'publication': declaration['publication'],
            'humanImageReview': declaration['humanImageReview']['disposition'],
            'assessments': {key: value['disposition']
                            for key, value in declaration['assessments'].items()},
            'unsupportedSemantics': declaration['unsupportedSemantics'],
            'uncertainties': declaration['uncertainties'],
            'policyRestrictions': declaration['policyRestrictions'],
            'remainingBlockers': declaration['remainingBlockers'],
            'residualAtlasIssues': declaration['residualAtlasIssues'],
        }
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        result['blockers'].append({'code': 'invalid-declaration', 'detail': str(error)})

    try:
        manifest, payload = bundle_consumer.verify(bundle_directory, expected_manifest_sha256)
        # Refuse ambiguous provenance even if the existing bundle verifier's JSON
        # parser would select the final duplicate key. Use captured bytes only.
        json.loads(payload['bundle.json'], object_pairs_hook=declarations.unique_object)
        report = json.loads(payload['report.json'], object_pairs_hook=declarations.unique_object)
        result['bundleIntegrityVerified'] = True
        result['verifiedBundleManifestSha256'] = bundle_consumer.sha(payload['bundle.json'])
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        result['blockers'].append({'code': 'bundle-verification-failed', 'detail': str(error)})

    if result['blockers']:
        return result

    def compare(field: str, declared: Any, verified: Any) -> None:
        if type(declared) is not type(verified) or declared != verified:
            result['mismatches'].append({'field': field, 'declared': declared, 'verified': verified})

    declared_bundle = declaration['bundle']
    compare('bundle.schemaVersion', declared_bundle['schemaVersion'], manifest['schemaVersion'])
    compare('bundle.manifestSha256', declared_bundle['manifestSha256'],
            result['verifiedBundleManifestSha256'])
    compare('bundle.sourceSha256', declared_bundle['sourceSha256'], manifest['sourceSha256'])
    for field in ('repository', 'revision', 'dirty', 'exporterSha256'):
        compare('bundle.producer.' + field, declared_bundle['producer'][field], manifest['producer'][field])
    for name in sorted(bundle_consumer.FILES):
        compare('bundle.payloadSha256.' + name, declared_bundle['payloadSha256'][name],
                bundle_consumer.sha(payload[name]))
    compare('bundle.actualWriterSha256', declared_bundle['actualWriterSha256'], report['writerSha256'])
    for flag in ('sourceCertified', 'safeToPromote'):
        compare('bundle.researchFlags.' + flag, declared_bundle['researchFlags'][flag], manifest[flag])
    if result['mismatches']:
        result['blockers'].append({'code': 'provenance-mismatch',
                                   'detail': 'Declared provenance differs from the verified bundle snapshot.'})
    else:
        result['status'] = 'consistent'
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('declaration', type=Path, help='private proposed declaration JSON')
    parser.add_argument('bundle', type=Path, help='private v1 bundle directory')
    parser.add_argument('--expected-manifest-sha256', required=True,
                        help='manifest pin supplied independently by the exporting owner')
    args = parser.parse_args(argv)
    result = check(args.declaration, args.bundle, args.expected_manifest_sha256)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'consistent' else 2


if __name__ == '__main__':
    sys.exit(main())
