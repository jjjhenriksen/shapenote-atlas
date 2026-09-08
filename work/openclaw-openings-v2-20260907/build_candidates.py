"""Versioned first-system extensions from directly inspected retained sources.

Pitch spellings are the visual transcription. Independent staff coordinates are
retained for verification; they are not synthesized from these pitch spellings.
No prior candidate, publication, or source bytes are changed.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as E

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PREVIOUS = ROOT / 'work/openclaw-openings-20260907'
TYPES = {'w': ('whole', 8, False), 'h': ('half', 4, False),
         'q': ('quarter', 2, False), 'qd': ('quarter', 3, True),
         'e': ('eighth', 1, False)}

# pitch@x,y:type. Coordinates use the explicitly named visual review space,
# with origin at the top left of the whole page. Bars are read left to right.
SPECS = [
    dict(slug='kentucky-new-salem', measures=8,
         barlines=[208, 354, 586, 783, 990, 1166, 1383, 1581, 1727],
         image='work/openclaw-openings-20260907/renders/kentucky.png',
         display=[1780, 1376], actual=[2200, 1700],
         bottoms=[205, 331, 458, 585], spacing=11.2,
         curves=[dict(measure=2, firstNote=1, lastNote=2, kind='slur',
                      parts=['P1','P2','P3','P4'],
                      observation='Printed curve joins distinct pitches in each voice.')],
         streams=[
             [
                 'C5@379,177:qd Bb4@441,183:e A4@482,188:q G4@546,194:q',
                 'F4@625,199:h A4@690,188:q Bb4@750,183:q',
                 'A4@822,188:h Bb4@895,183:q Bb4@957,183:q',
                 'C5@1033,177:h A4@1107,188:h',
                 'C5@1206,177:h C5@1278,177:q G4@1346,194:q',
                 'A4@1424,188:h C5@1490,177:q C5@1544,177:q',
                 'C5@1646,177:w',
             ], [
                 'D3@379,309:qd E3@444,303:e F3@482,297:q G3@546,292:q',
                 'A3@625,286:h G3@690,292:q F3@750,297:q',
                 'D3@822,309:h D3@895,309:q D3@957,309:q',
                 'C3@1033,314:h F3@1107,297:h',
                 'A3@1206,286:h A3@1278,286:q G3@1346,292:q',
                 'F3@1424,297:h F3@1490,297:q G3@1544,292:q',
                 'A3@1646,286:w',
             ], [
                 'F4@379,451:qd G4@445,446:e A4@482,440:q Bb4@546,434:q',
                 'C5@625,429:h D5@690,424:q Bb4@750,434:q',
                 'A4@822,440:h G4@895,446:q G4@957,446:q',
                 'F4@1033,451:h C5@1107,429:h',
                 'F5@1206,413:h F5@1278,413:q G5@1346,407:q',
                 'A5@1424,402:h G5@1490,407:q E5@1544,419:q',
                 'F5@1646,413:w',
             ], [
                 'F3@379,552:qd E3@444,558:e F3@482,552:q G3@546,546:q',
                 'C3@625,569:h D3@690,563:q Bb2@750,574:q',
                 'A2@822,580:h C3@895,569:q C3@957,569:q',
                 'F3@1033,552:h F3@1107,552:h',
                 'F3@1206,552:h F3@1278,552:q G3@1346,546:q',
                 'A3@1424,541:h G3@1490,546:q C4@1544,530:q',
                 'F3@1646,552:w',
             ],
         ]),
    dict(slug='shenandoah-something-new', measures=7,
         barlines=[150, 277, 515, 777, 1005, 1172, 1397, 1641],
         image='work/luna-program-20260904/source_only/retained-sources/shenandoah-010-something-new.jpg',
         display=[1654,1157], actual=[1654,1157],
         bottoms=[168,293,410,530], spacing=12.2,
         curves=[dict(measure=5, firstNote=1, lastNote=2, kind='tie',
                      parts=['P1','P2','P3','P4'],
                      observation='Printed curve joins equal pitches; dotted quarter tied to quarter, followed by separate eighth.')],
         streams=[
             [
                 'D5@311,132:q D5@365,132:e D5@408,132:e C5@447,138:e Bb4@486,144:e',
                 'D5@555,132:q D5@607,132:e D5@642,132:e F5@694,119:e G5@746,113:e',
                 'F5@818,119:q F5@873,119:e D5@910,132:e C5@950,138:e Bb4@987,144:e',
                 'C5@1027,138:qd C5@1093,138:q F5@1143,119:e',
                 'D5@1209,132:q Bb4@1266,144:e D5@1309,132:q Bb4@1370,144:e',
                 'G4@1445,156:q G4@1500,156:e Bb4@1537,144:e C5@1574,138:e D5@1613,132:e',
             ], [
                 'D4@311,299:q D4@365,299:e D4@408,299:q F4@488,287:e',
                 'Bb4@555,269:q Bb4@608,269:e Bb4@654,269:e A4@695,275:e Bb4@745,269:e',
                 'F4@818,287:q F4@874,287:e G4@910,281:e A4@950,275:e Bb4@987,269:e',
                 'A4@1027,275:qd A4@1093,275:q F4@1143,287:e',
                 'F4@1209,287:q F4@1266,287:e F4@1309,287:q F4@1370,287:e',
                 'Bb4@1445,269:q Bb4@1500,269:e G4@1537,281:e F4@1574,287:e Bb4@1613,269:e',
             ], [
                 'Bb4@311,386:q Bb4@367,386:e Bb4@411,386:e C5@447,380:e D5@486,374:e',
                 'G4@555,398:q G4@608,398:e G4@651,398:e F4@695,404:e G4@746,398:e',
                 'Bb4@818,386:q Bb4@874,386:e Bb4@914,386:e C5@950,380:e D5@988,374:e',
                 'C5@1027,380:qd C5@1093,380:q D5@1143,374:e',
                 'F5@1209,362:q D5@1266,374:e F5@1309,362:q F5@1370,362:e',
                 'D5@1445,374:q D5@1500,374:e C5@1537,380:e Bb4@1574,386:e G4@1613,398:e',
             ], [
                 'F3@311,493:q F3@367,493:e F3@411,493:e G3@447,487:e Bb3@486,475:e',
                 'G3@555,487:q G3@608,487:e G3@651,487:e F3@695,493:e D3@746,505:e',
                 'F3@818,493:q F3@874,493:e Bb3@914,475:e A3@950,481:e G3@988,487:e',
                 'F3@1027,493:qd F3@1093,493:q F3@1143,493:e',
                 'Bb3@1209,475:q F3@1266,493:e Bb3@1309,475:q F3@1370,493:e',
                 'G3@1445,487:q G3@1500,487:e G3@1537,487:e F3@1574,493:e D3@1613,505:e',
             ],
         ]),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def child(parent, tag, text=None, **attrs):
    out = E.SubElement(parent, tag, attrs)
    if text is not None:
        out.text = str(text)
    return out


def write_versioned(path, data):
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f'Refusing to change an existing candidate/evidence version: {path}')
    path.write_bytes(data)


def build(spec):
    slug = spec['slug']
    old_evidence = PREVIOUS / f'{slug}-evidence-v1.json'
    original = json.loads(old_evidence.read_text())
    prior = PREVIOUS / original['candidate']
    if sha(prior) != original['candidateSha256']:
        raise ValueError('Predecessor no longer matches its issued evidence')
    root = E.parse(prior).getroot()
    root.find('work/work-title').text = original['title'] + ' — first system review draft v2'
    root.find('identification/source').text = ('Retained source ' + Path(original['sourcePath']).name +
                                             f", printed page 10; first {spec['measures']} bars only.")
    root.find("identification/miscellaneous/miscellaneous-field[@name='coverage']").text = (
        f"First printed system ({spec['measures']} complete measures); remainder omitted, not silence.")
    observations = []
    for i, (part, stream) in enumerate(zip(root.findall('part'), spec['streams'])):
        assert len(stream) == spec['measures'] - 1
        for number, encoded in enumerate(stream, 2):
            measure = child(part, 'measure', number=str(number))
            onset = Fraction(0)
            notes = []
            for index, token in enumerate(encoded.split(), 1):
                match = re.fullmatch(r'([A-G])(b?)([0-9])@(\d+),(\d+):(w|h|q|qd|e)', token)
                if not match:
                    raise ValueError(token)
                step, flat, octave, x, y, code = match.groups()
                typ, units, dotted = TYPES[code]
                n = child(measure, 'note')
                pitch = child(n, 'pitch')
                child(pitch, 'step', step)
                if flat:
                    child(pitch, 'alter', -1)
                child(pitch, 'octave', octave)
                child(n, 'duration', units)
                curve = next((c for c in spec['curves'] if c['measure'] == number and
                              part.attrib['id'] in c['parts'] and index in (c['firstNote'],c['lastNote'])), None)
                endpoint = 'start' if curve and index == curve['firstNote'] else 'stop'
                if curve and curve['kind'] == 'tie':
                    child(n, 'tie', type=endpoint)
                child(n, 'type', typ)
                if dotted:
                    child(n, 'dot')
                if curve:
                    notation = child(n, 'notations')
                    if curve['kind'] == 'tie':
                        child(notation, 'tied', type=endpoint)
                    else:
                        child(notation, 'slur', type=endpoint, number='1')
                notes.append(dict(noteIndex=index, noteCenter=[int(x),int(y)],
                                  observedPitch=step+flat+octave,
                                  observedType=typ, observedDot=dotted,
                                  onsetQuarter=float(onset), durationQuarter=units/2))
                onset += Fraction(units,2)
            observations.append(dict(part=part.attrib['id'], measure=number,
                                     xRange=spec['barlines'][number-1:number+1],
                                     staffBottomY=spec['bottoms'][i],
                                     staffLineSpacing=spec['spacing'], notes=notes))
    E.indent(root)
    candidate = BASE / f'{slug}-first-system-candidate-v2.musicxml'
    write_versioned(candidate, E.tostring(root, encoding='utf-8', xml_declaration=True))
    evidence = deepcopy(original)
    evidence.update(version=2, candidate=candidate.name, candidateSha256=sha(candidate),
                    predecessorPath=str(prior.relative_to(ROOT)), predecessorSha256=sha(prior),
                    predecessorEvidencePath=str(old_evidence.relative_to(ROOT)),
                    predecessorEvidenceSha256=sha(old_evidence),
                    coverage=f"complete first printed system: {spec['measures']} measures across four voices",
                    completeMeasuresPerPart=spec['measures'],
                    pitchedNotes=len(root.findall('.//note/pitch')),
                    addedPitchedNotes=len(root.findall('.//note/pitch'))-4,
                    sourceReviewMethod='Direct inspection of retained full-page image; manual staff-position and duration reading, not OMR.',
                    curveObservations=spec['curves'], measureObservations=observations,
                    coordinateSystem=dict(origin='top-left', imagePath=spec['image'],
                                          imageSha256=sha(ROOT/spec['image']),
                                          reviewDisplayDimensions=spec['display'],
                                          actualImageDimensions=spec['actual'],
                                          conversion='Multiply display coordinates by actual/display dimensions.',
                                          firstSystemBarlinesX=spec['barlines']),
                    limitations=[
                        'Only the full first printed system is included; all later systems are omitted, not silence.',
                        'Lyrics and notehead shapes remain omitted pending direct underlay/glyph review.',
                        'Printed key label is retained as evidence; MusicXML mode remains unset.',
                        'Printed clefs are literal; no unprinted octave transposition is applied.',
                        'Retained source filename links this page to the book; exact-edition provenance is not newly certified.',
                        'No final barline, repeat, or unseen navigation is invented at the excerpt boundary.',
                        'Human-review-required draft, not an exact-edition verified score.'
                    ])
    evidence.pop('renderSha256',None)
    write_versioned(BASE/f'{slug}-evidence-v2.json',
                    (json.dumps(evidence,ensure_ascii=False,indent=2)+'\n').encode())
    print(candidate.name, evidence['pitchedNotes'], 'pitched notes', spec['measures'], 'measures per part')


if __name__ == '__main__':
    for spec in SPECS:
        build(spec)
