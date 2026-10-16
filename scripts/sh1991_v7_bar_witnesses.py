#!/usr/bin/env python3
"""Read-only exact physical bar-witness comparison; not source certification."""
import argparse
from pathlib import Path
import sh1991_pilot as pilot
from sh1991_fa_survival import read_xml
from sh1991_head_audit import write_report
WORK=pilot.DEFAULT_WORK

def inventory(directory,evidence):
    files=list(directory.glob('*.omr'))
    if len(files)!=1:raise ValueError('ambiguous retained graph')
    path=files[0];key=str(path.relative_to(pilot.ROOT))
    if pilot.digest(path.read_bytes())!=evidence[key]:raise ValueError('frozen graph drift')
    sheet=read_xml(path,'sheet#1/sheet#1.xml');result={}
    for system in sheet.findall('.//system'):
        for node in system.findall('./sig/inters/barline'):
            box=node.find('bounds')
            if node.get('glyph') is None or box is None:continue
            identity=(system.get('id'),node.get('staff'),node.get('glyph'))
            if identity in result:raise ValueError('duplicate physical bar identity')
            result[identity]={'id':node.get('id'),'staff':node.get('staff'),'box':dict(box.attrib)}
    if not result:raise ValueError('empty physical bar extraction')
    return result,key

def summarize(output):
    prior=pilot.load(pilot.ROOT/'docs/experiments/sh1991-fa-proximity-v3-20261015.json');current=pilot.load(WORK/'support-v7/report.json');rows=[];evidence={}
    for song in current['protocol']['trainingProbe']:
        before,ap=inventory(WORK/'fa-discrimination-v3/control/baseline'/song,prior['evidenceSha256'])
        v3,vp=inventory(WORK/'fa-discrimination-v3/candidate/baseline'/song,prior['evidenceSha256'])
        after,bp=inventory(WORK/'support-v7/candidate/baseline'/song,current['evidenceSha256'])
        def detail(key,source):return {'system':key[0],'staff':key[1],'glyph':key[2],**source[key]}
        rows.append({'songNo':song,'controlPhysicalWitnesses':len(before),'candidatePhysicalWitnesses':len(after),'lost':[detail(k,before) for k in sorted(set(before)-set(after))],'gained':[detail(k,after) for k in sorted(set(after)-set(before))],'matchedBoxesChanged':[{'system':k[0],'staff':k[1],'glyph':k[2],'before':before[k],'after':after[k]} for k in sorted(set(before)&set(after)) if before[k]['box']!=after[k]['box']],'v3LostControlWitnesses':[detail(k,before) for k in sorted(set(before)-set(v3))],'v3LostNowRestored':[detail(k,after) for k in sorted((set(before)-set(v3))&set(after))]})
        for p in [ap,vp,bp]:evidence[p]=pilot.digest((pilot.ROOT/p).read_bytes())
    report={'schemaVersion':1,'method':'Exact system, staff and physical-glyph identity of retained final barline nodes; geometry changes reported separately. Synthetic nodes without glyph excluded. No source review or musical no-regression certification.','sourceCertified':False,'rows':rows,'evidenceSha256':evidence,'analysisScriptSha256':pilot.digest(Path(__file__).read_bytes())}
    write_report(output,report)
    for r in rows:print(r['songNo'],'lost',len(r['lost']),'gained',len(r['gained']),'V3-lost restored',len(r['v3LostNowRestored']))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args();summarize(a.output)
