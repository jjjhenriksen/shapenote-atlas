#!/usr/bin/env python3
"""Read-only analysis repair for completed stemless-v1 recognition.

The frozen v1 analyzer stopped on legitimate duplicate CAUTIONARY IDs. Keep it
unchanged. This separate analyzer excludes only non-exported cautionary stacks;
ambiguous exported IDs still fail. No recognition entry point.
"""
from pathlib import Path
import argparse
import json
from omr_stemless_study import (check, verify_controls, verify_receipt, digest,
    load, immutable, survival, audit, stage_trace, FAMILIES, preservation)
import omr_stemless_study as study

def span_inventory(sheet, export):
    """No positional zip: exported labels must resolve to a unique physical span."""
    systems = sheet.findall('./page/system')
    if len(systems) != 1:
        raise ValueError('Need one physical system')
    stacks = [s for s in systems[0].findall('stack') if s.get('special') != 'CAUTIONARY']
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


def analyze(out, destination):
    import omr_terminal_diagnosis as diagnosis
    import omr_measure_consensus_study as consensus
    import omr_acceptance_audit as acceptance
    out = Path(out).resolve(); destination=Path(destination).resolve(); p = check(out)
    if destination == out or out in destination.parents or destination in out.parents:
        raise ValueError('Analysis must stay outside retained recognition evidence')
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
    report = dict(analysisPolicy='Read-only analysis repair: omit CAUTIONARY stacks from exported-label lookup because they intentionally reuse preceding IDs; do not normalize any exported musical span or event. Recognition recipes/outputs untouched.', protocolSha256=digest(out/'protocol.json'), cases=results,
                  allControlsExactlyReplayed=True, safeToPromote=False, wholeScoresAccepted=0,
                  sourceCertified=False, exposure='Consumed development only; no held-out evaluation or source-certified score')
    check(out); immutable(destination/'report.json',report)
    immutable(destination/'receipt.json',dict(reportSha256=digest(destination/'report.json'),
              analysisCodeSha256=digest(__file__), recognitionProtocolSha256=digest(out/'protocol.json'),
              recognitionSha256={arm+'/'+c['id']:digest(out/arm/c['id']/'recognition.json')
                                 for c in p['cases'] for arm in ('off','on')}))
    return report


if __name__ == '__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--study',required=True,type=Path);a.add_argument('--out',required=True,type=Path)
    args=a.parse_args();result=analyze(args.study,args.out)
    print(json.dumps(result,indent=2))
