#!/usr/bin/env python3
"""One versioned, local consumed-development on/off bar-consensus study.

Never run a historical runner/engine, refreeze, overwrite completed results or
retry a started invocation. All new default-off controls must reproduce the
archived written events before the candidate property may be enabled.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import subprocess

import omr_head_proposal_study as evidence
import sh1991_pilot as pilot

load, digest, immutable = evidence.load, evidence.digest, evidence.immutable
COHORT = ['469', '501t', '531']


def check(out):
    p = load(Path(out)/'protocol.json')
    for path, sha in p['filesSha256'].items():
        if digest(path) != sha:
            raise ValueError('Frozen study input/code drift: '+path)
    if pilot.engine_identity(Path(p['engineExecutable'])) != p['engine']:
        raise ValueError('Frozen separate engine drift')
    if [c['id'] for c in p['cases']] != COHORT:
        raise ValueError('Consumed development cohort drift')
    return p


def freeze(config, out):
    config, out = Path(config).resolve(), Path(out).resolve()
    if (out/'protocol.json').exists():
        return check(out)
    p = load(config)
    if [c['id'] for c in p['cases']] != COHORT:
        raise ValueError('Only the three fixed consumed development sources are allowed')
    paths = [config, Path(__file__), Path(pilot.__file__), Path(evidence.__file__),
             Path(p['JAVA_HOME'])/'bin/java', *map(Path, p['extraInputs'])]
    for case in p['cases']:
        paths += [Path(case[k]) for k in ('source', 'archivedExport', 'archivedGraph')]
    if any(out == path or out in path.parents for path in paths):
        raise ValueError('Keep output outside retained inputs/code')
    p.update(createdAt=pilot.now(),
             phase='Consumed development only; same-binary property off/on; not held-out evidence',
             engine=pilot.engine_identity(Path(p['engineExecutable'])),
             filesSha256={str(path.resolve()): digest(path) for path in paths},
             failurePolicy='No implicit retry after started.json. All off controls must reproduce archived events before any candidate runs.',
             candidateProperty='atlas.barConsensus',
             sourceCertified=False, safeToPromote=False)
    immutable(out/'protocol.json', p)
    return check(out)


def verify_receipt(directory, protocol_sha):
    receipt = load(directory/'recognition.json')
    if receipt['protocolSha256'] != protocol_sha:
        raise ValueError('Recognition protocol drift')
    for name, sha in receipt['artifactsSha256'].items():
        path = (directory/name).resolve()
        if directory not in path.parents or digest(path) != sha:
            raise ValueError('Retained study artifact drift')
    return receipt


def recognize(out, case, arm):
    out = Path(out).resolve(); p = check(out)
    protocol_sha = digest(out/'protocol.json')
    if arm not in {'off', 'on'} or case not in p['cases']:
        raise ValueError('Unsupported arm/case')
    if arm == 'on' and not verify_controls(out)['allControlsMatch']:
        raise ValueError('Default-off control regression; do not enable candidate')
    directory = out/arm/case['id']
    if (directory/'recognition.json').exists():
        return verify_receipt(directory, protocol_sha)
    started = directory/'started.json'
    if started.exists():
        raise ValueError('Recognition already started; no implicit retry')
    opts = p['settings']['JAVA_OPTS']+' -Datlas.barConsensus='+('true' if arm == 'on' else 'false')
    command = [p['engineExecutable'], '-batch', '-export']
    for value in p['settings']['constants']:
        command += ['-constant', value]
    command += ['-output', str(directory/'raw'), case['source']]
    immutable(started, {'beganAt': pilot.now(), 'protocolSha256': protocol_sha,
                        'command': command, 'JAVA_HOME': p['JAVA_HOME'], 'JAVA_OPTS': opts})
    env = {**os.environ, 'JAVA_HOME': p['JAVA_HOME'], 'JAVA_OPTS': opts}
    with (directory/'audiveris.log').open('x') as log:
        proc = subprocess.Popen(command, env=env, stdout=log, stderr=log, start_new_session=True)
        try:
            code = proc.wait(timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL); proc.wait()
            code = 124
    graphs, exports = list((directory/'raw').rglob('*.omr')), list((directory/'raw').rglob('*.mxl'))
    artifacts = [directory/'audiveris.log', *graphs, *exports]
    receipt = {'protocolSha256': protocol_sha, 'endedAt': pilot.now(), 'exitCode': code,
               'status': 'exported' if code == 0 and len(graphs) == len(exports) == 1 else 'recognition-failed',
               'graph': str(graphs[0].relative_to(directory)) if len(graphs) == 1 else None,
               'export': str(exports[0].relative_to(directory)) if len(exports) == 1 else None,
               'artifactsSha256': {str(f.relative_to(directory)): digest(f) for f in artifacts}}
    check(out)
    immutable(directory/'recognition.json', receipt)
    return receipt


def verify_controls(out, execute=False):
    out = Path(out).resolve(); p = check(out); rows = []
    for case in p['cases']:
        directory = out/'off'/case['id']
        receipt = (recognize(out, case, 'off') if execute else
                   verify_receipt(directory, digest(out/'protocol.json')))
        same = (receipt['status'] == 'exported' and
                pilot.score((directory/receipt['export']).read_bytes()) ==
                pilot.score(Path(case['archivedExport']).read_bytes()))
        rows.append({'source': case['id'], 'recognitionStatus': receipt['status'],
                     'matchesArchivedWrittenEvents': same,
                     'recognitionSha256': digest(directory/'recognition.json')})
    result = {'protocolSha256': digest(out/'protocol.json'), 'controls': rows,
              'allControlsMatch': all(r['matchesArchivedWrittenEvents'] for r in rows)}
    immutable(out/'controls.json', result)
    return result


def run(out):
    controls = verify_controls(out, execute=True)
    if not controls['allControlsMatch']:
        raise ValueError('Default-off control regression; do not enable candidate')
    p = check(out)
    for case in p['cases']:
        recognize(out, case, 'on')
    return replay(out)


def replay(out):
    out = Path(out).resolve(); p = check(out)
    controls = verify_controls(out)
    rows = {case['id']: verify_receipt(out/'on'/case['id'], digest(out/'protocol.json'))
            for case in p['cases']}
    return {'allControlsMatch': controls['allControlsMatch'],
            'candidateStatus': {k: v['status'] for k, v in rows.items()}}


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--freeze', type=Path, metavar='CONFIG')
    mode.add_argument('--run', action='store_true')
    mode.add_argument('--replay', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        freeze(args.freeze, args.out); print('Consumed-development recipe and inputs frozen before active inference.')
    else:
        print(json.dumps(run(args.out) if args.run else replay(args.out), indent=2))
