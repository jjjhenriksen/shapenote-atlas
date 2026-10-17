#!/usr/bin/env python3
"""Versioned consumed-development study. Never execute historical runners."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import omr_head_proposal_study as prior
import omr_head_transfer as transfer
import omr_head_topology as detector

ROOT = Path(__file__).resolve().parents[1]
digest, load, immutable = prior.digest, prior.load, prior.immutable


def check_clayton(retained, clayton):
    p = transfer.check(retained, clayton)
    report, receipt = load(clayton/'report.json'), load(clayton/'receipt.json')
    lock = load(clayton/'inference-lock.json')
    if (receipt['reportSha256'] != digest(clayton/'report.json')
            or receipt['recognitionSha256'] != digest(clayton/'recognition.json')
            or lock['protocolSha256'] != digest(clayton/'protocol.json')
            or lock['labelsSha256'] != digest(clayton/'source-observations.json')
            or report['inferenceLockSha256'] != digest(clayton/'inference-lock.json')
            or report['recognitionSha256'] != digest(clayton/'recognition.json')
            or report['protocolSha256'] != digest(clayton/'protocol.json')):
        raise ValueError('Clayton retained chain drift')
    recognition = load(clayton/'recognition.json')
    transfer.check_bindings(recognition['artifactsSha256'], clayton)
    if recognition['status'] != 'graph-ready' or p['source'] != 'SH2025/531':
        raise ValueError('Need completed Clayton baseline')
    return p


def protocol(retained, clayton):
    p = check_clayton(retained, clayton)
    result = prior.protocol(retained)
    result['phase'] = 'Consumed development on SH2025/219 and 531; not held-out validation'
    result['topologyRecipe'] = detector.RECIPE
    result['primaryArm'] = 'native-plus-topology'
    result['externalFilesSha256'] = {str(clayton/name): digest(clayton/name) for name in (
        'protocol.json', 'source-observations.json', 'inference-lock.json',
        'report.json', 'receipt.json', 'recognition.json')}
    result['retainedInputsSha256'].update(p['retainedInputsSha256'])
    result['externalFilesSha256'].update({str(clayton/name): sha for name, sha in
                                         load(clayton/'recognition.json')['artifactsSha256'].items()})
    for module in (detector, transfer, prior):
        result['codeSha256'][str(Path(module.__file__).relative_to(ROOT))] = digest(module.__file__)
    result['codeSha256'][str(Path(__file__).relative_to(ROOT))] = digest(__file__)
    return result


def analyze(image, labels, native, bank):
    detected = detector.propose(image, labels['windows'])
    filled = prior.classify(image, detected['filled'], bank)
    holes = prior.classify(image, detected['holes'], bank)
    selected = detector.select(filled, holes)
    fused, suppressed = detector.dense.fuse(native, selected)
    old_filled = prior.classify(image, detector.dense.propose(image, labels['windows'])['proposals'], bank)
    old_selected = [r for r in old_filled if r.get('selectivePrediction') == 'square/filled']
    old_fused, _ = detector.dense.fuse(native, old_selected)
    arms = {'native': native, 'native-plus-old-squares': old_fused,
            'holes-all': holes, 'topology-selected': selected, 'native-plus-topology': fused}
    return {'sourceHeadCount': len(labels['rows']),
            'sourceByClass': dict(Counter(r['label'] or 'unresolved' for r in labels['rows'])),
            'arms': {name: prior.summarize(labels['rows'], rows) for name, rows in arms.items()},
            'predictions': arms, 'filled': filled, 'holes': holes, 'suppressed': suppressed,
            'vetoes': detected['vetoes'], 'staffLattices': detected['staffLattices'],
            'denseGeometricVetoes': detected['denseGeometricVetoes']}


def run(retained, clayton, out):
    from PIL import Image
    retained, clayton, out = [Path(p).resolve() for p in (retained, clayton, out)]
    for protected in (retained, clayton):
        if out == protected or protected in out.parents:
            raise ValueError('Never write inside retained evidence checkout')
    before = protocol(retained, clayton)
    immutable(out/'protocol.json', before)
    if (out/'report.json').exists():
        if digest(out/'report.json') != load(out/'receipt.json')['reportSha256']:
            raise ValueError('Completed topology development report drift')
        return load(out/'report.json')
    labels219, old219, manifest = prior.retained_evidence(retained)
    bank = prior.fit_bank(retained, manifest, labels219['sourceSha256'])
    p531 = load(clayton/'protocol.json')
    if p531['sourceSha256'] in bank['sourceHashes']:
        raise ValueError('Clayton source leakage')
    cases = [
        ('SH2025/219', retained/prior.SOURCE, labels219,
         [dict(r, **r['models']['expanded']) for r in old219['automaticPredictions']]),
        ('SH2025/531', retained/p531['sourcePath'], load(clayton/'source-observations.json'),
         load(clayton/'report.json')['predictions']['native'])]
    pages = {}
    for source, path, labels, native in cases:
        with Image.open(path) as image:
            transfer.validate_census(labels, {'sourceSha256': digest(path)}, image.size)
            pages[source] = analyze(image, labels, native, bank)
    if before != protocol(retained, clayton):
        raise ValueError('Code/input drift during development')
    report = {'protocolSha256': digest(out/'protocol.json'), 'pages': pages,
              'phase': before['phase'], 'sourceCertified': False,
              'safeToPromote': False, 'wholeScoresAccepted': 0}
    immutable(out/'report.json', report)
    immutable(out/'receipt.json', {'reportSha256': digest(out/'report.json')})
    return report


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retained-root', type=Path, required=True)
    parser.add_argument('--clayton-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.retained_root, args.clayton_root, args.out)
    print(json.dumps({source: {name: row['0.5']['summary'] for name, row in page['arms'].items()}
                      for source, page in report['pages'].items()}, indent=2))
