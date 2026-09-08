"""Check exported structure, metrical completeness and observed staff-position parity.
Coordinates are visual-review observations, not independent optical recognition.
"""
from pathlib import Path
from fractions import Fraction
import hashlib,json,xml.etree.ElementTree as E
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(e):
 src=ROOT/e['sourcePath'];assert sha(src)==e['sourceSha256'], 'source hash'
 xml=BASE/e['candidate'];assert sha(xml)==e['candidateSha256'],'candidate hash'
 root=E.parse(xml).getroot();assert root.tag=='score-partwise'
 parts=root.findall('part');assert len(parts)==4
 assert [p.attrib['id'] for p in parts]==[v['part'] for v in e['voiceObservations']]
 assert not root.findall('.//lyric') and not root.findall('.//notehead') and not root.findall('.//mode')
 assert not root.findall('.//repeat') and not root.findall('.//ending') and not root.findall('.//tie')
 assert e['reviewRequired'] and not e['safeToPromote']
 totalNotes=0
 for p,v in zip(parts,e['voiceObservations']):
  ms=p.findall('measure');assert len(ms)==1
  m=ms[0];a=m.find('attributes');div=int(a.findtext('divisions'))
  assert a.findtext('clef/sign')==v['clef'] and int(a.findtext('clef/line'))==v['clefLine']
  assert int(a.findtext('key/fifths'))==e['keySignatureFifths']
  bar=Fraction(int(a.findtext('time/beats'))*4,int(a.findtext('time/beat-type')))
  notes=m.findall('note');assert len(notes)==2 and notes[0].find('rest') is not None and notes[1].find('pitch') is not None
  onset=Fraction(0)
  for n in notes:
   duration=Fraction(int(n.findtext('duration')),div)
   typed={'half':Fraction(2),'quarter':Fraction(1)}[n.findtext('type')]
   if n.find('dot') is not None:typed*=Fraction(3,2)
   assert duration==typed,'duration/type inconsistency'
   if n.find('pitch') is not None:
    assert onset==Fraction(str(v['noteOnsetQuarter'])) and duration==Fraction(str(v['noteDurationQuarter']))
    pit=n.find('pitch');step=pit.findtext('step');octave=int(pit.findtext('octave'));alter=int(pit.findtext('alter','0'))
    assert (step,octave,alter)==(v['step'],v['octave'],v['alter'])
    staffSteps=(v['staffBottomY']-v['noteCenter'][1])/(v['staffLineSpacing']/2)
    assert abs(staffSteps-round(staffSteps))<.3,'ambiguous coordinate'
    baseline=('E',4) if v['clef']=='G' else ('G',2)
    letters='CDEFGAB';index=baseline[1]*7+letters.index(baseline[0])+round(staffSteps)
    assert (letters[index%7],index//7)==(step,octave),'staff-coordinate pitch disagrees with XML'
    # Signature alteration is independent of the encoded pitch table.
    expected=-1 if step in 'BE'[:abs(e['keySignatureFifths'])] else 0
    assert alter==expected,'key-signature pitch alteration mismatch'
    totalNotes+=1
   onset+=duration
  assert onset==bar,'incomplete or overflowing first bar'
 assert totalNotes==4
 return dict(candidate=e['candidate'],parts=len(parts),pitchedNotes=totalNotes,completeMeasuresPerPart=1,result='pass')
if __name__=='__main__':
 for f in sorted(BASE.glob('*-evidence-v1.json')):print(json.dumps(check(json.loads(f.read_text()))))
