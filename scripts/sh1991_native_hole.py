#!/usr/bin/env python3
"""Same-binary training-only native Fa hole reassignment experiment and replay."""
import argparse
from collections import Counter
import os
from pathlib import Path
import sh1991_pilot as pilot
import sh1991_fa_experiment as fa
import sh1991_fa_survival as survival
from sh1991_barline_run import immutable
from sh1991_head_audit import write_report, heads_in_graph, match
from omr_point_eval import summarize_points
from sh1991_eval_diagnostics import prediction
WORK=pilot.DEFAULT_WORK/'native-hole-v6'
ENGINE=pilot.DEFAULT_WORK/'toolchain/audiveris-native-hole-v6'
ARMS=('reference','v3-control','candidate')

def checked():
    protocol=pilot.load(WORK/'protocol.json')
    if protocol!=pilot.load(pilot.ROOT/'experiments/audiveris-native-hole-v6/protocol.json'): raise ValueError('protocol drift')
    if pilot.digest((pilot.DEFAULT_WORK/'anchor-v5/report.json').read_bytes())!=protocol['parentDiagnosticSha256']: raise ValueError('diagnostic drift')
    dataset=pilot.load(pilot.DEFAULT_WORK/'fa-discrimination-v3/candidate/dataset.json')
    survival.verify_training_cohort(dataset,pilot.load(pilot.DEFAULT_WORK/'dataset.json'),protocol['trainingProbe'])
    return protocol,dataset

def settings(arm):
    opts='-Datlas.barTrace=true -Datlas.faStemBarGuard=true -Datlas.faBarProximity=true -Datlas.nativeFaHole='+str(arm=='candidate').lower()
    constants=['org.audiveris.omr.sheet.ProcessingSwitches.faHeads='+str(arm!='reference').lower(),'org.audiveris.omr.Main.persistBatchCliConstants=false','org.audiveris.omr.sheet.note.NoteHeadsBuilder.dumpTemplateNotes=true']
    return opts,constants

def run(arm):
    protocol,dataset=checked();executable=ENGINE/'app/build/install/app/bin/Audiveris'
    engine={'identity':pilot.engine_identity(executable),'patchSha256':pilot.digest((pilot.ROOT/'experiments/audiveris-native-hole-v6/native-hole.patch').read_bytes())}
    immutable(WORK/'engine.json',engine);directory=WORK/arm;immutable(directory/'dataset.json',dataset)
    opts,constants=settings(arm);java_home=str(pilot.DEFAULT_WORK/'toolchain/jdk25/jdk-25.0.4.1+1/Contents/Home')
    immutable(directory/'execution.json',{'JAVA_HOME':java_home,'JAVA_OPTS':opts,'constants':constants,'engine':engine,'runnerSha256':pilot.digest(Path(__file__).read_bytes()),'protocolSha256':pilot.digest((WORK/'protocol.json').read_bytes())})
    os.environ['JAVA_HOME']=java_home;os.environ['JAVA_OPTS']=opts
    pilot.run(directory,executable,2,180,engine_constants=constants)

def summarize(output):
    protocol,_=checked();prior=pilot.load(pilot.ROOT/'docs/experiments/sh1991-fa-proximity-v3-20261015.json');engine=pilot.load(WORK/'engine.json')
    if pilot.engine_identity(ENGINE/'app/build/install/app/bin/Audiveris')!=engine['identity']: raise ValueError('engine drift')
    if pilot.digest((pilot.ROOT/'experiments/audiveris-native-hole-v6/native-hole.patch').read_bytes())!=engine['patchSha256']: raise ValueError('patch drift')
    benchmark=pilot.load(pilot.ROOT/'docs/experiments/sh1991-fa-discrimination-benchmark-20261015.json')
    if pilot.digest((pilot.ROOT/'docs/experiments/sh1991-fa-discrimination-benchmark-20261015.json').read_bytes())!=prior['benchmarkSha256']: raise ValueError('benchmark drift')
    arms={};evidence={};controls={}
    for arm in ARMS:
        directory=WORK/arm;pilot.verify(directory);result=pilot.load(directory/'baseline-results.json');execution=pilot.load(directory/'execution.json');opts,constants=settings(arm)
        if execution['JAVA_OPTS']!=opts or execution['constants']!=constants or execution['engine']!=engine or execution['runnerSha256']!=pilot.digest(Path(__file__).read_bytes()): raise ValueError('execution drift')
        if {r['songNo'] for r in result['records']}!=set(protocol['trainingProbe']): raise ValueError('incomplete cohort')
        pages=[];points=[];totals=Counter();topology=Counter();retained=[]
        for receipt in result['records']:
            if receipt['engineIdentity']!=engine['identity'] or receipt['status']!='exported': raise ValueError('failed or stale recognition')
            page=directory/'baseline'/receipt['songNo'];graphs=list(page.glob('*.omr'))
            if len(graphs)!=1: raise ValueError('missing graph')
            sheet=survival.read_xml(graphs[0],'sheet#1/sheet#1.xml');graph_rows,stats=survival.graph_rows(sheet,survival.read_xml(pilot.ROOT/receipt['output']));heads=heads_in_graph(sheet)
            selected=[r for r in benchmark['rows'] if r['songNo']==receipt['songNo'] and r['label']=='head'];hits=match(selected,heads,.5)
            for source in selected:
                native=graph_rows[hits[source['id']]['id']] if source['id'] in hits else None
                points.append({'id':source['id'],'songNo':source['songNo'],'sourceShape':source['shape'],'sourceFill':source['fill'],'prediction':prediction(native)})
                retained.append({'sourceId':source['id'],'shape':source['shape'],'fill':source['fill'],'retainedHead':native})
            totals.update(stats['stages']);topology.update(stats['topology']);pages.append({'songNo':receipt['songNo'],**stats})
            if arm!='candidate':
                old_arm='control' if arm=='reference' else 'candidate';old=next(r for r in pilot.load(pilot.DEFAULT_WORK/'fa-discrimination-v3'/old_arm/'baseline-results.json')['records'] if r['songNo']==receipt['songNo'])
                c=pilot.compare(pilot.score((pilot.ROOT/old['output']).read_bytes()),pilot.score((pilot.ROOT/receipt['output']).read_bytes()))
                controls[arm+'/'+receipt['songNo']]=c['exactWrittenEvents'] and c['measureCountsMatch']
            for path in [page/'audiveris.log',page/'run.json',graphs[0],pilot.ROOT/receipt['output'],directory/'execution.json']:
                evidence[str(path.relative_to(pilot.ROOT))]=pilot.digest(path.read_bytes())
        arms[arm]={'score':result['summary']['all'],'headAudit':fa.head_statistics(directory),'stages':dict(totals),'topology':dict(topology),'pages':pages,'benchmarkRows':retained}
        # The reusable evaluator uses source and prediction fields; retain exact source row schema.
        from sh1991_eval_diagnostics import prediction as pred
        adapted=[{'id':source['sourceId'],'source':{'shape':source['shape'],'fill':source['fill']},'prediction':pred(source['retainedHead'])} for source in retained]
        arms[arm]['sourcePoints']=adapted
    if not all(controls.values()): raise ValueError('default-off control written events drift')
    for arm,old in [('reference','control'),('v3-control','candidate')]:
        for key in ('score','headAudit','stages','topology'):
            if arms[arm][key]!=prior['arms'][old][key]: raise ValueError('control metric drift '+arm+'/'+key)
    checks=fa.gate(protocol['selectionRule'],arms['reference']['score'],arms['candidate']['score'],arms['reference']['headAudit'],arms['candidate']['headAudit'],all(controls.values()))
    report={'schemaVersion':1,'protocol':protocol,'engine':engine,'controls':controls,'checks':checks,'passesAllTrainingGates':all(checks.values()),'arms':arms,'evidenceSha256':evidence,'analysisScriptSha256':pilot.digest(Path(__file__).read_bytes()),'heldOutRun':False,'sourceCertified':False,'safeToPromote':False}
    write_report(output,report);print('gates',checks)
    for arm in ARMS: print(arm,arms[arm]['headAudit'],arms[arm]['score'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',choices=ARMS);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.run:run(a.run)
    elif a.output:summarize(a.output)
    else:p.error('provide --run ARM or --output PATH')
