#!/usr/bin/env python3
"""Fresh-page, source-first evaluation of a frozen agent correction implementation.

This harness never reads reference XML. It consumes a pre-frozen protocol,
source-image receipts and source-only observations. It is not model training or
an independent source-observation verifier.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import sh1991_pilot as pilot
import sh1991_agent_correction as correction

WORK = pilot.DEFAULT_WORK / 'agent-unseen-v1-20261016'


def check(work):
    protocol = pilot.load(work/'protocol.json')
    sources = pilot.load(work/'sources.json')
    observations = pilot.load(work/'source-observations.json')
    if correction.digest(correction.__file__) != protocol['correctionSha256']:
        raise ValueError('Frozen correction implementation drift')
    if correction.digest(pilot.ROOT/'scripts/sh1991_agent_render.mjs') != protocol['rendererSha256']:
        raise ValueError('Frozen renderer drift')
    executable = Path(protocol['engineExecutable'])
    if pilot.engine_identity(executable) != protocol['engine']:
        raise ValueError('Frozen engine drift')
    if sources['protocolSha256'] != correction.digest(work/'protocol.json'):
        raise ValueError('Source protocol binding drift')
    cohort = {r['songNo'] for r in protocol['cohort']}
    if {r['songNo'] for r in sources['records']} != cohort:
        raise ValueError('Source cohort differs from frozen selection')
    if set(observations['expectedTopStaffMeasures']) != cohort:
        raise ValueError('Observer cohort differs from frozen selection')
    if observations['sourceCards'] != pilot.load(work/'review-selection.json')['cards']:
        raise ValueError('Observer selection drift')
    original = pilot.load(pilot.DEFAULT_WORK/'dataset.json')
    old_pages = {str(r['page']) for r in original['records']}
    if any(str(r['page']) in old_pages for r in protocol['cohort']):
        raise ValueError('Original consumed page leakage')
    old_hashes = {r['image']['sha256'] for r in original['records']}
    for row in sources['records']:
        if row['image']['sha256'] in old_hashes:
            raise ValueError('Original consumed source-image leakage')
        if correction.digest(pilot.ROOT/row['image']['path']) != row['image']['sha256']:
            raise ValueError('Source image drift')
    for card in observations['sourceCards']:
        if correction.digest(pilot.ROOT/card['card']) != card['cardSha256']:
            raise ValueError('Source card drift')
    return protocol, sources


def recognize(work):
    protocol, sources = check(work)
    # Copy and pin this launcher before launching inference; resuming cannot
    # silently use a changed controller or post-output observations.
    correction.immutable(work/'recognition-runner.py', Path(__file__).read_bytes())
    execution = {'protocolSha256': correction.digest(work/'protocol.json'),
                 'sourceObservationSha256': correction.digest(work/'source-observations.json'),
                 'sourceManifestSha256': correction.digest(work/'sources.json'),
                 'runnerSha256': correction.digest(__file__),
                 'settings': protocol['settings'], 'engine': protocol['engine']}
    correction.immutable(work/'execution.json', correction.json_bytes(execution))
    env = {**os.environ, 'JAVA_HOME': protocol['JAVA_HOME'],
           'JAVA_OPTS': protocol['settings']['JAVA_OPTS']}
    started_at = pilot.now()

    def page(row):
        directory = work/'candidate/baseline'/row['songNo']
        directory.mkdir(parents=True, exist_ok=True)
        receipt = directory/'run.json'
        command = [protocol['engineExecutable'], '-batch', '-export']
        for constant in protocol['settings']['constants']:
            command += ['-constant', constant]
        command += ['-output', str(directory), str((pilot.ROOT/row['image']['path']).resolve())]
        if receipt.exists():
            result = pilot.load(receipt)
            if (result['command'] != command or result['executionSha256'] != correction.digest(work/'execution.json')
                    or result['inputSha256'] != row['image']['sha256']):
                raise ValueError('Existing recognition receipt drift')
            if result.get('output') and correction.digest(pilot.ROOT/result['output']) != result['outputSha256']:
                raise ValueError('Existing output drift')
            return result
        marker = directory/'running.json'
        if marker.exists():
            prior = pilot.load(marker)
            try:
                os.kill(prior['pid'], 0)
            except ProcessLookupError:
                raise ValueError('Interrupted recognition without receipt; inspect retained log before a new experiment')
            raise ValueError(f"Recognition already running: PID {prior['pid']}")
        started = time.monotonic()
        timeout = False
        with (directory/'audiveris.log').open('w') as log:
            process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            marker.write_bytes(correction.json_bytes({'pid':process.pid, 'command':command, 'startedAt':pilot.now()}))
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
        exports = sorted(directory.rglob('*.mxl')) + sorted(directory.rglob('*.musicxml'))
        result = {'songNo':row['songNo'], 'command':command, 'inputSha256':row['image']['sha256'],
                  'executionSha256':correction.digest(work/'execution.json'), 'exitCode':code,
                  'timedOut':timeout, 'seconds':time.monotonic()-started,
                  'sourceCertified':False, 'safeToPromote':False,
                  'status':'exported' if code == 0 and len(exports)==1 else 'recognition-failed'}
        if result['status'] == 'exported':
            result.update(output=str(exports[0].relative_to(pilot.ROOT)), outputSha256=correction.digest(exports[0]))
        correction.immutable(receipt, correction.json_bytes(result))
        print(row['songNo'], result['status'], round(result['seconds'], 2), flush=True)
        return result

    with ThreadPoolExecutor(max_workers=2) as executor:
        records = list(executor.map(page, sources['records']))
    # Adapter layout matches the frozen correction v1 input interface. This
    # dataset has no label or candidate-reference path by design.
    correction.immutable(work/'candidate/dataset.json', correction.json_bytes({'records':sources['records']}))
    correction.immutable(work/'candidate/baseline-results.json', correction.json_bytes({'records':records}))
    completion = {'beganAt':started_at, 'endedAt':pilot.now(), 'records':records,
                  'sourceObservationSha256':execution['sourceObservationSha256'],
                  'candidateReferenceXmlRead':False, 'failedPages':sum(r['status']!='exported' for r in records)}
    # Run timestamps are retained only on first completion; receipt replay is
    # permitted, but never replaces the original completion history.
    if not (work/'recognition-complete.json').exists():
        correction.immutable(work/'recognition-complete.json', correction.json_bytes(completion))
    return completion


def evaluate(work):
    protocol, sources = check(work)
    execution = pilot.load(work/'execution.json')
    if execution['sourceObservationSha256'] != correction.digest(work/'source-observations.json'):
        raise ValueError('Source observations changed after recognition began')
    completion = pilot.load(work/'recognition-complete.json')
    if completion['failedPages']:
        # Every selected page remains in the result. Do not replace failures
        # or silently report a smaller successful cohort.
        result = {'cohort':protocol['cohort'], 'recognitionFailedPages':completion['failedPages'],
                  'scopedCyclePass':False, 'wholeScoreAcceptance':False,
                  'safeToPromote':False, 'humanReviewRequired':False,
                  'nextOwner':'agent', 'records':completion['records']}
    else:
        # Frozen correction v1 explicitly rejects output nested under its
        # source-evidence directory. Keep this fresh adapter's derivative as
        # a sibling too; do not weaken that preservation guard for the test.
        output = work.with_name(work.name+'-corrected')
        corrected = correction.run(work, output)
        correction.verify(work, output)
        correction.excerpts(work, output)
        render = subprocess.run(['node', str(pilot.ROOT/'scripts/sh1991_agent_render.mjs'), str(output)],
                                cwd=pilot.ROOT, timeout=120, capture_output=True, text=True)
        (work/'render-controller.log').write_text(render.stdout+render.stderr)
        receipt = pilot.load(output/'render-receipt.json') if (output/'render-receipt.json').exists() else None
        result = {'cohort':protocol['cohort'], 'recognitionFailedPages':0,
                  'summary':corrected['summary'], 'renderSummary':receipt['summary'] if receipt else None,
                  'scopedCyclePass':corrected['summary']['blocked']==0 and render.returncode==0,
                  'wholeScoreAcceptance':False, 'safeToPromote':False,
                  'humanReviewRequired':False, 'nextOwner':'agent',
                  'verificationLimits':protocol['knownLimits'],
                  'recognitionRunnerSha256':execution['runnerSha256'],
                  'analysisRunnerSha256':correction.digest(__file__),
                  'evidenceSha256':{str(p.relative_to(pilot.ROOT)):correction.digest(p) for p in
                                    [work/'protocol.json', work/'sources.json', work/'source-observations.json',
                                     work/'execution.json', work/'recognition-complete.json', output/'report.json']}}
        if receipt:
            result['evidenceSha256'][str((output/'render-receipt.json').relative_to(pilot.ROOT))] = correction.digest(output/'render-receipt.json')
    correction.immutable(work/'evaluation.json', correction.json_bytes(result))
    print(result)
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['recognize','evaluate'])
    parser.add_argument('--work',type=Path,default=WORK)
    args=parser.parse_args()
    result=(recognize if args.action=='recognize' else evaluate)(args.work.resolve())
    sys.exit(1 if result.get('failedPages',0) or result.get('scopedCyclePass') is False else 0)
