"""Create new bounded, editable retained-source opening candidates."""
from pathlib import Path
import hashlib, json, xml.etree.ElementTree as E
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
SRC=ROOT/'work/luna-program-20260904/source_only/retained-sources'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def child(p,t,text=None,**a):
 x=E.SubElement(p,t,a)
 if text is not None:x.text=str(text)
 return x
specs=[dict(slug='kentucky-new-salem',title='New Salem',book='kentucky',record='kentucky 10 — New-Salem',file='kentucky-010-new-salem.pdf',fifths=-1,beats=4,beat_type=4,duration=4,type='half',dotted=False,label='F Major.',coordsSpace=[1780,1376],image='renders/kentucky.png',imageActualSize=[2200,1700],bar=[208,354],voices=[('G',2,'C',5,0,297,177,205,11.2),('F',4,'F',3,0,297,297,331,11.2),('G',2,'F',4,0,297,451,458,11.2),('F',4,'F',3,0,297,552,585,11.2)]),dict(slug='shenandoah-something-new',title='Something New',book='shenandoah',record='shenandoah 10 — Something New',file='shenandoah-010-something-new.jpg',fifths=-2,beats=6,beat_type=8,duration=3,type='quarter',dotted=True,label='B♭ Major.',coordsSpace=[1654,1157],image=None,imageActualSize=[1654,1157],bar=[150,277],voices=[('G',2,'B',4,-1,224,144,168,12.2),('G',2,'F',4,0,224,287,293,12.2),('G',2,'F',4,0,224,404,410,12.2),('F',4,'B',3,-1,224,474,530,12.2)])]
for s in specs:
 root=E.Element('score-partwise',version='4.0')
 work=child(root,'work');child(work,'work-title',s['title']+' — opening measure review draft v1')
 ident=child(root,'identification');child(ident,'source','Retained source '+s['file']+', printed page 10; first bar only.')
 misc=child(ident,'miscellaneous');child(misc,'miscellaneous-field','true',name='review-required');child(misc,'miscellaneous-field','false',name='safe-to-promote');child(misc,'miscellaneous-field','First printed measure only; no claim of complete tune or exact-edition certification.',name='coverage')
 pl=child(root,'part-list')
 for i in range(4):
  sp=child(pl,'score-part',id='P'+str(i+1));child(sp,'part-name','Printed voice '+str(i+1))
 ev=[]
 for i,(clef,line,step,octave,alter,x,y,bottom,spacing) in enumerate(s['voices'],1):
  p=child(root,'part',id='P'+str(i));m=child(p,'measure',number='1');a=child(m,'attributes');child(a,'divisions',2)
  key=child(a,'key');child(key,'fifths',s['fifths'])
  tm=child(a,'time',**({'symbol':'common'} if s['beats']==4 else {}));child(tm,'beats',s['beats']);child(tm,'beat-type',s['beat_type'])
  c=child(a,'clef');child(c,'sign',clef);child(c,'line',line)
  for rest in [True,False]:
   n=child(m,'note')
   if rest:child(n,'rest')
   else:
    pit=child(n,'pitch');child(pit,'step',step)
    if alter:child(pit,'alter',alter)
    child(pit,'octave',octave)
   child(n,'duration',s['duration']);child(n,'type',s['type'])
   if s['dotted']:child(n,'dot')
  ev.append(dict(part='P'+str(i),clef=clef,clefLine=line,noteCenter=[x,y],staffBottomY=bottom,staffLineSpacing=spacing,step=step,octave=octave,alter=alter,restDurationQuarter=s['duration']/2,noteOnsetQuarter=s['duration']/2,noteDurationQuarter=s['duration']/2))
 out=BASE/(s['slug']+'-opening-candidate-v1.musicxml');E.indent(root);E.ElementTree(root).write(out,encoding='utf-8',xml_declaration=True)
 source=SRC/s['file']
 evidence=dict(version=1,title=s['title'],bookId=s['book'],recordId=s['record'],candidate=out.name,candidateSha256=sha(out),sourcePath=str(source.relative_to(ROOT)),sourceSha256=sha(source),sourcePrintedPage='10',directVisualReview=True,reviewDate='2026-09-07',coverage='one complete opening measure across all four printed voices',reviewRequired=True,safeToPromote=False,printedKeyLabel=s['label'],mode='unknown',keySignatureFifths=s['fifths'],coordinateSystem=dict(origin='top-left',reviewDisplayDimensions=s['coordsSpace'],actualImageDimensions=s['imageActualSize'],conversion='Multiply display x/y by actual width/height divided by display width/height.',image=s['image'] or str(source.relative_to(ROOT)),firstMeasureXRange=s['bar']),voiceObservations=ev,limitations=['Only first printed bar transcribed; remainder omitted, not silence.','Lyrics and notehead shapes intentionally omitted pending separate underlay/glyph review.','Printed key label retained here; no mode inference encoded in MusicXML.','Printed clefs retained literally; no unprinted octave transposition applied.','Retained source filename links this page to the book; exact-edition provenance is not newly certified.','No terminal final barline or repeats invented at excerpt boundary.'])
 if s['image']:evidence['renderSha256']=sha(BASE/s['image'])
 (BASE/(s['slug']+'-evidence-v1.json')).write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
 print(out.name,sha(out))
