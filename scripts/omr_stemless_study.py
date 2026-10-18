#!/usr/bin/env python3
"""Frozen default-off stemless whole-note development experiment.

Retains consumed controls, never retries a started invocation, and forbids
candidate execution unless all same-binary controls exactly replay the archive.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import subprocess

import omr_head_proposal_study as evidence
import sh1991_pilot as pilot
import omr_score_audit as audit
import sh1991_fa_survival as survival

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
             Path(p['JAVA_HOME'])/'bin/java', *map(Path, p['extraInputs']), Path(audit.__file__), Path(survival.__file__)]
    for case in p['cases']:
        paths += [Path(case[k]) for k in ('source', 'archivedExport', 'archivedGraph')]
    if any(out == path or out in path.parents for path in paths):
        raise ValueError('Keep output outside retained inputs/code')
    p.update(createdAt=pilot.now(),
             phase='Consumed development only; same-binary property off/on; not held-out evidence',
             engine=pilot.engine_identity(Path(p['engineExecutable'])),
             filesSha256={str(path.resolve()): digest(path) for path in paths},
             failurePolicy='One invocation per arm/source; no implicit retry. All controls must exactly reproduce retained paired-v3 on-arm score inventories before candidate execution. No header normalization or outcome-driven threshold sweep.',
             candidateProperty='atlas.stemlessHeads',
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
    opts = p['settings']['JAVA_OPTS']+' -Datlas.stemlessHeads='+('true' if arm == 'on' else 'false')
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
        r = recognize(out, case, 'off') if execute else verify_receipt(directory, digest(out/'protocol.json'))
        same = r['status'] == 'exported' and pilot.score((directory/r['export']).read_bytes()) == pilot.score(Path(case['archivedExport']).read_bytes())
        rows.append(dict(source=case['id'], recognitionStatus=r['status'], exactInventoryReplay=same,
                         receiptSha256=digest(directory/'recognition.json')))
    result = dict(controls=rows, allControlsMatch=all(r['exactInventoryReplay'] for r in rows),
                  protocolSha256=digest(out/'protocol.json'))
    immutable(out/'controls.json', result)
    return result


def stage_trace(text, left, right):
    """Explicit zero stages are observed; missing stage records stay unavailable."""
    stages = {}; ids = {}
    for line in text.splitlines():
        c = line.split('|')
        if c[0] == 'STEMCOUNT':
            if len(c) != 5:
                raise ValueError('Malformed stage count')
            if c[2] == 'EXIT':
                key = c[1]
                stages.setdefault(key, dict(heads=0, terminalHeads=0, terminalChords=0,
                                           terminalVoicedHeads=0, newFamilyHeads=0))
        elif c[0] == 'STEMTRACE':
            if len(c) != 15:
                raise ValueError('Malformed head stage row')
            if c[2] != 'EXIT':
                continue
            key = c[1]; row = stages.setdefault(key, dict(heads=0, terminalHeads=0, terminalChords=0,
                                                         terminalVoicedHeads=0, newFamilyHeads=0))
            row['heads'] += 1
            row['newFamilyHeads'] += c[5] in FAMILIES
            center = float(c[7])+float(c[9])/2
            if left < center < right:
                row['terminalHeads'] += 1
                row['terminalVoicedHeads'] += int(c[14]) > 0
                if int(c[12]) > 0:
                    ids.setdefault(key,set()).add((c[3],c[12]))
    for key, value in stages.items():
        value['terminalChords'] = len(ids.get(key,set()))
    return {s: stages.get(s) for s in ('HEADS','REDUCTION','CHORDS','RHYTHMS','PAGE')}


FAMILIES = {'WHOLE_NOTE_NARROW','WHOLE_NOTE_FA_LEFT','WHOLE_NOTE_FA_UP_RIGHT','WHOLE_NOTE_SQUARE'}


def span_inventory(sheet, export):
    """No positional zip: exported labels must resolve to a unique physical span."""
    systems = sheet.findall('./page/system')
    if len(systems) != 1:
        raise ValueError('Need one physical system')
    stacks = systems[0].findall('stack')
    spans = {s.get('id'):(float(s.get('left')),float(s.get('right'))) for s in stacks}
    if len(spans) != len(stacks):
        raise ValueError('Ambiguous physical span identity')
    result = {}
    for segment in audit.inspect(export)['segments']:
        if segment['number'] not in spans:
            raise ValueError('Export without physical span')
        key = (segment['part'], *spans[segment['number']])
        if key in result:
            raise ValueError('Duplicate exported span')
        result[key] = segment['events']
    return result


def preservation(before, after):
    changed = [key for key,events in before.items() if after.get(key) != events]
    return dict(existingSpans=len(before), unchangedSpans=len(before)-len(changed),
                allExistingSpansExactlyPreserved=not changed,
                changedSpans=[list(k) for k in changed],
                addedSpans=[list(k) for k in after if k not in before])


def analyze(out):
    import omr_terminal_diagnosis as diagnosis
    import omr_measure_consensus_study as consensus
    import omr_acceptance_audit as acceptance
    out = Path(out).resolve(); p = check(out)
    controls = verify_controls(out); results = {}
    if not controls['allControlsMatch']:
        raise ValueError('Control mismatch; candidate interpretation blocked')
    for case in p['cases']:
        arms = {}; inventories = {}
        for arm in ('off','on'):
            d = out/arm/case['id']; r = verify_receipt(d,digest(out/'protocol.json'))
            if r['status'] != 'exported':
                arms[arm] = dict(status=r['status']); continue
            sheet = survival.read_xml(d/r['graph'],'sheet#1/sheet#1.xml')
            export = survival.read_xml(d/r['export'])
            stacks = sheet.findall('./page/system/stack')
            last = stacks[-1]
            inventories[arm] = span_inventory(sheet,export)
            arms[arm] = dict(status='exported', terminal=diagnosis.terminal(sheet,export),
                stages=stage_trace((d/'audiveris.log').read_text(),float(last.get('left')),float(last.get('right'))),
                wholeImageNewFamilyHeads=sum(n.get('shape') in FAMILIES for n in sheet.findall('.//sig/inters/head')))
            if case.get('sourceGrid'):
                observed = load(case['sourceGrid'])
                if observed['source']['sha256'] != digest(case['source']):
                    raise ValueError('Source observation identity differs')
                geometry = consensus.geometry_map(observed,sheet,export)
                arms[arm]['sourceAudit'] = acceptance.compare(observed,export,geometry['map'])
        results[case['id']] = dict(arms=arms, preservation=preservation(inventories['off'],inventories['on'])
                                  if len(inventories)==2 else None)
    report = dict(protocolSha256=digest(out/'protocol.json'), cases=results,
                  allControlsExactlyReplayed=True, safeToPromote=False, wholeScoresAccepted=0,
                  sourceCertified=False, exposure='Consumed development only; no held-out evaluation or source-certified score')
    check(out); immutable(out/'report.json',report)
    immutable(out/'receipt.json',dict(reportSha256=digest(out/'report.json'),
              recognitionSha256={arm+'/'+c['id']:digest(out/arm/c['id']/'recognition.json')
                                 for c in p['cases'] for arm in ('off','on')}))
    return report


def run(out):
    if not verify_controls(out, execute=True)['allControlsMatch']:
        raise ValueError('Default-off regression; no candidate execution')
    p = check(out)
    for case in p['cases']:
        recognize(out,case,'on')
    return analyze(out)


if __name__ == '__main__':
    import json
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--out',required=True,type=Path)
    group=a.add_mutually_exclusive_group(required=True)
    group.add_argument('--freeze',type=Path); group.add_argument('--run',action='store_true')
    group.add_argument('--analyze',action='store_true')
    args=a.parse_args()
    if args.freeze:
        freeze(args.freeze,args.out)
        print('Frozen before inference; no source coordinates supplied to engine.')
    else:
        result=run(args.out) if args.run else analyze(args.out)
        print(json.dumps(result,indent=2))
