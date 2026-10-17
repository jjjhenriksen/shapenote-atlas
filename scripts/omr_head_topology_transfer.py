#!/usr/bin/env python3
"""Freeze topology development before a seventh-source, one-shot transfer."""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
from pathlib import Path

import omr_head_topology_study as development
import omr_head_transfer as previous

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('work/source-images/2025/469-thy-strength-8009691e25.jpg')
digest, load, immutable = development.digest, development.load, development.immutable
check = previous.check


def prepare(retained, clayton, developed, out):
    retained, clayton, developed, out = [Path(p).resolve() for p in (retained, clayton, developed, out)]
    for protected in (retained, clayton, developed):
        if out == protected or protected in out.parents:
            raise ValueError('Never write inside retained evidence')
    if (out/'protocol.json').exists():
        return check(retained, out)
    p = development.protocol(retained, clayton)
    if (p != load(developed/'protocol.json')
            or digest(developed/'report.json') != load(developed/'receipt.json')['reportSha256']
            or load(developed/'report.json')['protocolSha256'] != digest(developed/'protocol.json')):
        raise ValueError('Development result/code binding drift')
    selected = load(retained/previous.SELECTION)['eligible'][6]
    if selected['songNo'] != '469':
        raise ValueError('Seventh original source rank drift')
    _, _, manifest = development.prior.retained_evidence(retained)
    sha = digest(retained/SOURCE)
    if sha in {r['sourceSha256'] for r in manifest['samples']}:
        raise ValueError('Evaluation source leakage')
    engine = load(clayton/'protocol.json')
    p['retainedInputsSha256'][str(SOURCE)] = sha
    p['externalFilesSha256'].update(engine['externalFilesSha256'])
    for name in ('protocol.json', 'report.json', 'receipt.json'):
        p['externalFilesSha256'][str(developed/name)] = digest(developed/name)
    for module in (development, previous.native, previous.native.native, previous.native.pilot):
        p['codeSha256'][str(Path(module.__file__).relative_to(ROOT))] = digest(module.__file__)
    p['codeSha256'][str(Path(__file__).relative_to(ROOT))] = digest(__file__)
    p.update({
        'phase': 'Pre-source-frozen topology transfer; no post-result tuning',
        'createdAt': previous.native.pilot.now(), 'source': 'SH2025/469',
        'sourcePath': str(SOURCE), 'sourceSha256': sha, 'selected': selected,
        'selectionRule': 'Seventh source in original hash-ranked list; previous six consumed; no replacement on failure',
        'exposure': 'New complete-window census; generic earlier processing/metadata may exist. Not globally untouched data.',
        'scope': engine['scope'], 'observations': engine['observations'],
        'engineExecutable': engine['engineExecutable'], 'engine': engine['engine'],
        'JAVA_HOME': engine['JAVA_HOME'], 'settings': engine['settings'],
        'recognitionPolicy': engine['recognitionPolicy'], 'failurePolicy': engine['failurePolicy'],
        'training': 'Unchanged 373 exemplars; no 219, 531 or 469 exemplars added',
    })
    # Avoid retaining the inherited runner hash as if it described this runner.
    p.pop('runnerSha256', None)
    immutable(out/'protocol.json', p)
    check(retained, out)
    return p


def lock_census(retained, out, labels_path):
    from PIL import Image
    out = Path(out); p = check(retained, out); labels = load(labels_path)
    with Image.open(Path(retained)/p['sourcePath']) as image:
        previous.validate_census(labels, p, image.size)
    immutable(out/'source-observations.json', labels)
    immutable(out/'inference-lock.json', {
        'protocolSha256': digest(out/'protocol.json'),
        'labelsSha256': digest(out/'source-observations.json')})
    return p, labels


def recognize(retained, out, p):
    out = Path(out)
    if (out/'recognition.json').exists():
        receipt = load(out/'recognition.json')
        if receipt['inferenceLockSha256'] != digest(out/'inference-lock.json'):
            raise ValueError('Recognition lock drift')
        previous.check_bindings(receipt['artifactsSha256'], out)
        return receipt
    raw = out/'raw'
    command = [p['engineExecutable'], '-batch', '-export']
    for value in p['settings']['constants']:
        command += ['-constant', value]
    command += ['-output', str(raw.resolve()), str((Path(retained)/p['sourcePath']).resolve())]
    started = out/'started.json'
    if started.exists():
        raise ValueError('Recognition already started; no implicit retry')
    immutable(started, {'command': command, 'beganAt': previous.native.pilot.now(),
                        'inferenceLockSha256': digest(out/'inference-lock.json')})
    raw.mkdir()
    env = {**os.environ, 'JAVA_HOME': p['JAVA_HOME'], 'JAVA_OPTS': p['settings']['JAVA_OPTS']}
    with (out/'audiveris.log').open('x') as log:
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
    graphs = list(raw.rglob('*.omr'))
    artifacts = [out/'audiveris.log', *graphs, *raw.rglob('*.mxl')]
    result = {'inferenceLockSha256': digest(out/'inference-lock.json'),
              'exitCode': code, 'endedAt': previous.native.pilot.now(),
              'status': 'graph-ready' if code == 0 and len(graphs) == 1 else 'recognition-failed',
              'graph': str(graphs[0].relative_to(out)) if len(graphs) == 1 else None,
              'artifactsSha256': {str(f.relative_to(out)): digest(f) for f in artifacts}}
    check(retained, out)
    immutable(out/'recognition.json', result)
    return result


def evaluate(retained, out):
    from PIL import Image
    out = Path(out); p = check(retained, out)
    labels, lock = load(out/'source-observations.json'), load(out/'inference-lock.json')
    if (lock['protocolSha256'] != digest(out/'protocol.json')
            or lock['labelsSha256'] != digest(out/'source-observations.json')):
        raise ValueError('Census/protocol lock drift')
    receipt = recognize(retained, out, p)
    if (out/'report.json').exists():
        saved = load(out/'receipt.json')
        if (saved['reportSha256'] != digest(out/'report.json')
                or saved['recognitionSha256'] != digest(out/'recognition.json')):
            raise ValueError('Completed report/recognition drift')
        return load(out/'report.json')
    _, _, manifest = development.prior.retained_evidence(Path(retained))
    bank = development.prior.fit_bank(Path(retained), manifest, p['sourceSha256'])
    heads = None; queries = []
    with Image.open(Path(retained)/p['sourcePath']) as image:
        previous.validate_census(labels, p, image.size)
        lattices = [development.detector.dense.geometry.staff_lines(image, w['box'])
                    for w in labels['windows']]
        if receipt['status'] == 'graph-ready':
            heads = previous.native.graph_heads(out/receipt['graph'], Path(retained)/p['sourcePath'], image.size)
            for head in heads:
                for window, lattice in zip(labels['windows'], lattices):
                    a, b, c, d = window['box']
                    if a <= head['x'] < c and b <= head['y'] < d:
                        row = dict(head, staff=window['staff'], origin='native')
                        if lattice['status'] == 'proposal':
                            row['interline'] = lattice['interline']
                            row = development.prior.classify(image, [row], bank)[0]
                        else:
                            row.update(prediction=None, selectivePrediction=None,
                                       reason='unresolved-auto-staff-lattice')
                        queries.append(row)
        report = development.analyze(image, labels, queries, bank)
    if receipt['status'] != 'graph-ready':
        # Failed native inference must not masquerade as a zero-count baseline.
        for name in ('native', 'native-plus-old-squares', 'native-plus-topology'):
            report['arms'].pop(name); report['predictions'].pop(name)
    report.update({'source': p['source'], 'phase': p['phase'],
                   'protocolSha256': digest(out/'protocol.json'),
                   'inferenceLockSha256': digest(out/'inference-lock.json'),
                   'recognitionSha256': digest(out/'recognition.json'),
                   'recognitionStatus': receipt['status'],
                   'nativeHeadNodesAllImage': len(heads) if heads is not None else None,
                   'primaryArm': p['primaryArm'], 'wholeScoresAccepted': 0,
                   'sourceCertified': False, 'safeToPromote': False,
                   'pitchRhythmAccuracy': None, 'exportedEventAccuracy': None,
                   'measuredHumanMinutes': None})
    check(retained, out)
    if lock['labelsSha256'] != digest(out/'source-observations.json'):
        raise ValueError('Source census drift during inference')
    immutable(out/'report.json', report)
    immutable(out/'receipt.json', {'reportSha256': digest(out/'report.json'),
                                 'recognitionSha256': digest(out/'recognition.json')})
    return report


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retained-root', required=True, type=Path)
    parser.add_argument('--clayton-root', type=Path)
    parser.add_argument('--development-root', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--labels', type=Path)
    mode.add_argument('--evaluate', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        if not args.clayton_root or not args.development_root:
            parser.error('--prepare requires --clayton-root and --development-root')
        prepare(args.retained_root, args.clayton_root, args.development_root, args.out)
        print('Frozen before seventh-source inspection.')
    elif args.labels:
        lock_census(args.retained_root, args.out, args.labels)
        print('Source census locked before inference.')
    else:
        report = evaluate(args.retained_root, args.out)
        print(json.dumps({name: row['0.5']['summary'] for name, row in report['arms'].items()}, indent=2))
