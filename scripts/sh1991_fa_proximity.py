#!/usr/bin/env python3
"""Frozen training-only fa proximity experiment and saved-artifact replay."""
import argparse
from collections import Counter
import math
import os
from pathlib import Path

import sh1991_pilot as pilot
import sh1991_fa_experiment as fa
import sh1991_fa_survival as survival
import sh1991_barline_trace as bars
from sh1991_barline_run import immutable
from sh1991_head_audit import heads_in_graph, match, write_report

WORK = pilot.DEFAULT_WORK / 'fa-discrimination-v3'
ARMS = ('control', 'v2-control', 'candidate')
BENCHMARK = pilot.ROOT / 'docs/experiments/sh1991-fa-discrimination-benchmark-20261015.json'


def run(arm):
    protocol = pilot.load(WORK / 'protocol.json')
    benchmark = pilot.load(BENCHMARK)
    if pilot.digest(BENCHMARK.read_bytes()) != protocol['benchmarkSha256']:
        raise ValueError('benchmark drift')
    dataset = pilot.load(fa.WORK / ('off' if arm == 'control' else 'on') / 'dataset.json')
    survival.verify_training_cohort(dataset, pilot.load(pilot.DEFAULT_WORK / 'dataset.json'), protocol['trainingProbe'])
    immutable(WORK / arm / 'dataset.json', dataset)
    toolchain = pilot.DEFAULT_WORK / 'toolchain'
    executable = toolchain / 'audiveris-fa-proximity-v3/app/build/install/app/bin/Audiveris'
    patch = pilot.ROOT / 'experiments/audiveris-fa-proximity-v3/fa-proximity.patch'
    engine = {'identity':pilot.engine_identity(executable), 'patchSha256':pilot.digest(patch.read_bytes()),
              'probePointsSha256':pilot.digest((WORK/'probe-points.tsv').read_bytes())}
    immutable(WORK/'engine.json', engine)
    java_home = str((toolchain / 'jdk25/jdk-25.0.4.1+1/Contents/Home').resolve())
    java_opts = '-Datlas.barTrace=true -Datlas.faStemBarGuard=true -Datlas.faBarProximity=' + str(arm == 'candidate').lower() + ' -Datlas.templatePoints=' + str((WORK/'probe-points.tsv').resolve())
    constants = ['org.audiveris.omr.sheet.ProcessingSwitches.faHeads=' + str(arm != 'control').lower(),
                 'org.audiveris.omr.Main.persistBatchCliConstants=false',
                 'org.audiveris.omr.sheet.note.NoteHeadsBuilder.dumpTemplateNotes=true']
    immutable(WORK/arm/'execution.json', {'JAVA_HOME':java_home, 'JAVA_OPTS':java_opts,
              'constants':constants, 'engine':engine, 'runnerSha256':pilot.digest(Path(__file__).read_bytes())})
    os.environ['JAVA_HOME'] = java_home; os.environ['JAVA_OPTS'] = java_opts
    pilot.run(WORK/arm, executable, 2, 180, engine_constants=constants)


def probes(text):
    result = {}
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.startswith('FAPROBE|'):
            continue
        p = line.split('|')
        if len(p) != 10:
            raise ValueError('malformed template probe')
        key, shape = p[1:3]
        distance = float(p[5]); hole = float(p[6])
        if not math.isfinite(distance) or p[8] not in ('true','false') or p[9] not in ('true','false'):
            raise ValueError('invalid template probe values')
        event = {'shape':shape,'x':float(p[3]),'y':float(p[4]),'distance':distance,
                 'holeWhiteRatio':hole if math.isfinite(hole) else None,
                 'anchor':p[7], 'seed':p[8]=='true','veto':p[9]=='true','line':line_no}
        entry = result.setdefault(key, {'evaluations':0,'vetoes':0,'bestByShape':{},'bestAllowedByShape':{}})
        entry['evaluations'] += 1; entry['vetoes'] += event['veto']
        for name in ('bestByShape','bestAllowedByShape'):
            if name == 'bestAllowedByShape' and event['veto']:
                continue
            if shape not in entry[name] or distance < entry[name][shape]['distance']:
                entry[name][shape] = event
    return result


def summarize(output):
    protocol = pilot.load(WORK/'protocol.json'); benchmark = pilot.load(BENCHMARK)
    if pilot.digest(BENCHMARK.read_bytes()) != protocol['benchmarkSha256']:
        raise ValueError('benchmark drift')
    if pilot.digest((pilot.ROOT/'docs/experiments/sh1991-head-shape-audit-20261015.json').read_bytes()) != benchmark['parentAuditSha256']:
        raise ValueError('original audit drift')
    original = pilot.load(WORK/'v2-original-inventory.json')
    for path, sha in original.items():
        if pilot.digest((pilot.ROOT/path).read_bytes()) != sha:
            raise ValueError('v2 artifact drift: '+path)
    engine = pilot.load(WORK/'engine.json')
    if pilot.digest((pilot.ROOT/'experiments/audiveris-fa-proximity-v3/fa-proximity.patch').read_bytes()) != engine['patchSha256']:
        raise ValueError('patch drift')
    if pilot.digest((WORK/'probe-points.tsv').read_bytes()) != engine['probePointsSha256']:
        raise ValueError('probe-point drift')
    expected = {r['id'] for r in benchmark['rows']}
    if len(expected) != len(benchmark['rows']) or len(expected) != 234:
        raise ValueError('benchmark duplicate or incomplete')
    parent = pilot.load(pilot.DEFAULT_WORK/'dataset.json'); arms = {}; evidence = {}
    for arm in ARMS:
        directory = WORK/arm; pilot.verify(directory)
        survival.verify_training_cohort(pilot.load(directory/'dataset.json'),parent,protocol['trainingProbe'])
        execution = pilot.load(directory/'execution.json')
        enabled = '-Datlas.faBarProximity='+str(arm=='candidate').lower()
        if enabled not in execution['JAVA_OPTS'].split() or execution['engine'] != engine:
            raise ValueError('execution environment drift')
        result = pilot.load(directory/'baseline-results.json'); pages = []; totals = Counter(); topology = Counter(); negatives = []; benchmark_rows = []
        if {r['songNo'] for r in result['records']} != set(protocol['trainingProbe']) or len(result['records']) != 5:
            raise ValueError('incomplete training receipt cohort')
        for receipt in result['records']:
            if receipt['engineIdentity'] != engine['identity'] or pilot.engine_identity(Path(receipt['command'][0])) != engine['identity']:
                raise ValueError('engine identity drift')
            required = 'org.audiveris.omr.sheet.ProcessingSwitches.faHeads='+str(arm!='control').lower()
            if required not in receipt['command']:
                raise ValueError('wrong experimental fa arm')
            song = receipt['songNo']; page_dir = directory/'baseline'/song
            if pilot.load(page_dir/'run.json') != receipt:
                raise ValueError('aggregate/per-image receipt mismatch')
            graph_files = list(page_dir.glob('*.omr'))
            if len(graph_files)!=1: raise ValueError('expected one retained graph')
            graph = graph_files[0]; export = pilot.ROOT/receipt['output']; log = page_dir/'audiveris.log'
            for path in (graph,export,log,page_dir/'run.json',directory/'execution.json'):
                evidence[str(path.relative_to(pilot.ROOT))] = pilot.digest(path.read_bytes())
            sheet = survival.read_xml(graph,'sheet#1/sheet#1.xml')
            rows, summary = survival.graph_rows(sheet,survival.read_xml(export)); heads = heads_in_graph(sheet)
            text = log.read_text(); trace = bars.parse_trace(text); proposed = probes(text)
            if set(proposed)-expected: raise ValueError('unknown probe row')
            selected = [r for r in benchmark['rows'] if r['songNo']==song]
            positive = [r for r in selected if r['label']=='head']; hits = match(positive,heads,.5)
            interline = float(sheet.find('scale/interline').get('main'))
            for source in selected:
                event = {'sourceId':source['id'],'label':source['label'],'shape':source['shape'],'fill':source['fill'],
                         'probes':proposed.get(source['id'],{'evaluations':0,'vetoes':0,'bestByShape':{},'bestAllowedByShape':{}})}
                if source['label']=='head':
                    head = hits.get(source['id']); event['retainedHead'] = rows[head['id']] if head else None
                else:
                    near = [h for h in heads if math.hypot(h['x']-source['x'],h['y']-source['y'])<=interline*.5]
                    event['nearbyRetainedHeads'] = near; negatives.append(event)
                benchmark_rows.append(event)
            totals.update(summary['stages']); topology.update(summary['topology'])
            prior_dir = pilot.DEFAULT_WORK/('fa-template-v1/off' if arm=='control' else 'barline-v2/revised')
            prior = next(r for r in pilot.load(prior_dir/'baseline-results.json')['records'] if r['songNo']==song)
            agreement = pilot.compare(pilot.score((pilot.ROOT/prior['output']).read_bytes()),pilot.score(export.read_bytes()))
            pages.append({'songNo':song, **summary,'barTrace':bars.compact_trace(trace),
                          'measureLog':survival.log_evidence(text),
                          'matchesPriorWrittenEvents':agreement['exactWrittenEvents'] and agreement['measureCountsMatch']})
        cohorts = {}
        for name, selection in [('triangle',[r for r in benchmark_rows if r['shape']=='triangle']),
                                ('other',[r for r in benchmark_rows if r['label']=='head' and r['shape']!='triangle'])]:
            cohorts[name]={'observed':len(selection),**{stage:sum(bool(r.get('retainedHead') and r['retainedHead'][stage]) for r in selection) for stage in survival.STAGES}}
        arms[arm]={'score':result['summary']['all'],'headAudit':fa.head_statistics(directory),'stages':dict(totals),'topology':dict(topology),
                   'sourceCohorts':cohorts,'nonHeadPoints':len(negatives),
                   'nonHeadPointsWithRetainedHeads':sum(bool(r['nearbyRetainedHeads']) for r in negatives),
                   'nonHeadNearbyRetainedHeadCount':sum(len(r['nearbyRetainedHeads']) for r in negatives),
                   'pages':pages,'benchmarkRows':benchmark_rows}
    if not all(p['matchesPriorWrittenEvents'] for a in ('control','v2-control') for p in arms[a]['pages']):
        raise ValueError('diagnostic/default-off control event drift')
    prior = pilot.load(pilot.ROOT/'docs/experiments/sh1991-barline-v2-20261015.json')
    for arm, old in [('control','off'),('v2-control','revised')]:
        for key in ('headAudit','stages','topology','score','sourceCohorts'):
            if arms[arm][key] != prior['arms'][old][key]:
                raise ValueError('diagnostic control metrics drift: '+arm+'/'+key)
    checks = fa.gate(protocol['selectionRule'],arms['control']['score'],arms['candidate']['score'],
                     arms['control']['headAudit'],arms['candidate']['headAudit'],True)
    report = {'schemaVersion':1,'protocol':protocol,'engine':engine,'benchmarkSha256':protocol['benchmarkSha256'],
              'arms':arms,'checks':checks,'passesAllTrainingGates':all(checks.values()),'sourceCertified':False,'safeToPromote':False,
              'heldOutRun':False,'v2FilesUnchanged':len(original),'evidenceSha256':evidence,
              'analysisScriptSha256':pilot.digest(Path(__file__).read_bytes()),
              'probeCaveat':'Best scanner-proposed distances within 0.5 interline, not exhaustive forced template scoring, calibrated probabilities, or an unbiased precision set. No proposals is explicit.'}
    for path,sha in evidence.items():
        if pilot.digest((pilot.ROOT/path).read_bytes())!=sha: raise ValueError('artifact changed during replay')
    write_report(output,report)
    for a,v in arms.items(): print(a,{k:v[k] for k in ('score','headAudit','stages','topology','sourceCohorts','nonHeadPointsWithRetainedHeads')})
    print('Gates',checks)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',choices=ARMS)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.run: run(args.run)
    elif args.output: summarize(args.output)
    else: parser.error('provide --run ARM or --output PATH')
