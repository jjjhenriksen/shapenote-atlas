#!/usr/bin/env python3
"""Pinned training-only read-only forced template scores at explicit internal anchors."""
import argparse
from collections import Counter, defaultdict
import json
import math
import os
from pathlib import Path
import sh1991_pilot as pilot
import sh1991_fa_experiment as fa
import sh1991_fa_survival as survival
from sh1991_barline_run import immutable
from sh1991_head_audit import write_report

WORK=pilot.DEFAULT_WORK/'anchor-v5'
ENGINE=pilot.DEFAULT_WORK/'toolchain/audiveris-anchor-v5'
BENCHMARK=pilot.ROOT/'docs/experiments/sh1991-fa-discrimination-benchmark-20261015.json'
ARMS=('off','forced')

def validate():
    protocol=pilot.load(WORK/'protocol.json')
    if protocol != pilot.load(pilot.ROOT/'experiments/audiveris-anchor-v5/protocol.json'):
        raise ValueError('protocol drift')
    if pilot.digest(BENCHMARK.read_bytes()) != protocol['benchmarkSha256']:
        raise ValueError('benchmark drift')
    if pilot.digest((WORK/'points.tsv').read_bytes()) != protocol['pointsSha256']:
        raise ValueError('point file drift')
    dataset=pilot.load(pilot.DEFAULT_WORK/'fa-discrimination-v3/candidate/dataset.json')
    survival.verify_training_cohort(dataset,pilot.load(pilot.DEFAULT_WORK/'dataset.json'),protocol['trainingProbe'])
    return protocol,dataset

def run(arm):
    protocol,dataset=validate()
    executable=ENGINE/'app/build/install/app/bin/Audiveris'
    engine={'identity':pilot.engine_identity(executable), 'sourceSha256':{name:pilot.digest((pilot.ROOT/'experiments/audiveris-anchor-v5'/name).read_bytes()) for name in ['ForcedTemplateProbe.java','probe-call.patch']}}
    immutable(WORK/'engine.json',engine)
    directory=WORK/arm
    immutable(directory/'dataset.json',dataset)
    java_home=str(pilot.DEFAULT_WORK/'toolchain/jdk25/jdk-25.0.4.1+1/Contents/Home')
    opts='-Datlas.barTrace=true -Datlas.faStemBarGuard=true -Datlas.faBarProximity=true'
    if arm=='forced': opts+=' -Datlas.forcedTemplatePoints='+str(WORK/'points.tsv')
    constants=['org.audiveris.omr.sheet.ProcessingSwitches.faHeads=true','org.audiveris.omr.Main.persistBatchCliConstants=false','org.audiveris.omr.sheet.note.NoteHeadsBuilder.dumpTemplateNotes=true']
    immutable(directory/'execution.json',{'JAVA_HOME':java_home,'JAVA_OPTS':opts,'constants':constants,'engine':engine,'runnerSha256':pilot.digest(Path(__file__).read_bytes()),'protocolSha256':pilot.digest((WORK/'protocol.json').read_bytes())})
    os.environ['JAVA_HOME']=java_home;os.environ['JAVA_OPTS']=opts
    pilot.run(directory,executable,2,180,engine_constants=constants)

def read_scores(text):
    scores={}
    for n,line in enumerate(text.splitlines(),1):
        if not line.startswith('ANCHOR5|'): continue
        p=line.split('|')
        if len(p)!=20: raise ValueError('malformed forced score')
        key=(p[1],p[4],p[5],int(p[6]),int(p[7]),p[8])
        if key in scores: raise ValueError('duplicate forced score')
        row={'staffId':p[2],'pointSize':int(p[3]),'pivot':[int(p[9]),int(p[10])],'origin':[int(p[11]),int(p[12])],'center':[float(p[13]),float(p[14])],'size':[int(p[15]),int(p[16])],'distance':float(p[17]),'holeWhiteRatio':float(p[18]),'counts':json.loads(p[19]),'line':n}
        if not all(math.isfinite(row[k]) for k in ('distance','holeWhiteRatio')) or len(row['counts'])!=8: raise ValueError('invalid score')
        scores[key]=row
    return scores

def summarize(output):
    protocol,_=validate(); benchmark=pilot.load(BENCHMARK); prior=pilot.load(pilot.ROOT/'docs/experiments/sh1991-fa-proximity-v3-20261015.json')
    engine=pilot.load(WORK/'engine.json'); executable=ENGINE/'app/build/install/app/bin/Audiveris'
    if pilot.engine_identity(executable)!=engine['identity']: raise ValueError('engine drift')
    evidence={}; arms={}; all_scores={}
    for arm in ARMS:
        directory=WORK/arm; pilot.verify(directory); result=pilot.load(directory/'baseline-results.json')
        execution=pilot.load(directory/'execution.json')
        expected_opts='-Datlas.barTrace=true -Datlas.faStemBarGuard=true -Datlas.faBarProximity=true'+(' -Datlas.forcedTemplatePoints='+str(WORK/'points.tsv') if arm=='forced' else '')
        if execution['JAVA_OPTS']!=expected_opts or execution['engine']!=engine or execution['runnerSha256']!=pilot.digest(Path(__file__).read_bytes()): raise ValueError('execution drift')
        if {r['songNo'] for r in result['records']}!=set(protocol['trainingProbe']): raise ValueError('missing cohort')
        equivalence={}; structural=[]
        for r in result['records']:
            if r['engineIdentity']!=engine['identity'] or r['status']!='exported': raise ValueError('failed/changed engine')
            old=next(v for v in pilot.load(pilot.DEFAULT_WORK/'fa-discrimination-v3/candidate/baseline-results.json')['records'] if v['songNo']==r['songNo'])
            c=pilot.compare(pilot.score((pilot.ROOT/old['output']).read_bytes()),pilot.score((pilot.ROOT/r['output']).read_bytes()))
            equivalence[r['songNo']]=c['exactWrittenEvents'] and c['measureCountsMatch']
            page=directory/'baseline'/r['songNo']; graphs=list(page.glob('*.omr'))
            if len(graphs)!=1: raise ValueError('ambiguous graph')
            sheet=survival.read_xml(graphs[0],'sheet#1/sheet#1.xml')
            _,stats=survival.graph_rows(sheet,survival.read_xml(pilot.ROOT/r['output']));structural.append({'songNo':r['songNo'],**stats})
            log=page/'audiveris.log'; scores=read_scores(log.read_text())
            if arm=='off' and scores: raise ValueError('unexpected forced diagnostics')
            if set(all_scores)&set(scores): raise ValueError('duplicate point identity')
            if arm=='forced': all_scores.update(scores)
            for f in [log,graphs[0],page/'run.json',pilot.ROOT/r['output'],directory/'execution.json']:
                evidence[str(f.relative_to(pilot.ROOT))]=pilot.digest(f.read_bytes())
        arms[arm]={'sameWrittenEventsAsFrozenV3':equivalence,'score':result['summary']['all'],'headAudit':fa.head_statistics(directory),'structure':structural}
    if not all(v for a in arms.values() for v in a['sameWrittenEventsAsFrozenV3'].values()): raise ValueError('diagnostics changed recognition')
    if arms['off']['score']!=arms['forced']['score'] or arms['off']['headAudit']!=arms['forced']['headAudit']: raise ValueError('diagnostic control metrics drift')
    rows=[]; strata=defaultdict(Counter)
    positives=[r for r in benchmark['rows'] if r['label']=='head']
    if len(all_scores)!=len(positives)*432: raise ValueError('incomplete forced score grid')
    for source in positives:
        detail={'sourceId':source['id'],'shape':source['shape'],'fill':source['fill'],'families':{}}
        for filled,opened in protocol['templatePairs']:
            family=filled.removeprefix('NOTEHEAD_').removesuffix('_FILLED'); entry={}
            for mode in protocol['modes']:
                f=all_scores[(source['id'],mode,'MIDDLE_LEFT',0,0,filled)];o=all_scores[(source['id'],mode,'MIDDLE_LEFT',0,0,opened)]
                if mode=='anchor' and f['pivot']!=o['pivot']: raise ValueError('noncomparable internal anchors')
                winner='filled' if f['distance']<o['distance'] else 'open' if o['distance']<f['distance'] else 'tie'
                entry[mode]={'filled':f,'open':o,'winner':winner}
                key='/'.join((source['shape'],source['fill'],family,mode));strata[key].update(points=1,filledWins=winner=='filled',openWins=winner=='open',ties=winner=='tie',correctFill=winner==source['fill'],holeAbsent=o['counts'][4]==0)
            detail['families'][family]=entry
        rows.append(detail)
    report={'schemaVersion':1,'protocol':protocol,'engine':engine,'arms':arms,'forcedEvaluationCount':len(all_scores),'zeroOffsetMiddleLeftStrata':{k:dict(v) for k,v in sorted(strata.items())},'sourceRows':rows,'evidenceSha256':evidence,'analysisScriptSha256':pilot.digest(Path(__file__).read_bytes()),'heldOutRun':False,'sourceCertified':False,'safeToPromote':False,'passesAllTrainingGates':False,'interpretation':'Read-only paired scores. No new recognition repair or musical acceptance claimed. Original three gates remain failing.'}
    write_report(output,report)
    print('Verified forced evaluations:',len(all_scores));print(json.dumps(report['zeroOffsetMiddleLeftStrata'],indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',choices=ARMS);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.run: run(a.run)
    elif a.output: summarize(a.output)
    else: p.error('provide --run ARM or --output PATH')
