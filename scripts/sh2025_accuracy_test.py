#!/usr/bin/env python3
"""Frozen one-page cross-edition study, retaining failures and prior exposure.

Prepare before inference. No parameter search, test-driven repair code changes,
prior Penn draft reading, model refit, publication or source promotion.
Source observations are repair inputs, not independent accuracy gold.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import sh1991_agent_correction as archive
import sh1991_pilot as pilot
import omr_score_audit as audit
import omr_source_repair as repair
import sh1991_symbol_classifier as classifier

WORK = pilot.DEFAULT_WORK/'accuracy-tracks-v1'
CODE = ['scripts/omr_score_audit.py', 'scripts/omr_source_repair.py',
        'scripts/sh1991_symbol_classifier.py', 'scripts/sh2025_accuracy_test.py',
        'scripts/sh1991_agent_correction.py', 'scripts/agent_03_semantic_musicxml.py']
INPUTS = ['sh2025-selection-final.json', 'penn-source-observations-final.json',
          'penn-symbol-observations-final.json', 'symbol-study-final/model.json',
          'symbol-study-final/protocol.json']


def prepare(work):
    parent = pilot.load(pilot.DEFAULT_WORK/'agent-unseen-v1-20261016/protocol.json')
    observations = pilot.load(work/'penn-source-observations-final.json')
    audit.validate_observations(observations)
    selected = pilot.load(work/'sh2025-selection-final.json')['selected']
    if len(selected) != 1 or selected[0]['songNo'] != observations['songNo']:
        raise ValueError('Frozen test selection/observation drift')
    if pilot.engine_identity(Path(parent['engineExecutable'])) != parent['engine']:
        raise ValueError('V7 recognizer drift')
    source = archive.ROOT/observations['source']['path']
    if archive.digest(source) != observations['source']['sha256']:
        raise ValueError('Source image drift')
    constants = dict(parent['settings'])
    points = Path(constants['JAVA_OPTS'].split('-Datlas.templatePoints=', 1)[1].split()[0])
    protocol = {'study': 'SH2025 Penn one-page cross-edition accuracy-track test',
                'selection': selected, 'source': observations['source'],
                'engineExecutable': parent['engineExecutable'], 'engine': parent['engine'],
                'JAVA_HOME': parent['JAVA_HOME'], 'settings': constants,
                'templatePointsPath': str(points), 'templatePointsSha256': archive.digest(points),
                'codeSha256': {p: archive.digest(archive.ROOT/p) for p in CODE},
                'inputsSha256': {p: archive.digest(work/p) for p in INPUTS},
                'scope': {'pitchRhythmStaffMeasures': 48, 'sourceEvents': 120, 'symbolCrops': 48,
                          'sourceTiePairs': 8},
                'priorExposure': 'Penn generic OMR/metadata/OCR exists locally; no old Penn draft or reference XML read in this run. Not never-processed novelty.',
                'failurePolicy': 'Retain selected page and failed output in denominator; never replace or silently retry. Explicit hash-bound measure map allowed after reading output, not label/code changes.',
                'noModelRefit': True, 'noTestDrivenTuning': True,
                'independentSourceGold': False, 'safeToPromote': False}
    archive.immutable(work/'penn-test/protocol.json', archive.json_bytes(protocol))
    for p in CODE:
        archive.immutable(work/'penn-test/frozen-code'/Path(p).name, (archive.ROOT/p).read_bytes())
    return protocol


def check(work):
    protocol = pilot.load(work/'penn-test/protocol.json')
    for p, sha in protocol['codeSha256'].items():
        if archive.digest(archive.ROOT/p) != sha:
            raise ValueError('Frozen study code drift: '+p)
    for p, sha in protocol['inputsSha256'].items():
        if archive.digest(work/p) != sha:
            raise ValueError('Frozen study input drift: '+p)
    if archive.digest(archive.ROOT/protocol['source']['path']) != protocol['source']['sha256']:
        raise ValueError('Frozen source drift')
    if archive.digest(protocol['templatePointsPath']) != protocol['templatePointsSha256']:
        raise ValueError('Frozen template point drift')
    if pilot.engine_identity(Path(protocol['engineExecutable'])) != protocol['engine']:
        raise ValueError('Frozen engine drift')
    return protocol


def recognize(work):
    protocol = check(work)
    directory = work/'penn-test'
    receipt_path = directory/'recognition.json'
    if receipt_path.exists():
        receipt = pilot.load(receipt_path)
        if receipt['protocolSha256'] != archive.digest(directory/'protocol.json'):
            raise ValueError('Recognition protocol binding drift')
        if receipt.get('output') and archive.digest(archive.ROOT/receipt['output']) != receipt['outputSha256']:
            raise ValueError('Raw recognition output drift')
        return receipt
    if (directory/'started.json').exists():
        raise ValueError('Prior recognition started; inspect retained log, never silently retry')
    raw = directory/'raw'
    raw.mkdir(parents=True, exist_ok=True)
    command = [protocol['engineExecutable'], '-batch', '-export']
    for constant in protocol['settings']['constants']:
        command += ['-constant', constant]
    command += ['-output', str(raw.resolve()), str((archive.ROOT/protocol['source']['path']).resolve())]
    archive.immutable(directory/'started.json', archive.json_bytes({'beganAt': pilot.now(), 'command': command,
                      'protocolSha256': archive.digest(directory/'protocol.json')}))
    env = {**os.environ, 'JAVA_HOME': protocol['JAVA_HOME'], 'JAVA_OPTS': protocol['settings']['JAVA_OPTS']}
    started = time.monotonic()
    with (directory/'audiveris.log').open('w') as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=log, start_new_session=True)
        timeout = False
        try:
            code = process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            timeout = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            code = 124
    exports = sorted(raw.rglob('*.mxl'))
    receipt = {'protocolSha256': archive.digest(directory/'protocol.json'), 'command': command,
               'exitCode': code, 'timedOut': timeout, 'seconds': time.monotonic()-started,
               'status': 'exported' if code == 0 and len(exports) == 1 else 'recognition-failed',
               'selectedPages': 1, 'failedPages': int(code != 0 or len(exports) != 1),
               'endedAt': pilot.now(), 'logSha256': archive.digest(directory/'audiveris.log')}
    if receipt['status'] == 'exported':
        receipt.update(output=str(exports[0].relative_to(archive.ROOT)), outputSha256=archive.digest(exports[0]))
    archive.immutable(receipt_path, archive.json_bytes(receipt))
    print(json.dumps(receipt))
    return receipt


def evaluate(work):
    check(work)
    directory = work/'penn-test'
    recognition = recognize(work)  # Receipt-only replay; never reruns completed inference.
    symbol = classifier.test_model(work/'symbol-study-final/model.json',
                                   work/'penn-symbol-observations-final.json', directory/'symbols')
    result = {'recognition': recognition, 'symbols': {k: symbol[k] for k in ('samples', 'correct')},
              'independentSourceGold': False, 'safeToPromote': False, 'sourceCertified': False}
    if recognition['status'] == 'exported':
        score = archive.ROOT/recognition['output']
        before = audit.inspect(audit.read(score))
        archive.immutable(directory/'structure-before.json', archive.json_bytes(before))
        obs = pilot.load(work/'penn-source-observations-final.json')
        map_path = directory/'measure-map.json'
        if before['measureCounts'] != obs['expectedMeasuresPerPart'] and not map_path.exists():
            archive.immutable(directory/'needs-measure-map.json', archive.json_bytes({
                'status': 'blocked-explicit-source-draft-measure-map-required', 'counts': before['measureCounts'],
                'expectedCounts': obs['expectedMeasuresPerPart'], 'draftSha256': archive.digest(score)}))
            print('Explicit measure map required:', before['measureCounts'])
            return result
        fixed = repair.run(score, work/'penn-source-observations-final.json', directory/'corrected',
                           map_path if map_path.exists() else None)
        result['repair'] = {k: fixed[k] for k in ('checkedStaffMeasures', 'summary', 'ties', 'secondParser')}
    archive.immutable(directory/'evaluation.json', archive.json_bytes(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'recognize', 'evaluate'])
    parser.add_argument('--work', type=Path, default=WORK)
    args = parser.parse_args()
    {'prepare': prepare, 'recognize': recognize, 'evaluate': evaluate}[args.action](args.work.resolve())
