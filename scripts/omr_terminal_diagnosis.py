#!/usr/bin/env python3
"""Immutable, logging-only probes of two consumed terminal regions.

Supplied probe centers only select diagnostic log lines in the existing engine.
They never propose heads, change templates, or establish source correctness.
Historical study inputs, outputs, engine and runner are never changed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import signal
import subprocess

import omr_head_proposal_study as evidence
import omr_measure_consensus_paired as paired
import omr_score_audit as audit
import sh1991_fa_survival as survival
import sh1991_pilot as pilot

digest, load, immutable = evidence.digest, evidence.load, evidence.immutable


def check(out):
    p = load(Path(out)/'protocol.json')
    for path, sha in p['filesSha256'].items():
        if digest(path) != sha:
            raise ValueError('Diagnostic input/code drift: '+path)
    if pilot.engine_identity(Path(p['engineExecutable'])) != p['engine']:
        raise ValueError('Existing engine drift')
    return p


def freeze(config, out):
    config, out = Path(config).resolve(), Path(out).resolve()
    if (out/'protocol.json').exists():
        return check(out)
    p = load(config)
    parent = Path(p['retainedStudy']).resolve()
    original = paired.check(parent)
    if [c['id'] for c in p['cases']] != ['469', '501t']:
        raise ValueError('Only the two consumed diagnostic sources are allowed')
    files = [config, Path(__file__), parent/'protocol.json',
             *[Path(m.__file__) for m in (evidence, paired, audit, survival, pilot)]]
    rows = []
    for case in p['cases']:
        retained = next(c for c in original['cases'] if c['id'] == case['id'])
        directory = parent/'on'/case['id']
        rec = paired.verify_receipt(directory, digest(parent/'protocol.json'))
        if rec['status'] != 'exported':
            raise ValueError('Need successful retained comparator')
        case.update(source=retained['source'],
                    archivedGraph=str(directory/rec['graph']),
                    archivedExport=str(directory/rec['export']))
        files += [directory/'recognition.json', directory/'started.json',
                  *[directory/f for f in rec['artifactsSha256']], Path(case['source'])]
        if len(case['probes']) != 4 or len({r['id'] for r in case['probes']}) != 4:
            raise ValueError('Need four distinct source-selected diagnostic centers')
        for r in case['probes']:
            rows.append(f"{Path(case['source']).name}\t{r['id']}\t{r['x']}\t{r['y']}\n")
    out.mkdir(parents=True, exist_ok=True)
    points = out/'points.tsv'
    if points.exists():
        raise ValueError('Unfrozen points file already exists')
    points.write_text(''.join(rows))
    engine = Path(original['engineExecutable'])
    files += [points, Path(original['JAVA_HOME'])/'bin/java']
    # The executable fingerprint binds the distribution; source hashes support
    # causal reading without pretending source alone proves compiled behavior.
    engine_root = engine.parents[5]
    files += [engine_root/'app/src/main/java/org/audiveris/omr'/name for name in (
        'score/MeasureFixer.java', 'score/PartwiseBuilder.java',
        'sheet/note/NoteHeadsBuilder.java', 'glyph/ShapeSet.java')]
    p.update(engineExecutable=str(engine), engine=pilot.engine_identity(engine),
             JAVA_HOME=original['JAVA_HOME'], points=str(points),
             settings=original['settings'], createdAt=pilot.now(),
             phase='Consumed-source logging-only diagnostic; no recognition intervention',
             failurePolicy='One invocation per source. Started without receipt blocks retry. Exported score inventory must exactly reproduce retained on arm before interpreting probes.',
             sourceCertified=False, safeToPromote=False, wholeScoresAccepted=0,
             filesSha256={str(f.resolve()): digest(f) for f in files})
    immutable(out/'protocol.json', p)
    return check(out)


def verify(directory, sha):
    r = paired.verify_receipt(directory, sha)
    return r


def recognize(out, case):
    out = Path(out).resolve(); p = check(out); directory = out/case['id']
    sha = digest(out/'protocol.json')
    if (directory/'recognition.json').exists():
        return verify(directory, sha)
    if (directory/'started.json').exists():
        raise ValueError('Diagnostic already started; no implicit retry')
    opts = [v for v in p['settings']['JAVA_OPTS'].split()
            if not v.startswith('-Datlas.templatePoints=')]
    opts += ['-Datlas.barConsensus=true', '-Datlas.templatePoints='+p['points']]
    opts = ' '.join(opts)
    command = [p['engineExecutable'], '-batch', '-export']
    for constant in p['settings']['constants']:
        command += ['-constant', constant]
    command += ['-output', str(directory/'raw'), case['source']]
    immutable(directory/'started.json', dict(beganAt=pilot.now(), command=command,
              JAVA_OPTS=opts, protocolSha256=sha))
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
    graphs = list((directory/'raw').rglob('*.omr'))
    exports = list((directory/'raw').rglob('*.mxl'))
    files = [directory/'audiveris.log', *graphs, *exports]
    r = dict(protocolSha256=sha, endedAt=pilot.now(), exitCode=code,
             status='exported' if code == 0 and len(graphs) == len(exports) == 1 else 'recognition-failed',
             graph=str(graphs[0].relative_to(directory)) if len(graphs) == 1 else None,
             export=str(exports[0].relative_to(directory)) if len(exports) == 1 else None,
             artifactsSha256={str(f.relative_to(directory)): digest(f) for f in files})
    check(out); immutable(directory/'recognition.json', r)
    return r


def terminal(sheet, export):
    systems = sheet.findall('./page/system')
    if len(systems) != 1:
        raise ValueError('Only a single physical system is supported')
    system = systems[0]; stacks = system.findall('stack'); parts = system.findall('part')
    if not stacks or any(len(p.findall('measure')) != len(stacks) for p in parts):
        raise ValueError('Incomplete physical measure/stack correspondence')
    last = stacks[-1]; left, right = float(last.get('left')), float(last.get('right'))
    nodes = []
    for n in system.findall('./sig/inters/*'):
        b = n.find('bounds')
        if b is not None and left < float(b.get('x'))+float(b.get('w'))/2 < right:
            nodes.append(n)
    measures = [p.findall('measure')[-1] for p in parts]
    return dict(stack=dict(last.attrib), objectCounts=dict(Counter(n.tag for n in nodes)),
                measureHeadChordCounts=[len((m.findtext('head-chords') or '').split()) for m in measures],
                measureVoiceCounts=[len(m.findall('voice')) for m in measures],
                timedSlots=len(last.findall('slot')),
                exportedMeasures=[len(p.findall('measure')) for p in export.findall('part')],
                interpretation='Saved final snapshot only, not a per-step loss trace or source accuracy')


def probes(text, ids):
    rows = defaultdict(lambda: defaultdict(list))
    for line in text.splitlines():
        if not line.startswith('FAPROBE|'):
            continue
        c = line.split('|')
        if len(c) != 10 or c[1] not in ids:
            raise ValueError('Unexpected diagnostic probe line')
        rows[c[1]][c[2]].append(dict(distance=float(c[5]), hole=float(c[6]),
                                    anchor=c[7], seeded=c[8] == 'true', veto=c[9] == 'true'))
    return {key: {shape: dict(evaluations=len(values),
                 minimumDistance=min(v['distance'] for v in values),
                 physicalFaVetoes=sum(v['veto'] for v in values))
                 for shape, values in rows[key].items()} for key in ids}


def analyze(out):
    out = Path(out).resolve(); p = check(out); cases = {}
    for case in p['cases']:
        d = out/case['id']; r = verify(d, digest(out/'protocol.json'))
        if r['status'] != 'exported':
            cases[case['id']] = dict(status=r['status'], diagnostics=None); continue
        same = pilot.score((d/r['export']).read_bytes()) == pilot.score(Path(case['archivedExport']).read_bytes())
        if not same:
            cases[case['id']] = dict(status='control-mismatch', diagnostics=None); continue
        sheet = survival.read_xml(d/r['graph'], 'sheet#1/sheet#1.xml')
        export = survival.read_xml(d/r['export'])
        prior = survival.read_xml(Path(case['archivedGraph']), 'sheet#1/sheet#1.xml')
        cases[case['id']] = dict(status='exact-score-replay',
             terminal=terminal(sheet, export),
             archivedTerminal=terminal(prior, survival.read_xml(Path(case['archivedExport']))),
             probes=probes((d/'audiveris.log').read_text(), [r['id'] for r in case['probes']]))
    report = dict(cases=cases, protocolSha256=digest(out/'protocol.json'),
                  allScoreInventoriesExactlyReproduced=all(r['status']=='exact-score-replay' for r in cases.values()),
                  sourceCertified=False, safeToPromote=False, wholeScoresAccepted=0)
    check(out); immutable(out/'report.json', report)
    immutable(out/'receipt.json', dict(reportSha256=digest(out/'report.json'),
              recognitionSha256={c['id']: digest(out/c['id']/'recognition.json') for c in p['cases']}))
    return report


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--freeze'); a.add_argument('--out', required=True)
    a.add_argument('--run', action='store_true'); a.add_argument('--analyze', action='store_true')
    args = a.parse_args(); out = Path(args.out).resolve()
    if args.freeze:
        freeze(args.freeze, out)
    if args.run:
        p = check(out)
        for case in p['cases']:
            recognize(out, case)
    if args.analyze:
        print(json.dumps(analyze(out), indent=2))
