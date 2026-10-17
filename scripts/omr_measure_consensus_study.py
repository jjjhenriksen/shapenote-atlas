#!/usr/bin/env python3
"""Read-only analysis of versioned consumed-development bar consensus runs."""
from __future__ import annotations

import argparse
from collections import Counter
import math
from pathlib import Path

import omr_acceptance_audit as acceptance
import omr_export_trace as trace
import omr_localization_eval as localization
import omr_localization_study as native
import omr_measure_consensus_run as runner

load, digest, immutable = runner.load, runner.digest, runner.immutable


def mapped_errors(observed, inspected, geometry):
    """Error units under the declared map, retaining every orphan event too."""
    rows={(s['part'],s['measure']):s for s in inspected['segments']}
    result=Counter(); mapping=geometry['map']['mapping']
    for s in observed['segments']:
        pi,mi=s['part'],s['measure'];old=mapping[pi][mi]
        actual=rows[(pi,old)]['events'] if old is not None else []
        for (kind,event),count in acceptance.audit.errors(acceptance.audit.source_events(s),actual).items():
            result[('source',pi,mi,kind,event)]+=count
    for pi,indices in enumerate(geometry['map']['orphanDraftMeasures']):
        for mi in indices:
            row=rows[(pi,mi)]
            spans=[s for s in geometry['layout'] if s['label']==row['number'] and s['special']!='CAUTIONARY']
            if len(spans)!=1:
                raise ValueError('Orphan event lacks unique physical context')
            context=(spans[0]['left'],spans[0]['right'])
            for event in row['events']:
                result[('orphan',pi,context,'extra',acceptance.audit.event_key(event))]+=1
    return result


def geometry_map(observed, sheet, export, tolerance=4):
    """Whole-source map using only explicit source boundaries and graph layout.

    Merged, special/absent and ambiguous regions stay null; every unused XML
    measure is an explicit orphan. Never align using the event pitches to score.
    """
    expected = acceptance.validate_grid(observed)
    edges = observed['writtenGrid']['edges']
    systems = sheet.findall('./page/system')
    if len(systems) != 1:
        raise ValueError('Geometry mapping requires one complete declared system')
    system = systems[0]; physical = system.findall('part'); parts = export.findall('part')
    if (len(parts) != len(expected) or [p.get('id') for p in parts] != [f"P{p.get('id')}" for p in physical]
            or any(len(p.findall('staff')) != 1 for p in physical)):
        raise ValueError('Unsupported physical/logical source part mapping')
    stacks = system.findall('stack')
    if any(len(p.findall('measure')) != len(stacks) for p in physical):
        raise ValueError('Physical part/stack coverage differs')
    layout = []
    for st in stacks:
        a, b = float(st.get('left')), float(st.get('right'))
        if not math.isfinite(a+b) or not a < b:
            raise ValueError('Invalid native geometry')
        layout.append({'label': st.get('id'), 'left': a, 'right': b, 'special': st.get('special')})
    candidates = []
    for mi, (a,b) in enumerate(zip(edges, edges[1:])):
        ids = [i for i,s in enumerate(layout) if s['special'] in {None,'PICKUP'}
               and (s['left'] <= a+tolerance if mi == 0 else abs(s['left']-a) <= tolerance)
               and abs(s['right']-b) <= tolerance]
        candidates.append(ids)
    uses = Counter(i for ids in candidates for i in ids)
    mappings, orphans = [], []
    for part in parts:
        measures = part.findall('measure'); labels = [m.get('number') for m in measures]
        if len(set(labels)) != len(labels):
            raise ValueError('Duplicate exported measure label')
        row = []
        for ids in candidates:
            i = ids[0] if len(ids) == 1 and uses[ids[0]] == 1 else None
            label = layout[i]['label'] if i is not None else None
            row.append(labels.index(label) if label in labels else None)
        mappings.append(row)
        orphans.append([i for i in range(len(measures)) if i not in row])
    mapping = {'mapping': mappings, 'orphanDraftMeasures': orphans}
    acceptance.audit.measure_map(observed, [len(p.findall('measure')) for p in parts], mapping)
    proposed = [s['right'] for s in layout[:-1] if edges[0] < s['right'] < edges[-1]]
    # Same predeclared order-preserving matching used by earlier image studies.
    from omr_image_study import match_boundaries
    return {'map': mapping, 'layout': layout,
            'boundaries': match_boundaries(edges[1:-1], proposed, tolerance),
            'sourceMeasuresPerPart': expected,
            'geometricallyAlignedSourceMeasures': [sum(i is not None for i in row) for row in mappings],
            'method': 'Mutually unique complete-span layout matches at 4 pixels; no pitch/rhythm/shape matching. Source and orphan denominators retained.'}


def opening_trace(labels, graph_path, source_path, sheet, export):
    from PIL import Image
    with Image.open(source_path) as image:
        heads = native.graph_heads(graph_path, source_path, image.size)
    predictions = []
    for head in heads:
        for window in labels['windows']:
            a,b,c,d = window['box']
            if a <= head['x'] < c and b <= head['y'] < d:
                predictions.append(dict(head, staff=window['staff'], origin='native'))
    graph, summary = trace.graph_export_rows(sheet, export)
    exported, _ = trace.export_details(export)
    return {'wholeImage': summary,
            'radii': {str(radius): trace.trace_arm(labels['rows'], predictions,
                       localization.match(labels['rows'], predictions, radius), graph, exported)
                      for radius in (.35,.5,.75)}}


def case_analysis(study, p, case, arm, whole, heads):
    directory = study/arm/case['id']
    rec = runner.verify_receipt(directory, digest(study/'protocol.json'))
    if rec['status'] != 'exported':
        return {'status': 'recognition-failed', 'exportedMeasures': None,
                'eventComparison': None, 'sourceAccuracy': None,
                'reason': 'Failed recognition/export is unavailable, not a zero-event baseline'}
    sheet = trace.survival.read_xml(directory/rec['graph'], 'sheet#1/sheet#1.xml')
    export = trace.survival.read_xml(directory/rec['export'])
    inspected = acceptance.audit.inspect(export)
    report = {'status': 'exported', 'exportedMeasures': inspected['measureCounts'],
              'structureFindings': inspected['findingCounts'],
              'wholeImageHeads': sum(1 for _ in sheet.findall('.//sig/inters/head')),
              'sourceAccuracy': None}
    if whole is not None:
        observed = load(whole)
        if observed['source']['sha256'] != digest(case['source']):
            raise ValueError('Whole-song source identity differs')
        if 'writtenGrid' in observed:
            aligned = geometry_map(observed, sheet, export)
            report['geometry'] = aligned
            report['acceptanceAudit'] = acceptance.compare(observed, export, aligned['map'])
        elif case['id']=='501t':
            paths=[Path(f) for f in p['extraInputs'] if Path(f).name=='penn-development-map.json']
            if len(paths)!=1:
                raise ValueError('Need the frozen historical Penn map for the v1 control')
            report['geometry'] = None
            report['acceptanceAudit'] = acceptance.compare(observed, export, load(paths[0]))
            report['alignmentMethod'] = 'Historical reviewed consumed-development Penn map; not the v2 physical-grid map'
    if heads is not None:
        labels=load(heads)
        if labels['sourceSha256']!=digest(case['source']):
            raise ValueError('Head census source identity differs')
        report['headTrace'] = opening_trace(labels, directory/rec['graph'], Path(case['source']), sheet, export)
    text = (directory/'audiveris.log').read_text()
    report['loggedRestoredBars'] = sum('AtlasBarConsensus' in line and ' synthetic=' in line for line in text.splitlines())
    report['loggedCollisionAbstentions'] = text.count('abstain=column-join-collision')
    return report


def analyze(study, out, thy_grid, penn_grid, thy_heads, clayton_heads, paired=False):
    study, out = Path(study).resolve(), Path(out).resolve()
    if out == study or study in out.parents or out in study.parents:
        raise ValueError('Analysis outputs must be outside retained recognition evidence')
    if paired:
        import omr_measure_consensus_paired as execution
    else:
        execution=runner
    execution.replay(study); p = execution.check(study)
    supplied = [Path(x).resolve() for x in (thy_grid,penn_grid,thy_heads,clayton_heads)]
    if any(p['filesSha256'].get(str(path)) != digest(path) for path in supplied):
        raise ValueError('Analysis source observations must be frozen study inputs')
    inputs = {str(path): sha for path,sha in ((study/'protocol.json',digest(study/'protocol.json')),
                                              (study/'controls.json',digest(study/'controls.json')))}
    code = {str(Path(m.__file__).resolve()): digest(m.__file__)
            for m in (acceptance,acceptance.audit,trace,trace.survival,native,native.native,
                      localization,runner,runner.pilot,runner.evidence)}
    code[str(Path(__file__).resolve())] = digest(__file__)
    code[str(Path(execution.__file__).resolve())] = digest(execution.__file__)
    results = {}
    for case in p['cases']:
        whole = thy_grid if case['id']=='469' else penn_grid if case['id']=='501t' else None
        heads = thy_heads if case['id']=='469' else clayton_heads if case['id']=='531' else None
        results[case['id']] = {}
        for arm in ('off','on'):
            d=study/arm/case['id']; rec=runner.verify_receipt(d,digest(study/'protocol.json'))
            for name in ('started.json','recognition.json',*rec['artifactsSha256']):
                inputs[str(d/name)] = digest(d/name)
            results[case['id']][arm] = case_analysis(study,p,case,arm,whole,heads)
    controls=load(study/'controls.json')
    checks = {'allControlsSatisfyDeclaredPolicy':controls['allControlsMatch'],
              'allCandidateExports':all(v['on']['status']=='exported' for v in results.values())}
    thy_off,thy_on=results['469']['off'],results['469']['on']
    checks['thyBoundaryGainWithoutExtras'] = (thy_on['status']=='exported'
        and thy_on['geometry']['boundaries']['matched']>thy_off['geometry']['boundaries']['matched']
        and thy_on['geometry']['boundaries']['extra']==0)
    for sid in ('469','531'):
        before,after=results[sid]['off'],results[sid]['on']
        checks[sid+'OpeningHeadRetentionNoRegression'] = after['status']=='exported' and all(
            after['headTrace']['radii'][r]['geometricallyMatched']>=v['geometricallyMatched']
            for r,v in before['headTrace']['radii'].items())
    before,after=results['501t']['off'],results['501t']['on']
    event_delta=None
    if after['status']=='exported':
        old,new=[v['acceptanceAudit']['gates']['pitchRhythm'] for v in (before,after)]
        checks['pennCompleteEventNoRegression'] = (old['status'] in {'pass','fail'} and new['status'] in {'pass','fail'}
            and new['missingEventUnits']+new['extraEventUnits']<=old['missingEventUnits']+old['extraEventUnits'])
        if before.get('geometry') is not None and after.get('geometry') is not None:
            case=next(c for c in p['cases'] if c['id']=='501t')
            inventories=[]
            for arm,row in (('off',before),('on',after)):
                d=study/arm/'501t';rec=runner.verify_receipt(d,digest(study/'protocol.json'))
                inventories.append(mapped_errors(load(penn_grid),acceptance.audit.inspect(
                    acceptance.audit.read(d/rec['export'])),row['geometry']))
            old_errors,new_errors=inventories
            event_delta={'beforeErrorUnits':sum(old_errors.values()),'afterErrorUnits':sum(new_errors.values()),
                         'errorUnitsRemoved':sum((old_errors-new_errors).values()),
                         'errorUnitsIntroduced':sum((new_errors-old_errors).values()),
                         'interpretation':'Map-dependent missing/extra complete-event units against consumed provisional source observations, including physical-span-keyed orphans; not independent musical mistakes.'}
    else:
        checks['pennCompleteEventNoRegression'] = False
    result = {'schemaVersion':1,'studyProtocolSha256':digest(study/'protocol.json'),
              'phase':p['phase'],'cases':results,'checks':checks,
              'controlReceipt':controls,
              'pennEventErrorDelta':event_delta,
              'passesDevelopmentGates':all(checks.values()),'sourceCertified':False,
              'safeToPromote':False,'wholeScoresAccepted':0,'inputsSha256':inputs,'codeSha256':code}
    runner.check(study)
    if any(digest(path)!=sha for path,sha in {**inputs,**code}.items()):
        raise ValueError('Input/code drift during analysis')
    immutable(out/'report.json',result)
    immutable(out/'receipt.json',{'reportSha256':digest(out/'report.json'),
                                 'inputsSha256':inputs,'codeSha256':code})
    return result


if __name__=='__main__':
    import json
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('study','out','thy-grid','penn-grid','thy-heads','clayton-heads'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--paired',action='store_true',help='Use the explicit v3 header-normalized control policy; never reinterpret v2')
    args=parser.parse_args()
    report=analyze(args.study,args.out,args.thy_grid,args.penn_grid,args.thy_heads,args.clayton_heads,args.paired)
    print(json.dumps({'checks':report['checks'],'passesDevelopmentGates':report['passesDevelopmentGates'],
        'measures':{sid:{arm:v['exportedMeasures'] for arm,v in arms.items()} for sid,arms in report['cases'].items()}},indent=2))
