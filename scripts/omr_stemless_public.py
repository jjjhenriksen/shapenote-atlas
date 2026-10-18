#!/usr/bin/env python3
"""Publish only hash-bound aggregate stemless development measurements."""
from pathlib import Path
import argparse
from collections import Counter
import omr_stemless_study as study
import omr_stemless_analysis as analysis
import omr_measure_consensus_study as consensus


def summarize(root, analyzed):
    root, analyzed = Path(root).resolve(), Path(analyzed).resolve()
    p = study.check(root); r = study.load(analyzed/'report.json'); receipt = study.load(analyzed/'receipt.json')
    if (receipt['reportSha256'] != study.digest(analyzed/'report.json')
            or receipt['analysisCodeSha256'] != study.digest(analysis.__file__)
            or r['protocolSha256'] != study.digest(root/'protocol.json')
            or receipt['recognitionProtocolSha256'] != r['protocolSha256']):
        raise ValueError('Analysis provenance drift')
    cases = {}
    for case in p['cases']:
        row = r['cases'][case['id']]; result = {'existingStaffMeasureSpans':row['preservation']['existingSpans'],
            'unchangedStaffMeasureSpans':row['preservation']['unchangedSpans'],
            'allExistingSpansExactlyPreserved':row['preservation']['allExistingSpansExactlyPreserved'], 'arms':{}}
        for arm in ('off','on'):
            d=root/arm/case['id']; rec=study.verify_receipt(d,r['protocolSha256'])
            if receipt['recognitionSha256'][arm+'/'+case['id']] != study.digest(d/'recognition.json'):
                raise ValueError('Recognition receipt drift')
            old = row['arms'][arm]
            result['arms'][arm] = {'status':old['status'], 'stages':old.get('stages'),
                'wholeImageNewFamilyHeads':old.get('wholeImageNewFamilyHeads')}
            if old['status'] != 'exported':continue
            result['arms'][arm]['exportedMeasuresPerPart']=old['terminal']['exportedMeasures']
            result['arms'][arm]['terminalHeadChordsPerPart']=old['terminal']['measureHeadChordCounts']
            if case.get('sourceGrid'):
                observed=study.load(case['sourceGrid'])
                sheet=study.survival.read_xml(d/rec['graph'],'sheet#1/sheet#1.xml')
                export=study.survival.read_xml(d/rec['export'])
                first=observed['writtenGrid']['edges'][0]
                heads=sheet.findall('.//sig/inters/head')
                result['arms'][arm]['newFamilyHeadsBeforeObservedMusic']=sum(
                    h.get('shape') in study.FAMILIES and
                    float(h.find('bounds').get('x'))+float(h.find('bounds').get('w'))/2 < first for h in heads)
                audit=old['sourceAudit']['gates']['pitchRhythm']
                result['arms'][arm]['sourceEventAudit']={k:v for k,v in audit.items() if k!='differences'}
                if observed.get('segments'):
                    mapping=consensus.geometry_map(observed,sheet,export)['map']['mapping']
                    actual={(s['part'],s['measure']):s['events'] for s in study.audit.inspect(export)['segments']}
                    final=observed['expectedMeasuresPerPart'][0]-1
                    matched=missing=extra=source=0
                    for segment in observed['segments']:
                        if segment['measure'] != final:continue
                        pi=segment['part'];mi=mapping[pi][final]
                        wanted=study.audit.source_events(segment);got=actual[(pi,mi)] if mi is not None else []
                        errors=study.audit.errors(wanted,got)
                        miss=sum(v for (kind,_),v in errors.items() if kind=='missing')
                        ext=sum(v for (kind,_),v in errors.items() if kind=='extra')
                        source+=len(wanted);missing+=miss;extra+=ext;matched+=len(wanted)-miss
                    result['arms'][arm]['terminalSourceEvents'] = dict(source=source,matched=matched,missing=missing,extra=extra)
        cases[case['id']]=result
    return dict(version=1, date='2026-10-18', outcome='rejected-development-prototype',
        allDefaultOffInventoriesExactlyReplayed=r['allControlsExactlyReplayed'],
        recognitionInvocations=6, cases=cases,
        provenance=dict(protocolSha256=r['protocolSha256'],analysisSha256=study.digest(analyzed/'report.json'),
                        analysisReceiptSha256=study.digest(analyzed/'receipt.json'), engine=p['engine'],
                        publisherSha256=study.digest(__file__)),
        limitations=['Previously consumed development only; no held-out evaluation',
            'Penn event labels are same-agent provisional observations, not independent gold',
            'Thy Strength has structure/header source observations only; Clayton has no whole-song source-event grid',
            'No all-rest source measures in the Penn labels and no explicit courtesy-only negative cohort; precision there remains untested',
            'Head-stage snapshots locate loss by REDUCTION exit, not every individual removal operation or exact reason',
            'Original analyzer failed on non-exported cautionary IDs; separate read-only repair used; no recognition rerun'],
        sourceCertified=False,wholeScoresAccepted=0,safeToPromote=False)


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--study',required=True);a.add_argument('--analysis',required=True);a.add_argument('--out',required=True)
    args=a.parse_args();study.immutable(Path(args.out),summarize(args.study,args.analysis))
