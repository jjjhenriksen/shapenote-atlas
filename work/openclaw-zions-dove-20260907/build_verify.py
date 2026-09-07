#!/usr/bin/env python3
"""Export bounded directly reviewed second-3; never mutate historical candidates."""
import copy
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
LANE = ROOT / 'work/luna-program-20260904/existing_books'
BASE = LANE / 'ch7-10-first-system-candidate-v17'
SCAN = LANE / 'assets/christian-harmony/batch-01/scans/10-zions-dove.jpg'
STEM = OUT / 'ch7-10-first-system-candidate-v21'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def retain_bytes(path, payload):
    if path.exists():
        assert path.read_bytes() == payload, 'Never overwrite a released candidate: ' + str(path)
    else:
        path.write_bytes(payload)

def structural(e):
    return (e.tag, sorted(e.attrib.items()), (e.text or '').strip(), tuple(structural(c) for c in e))

# Direct review of full retained 1654x1119 scan on 2026-09-07.
# Columns: pitch, quarter beats, head center x/y; NOT pitch-derived shape evidence.
OBSERVED = {
    'Treble': [('Eb5', 2, 457, 668), ('Bb4', 2, 482, 687)],
    'Alto': [('Ab4', 2, 457, 821), ('G4', 2, 482, 827)],
    'Tenor': [('C5', 2, 457, 911), ('Eb5', 2, 482, 898)],
    'Bass': [('Eb3', 4, 458, 1039)],
}
LYRICS = {'Treble': ('1', 'dove,'), 'Tenor': ('2', 'be;')}
assert sha(SCAN) == 'eba3f9387bf9b2ba9b83bee3e8c6f7abb33f37acb38ddf3f726423175af78584'
originals = {str(p.relative_to(ROOT)): sha(p) for p in LANE.glob('*v*.json')}
originals.update({str(p.relative_to(ROOT)): sha(p) for p in LANE.glob('*v*.musicxml')})
d = json.loads(BASE.with_suffix('.json').read_text())
base_json = copy.deepcopy(d)
tree = ET.parse(BASE.with_suffix('.musicxml'))
base_xml = copy.deepcopy(tree.getroot())
d['status'] = 'partial-first-and-second-system-review-candidate-v21'
d['safeToPromote'] = False
d['sourceScan'] = str(SCAN.relative_to(ROOT))
d['preservedCandidates'] += ['ch7-10-first-system-candidate-v17.json', 'ch7-10-first-system-candidate-v20.json']
d['reviewV21'] = {
    'date': '2026-09-07', 'measure': 'second-3', 'sourceXWindow': [438,502],
    'base': str(BASE.relative_to(ROOT)) + '.musicxml',
    'supersedes': 'v20 appendix only; all v17 semantics preserved',
    'directObservation': 'Treble dove, and tenor be; belong to this slurred bar. The and And begin after x502. No second-note text printed in this bar.',
    'remainingGaps': ['Second system after x502 remains untranscribed, including printed endings/repeat.', 'New noteheads have no audited shape tags.', 'No added lyric extend markers: printed slurs retained separately.', 'No alto/bass lyric underlay inferred from other staves.', 'Full exact-edition semantics review still required.'],
}
for jp, xp in zip(d['parts'], tree.getroot().findall('part')):
    name = jp['name']
    cursor = 52.0
    m = ET.SubElement(xp, 'measure', {'number':'second-3'})
    ET.SubElement(ET.SubElement(m, 'attributes'), 'divisions').text='1'
    for i, (pitch, beats, x, y) in enumerate(OBSERVED[name]):
        typ = 'whole' if beats == 4 else 'half'
        event = {'onset':cursor, 'beats':float(beats), 'measure':'second-3', 'rest':False,
                 'type':typ, 'staffX':x, 'staffY':y, 'stepPitch':pitch,
                 'pitchDerivation':'direct second-system staff position with printed four-flat signature; not shape',
                 'shapeGlyphObserved':'not-audited-in-v21'}
        n=ET.SubElement(m,'note'); p=ET.SubElement(n,'pitch'); ET.SubElement(p,'step').text=pitch[0]
        if 'b' in pitch: ET.SubElement(p,'alter').text='-1'
        ET.SubElement(p,'octave').text=pitch[-1]
        ET.SubElement(n,'duration').text=str(beats); ET.SubElement(n,'type').text=typ
        if name != 'Bass':
            slur_type = 'start' if i == 0 else 'stop'
            event['sourceObservedSlur'] = {'type':slur_type, 'number':'1', 'evidence':'visible curve between distinct pitches, not tie'}
            ET.SubElement(ET.SubElement(n,'notations'),'slur',{'type':slur_type,'number':'1'})
        if i == 0 and name in LYRICS:
            num,word=LYRICS[name]
            event['lyrics']=[{'number':num,'syllable':word,'sourceAnchored':True,'syllabic':'single'}]
            l=ET.SubElement(n,'lyric',{'number':num}); ET.SubElement(l,'syllabic').text='single'; ET.SubElement(l,'text').text=word
        jp['events'].append(event); cursor += beats
    assert cursor == 56
retain_bytes(STEM.with_suffix('.json'), (json.dumps(d, indent=2)+'\n').encode())
xml_bytes = io.BytesIO()
tree.write(xml_bytes, encoding='utf-8', xml_declaration=True)
retain_bytes(STEM.with_suffix('.musicxml'), xml_bytes.getvalue())
# Verify exported bytes, preserved XML structure, actual JSON/XML parity and measure cursors.
r=ET.parse(STEM.with_suffix('.musicxml')).getroot()
j=json.loads(STEM.with_suffix('.json').read_text())
part_receipts=[]
for oldp,newp,oldj,newj in zip(base_xml.findall('part'),r.findall('part'),base_json['parts'],j['parts']):
    measures=newp.findall('measure'); last=measures[-1]
    assert last.attrib == {'number':'second-3'}
    restored=copy.deepcopy(newp); restored.remove(restored.findall('measure')[-1])
    assert structural(restored) == structural(oldp)
    assert newj['events'][:len(oldj['events'])] == oldj['events']
    appended=newj['events'][len(oldj['events']):]
    assert len(last.findall('note')) == len(appended)
    cursor=52.0
    for n,e in zip(last.findall('note'),appended):
        pitch=n.find('pitch'); actual=pitch.findtext('step')+('b' if pitch.findtext('alter')=='-1' else '')+pitch.findtext('octave')
        assert actual == e['stepPitch']
        assert float(n.findtext('duration')) == e['beats'] and e['onset'] == cursor
        assert n.findtext('type') == e['type']
        assert [l.findtext('text') for l in n.findall('lyric')] == [l['syllable'] for l in e.get('lyrics',[])]
        assert not n.findall('tie') and not n.findall('notehead') and not n.findall('.//extend')
        cursor += e['beats']
    assert cursor == 56
    part_receipts.append({'part':newj['name'],'prefixPreserved':True,'eventsAdded':len(appended),'endOnset':cursor,'totalPitchedNotes':len(newp.findall('.//note/pitch'))})
assert originals == {p:sha(ROOT/p) for p in originals}
receipt={'status':'passed','safeToPromote':False,'sourceSha256':sha(SCAN),
         'baseXmlSha256':sha(BASE.with_suffix('.musicxml')),'candidateXmlSha256':sha(STEM.with_suffix('.musicxml')),
         'candidateJsonSha256':sha(STEM.with_suffix('.json')),'parts':part_receipts,
         'historicalFilesUnchanged':len(originals),'newLyrics':[l.findtext('text') for p in r.findall('part') for l in p.findall('measure')[-1].findall('.//lyric')],
         'scope':'Structural preservation and exported parity only; direct scan review is separately documented, not established by these assertions.'}
(OUT/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
