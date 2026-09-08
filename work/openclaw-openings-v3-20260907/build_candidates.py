"""Full-notation v3 extensions; manual transcription of directly viewed pages."""
from copy import deepcopy
from fractions import Fraction
import hashlib, json, re
from pathlib import Path
import xml.etree.ElementTree as E
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
PREVIOUS=ROOT/'work/openclaw-openings-v2-20260907'
TYPES={'w':('whole',8,False),'h':('half',4,False),'hd':('half',6,True),'q':('quarter',2,False),'qd':('quarter',3,True),'e':('eighth',1,False)}
SPECS=[dict(slug='kentucky-new-salem', start=9, measures=16,
 barlines=[180,330,532,739,965,1157,1367,1568,1727],
 bottoms=[720,853,987,1113],spacing=11.2,
 curves=[dict(measure=10,firstNote=1,lastNote=2,kind='slur',parts=['P1','P2','P3','P4'],observation='Distinct-pitch curve over dotted quarter and eighth.'),dict(measure=13,firstNote=2,lastNote=3,kind='slur',parts=['P1','P2','P3','P4'],observation='Distinct-pitch curve over the final two quarters.')],
 boundary=dict(style='light-heavy',repeat='backward',xRange=[1695,1727],observation='Terminal repeat dots and thin/thick barline visible in all four voices. No forward repeat sign is printed at either system opening; no opening sign or repeat count is invented.'),
 streams=[[
 'R@204,694:h F5@271,675:h',
 'C5@354,692:qd D5@415,687:e C5@447,692:q A4@495,703:q',
 'C5@568,692:h D5@644,687:q E5@700,681:q',
 'D5@783,687:h D5@850,687:e E5@887,681:e F5@924,675:q',
 'C5@1005,692:h C5@1073,692:q A4@1119,703:q',
 'F4@1204,714:h A4@1278,703:q C5@1327,692:q',
 'D5@1407,687:h C5@1473,692:q C5@1534,692:q',
 'C5@1617,692:w'],[
 'R@204,827:h C4@271,797:h',
 'A3@354,808:qd G3@415,814:e F3@447,820:q D3@495,831:q',
 'C3@568,837:h A2@644,848:q C3@700,837:q',
 'D3@783,831:h D3@850,831:e C3@887,837:e D3@924,831:q',
 'G3@1005,814:h A3@1073,808:q F3@1119,820:q',
 'A3@1204,808:h A3@1278,808:q F3@1327,820:q',
 'D3@1407,831:h C3@1473,837:q C3@1534,837:q',
 'F3@1617,820:w'],[
 'R@204,961:h C5@271,959:h',
 'F5@354,943:qd G5@415,937:e F5@447,943:q D5@495,954:q',
 'C5@568,959:h A4@644,970:q C5@700,959:q',
 'D5@783,954:h D5@850,954:e C5@887,959:e A4@924,970:q',
 'G4@1005,976:h F4@1073,982:q A4@1119,970:q',
 'C5@1204,959:h D5@1278,954:q F4@1327,982:q',
 'A4@1407,970:h G4@1473,976:q G4@1534,976:q',
 'F4@1617,982:w'],[
 'R@204,1087:h F3@271,1079:h',
 'F3@354,1079:qd G3@415,1073:e F3@447,1079:q D3@495,1090:q',
 'F3@568,1079:h G3@644,1073:q A3@700,1068:q',
 'G3@783,1073:h G3@850,1073:q F3@924,1079:q',
 'C3@1005,1096:h C3@1073,1096:q D3@1119,1090:q',
 'F3@1204,1079:h G3@1278,1073:q F3@1327,1079:q',
 'D3@1407,1090:h C3@1473,1096:q C3@1534,1096:q',
 'F3@1617,1079:w']])]

SPECS.append(dict(slug='shenandoah-something-new',start=8,measures=15,
 barlines=[107,355,503,752,877,1082,1304,1557,1641],bottoms=[711,833,957,1075],spacing=12.2,
 curves=[dict(measure=9,firstNote=1,lastNote=3,kind='slur',parts=['P1','P2','P3'],observation='Printed curve spans three notes; P2 returns to its opening pitch through a different middle pitch, so this is not a tie.'),dict(measure=9,firstNote=1,lastNote=2,kind='tie',parts=['P4'],observation='Equal-pitch dotted quarter and quarter connected by a curve.'),dict(measure=11,firstNote=1,lastNote=2,kind='tie',parts=['P1','P2','P3','P4'],observation='Equal-pitch dotted quarter and quarter connected by a curve.')],
 boundary=dict(style='light-heavy',repeat=None,xRange=[1631,1641],observation='Terminal thin/thick barline, with no repeat dots. Dots near x1611 belong to each final dotted half note at x1589.'),
 streams=[[
 'F5@126,662:q F5@183,662:e D5@245,675:e C5@287,681:e Bb4@327,687:e',
 'Bb4@369,687:q D5@409,675:e F5@442,662:q G5@481,656:e',
 'F5@541,662:q F5@598,662:e D5@641,675:e C5@686,681:e Bb4@728,687:e',
 'C5@770,681:qd C5@811,681:q F5@854,662:e',
 'D5@910,675:q Bb4@967,687:e D5@1001,675:q Bb4@1054,687:e',
 'G4@1124,700:q G4@1173,700:e Bb4@1213,687:e C5@1240,681:e D5@1279,675:e',
 'F5@1341,662:q F5@1399,662:e D5@1444,675:q C5@1521,681:e',
 'Bb4@1589,687:hd'],[
 'D5@126,797:q D5@183,797:e Bb4@245,809:q G4@327,822:e',
 'F4@369,827:q G4@409,822:e F4@442,827:q Bb4@481,809:e',
 'D5@541,797:q D5@598,797:e G4@641,822:e A4@686,815:e Bb4@728,809:e',
 'A4@770,815:qd A4@811,815:q F4@854,827:e',
 'F4@910,827:q F4@967,827:e F4@1001,827:q F4@1054,827:e',
 'Bb4@1124,809:q Bb4@1173,809:e G4@1213,822:e F4@1240,827:e Bb4@1279,809:e',
 'D4@1341,839:q D4@1399,839:e D4@1444,839:e F4@1483,827:e G4@1521,822:e',
 'F4@1589,827:hd'],[
 'Bb4@126,934:q Bb4@183,934:e G4@245,946:e F4@287,952:e G4@327,946:e',
 'Bb4@369,934:q G4@409,946:e F4@442,952:q G4@481,946:e',
 'Bb4@541,934:q Bb4@598,934:e Bb4@641,934:e C5@686,928:e D5@728,922:e',
 'C5@770,928:qd C5@811,928:q D5@854,922:e',
 'F5@910,910:q D5@967,922:e F5@1001,910:q F5@1054,910:e',
 'D5@1124,922:q D5@1173,922:e C5@1213,928:e Bb4@1240,934:e G4@1279,946:e',
 'Bb4@1341,934:q Bb4@1399,934:e G4@1444,946:e F4@1483,952:e G4@1521,946:e',
 'Bb4@1589,934:hd'],[
 'F3@126,1039:q F3@183,1039:e G3@245,1033:e F3@287,1039:e D3@327,1052:e',
 'Bb2@369,1064:qd Bb2@442,1064:q D3@481,1052:e',
 'F3@541,1039:q F3@598,1039:e Bb3@641,1021:e A3@686,1027:e G3@728,1033:e',
 'F3@770,1039:qd F3@811,1039:q F3@854,1039:e',
 'Bb3@910,1021:q F3@967,1039:e Bb3@1001,1021:q Bb3@1054,1021:e',
 'G3@1124,1033:q G3@1173,1033:e G3@1213,1033:e F3@1240,1039:e D3@1279,1052:e',
 'F3@1341,1039:q F3@1399,1039:e D3@1444,1052:q F3@1521,1039:e',
 'Bb2@1589,1064:hd']]))

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def child(parent,tag,text=None,**attrs):
 out=E.SubElement(parent,tag,attrs)
 if text is not None:out.text=str(text)
 return out
def write_versioned(p,data):
 if p.exists() and p.read_bytes()!=data:raise ValueError('Existing version differs: '+str(p))
 p.write_bytes(data)
def build(spec):
 slug=spec['slug']; old_evidence=PREVIOUS/f'{slug}-evidence-v2.json'
 original=json.loads(old_evidence.read_text());prior=PREVIOUS/original['candidate']
 assert sha(prior)==original['candidateSha256']
 root=E.parse(prior).getroot()
 root.find('work/work-title').text=original['title']+' — full notation review draft v3'
 root.find('identification/source').text='Retained source '+Path(original['sourcePath']).name+f", printed page 10; both printed systems ({spec['measures']} measures)."
 root.find("identification/miscellaneous/miscellaneous-field[@name='coverage']").text=f"Both complete printed systems ({spec['measures']} measures); lyrics and shapes remain unencoded."
 observations=[]
 for i,(part,stream) in enumerate(zip(root.findall('part'),spec['streams'])):
  assert len(stream)==spec['measures']-spec['start']+1
  for number,encoded in enumerate(stream,spec['start']):
   measure=child(part,'measure',number=str(number));onset=Fraction(0);notes=[]
   for index,token in enumerate(encoded.split(),1):
    pitch_str,xy,code=re.fullmatch(r'([A-G]b?[0-9]|R)@(\d+,\d+):(w|hd|h|qd|q|e)',token).groups()
    x,y=map(int,xy.split(','));typ,units,dotted=TYPES[code]
    n=child(measure,'note')
    if pitch_str=='R':child(n,'rest')
    else:
     step,flat,octave=re.fullmatch(r'([A-G])(b?)([0-9])',pitch_str).groups()
     p=child(n,'pitch');child(p,'step',step)
     if flat:child(p,'alter',-1)
     child(p,'octave',octave)
    child(n,'duration',units)
    curve=next((c for c in spec['curves'] if c['measure']==number and part.attrib['id'] in c['parts'] and index in (c['firstNote'],c['lastNote'])),None)
    endpoint='start' if curve and index==curve['firstNote'] else 'stop'
    if curve and curve['kind']=='tie':child(n,'tie',type=endpoint)
    child(n,'type',typ)
    if dotted:child(n,'dot')
    if curve:
     ns=child(n,'notations')
     if curve['kind']=='tie':child(ns,'tied',type=endpoint)
     else:child(ns,'slur',type=endpoint,number='1')
    notes.append(dict(noteIndex=index,noteCenter=[x,y],observedPitch=pitch_str,observedType=typ,observedDot=dotted,onsetQuarter=float(onset),durationQuarter=units/2))
    onset+=Fraction(units,2)
   observations.append(dict(part=part.attrib['id'],measure=number,xRange=spec['barlines'][number-spec['start']:number-spec['start']+2],staffBottomY=spec['bottoms'][i],staffLineSpacing=spec['spacing'],notes=notes))
   if number==spec['measures']:
    barline=child(measure,'barline',location='right');child(barline,'bar-style',spec['boundary']['style'])
    if spec['boundary']['repeat']:child(barline,'repeat',direction=spec['boundary']['repeat'])
 E.indent(root);candidate=BASE/f'{slug}-full-notation-candidate-v3.musicxml'
 write_versioned(candidate,E.tostring(root,encoding='utf-8',xml_declaration=True))
 evidence=deepcopy(original)
 evidence.update(version=3,candidate=candidate.name,candidateSha256=sha(candidate),predecessorPath=str(prior.relative_to(ROOT)),predecessorSha256=sha(prior),predecessorEvidencePath=str(old_evidence.relative_to(ROOT)),predecessorEvidenceSha256=sha(old_evidence),coverage=f"both printed systems, {spec['measures']} measures across four voices",completeMeasuresPerPart=spec['measures'],predecessorMeasuresPerPart=spec['start']-1,pitchedNotes=len(root.findall('.//note/pitch')),addedPitchedNotes=len(root.findall('.//note/pitch'))-original['pitchedNotes'],curveObservations=original['curveObservations']+spec['curves'],measureObservations=observations,terminalBoundary=spec['boundary'],limitations=['Full written notation extent; lyrics and printed notehead shapes remain unencoded.','Printed key label is retained as evidence; mode remains unset.','Printed clefs are literal; no unprinted octave transposition is applied.','Human-review-required draft; retained filename provenance is not new exact-edition certification.']+(['Terminal backward repeat is encoded without inventing a forward boundary or repeat count. Atlas event-stream receipt is linear written-order playback, not repeat-navigation certification.'] if spec['boundary']['repeat'] else ['Plain terminal thin/thick barline; final note dots are duration dots, not repeat signs.']))
 evidence['coordinateSystem']['secondSystemBarlinesX']=spec['barlines']
 evidence['coordinateSystem']['secondSystemFirstMeasure']=spec['start']
 write_versioned(BASE/f'{slug}-evidence-v3.json',(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n').encode())
 print(candidate.name,evidence['pitchedNotes'],'pitches')
if __name__=='__main__':
 for spec in SPECS:build(spec)
