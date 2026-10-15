#!/usr/bin/env python3
"""Publish only source pointers, hashes and measurements, never scan/XML bytes."""
import argparse
from pathlib import Path
import subprocess

import sh1991_pilot as pilot


def report(work, destination):
    pilot.verify(work)
    pilot.verify(work, 'grayscale-2x')
    for phase in ('train', 'test'):
        pilot.verify(work / ('staff-probe-' + phase))
    dataset = pilot.load(work / 'dataset.json')
    raw = pilot.load(work / 'baseline-results.json')
    scale = pilot.load(work / 'grayscale-2x-results.json')
    source = work / 'toolchain/audiveris-source'
    source_commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    executable = source / 'app/build/install/app/bin/Audiveris'
    source_dirty = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True).strip()
    if source_dirty:
        raise ValueError('engine source checkout changed')
    output = {'schemaVersion': 1, 'experiment': 'sh1991-v1',
              'datasetSha256': pilot.digest((work / 'dataset.json').read_bytes()),
              'datasetFrozenAt': dataset['frozenAt'], 'seed': dataset['seed'],
              'sourceCorpusSha256': dataset['sourceCorpusSha256'], 'splits': dataset['splits'],
              'engine': {'name': 'Audiveris', 'version': '5.11.0', 'sourceCommit': source_commit,
                         'retainedInstallIdentity': pilot.engine_identity(executable),
                         'runtime': 'task-local Temurin JDK 25.0.4.1+1, macOS arm64; local CPU',
                         'initialRunFingerprintCaveat': 'Raw, enlargement and training staff receipts predate per-run library fingerprints; retained output hashes and reevaluated metrics verified. Held-out staff receipts include per-run engine identity.'},
              'evaluators': {name: pilot.digest((pilot.ROOT / 'scripts' / name).read_bytes())
                             for name in ('sh1991_pilot.py', 'sh1991_staff_probe.py')},
              'raw': {'summary': raw['summary'],
                      'exactWrittenEventPages': sum(r['metrics']['exactWrittenEvents'] for r in raw['records']),
                      'partCountMatchPages': sum(r['metrics']['partCountMatch'] for r in raw['records']),
                      'measureCountMatchPages': sum(r['metrics']['measureCountsMatch'] for r in raw['records'])},
              'enlargementTrainingProbe': {'pageIds': [r['songNo'] for r in scale['records']], 'summary': scale['summary']['all'],
                                           'decision': pilot.load(work / 'preprocessing-probe-decision.json')},
              'staffIsolation': {}, 'records': [],
              'sourceBytesIncluded': False, 'modelFineTuned': False, 'trainingEligiblePages': 0,
              'sourceCertifiedPages': 0, 'humanCorrectionMinutes': None,
              'limitations': ['Unreviewed candidate labels, not ground truth', 'SH1991 four-shape only, one scan family',
                             'Known groups isolated; unrecognized near-duplicates still require independent audit',
                             'Ordered-part edit alignment; pitch spelling/octave exact; duration rational quarter notes; onset uses written measure ordinal',
                             'Grace notes skipped; unpitched notes rejected; no repeat unfolding or tie merging',
                             'No literal notehead/fill, lyric, source-certified voice/staff, tie/slur/repeat fidelity score',
                             'No human usability/correction-time measurement or source-obscuration/edition controls',
                             'Staff probe uses reference part-count/order metadata; not autonomous page parsing']}
    for phase in ('train', 'test'):
        directory = work / ('staff-probe-' + phase)
        result = pilot.load(directory / 'baseline-results.json')
        output['staffIsolation'][phase] = {'design': pilot.load(directory / 'design.json'),
                                          'decision': pilot.load(directory / 'decision.json'),
                                          'partImages': len(result['records']),
                                          'summary': result['summary']['all'],
                                          'exactPartImages': sum(r['metrics']['exactWrittenEvents'] for r in result['records'] if r.get('metrics')),
                                          'partCountMatches': sum(r['metrics']['partCountMatch'] for r in result['records'] if r.get('metrics'))}
    for row in dataset['records']:
        output['records'].append({k: row[k] for k in ('songId', 'songNo', 'title', 'group', 'split', 'edition', 'pairingStatus')})
        output['records'][-1].update({field: {k: row[field][k] for k in ('url', 'sha256')} for field in ('image', 'label')})
    pilot.write(destination, output)
    print('Wrote sanitized report:', destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=pilot.DEFAULT_WORK)
    parser.add_argument('--output', type=Path, default=pilot.ROOT / 'docs/experiments/sh1991-omr-baseline-20261015.json')
    args = parser.parse_args()
    report(args.work.resolve(), args.output)
