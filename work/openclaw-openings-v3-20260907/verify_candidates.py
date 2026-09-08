"""Check issued XML against predecessors, metrical notation, and visual coordinates.

Coordinates are retained manual observations, not an automatic optical audit.
This verifies that the exported XML implements those observations; it does not
certify missing lyrics, notehead shapes, mode, or exact-edition provenance.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as E
import zipfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
LETTERS = 'CDEFGAB'
TYPED_QUARTERS = {'whole': Fraction(4), 'half': Fraction(2),
                  'quarter': Fraction(1), 'eighth': Fraction(1,2)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(node):
    return E.canonicalize(E.tostring(node, encoding='unicode'), strip_text=True)


def xml_pitch(note):
    p = note.find('pitch')
    return p.findtext('step'), int(p.findtext('octave')), int(p.findtext('alter','0'))


def coordinate_pitch(observation, voice, fifths):
    # Derive pitch from staff position independently of observedPitch strings.
    steps = ((voice['staffBottomY'] - observation['noteCenter'][1]) /
             (voice['staffLineSpacing']/2))
    assert abs(steps-round(steps)) < .31, 'ambiguous source coordinate'
    clef = voice['clef']
    baseline = ('E',4) if clef == 'G' else ('G',2)
    index = baseline[1]*7 + LETTERS.index(baseline[0]) + round(steps)
    step, octave = LETTERS[index%7], index//7
    alteration = -1 if step in 'BEADGCF'[:abs(fifths)] else 0
    return step, octave, alteration


def check_structure(root, prior, evidence):
    parts, old_parts = root.findall('part'), prior.findall('part')
    assert root.tag == 'score-partwise' and len(parts) == len(old_parts) == 4
    assert canonical(root.find('part-list')) == canonical(prior.find('part-list')), 'part list changed'
    assert [p.attrib['id'] for p in parts] == [p.attrib['id'] for p in old_parts]
    for tag in ['lyric','notehead','mode','ending','backup','forward','chord']:
        assert not root.findall('.//'+tag), f'unreviewed {tag}'
    assert root.findtext("identification/miscellaneous/miscellaneous-field[@name='review-required']") == 'true'
    assert root.findtext("identification/miscellaneous/miscellaneous-field[@name='safe-to-promote']") == 'false'
    assert evidence['reviewRequired'] and not evidence['safeToPromote']
    observations = {(x['part'],x['measure']):x for x in evidence['measureObservations']}
    assert len(observations) == 4*(evidence['completeMeasuresPerPart']-evidence['predecessorMeasuresPerPart'])
    counts = {}
    measure_duration = None
    for part, old_part, v1 in zip(parts, old_parts, evidence['voiceObservations']):
        part_id = part.attrib['id']
        measures = part.findall('measure')
        old = old_part.findall('measure')
        assert len(old) == evidence['predecessorMeasuresPerPart']
        assert all(canonical(a)==canonical(b) for a,b in zip(measures,old)), 'v2 prefix XML changed'
        assert len(measures) == evidence['completeMeasuresPerPart']
        attrs = measures[0].find('attributes')
        div = int(attrs.findtext('divisions'))
        fifths = int(attrs.findtext('key/fifths'))
        assert fifths == evidence['keySignatureFifths']
        assert attrs.findtext('clef/sign') == v1['clef']
        assert int(attrs.findtext('clef/line')) == v1['clefLine']
        bar = Fraction(int(attrs.findtext('time/beats'))*4, int(attrs.findtext('time/beat-type')))
        assert measure_duration is None or measure_duration == bar
        measure_duration = bar
        pitched = 0
        for number, measure in enumerate(measures, 1):
            assert measure.attrib['number'] == str(number)
            notes = measure.findall('note')
            if number > evidence['predecessorMeasuresPerPart']:
                assert measure.find('attributes') is None, 'unexpected inherited-attribute change'
                obs = observations[(part_id,number)]
                voice = dict(staffBottomY=obs['staffBottomY'], staffLineSpacing=obs['staffLineSpacing'],
                             clef=v1['clef'])
                assert len(notes) == len(obs['notes'])
                assert obs['xRange'] == evidence['coordinateSystem']['secondSystemBarlinesX'][number-evidence['predecessorMeasuresPerPart']-1:number-evidence['predecessorMeasuresPerPart']+1]
                assert all(a['noteCenter'][0] < b['noteCenter'][0] for a,b in zip(obs['notes'],obs['notes'][1:])), 'source order'
            onset = Fraction(0)
            for index, note in enumerate(notes,1):
                duration = Fraction(int(note.findtext('duration')),div)
                typed = TYPED_QUARTERS[note.findtext('type')]
                dots = len(note.findall('dot'))
                assert dots <= 1
                if dots:
                    typed *= Fraction(3,2)
                assert duration == typed and duration > 0, 'duration/type mismatch'
                if note.find('pitch') is not None:
                    pitched += 1
                if number > evidence['predecessorMeasuresPerPart']:
                    observed = obs['notes'][index-1]
                    assert observed['noteIndex'] == index
                    assert obs['xRange'][0] < observed['noteCenter'][0] < obs['xRange'][1]
                    assert onset == Fraction(str(observed['onsetQuarter'])), 'incorrect note onset'
                    assert duration == Fraction(str(observed['durationQuarter'])), 'incorrect note length'
                    assert note.findtext('type') == observed['observedType'] and bool(dots) == observed['observedDot']
                    if observed['observedPitch']=='R':
                        assert note.find('rest') is not None, 'source rest omitted'
                    else:
                        actual = xml_pitch(note)
                        assert actual == coordinate_pitch(observed,voice,fifths), f'{part_id} m{number} n{index}: staff-coordinate pitch differs from XML'
                        spelling = actual[0] + ('b' if actual[2] == -1 else '') + str(actual[1])
                        assert spelling == observed['observedPitch'], 'written pitch differs from visual transcription'
                onset += duration
            assert onset == bar, f'{part_id} m{number}: incomplete/overflowing bar'
        counts[part_id] = pitched
    assert sum(counts.values()) == evidence['pitchedNotes']
    assert sum(counts.values()) - len(prior.findall('.//note/pitch')) == evidence['addedPitchedNotes']
    boundaries=root.findall('.//barline')
    assert len(boundaries)==4
    for part in parts:
        barline=part.findall('measure')[-1].find('barline')
        assert barline is not None and barline.attrib=={'location':'right'}
        assert barline.findtext('bar-style')==evidence['terminalBoundary']['style']
        expected_repeat=[{'direction':evidence['terminalBoundary']['repeat']}] if evidence['terminalBoundary']['repeat'] else []
        assert [r.attrib for r in barline.findall('repeat')]==expected_repeat
    assert len(root.findall('.//repeat')) == (4 if evidence['terminalBoundary']['repeat'] else 0)
    expected = []
    for curve in evidence['curveObservations']:
        for part_id in curve['parts']:
            measure = root.find(f"part[@id='{part_id}']/measure[@number='{curve['measure']}']")
            ns = measure.findall('note')
            a, b = ns[curve['firstNote']-1], ns[curve['lastNote']-1]
            if curve['kind'] == 'tie':
                assert xml_pitch(a) == xml_pitch(b), 'tie changes pitch'
                for tag in ['tie','notations/tied']:
                    assert [x.attrib for x in a.findall(tag)] == [{'type':'start'}]
                    assert [x.attrib for x in b.findall(tag)] == [{'type':'stop'}]
            else:
                assert any(xml_pitch(n)!=xml_pitch(a) for n in ns[curve['firstNote']:curve['lastNote']]), 'slur contains no pitch change'
                assert [x.attrib for x in a.findall('notations/slur')] == [{'type':'start','number':'1'}]
                assert [x.attrib for x in b.findall('notations/slur')] == [{'type':'stop','number':'1'}]
            expected.append(curve['kind'])
    assert len(root.findall('.//tie')) == 2*expected.count('tie')
    assert len(root.findall('.//tied')) == 2*expected.count('tie')
    assert len(root.findall('.//slur')) == 2*expected.count('slur')
    return dict(parts=4, pitchedNotesByPart=counts, pitchedNotes=sum(counts.values()),
                addedPitchedNotes=evidence['addedPitchedNotes'],
                completeMeasuresPerPart=evidence['completeMeasuresPerPart'],
                durationQuarterPerPart=float(measure_duration*evidence['completeMeasuresPerPart']),
                exactV2PrefixPreserved=True, ties=expected.count('tie'), slurs=expected.count('slur'))


def check(evidence):
    for key, hash_key in [('sourcePath','sourceSha256'),('predecessorPath','predecessorSha256'),
                          ('predecessorEvidencePath','predecessorEvidenceSha256')]:
        assert sha(ROOT/evidence[key]) == evidence[hash_key], key+' hash mismatch'
    coords = evidence['coordinateSystem']
    assert sha(ROOT/coords['imagePath']) == coords['imageSha256'], 'review image hash mismatch'
    candidate = BASE/evidence['candidate']
    assert sha(candidate) == evidence['candidateSha256'], 'candidate hash mismatch'
    prior = E.parse(ROOT/evidence['predecessorPath']).getroot()
    root = E.parse(candidate).getroot()
    result = check_structure(root,prior,evidence)
    # Prove checks reject semantic corruption even when a candidate hash is
    # recomputed: predecessor drift, coordinate-pitch drift, type inconsistency,
    # and dropped source curves are each independent error classes.
    mutations = {
        'predecessor drift': lambda r: setattr(r.find("part/measure[@number='1']/note/duration"),'text','1'),
        'pitch drift': lambda r: setattr(r.findall('part/measure')[-1].find('note/pitch/octave'),'text','8'),
        'duration drift': lambda r: setattr(r.findall('part/measure')[-1].find('note/duration'),'text','99'),
        'missing terminal boundary': lambda r: r.findall('part/measure')[-1].remove(r.findall('part/measure')[-1].find('barline')),
        'missing appended source curve': lambda r: r.findall('.//notations')[-1].clear(),
    }
    for name, mutate in mutations.items():
        corrupted = deepcopy(root)
        mutate(corrupted)
        try:
            check_structure(corrupted,prior,evidence)
        except AssertionError:
            continue
        raise AssertionError('Verifier accepted '+name)
    return dict(candidate=evidence['candidate'], result='pass',
                rejectedCorruptionClasses=list(mutations), **result)


def check_parser(evidence):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_data import parse_score, build_draft_playback_validation
    candidate = BASE/evidence['candidate']
    with tempfile.TemporaryDirectory(dir=BASE) as temporary:
        wrapper = Path(temporary)/'score.mxl'
        with zipfile.ZipFile(wrapper,'w') as archive:
            archive.writestr('score.xml',candidate.read_bytes())
        parsed = parse_score(str(candidate),wrapper)
    assert parsed is not None
    assert not build_draft_playback_validation(candidate.stem,parsed,{}), 'parser rejected durations'
    root = E.parse(candidate).getroot()
    assert len(parsed['parts']) == len(root.findall('part')) == 4
    for part, parsed_part in zip(root.findall('part'),parsed['parts']):
        notes = part.findall('measure/note')
        assert len(parsed_part['events']) == len(notes)
        div = int(part.findtext('measure/attributes/divisions'))
        onset = Fraction(0)
        for note,event in zip(notes,parsed_part['events']):
            duration = Fraction(int(note.findtext('duration')),div)
            assert (event['onset'],event['beats']) == (float(onset),float(duration))
            assert event['rest'] == (note.find('rest') is not None)
            if not event['rest']:
                assert (event['step'],event['octave'],event.get('alter',0)) == xml_pitch(note)
            assert event.get('tieStart',False) == (note.find("tie[@type='start']") is not None)
            assert event.get('tieStop',False) == (note.find("tie[@type='stop']") is not None)
            onset += duration
    return dict(durationValidation='pass', actualXmlEventStreamPreserved=True,
                events=sum(len(p['events']) for p in parsed['parts']),
                pitchedNotes=sum(sum(not e['rest'] for e in p['events']) for p in parsed['parts']),
                parserSourceSha256=sha(ROOT/'scripts/build_data.py'))


if __name__ == '__main__':
    results = []
    for path in sorted(BASE.glob('*-evidence-v3.json')):
        evidence = json.loads(path.read_text())
        results.append(dict(**check(evidence), parser=check_parser(evidence)))
    assert len(results) >= 1
    print(json.dumps(results,indent=2))
