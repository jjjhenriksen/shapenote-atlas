#!/usr/bin/env python3
"""One pre-source-frozen transfer of the unchanged #485 head-proposal recipe.

Only new output directories are writable. Source observations precede native
recognition and proposal inference. No historical experiment is executed again.
"""
from __future__ import annotations

import argparse
from collections import Counter
import math
import os
from pathlib import Path
import signal
import subprocess

import omr_head_proposal_study as prior
import omr_localization_study as native

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('work/source-images/2025/531-clayton-c4e7caa825.jpg')
SELECTION = Path('work/model-pilot/sh1991-v1/accuracy-tracks-v1/sh2025-selection-final.json')
digest, load, immutable = prior.digest, prior.load, prior.immutable


def check_bindings(bindings, root):
    for relative, expected in bindings.items():
        if digest(Path(root)/relative) != expected:
            raise ValueError('Frozen input/code drift: '+relative)


def prepare(retained, out):
    import numpy
    from PIL import __version__ as pillow
    retained, out = Path(retained).resolve(), Path(out).resolve()
    if out == retained or retained in out.parents:
        raise ValueError('Keep transfer output outside retained evidence checkout')
    existing = out/'protocol.json'
    if existing.exists():
        return check(retained, out)  # Never silently refreeze.
    selected = load(retained/SELECTION)['eligible'][5]
    if selected['songNo'] != '531':
        raise ValueError('Original sixth-source rank drift')
    labels, report, manifest = prior.retained_evidence(retained)
    source_sha = digest(retained/SOURCE)
    if source_sha in {r['sourceSha256'] for r in manifest['samples']}:
        raise ValueError('Transfer source entered training')
    engine = load(retained/prior.PRIOR/'development-protocol.json')
    if native.pilot.engine_identity(Path(engine['engineExecutable'])) != engine['engine']:
        raise ValueError('Fixed V7 engine drift')
    engine_inputs = load(retained/'work/model-pilot/sh1991-v1/accuracy-tracks-v1/penn-test/protocol.json')
    if digest(engine_inputs['templatePointsPath']) != engine_inputs['templatePointsSha256']:
        raise ValueError('Fixed template points drift')
    old = prior.protocol(retained)
    inputs = dict(old['retainedInputsSha256'])
    engine_input_path = Path('work/model-pilot/sh1991-v1/accuracy-tracks-v1/penn-test/protocol.json')
    inputs[str(engine_input_path)] = digest(retained/engine_input_path)
    for path in (SOURCE, SELECTION):
        inputs[str(path)] = digest(retained/path)
    modules = (prior, native, native.native, native.pilot)
    code = dict(old['codeSha256'])
    for module in modules:
        code[str(Path(module.__file__).relative_to(ROOT))] = digest(module.__file__)
    code[str(Path(__file__).relative_to(ROOT))] = digest(__file__)
    protocol = {
        'createdAt': native.pilot.now(), 'source': 'SH2025/531',
        'sourcePath': str(SOURCE), 'sourceSha256': source_sha, 'selected': selected,
        'selectionRule': 'Sixth original hash-ranked eligible source; previous five consumed. No outcome-based replacement.',
        'exposure': 'New source census for this transfer; catalogue metadata and generic archived OMR may exist. Not a globally untouched page.',
        'scope': 'Opening system, first four written measure spans including pickup if present, entire system if fewer; all pitched heads in four complete supplied staff windows.',
        'observations': 'Source-only same-agent provisional census before inference, unresolved literal labels stay null; not independent gold.',
        'recipe': old['recipe'], 'matchingRecipe': old['matchingRecipe'],
        'primaryArm': 'native-plus-selective-squares',
        'training': 'Unchanged archived 373-exemplar bank; no transfer exemplars added.',
        'retainedInputsSha256': inputs, 'codeSha256': code,
        'numpyVersion': numpy.__version__, 'pillowVersion': pillow,
        'engineExecutable': engine['engineExecutable'], 'engine': engine['engine'],
        'JAVA_HOME': engine['JAVA_HOME'], 'settings': engine['settings'],
        'externalFilesSha256': {engine_inputs['templatePointsPath']: digest(engine_inputs['templatePointsPath']),
                               str(Path(engine['JAVA_HOME'])/'bin/java'): digest(Path(engine['JAVA_HOME'])/'bin/java')},
        'recognitionPolicy': 'Exactly one run after census lock; no retry/replacement on failure; completed reuse verifies artifact bytes.',
        'failurePolicy': 'Retain all source/candidate denominators and all arms/radii. No tuning on transfer results. Recognition failure leaves native/fused metrics unavailable, never zero.',
        'sourceCertified': False, 'safeToPromote': False,
    }
    immutable(existing, protocol)
    return protocol


def check(retained, out):
    import numpy
    from PIL import __version__ as pillow
    p = load(Path(out)/'protocol.json')
    check_bindings(p['retainedInputsSha256'], retained)
    check_bindings(p['codeSha256'], ROOT)
    check_bindings(p['externalFilesSha256'], Path('/'))
    if (numpy.__version__, pillow) != (p['numpyVersion'], p['pillowVersion']):
        raise ValueError('Frozen dependency drift')
    if native.pilot.engine_identity(Path(p['engineExecutable'])) != p['engine']:
        raise ValueError('Frozen engine drift')
    return p


def validate_census(labels, protocol, image_size):
    if (labels['sourceSha256'] != protocol['sourceSha256']
            or labels['completeHeadCensus'] is not True):
        raise ValueError('Require source-bound complete census')
    windows, rows = labels['windows'], labels['rows']
    if [w['staff'] for w in windows] != [0, 1, 2, 3]:
        raise ValueError('Require four ordered staff windows')
    width, height = image_size
    for i, w in enumerate(windows):
        a, b, c, d = w['box']
        if (not all(math.isfinite(v) for v in (a, b, c, d))
                or not 0 <= a < c <= width or not 0 <= b < d <= height
                or (i and windows[i-1]['box'][3] > b)):
            raise ValueError('Invalid or overlapping window')
    if not rows or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Empty/duplicate census')
    for r in rows:
        if type(r['staff']) is not int or r['staff'] not in range(4):
            raise ValueError('Unknown source staff')
        a, b, c, d = windows[r['staff']]['box']
        if (not all(math.isfinite(r[k]) for k in ('x', 'y', 'interline'))
                or r['interline'] < 3 or not a <= r['x'] < c or not b <= r['y'] < d):
            raise ValueError('Invalid source center/spacing')
        if r['label'] is not None and r['label'] not in prior.training.prior.geometry.GLYPHS:
            raise ValueError('Unknown literal label')


def lock_census(retained, out, labels_path):
    from PIL import Image
    out = Path(out); protocol = check(retained, out)
    labels = load(labels_path)
    with Image.open(Path(retained)/SOURCE) as image:
        validate_census(labels, protocol, image.size)
    immutable(out/'source-observations.json', labels)
    immutable(out/'inference-lock.json', {
        'protocolSha256': digest(out/'protocol.json'),
        'labelsSha256': digest(out/'source-observations.json')})
    return protocol, labels


def recognize(retained, out, p):
    out = Path(out)
    if (out/'recognition.json').exists():
        receipt = load(out/'recognition.json')
        if receipt['inferenceLockSha256'] != digest(out/'inference-lock.json'):
            raise ValueError('Recognition lock drift')
        check_bindings(receipt['artifactsSha256'], out)
        return receipt
    raw = out/'raw'
    command = [p['engineExecutable'], '-batch', '-export']
    for value in p['settings']['constants']:
        command += ['-constant', value]
    command += ['-output', str(raw.resolve()), str((Path(retained)/SOURCE).resolve())]
    started = out/'started.json'
    if started.exists():
        raise ValueError('Recognition already started; no implicit retry')
    immutable(started, {'command': command, 'beganAt': native.pilot.now(),
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
              'exitCode': code, 'endedAt': native.pilot.now(),
              'status': 'graph-ready' if code == 0 and len(graphs) == 1 else 'recognition-failed',
              'graph': str(graphs[0].relative_to(out)) if len(graphs) == 1 else None,
              'artifactsSha256': {str(f.relative_to(out)): digest(f) for f in artifacts}}
    check(retained, out)
    immutable(out/'recognition.json', result)
    return result


def evaluate(retained, out):
    from PIL import Image
    out = Path(out); p = check(retained, out)
    labels = load(out/'source-observations.json'); lock = load(out/'inference-lock.json')
    if (lock['protocolSha256'] != digest(out/'protocol.json')
            or lock['labelsSha256'] != digest(out/'source-observations.json')):
        raise ValueError('Source/inference lock drift')
    receipt = recognize(retained, out, p)
    if (out/'report.json').exists():
        saved = load(out/'receipt.json')
        if (saved['reportSha256'] != digest(out/'report.json')
                or saved['recognitionSha256'] != digest(out/'recognition.json')):
            raise ValueError('Completed report/recognition drift')
        return load(out/'report.json')
    _, old, manifest = prior.retained_evidence(Path(retained))
    bank = prior.fit_bank(Path(retained), manifest, p['sourceSha256'])
    with Image.open(Path(retained)/SOURCE) as image:
        validate_census(labels, p, image.size)
        detected = prior.detector.propose(image, labels['windows'])
        proposals = prior.classify(image, detected['proposals'], bank)
        squares = [r for r in proposals if r.get('selectivePrediction') == 'square/filled']
        arms = {'image-only-all-cores': proposals, 'image-only-selective-squares': squares}
        suppressed = []; heads = None
        if receipt['status'] == 'graph-ready':
            heads = native.graph_heads(out/receipt['graph'], Path(retained)/SOURCE, image.size)
            queries = []
            for h in heads:
                for w, lattice in zip(labels['windows'], detected['staffLattices']):
                    a, b, c, d = w['box']
                    if a <= h['x'] < c and b <= h['y'] < d:
                        row = dict(h, staff=w['staff'], origin='native')
                        if lattice['status'] == 'proposal':
                            row['interline'] = lattice['interline']
                            row = prior.classify(image, [row], bank)[0]
                        else:
                            row.update(prediction=None, selectivePrediction=None,
                                       reason='unresolved-auto-staff-lattice')
                        queries.append(row)
            fused, suppressed = prior.detector.fuse(queries, squares)
            arms.update({'native': queries, 'native-plus-selective-squares': fused})
    report = {'protocolSha256': digest(out/'protocol.json'),
              'inferenceLockSha256': digest(out/'inference-lock.json'),
              'recognitionSha256': digest(out/'recognition.json'),
              'source': p['source'], 'sourceHeadCount': len(labels['rows']),
              'sourceByClass': dict(Counter(r['label'] or 'unresolved' for r in labels['rows'])),
              'primaryArm': p['primaryArm'], 'recognitionStatus': receipt['status'],
              'nativeHeadNodesAllImage': len(heads) if heads is not None else None,
              'arms': {name: prior.summarize(labels['rows'], rows) for name, rows in arms.items()},
              'candidateStages': {'denseCoreProposals': len(proposals), 'selectiveSquares': len(squares),
                                  'geometricVetoes': len(detected['geometricVetoes']), 'suppressed': len(suppressed)},
              'predictions': arms, 'suppressed': suppressed,
              'staffLattices': detected['staffLattices'], 'geometricVetoes': detected['geometricVetoes'],
              'sourceCertified': False, 'safeToPromote': False, 'wholeScoresAccepted': 0,
              'pitchRhythmAccuracy': None, 'exportedEventAccuracy': None,
              'measuredHumanMinutes': None}
    check(retained, out)
    if digest(out/'source-observations.json') != lock['labelsSha256']:
        raise ValueError('Census changed during inference')
    immutable(out/'report.json', report)
    immutable(out/'receipt.json', {'reportSha256': digest(out/'report.json'),
                                 'recognitionSha256': digest(out/'recognition.json')})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retained-root', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--labels', type=Path)
    mode.add_argument('--evaluate', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        prepare(args.retained_root, args.out); print('Frozen before source viewing.')
    elif args.labels:
        lock_census(args.retained_root, args.out, args.labels); print('Source census locked before inference.')
    else:
        r = evaluate(args.retained_root, args.out)
        import json
        print(json.dumps({name: values['0.5']['summary'] for name, values in r['arms'].items()}, indent=2))
