#!/usr/bin/env python3
"""One fixed V7 evaluation on the original eight test images; never tune here."""
import argparse
import os
from pathlib import Path
import sh1991_pilot as pilot
import sh1991_fa_support as train
import sh1991_fa_survival as survival
from sh1991_barline_run import immutable
from sh1991_head_audit import write_report
WORK=pilot.DEFAULT_WORK/'heldout-v7'
ARMS=('reference','candidate')

def prepare():
    # Lock selection before any new test recognition, not after seeing results.
    protocol=pilot.load(pilot.DEFAULT_WORK/'fa-template-v1/protocol.json')
    training=pilot.load(train.WORK/'report.json');parent=pilot.load(pilot.DEFAULT_WORK/'dataset.json')
    if not training['passesAllTrainingGates'] or not all(training['checks'].values()): raise ValueError('all frozen training gates required')
    if training['protocol']['selectionRule']!=protocol['selectionRule']: raise ValueError('original gate drift')
    if pilot.digest((pilot.DEFAULT_WORK/'dataset.json').read_bytes())!=protocol['parentDatasetSha256']: raise ValueError('original dataset drift')
    rows=[r for r in parent['records'] if r['split']=='test']
    if len(rows)!=8: raise ValueError('exact original eight test images required')
    dataset={**parent,'records':rows,'splits':{'train':0,'validation':0,'test':8},'experiment':'fixed-v7-heldout-once'}
    engine=pilot.load(train.WORK/'engine.json')
    if pilot.engine_identity(train.ENGINE/'app/build/install/app/bin/Audiveris')!=engine['identity']: raise ValueError('selected engine drift')
    lock={'study':'fixed-v7-heldout-once','originalHeldOutPolicy':protocol['heldOutPolicy'],'trainingReportSha256':pilot.digest((train.WORK/'report.json').read_bytes()),'originalProtocolSha256':pilot.digest((pilot.DEFAULT_WORK/'fa-template-v1/protocol.json').read_bytes()),'datasetSha256':pilot.digest((pilot.DEFAULT_WORK/'dataset.json').read_bytes()),'selectionRule':protocol['selectionRule'],'testSongs':[r['songNo'] for r in rows],'engine':engine,'settings':{a:{'JAVA_OPTS':train.settings(a)[0],'constants':train.settings(a)[1]} for a in ARMS},'runnerSha256':pilot.digest(Path(__file__).read_bytes()),'trainingRunnerSha256':pilot.digest(Path(train.__file__).read_bytes()),'patchSha256':{name:pilot.digest((pilot.ROOT/name).read_bytes()) for name in ['experiments/audiveris-native-hole-v6/native-hole.patch','experiments/audiveris-support-v7/support.patch']},'noFurtherTestDrivenChanges':True,'sourceCertified':False,'priorExposure':'Original test cohort was used for raw baseline and voice-layout study; not pristine across project. No V1-V7 test-driven tuning permitted.'}
    immutable(WORK/'selection-lock.json',lock)
    for a in ARMS:immutable(WORK/a/'dataset.json',dataset)
    return lock

def run(arm):
    lock=prepare();opts,constants=train.settings(arm);java_home=str(pilot.DEFAULT_WORK/'toolchain/jdk25/jdk-25.0.4.1+1/Contents/Home')
    immutable(WORK/arm/'execution.json',{'JAVA_HOME':java_home,'JAVA_OPTS':opts,'constants':constants,'engine':lock['engine'],'selectionLockSha256':pilot.digest((WORK/'selection-lock.json').read_bytes()),'runnerSha256':pilot.digest(Path(__file__).read_bytes())})
    os.environ['JAVA_HOME']=java_home;os.environ['JAVA_OPTS']=opts
    pilot.run(WORK/arm,train.ENGINE/'app/build/install/app/bin/Audiveris',2,180,engine_constants=constants)

def summarize(output):
    lock=prepare();arms={};evidence={};baseline_equivalence={}
    baseline=pilot.load(pilot.DEFAULT_WORK/'baseline-results.json')
    for arm in ARMS:
        directory=WORK/arm;pilot.verify(directory);result=pilot.load(directory/'baseline-results.json');execution=pilot.load(directory/'execution.json')
        if execution['selectionLockSha256']!=pilot.digest((WORK/'selection-lock.json').read_bytes()):raise ValueError('selection drift')
        if execution['JAVA_OPTS']!=lock['settings'][arm]['JAVA_OPTS'] or execution['constants']!=lock['settings'][arm]['constants']:raise ValueError('settings drift')
        if {r['songNo'] for r in result['records']}!=set(lock['testSongs']):raise ValueError('incomplete fixed test evaluation')
        pages=[]
        for receipt in result['records']:
            if receipt['engineIdentity']!=lock['engine']['identity']:raise ValueError('engine receipt drift')
            # pilot.run was supplied the frozen settings through JVM options/constants.
            expected_constants=lock['settings'][arm]['constants']
            for constant in expected_constants:
                if constant not in receipt['command']:raise ValueError('command constant missing')
            page=directory/'baseline'/receipt['songNo'];graphs=list(page.glob('*.omr'));entry={'songNo':receipt['songNo'],'status':receipt['status'],'exitCode':receipt['exitCode'],'metrics':receipt.get('metrics')}
            if receipt.get('output'):
                if len(graphs)!=1:raise ValueError('graph missing')
                sheet=survival.read_xml(graphs[0],'sheet#1/sheet#1.xml');_,stats=survival.graph_rows(sheet,survival.read_xml(pilot.ROOT/receipt['output']));entry.update(stats)
                if arm=='reference':
                    old=next(r for r in baseline['records'] if r['songNo']==receipt['songNo']);c=pilot.compare(pilot.score((pilot.ROOT/old['output']).read_bytes()),pilot.score((pilot.ROOT/receipt['output']).read_bytes()));baseline_equivalence[receipt['songNo']]=c['exactWrittenEvents'] and c['measureCountsMatch']
            pages.append(entry)
            for path in [page/'run.json',page/'audiveris.log',directory/'execution.json']+graphs+([pilot.ROOT/receipt['output']] if receipt.get('output') else []):evidence[str(path.relative_to(pilot.ROOT))]=pilot.digest(path.read_bytes())
        arms[arm]={'score':result['summary']['test'],'pages':pages}
    before=arms['reference']['score'];after=arms['candidate']['score'];rule=lock['selectionRule']
    checks={}
    for key,minimum in [('candidatePitchRecall',rule['candidatePitchRecallGainAtLeast']),('candidatePitchPrecision',-rule['candidatePitchPrecisionLossAtMost']),('candidateDurationRecall',-rule['candidateDurationRecallLossAtMost']),('candidateOnsetRecall',-rule['candidateOnsetRecallLossAtMost'])]:checks[key]=after[key] is not None and before[key] is not None and after[key]>=before[key]+minimum
    checks['exportCount']=after['exports']>=before['exports']
    report={'schemaVersion':1,'selectionLock':lock,'selectionLockSha256':pilot.digest((WORK/'selection-lock.json').read_bytes()),'arms':arms,'referenceWrittenEventsMatchOriginalBaseline':baseline_equivalence,'heldOutScoreComparisons':checks,'allHeldOutScoreComparisonsPass':all(checks.values()),'trainingGatesPassedBeforeTest':True,'heldOutRun':True,'tunedOnTest':False,'sourceHeadFillAndRetentionAccuracy':None,'sourceCertified':False,'safeToPromote':False,'evidenceSha256':evidence,'analysisScriptSha256':pilot.digest(Path(__file__).read_bytes()),'limitations':['No independent event/source-head gold on test images.','Fixed final evaluation only; no changes may use these results as fresh-held-out evidence.','Historical test exposure to baseline/voice probes disclosed in lock.']}
    write_report(output,report);print('Held-out score comparisons',checks)
    for arm in ARMS:print(arm,arms[arm]['score'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true');p.add_argument('--run',choices=ARMS);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.prepare:prepare()
    elif a.run:run(a.run)
    elif a.output:summarize(a.output)
    else:p.error('provide --prepare, --run ARM or --output PATH')
