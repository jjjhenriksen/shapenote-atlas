#!/usr/bin/env python3
"""Compare an immutable opt-in fa-template prototype with its same-binary control."""
import argparse
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET

import sh1991_pilot as pilot
from sh1991_head_audit import match, heads_in_graph, write_report

WORK = pilot.DEFAULT_WORK / 'fa-template-v1'
FROZEN_REPORT = pilot.ROOT / 'docs/experiments/sh1991-fa-template-v1-20261015.json'


def prepare(work):
    """Reconstruct the frozen training cohorts; never recognize or overwrite runs."""
    frozen = pilot.load(FROZEN_REPORT)
    protocol = frozen['protocol']
    parent = pilot.DEFAULT_WORK / 'dataset.json'
    if pilot.digest(parent.read_bytes()) != protocol['parentDatasetSha256']:
        raise ValueError('original dataset drift; this replay requires the retained dataset')
    dataset = pilot.load(parent)
    pilot.validate_dataset(dataset)
    selected = [r for r in dataset['records'] if r['songNo'] in protocol['trainingProbe']]
    if len(selected) != len(protocol['trainingProbe']) or any(r['split'] != 'train' for r in selected):
        raise ValueError('probe must contain exactly the frozen training records')
    candidates = [(work / 'protocol.json', protocol), (work / 'engine.json', frozen['engine'])]
    for arm in ('off', 'on'):
        subset = {**dataset, 'records': selected, 'splits': {'train': len(selected), 'validation': 0, 'test': 0},
                  'parentDatasetSha256': protocol['parentDatasetSha256'], 'experiment': 'fa-template-v1-' + arm}
        candidates.append((work / arm / 'dataset.json', subset))
    # Check every destination before writing any: an interrupted prepare is resumable.
    for path, value in candidates:
        if path.exists() and pilot.load(path) != value:
            raise ValueError(f'refusing to replace frozen replay metadata: {path}')
    for path, value in candidates:
        if not path.exists():
            pilot.write(path, value)
    print('Training-only replay metadata verified; no recognition launched')


def fill_of(shape):
    if shape in ('NOTEHEAD_BLACK', 'NOTEHEAD_BLACK_SMALL') or shape.endswith('_FILLED'):
        return 'filled'
    if shape in ('NOTEHEAD_VOID', 'NOTEHEAD_VOID_SMALL') or shape.endswith('_VOID'):
        return 'open'
    return None


def audited_rows():
    audit = pilot.load(pilot.ROOT / 'docs/experiments/sh1991-head-shape-audit-20261015.json')
    rows = [{k:v for k,v in r.items() if k != 'match'} for r in audit['observations']]
    # Reuse the prior audit's explicit coordinate adjudications, identically for both arms.
    for case in audit['postMatchVisualAdjudications']:
        row = next(r for r in rows if r['id'] == case['observationId'])
        row['x'] = case['retainedHead']['x']; row['y'] = case['retainedHead']['y']
    return audit, rows


def head_statistics(directory):
    audit, rows = audited_rows(); hits = {}; all_heads = {}
    for song in sorted({r['songNo'] for r in rows}):
        files = list((directory / 'baseline' / song).glob('*.omr'))
        if len(files) != 1: raise ValueError('expected one complete retained graph per audited image')
        with zipfile.ZipFile(files[0]) as archive:
            sheet = ET.fromstring(archive.read('sheet#1/sheet#1.xml'))
        heads = heads_in_graph(sheet); all_heads[song] = heads
        hits.update(match([r for r in rows if r['songNo'] == song], heads, .5))
    groups = {}
    for name, cohort in [('triangle',[r for r in rows if r['shape'] == 'triangle']),
                         ('other',[r for r in rows if r['shape'] != 'triangle'])]:
        detected = [r for r in cohort if r['id'] in hits]
        groups[name] = {'observed':len(cohort), 'retained':len(detected),
                        'retainedRecall':len(detected)/len(cohort),
                        'correctFill':sum(fill_of(hits[r['id']]['shape']) == r['fill'] for r in detected),
                        'fillCorrectAmongRetained':sum(fill_of(hits[r['id']]['shape']) == r['fill'] for r in detected)/len(detected) if detected else 0,
                        'faLabelsAmongRetained':sum(hits[r['id']]['shape'].startswith('NOTEHEAD_FA_') for r in detected),
                        'correctStaff':sum(hits[r['id']]['staffId'] == r['staffId'] for r in detected)}
    for fill in ('filled','open'):
        cohort = [r for r in rows if r['shape'] == 'triangle' and r['fill'] == fill]
        groups['triangle-' + fill] = {'observed':len(cohort),'retained':sum(r['id'] in hits for r in cohort),
                                    'correctFill':sum(r['id'] in hits and fill_of(hits[r['id']]['shape']) == fill for r in cohort)}
    used = {(r['songNo'], hits[r['id']]['id']) for r in rows if r['id'] in hits}
    groups['unmatchedGraphNodesInWindows'] = sum(
        h['staffId'] == p['staffId'] and 270 <= h['x'] < 1030 and p['cropBox'][1] <= h['y'] < p['cropBox'][3]
        and (p['songNo'],h['id']) not in used
        for p in audit['sourcePointers'] for h in all_heads[p['songNo']])
    groups['unmatchedGraphNodeCaveat'] = 'Interior x=[270,1030) avoids source-window boundary heads; unmatched nodes are candidates for false-positive review, not certified false positives.'
    return groups


def gate(rule, before, after, before_heads, after_heads, off_identical):
    def gain(key, minimum):
        return after[key] is not None and before[key] is not None and after[key] >= before[key] + minimum
    return {
        'offControlWrittenEventsIdentical':off_identical,
        'triangleRecovery':after_heads['triangle']['retainedRecall'] >= before_heads['triangle']['retainedRecall'] + rule['triangleRetainedRecallGainAtLeast'],
        'triangleFill':after_heads['triangle']['fillCorrectAmongRetained'] >= rule['fillCorrectAmongRetainedTrianglesAtLeast'],
        'otherHeadRetention':after_heads['other']['retainedRecall'] >= rule['nonTriangleHeadRetentionAtLeast'],
        'candidatePitchRecall':gain('candidatePitchRecall',rule['candidatePitchRecallGainAtLeast']),
        'candidatePitchPrecision':gain('candidatePitchPrecision',-rule['candidatePitchPrecisionLossAtMost']),
        'candidateDuration':gain('candidateDurationRecall',-rule['candidateDurationRecallLossAtMost']),
        'candidateOnset':gain('candidateOnsetRecall',-rule['candidateOnsetRecallLossAtMost']),
        'exportCount':after['exports'] >= before['exports']}


def summarize(work, output):
    protocol = pilot.load(work / 'protocol.json'); engine = pilot.load(work / 'engine.json')
    patch = pilot.ROOT / 'experiments/audiveris-fa-v1/fa-heads.patch'
    if pilot.digest(patch.read_bytes()) != engine['patchSha256']: raise ValueError('prototype patch drift')
    if pilot.digest((pilot.DEFAULT_WORK / 'dataset.json').read_bytes()) != protocol['parentDatasetSha256']:
        raise ValueError('original dataset drift')
    if pilot.digest((pilot.ROOT / 'docs/experiments/sh1991-head-shape-audit-20261015.json').read_bytes()) != protocol['headAuditSha256']:
        raise ValueError('source-head audit drift')
    results = {}
    for arm in ('off', 'on'):
        directory = work / arm; pilot.verify(directory)
        result = pilot.load(directory / 'baseline-results.json')
        cohort = pilot.load(directory / 'dataset.json')['records']
        if {r['songNo'] for r in cohort} != set(protocol['trainingProbe']) or any(r['split'] != 'train' for r in cohort):
            raise ValueError('experiment dataset must remain the frozen training-only cohort')
        if {r['songNo'] for r in result['records']} != set(protocol['trainingProbe']):
            raise ValueError('incomplete training cohort')
        for receipt in result['records']:
            if receipt['engineIdentity'] != engine['engineIdentity']: raise ValueError('engine drift')
            required = 'org.audiveris.omr.sheet.ProcessingSwitches.faHeads=' + ('true' if arm == 'on' else 'false')
            if required not in receipt['command']: raise ValueError('wrong experimental switch')
        results[arm] = result
    original = {r['songNo']:r for r in pilot.load(pilot.DEFAULT_WORK / 'baseline-results.json')['records']}
    controls = {}
    for row in results['off']['records']:
        old = original[row['songNo']]
        if row.get('output') and old.get('output'):
            compared = pilot.compare(pilot.score((pilot.ROOT/old['output']).read_bytes()),pilot.score((pilot.ROOT/row['output']).read_bytes()))
            controls[row['songNo']] = compared['exactWrittenEvents'] and compared['measureCountsMatch']
        else: controls[row['songNo']] = False
    heads = {arm:head_statistics(work / arm) for arm in ('off','on')}
    checks = gate(protocol['selectionRule'],results['off']['summary']['all'],results['on']['summary']['all'],heads['off'],heads['on'],all(controls.values()))
    decision = {'checks':checks,'passesAllTrainingGates':all(checks.values()),'offControlByImage':controls}
    pilot.write(work / 'decision.json', decision)
    report = {'schemaVersion':1,'experiment':'Audiveris Sacred Harp fa templates v1',
              'protocol':protocol,'protocolSha256':pilot.digest((work/'protocol.json').read_bytes()),
              'engine':engine,'decision':decision,
              'arms':{arm:{'summary':results[arm]['summary']['all'],'headAudit':heads[arm],
                           'pages':[{'songNo':r['songNo'],'status':r['status'],'exitCode':r['exitCode'],
                                     'outputSha256':r.get('outputSha256'),'metrics':r.get('metrics')} for r in results[arm]['records']]}
                      for arm in ('off','on')},
              'analysisScriptSha256':pilot.digest(Path(__file__).read_bytes()),
              'sourcePixelsChanged':False,'sourceCertified':False,'safeToPromote':False,'modelFineTuned':False,
              'heldOutRun':False,'interpretation':'Training-only input-independent template intervention; head observations single AI review, score comparisons against unreviewed candidate labels. A passed training rule is not source certification or production acceptance.'}
    write_report(output,report)
    print('Control agreement:',controls)
    print('Head statistics:',heads)
    print('Training gates:',decision)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,default=WORK)
    parser.add_argument('--prepare',action='store_true',help='Reconstruct frozen training metadata without recognition')
    parser.add_argument('--output',type=Path,default=FROZEN_REPORT)
    args = parser.parse_args()
    if args.prepare:
        prepare(args.work)
    else:
        summarize(args.work,args.output)
