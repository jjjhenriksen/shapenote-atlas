#!/usr/bin/env python3
"""Export and check a directly inspected four-bar Glimpse opening.

Source coordinates are manual visual observations, not automated optical proof.
The exported XML is checked against independently derived staff-coordinate pitch,
observed rhythm/glyph data, and both Atlas semantic/playback parsers.
"""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
SOURCE = ROOT / 'work/luna-program-20260904/source_only/retained-sources/sacredharptunes-a-glimpse-of-thee-jesse_325.pdf'
SOURCE_SHA = '86c05b5b9441859f740ded45efad776a093bd2926a2c79bc15e75e2b978b8338'
CANDIDATE = OUT / 'sacredharptunes-glimpse-opening-candidate-v1.musicxml'
EVIDENCE = OUT / 'sacredharptunes-glimpse-evidence-v1.json'
RECEIPT = OUT / 'verification.json'
CROP = OUT / 'renders/source-opening-400dpi.png'
LETTERS = 'CDEFGAB'
BAR_X = [220, 532, 878, 1086, 1437]
NOTE_X = [[270, 390, 462], [575, 654, 731, 807], [922, 1030],
          [1132, 1195, 1260, 1303, 1349, 1395]]
DURATIONS = [[4, 2, 2], [2, 2, 2, 2], [6, 2], [2, 2, 1, 1, 1, 1]]
# Read from the retained PDF, in printed top-to-bottom order. The printed
# treble clefs have no octave marks. No conventional octave shift is invented.
VOICES = [
    {'part': 'P1', 'clef': 'G', 'clefLine': 2, 'staffBottomY': 187,
     'pitches': ['D5 B4 G4', 'B4 D5 B4 A4', 'G4 G4', 'B4 D5 D5 C5 B4 A4'],
     'ys': [[108, 134, 161], [134, 108, 134, 147], [161, 161], [134, 108, 108, 121, 134, 147]],
     'shapes': ['normal square triangle', 'square normal square normal',
                'triangle triangle', 'square normal normal triangle square normal']},
    {'part': 'P2', 'clef': 'G', 'clefLine': 2, 'staffBottomY': 485,
     'pitches': ['G4 D4 E4', 'G4 F#4 G4 D4', 'D4 E4', 'G4 G4 G4 F#4 E4 D4'],
     'ys': [[458, 498, 485], [458, 471, 458, 498], [498, 485], [458, 458, 458, 471, 485, 498]],
     'shapes': ['triangle normal square', 'triangle diamond triangle normal',
                'normal square', 'triangle triangle triangle diamond square normal']},
    {'part': 'P3', 'clef': 'G', 'clefLine': 2, 'staffBottomY': 781,
     'pitches': ['G4 D5 C5', 'B4 A4 G4 A4', 'B4 C5', 'B4 B4 G4 A4 B4 C5'],
     'ys': [[755, 702, 715], [728, 742, 755, 742], [728, 715], [728, 728, 755, 742, 728, 715]],
     'shapes': ['triangle normal triangle', 'square normal triangle normal',
                'square triangle', 'square square triangle normal square triangle']},
    {'part': 'P4', 'clef': 'F', 'clefLine': 4, 'staffBottomY': 1078,
     'pitches': ['G3 G3 G3', 'E3 D3 G3 A3', 'D3 G3', 'E3 D3 G3 F#3 E3 F#3'],
     'ys': [[985, 985, 985], [1012, 1025, 985, 972], [1025, 985], [1012, 1025, 985, 998, 1012, 998]],
     'shapes': ['triangle triangle triangle', 'square normal triangle normal',
                'normal triangle', 'square normal triangle diamond square diamond']},
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(parent, tag, value, **attrs):
    result = ET.SubElement(parent, tag, attrs)
    result.text = str(value)
    return result


def write_once(path, payload):
    if path.exists():
        assert path.read_bytes() == payload, f'Issued artifact differs: {path.name}'
    else:
        path.write_bytes(payload)


def notation(duration):
    return {1: ('eighth', False), 2: ('quarter', False),
            4: ('half', False), 6: ('half', True)}[duration]


def split_pitch(pitch):
    return pitch[0], int(pitch[-1]), 1 if '#' in pitch else 0


def coordinate_pitch(y, voice):
    staff_steps = (voice['staffBottomY'] - y) / (26.5 / 2)
    assert abs(staff_steps - round(staff_steps)) < .09, 'Ambiguous coordinate'
    baseline = ('E', 4) if voice['clef'] == 'G' else ('G', 2)
    index = baseline[1] * 7 + LETTERS.index(baseline[0]) + round(staff_steps)
    step, octave = LETTERS[index % 7], index // 7
    return step, octave, 1 if step == 'F' else 0


def observations():
    result = []
    for voice in VOICES:
        for m in range(4):
            onset = 0
            notes = []
            for n, (pitch, shape, x, y, duration) in enumerate(zip(
                    voice['pitches'][m].split(), voice['shapes'][m].split(),
                    NOTE_X[m], voice['ys'][m], DURATIONS[m]), 1):
                typ, dotted = notation(duration)
                notes.append({'noteIndex': n, 'observedPitch': pitch,
                              'noteCenter': [x, y], 'onsetQuarter': onset / 2,
                              'durationQuarter': duration / 2,
                              'observedType': typ, 'observedDot': dotted,
                              'observedNotehead': shape,
                              'observedFilled': duration < 4})
                onset += duration
            result.append({'part': voice['part'], 'measure': m + 1,
                           'xRange': BAR_X[m:m+2],
                           'staffBottomY': voice['staffBottomY'],
                           'staffLineSpacing': 26.5, 'notes': notes})
    return result


def build():
    assert sha(SOURCE) == SOURCE_SHA, 'Retained source changed'
    root = ET.Element('score-partwise', version='4.0')
    work = ET.SubElement(root, 'work')
    text(work, 'work-title', 'A Glimpse of Thee — four-measure opening review draft v1')
    identification = ET.SubElement(root, 'identification')
    text(identification, 'creator', 'Jesse Pearlman Karlsberg, 2009', type='composer')
    text(identification, 'source',
         'https://media.sacredharptunes.com/jesse_325.pdf; '
         'retained one-page witness titled A GLIMPSE OF THEE. L.M.D.; '
         'first four printed measures only.')
    miscellaneous = ET.SubElement(identification, 'miscellaneous')
    for key, value in [
        ('review-required', 'true'), ('safe-to-promote', 'false'),
        ('coverage', 'First four printed measures in all four voices; remainder omitted, not silence.'),
        ('source-sha256', SOURCE_SHA),
        ('limitations', 'No lyrics or later repeat/ending topology encoded. '
         'One-sharp signature retained without a major/minor claim. '
         'Catalogue L.M. differs from source L.M.D.; exact-edition status unverified.'),
    ]:
        text(miscellaneous, 'miscellaneous-field', value, name=key)
    part_list = ET.SubElement(root, 'part-list')
    for v in VOICES:
        score_part = ET.SubElement(part_list, 'score-part', id=v['part'])
        text(score_part, 'part-name', 'Printed voice ' + v['part'][1:])
    for v in VOICES:
        part = ET.SubElement(root, 'part', id=v['part'])
        for m in range(4):
            measure = ET.SubElement(part, 'measure', number=str(m + 1))
            if m == 0:
                attrs = ET.SubElement(measure, 'attributes')
                text(attrs, 'divisions', 2)
                text(ET.SubElement(attrs, 'key'), 'fifths', 1)
                time = ET.SubElement(attrs, 'time')
                text(time, 'beats', 4)
                text(time, 'beat-type', 4)
                clef = ET.SubElement(attrs, 'clef')
                text(clef, 'sign', v['clef'])
                text(clef, 'line', v['clefLine'])
            for n, (written_pitch, shape, duration) in enumerate(zip(
                    v['pitches'][m].split(), v['shapes'][m].split(), DURATIONS[m])):
                note = ET.SubElement(measure, 'note')
                pitch = ET.SubElement(note, 'pitch')
                step, octave, alter = split_pitch(written_pitch)
                text(pitch, 'step', step)
                if alter:
                    text(pitch, 'alter', alter)
                text(pitch, 'octave', octave)
                text(note, 'duration', duration)
                typ, dotted = notation(duration)
                text(note, 'type', typ)
                if dotted:
                    ET.SubElement(note, 'dot')
                text(note, 'notehead', shape, filled='yes' if duration < 4 else 'no')
                # Only the directly visible m4 paired-eighth beams are copied.
                if m == 3 and n >= 2:
                    text(note, 'beam', 'begin' if n % 2 == 0 else 'end', number='1')
    ET.indent(root, space='  ')
    write_once(CANDIDATE, ET.tostring(root, encoding='utf-8', xml_declaration=True) + b'\n')


def verify():
    # Parse exported bytes, not the builder's in-memory tree.
    actual = ET.parse(CANDIDATE).getroot()
    assert actual.tag == 'score-partwise'
    assert len(actual.findall('part')) == 4
    assert len(actual.findall('.//note/pitch')) == 60
    assert len(actual.findall('.//note/notehead')) == 60
    assert len(actual.findall('.//dot')) == 4
    assert len(actual.findall('.//beam')) == 16
    for tag in ['lyric', 'mode', 'rest', 'tie', 'tied', 'slur', 'repeat',
                'ending', 'backup', 'forward', 'chord', 'barline', 'transpose']:
        assert not actual.findall('.//' + tag), f'Unreviewed {tag}'
    all_observations = observations()
    for voice, part in zip(VOICES, actual.findall('part')):
        assert part.attrib['id'] == voice['part']
        measures = part.findall('measure')
        assert len(measures) == 4
        attrs = measures[0].find('attributes')
        assert attrs.findtext('divisions') == '2'
        assert attrs.findtext('key/fifths') == '1'
        assert (attrs.findtext('time/beats'), attrs.findtext('time/beat-type')) == ('4', '4')
        assert attrs.findtext('clef/sign') == voice['clef']
        assert int(attrs.findtext('clef/line')) == voice['clefLine']
        for m, measure in enumerate(measures):
            assert measure.attrib['number'] == str(m+1)
            notes = measure.findall('note')
            obs = next(o for o in all_observations
                       if o['part'] == voice['part'] and o['measure'] == m+1)
            assert len(notes) == len(obs['notes'])
            onset = Fraction(0)
            for note, recorded in zip(notes, obs['notes']):
                p = note.find('pitch')
                pitch = p.findtext('step'), int(p.findtext('octave')), int(p.findtext('alter', '0'))
                assert pitch == coordinate_pitch(recorded['noteCenter'][1], voice)
                assert pitch == split_pitch(recorded['observedPitch'])
                assert obs['xRange'][0] < recorded['noteCenter'][0] < obs['xRange'][1]
                duration = Fraction(int(note.findtext('duration')), 2)
                typed = {'half': Fraction(2), 'quarter': Fraction(1),
                         'eighth': Fraction(1, 2)}[note.findtext('type')]
                if note.find('dot') is not None:
                    typed *= Fraction(3, 2)
                assert duration == typed == Fraction(str(recorded['durationQuarter']))
                assert onset == Fraction(str(recorded['onsetQuarter']))
                assert note.findtext('notehead') == recorded['observedNotehead']
                assert note.find('notehead').attrib == {'filled': 'yes' if recorded['observedFilled'] else 'no'}
                assert note.findtext('type') == recorded['observedType']
                assert (note.find('dot') is not None) == recorded['observedDot']
                onset += duration
            assert onset == 4, 'Written bar duration is not four quarters'

    sys.path.insert(0, str(ROOT / 'scripts'))
    from agent_11_lyrics_repeats import parse_musicxml_semantics
    from build_data import parse_score, build_draft_playback_validation
    semantic = parse_musicxml_semantics(CANDIDATE, source_id='sacredharptunes a-glimpse-of-thee',
                                       authority='isolated-review-candidate')
    assert semantic
    (OUT / 'renders').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUT / 'renders') as tmp:
        mxl = Path(tmp) / 'score.mxl'
        with zipfile.ZipFile(mxl, 'w') as archive:
            archive.writestr('score.xml', CANDIDATE.read_bytes())
        score = parse_score('draft://sacredharptunes/a-glimpse-of-thee/v1', mxl)
        assert score and len(score['parts']) == 4
        assert sum(len(part['events']) for part in score['parts']) == 60
        assert score['keySignature'] == '', 'Unknown mode became a tonal key'
        for part, parsed_part in zip(actual.findall('part'), score['parts']):
            notes = part.findall('measure/note')
            assert len(notes) == len(parsed_part['events']) == 15
            onset = Fraction(0)
            for note, event in zip(notes, parsed_part['events']):
                duration = Fraction(int(note.findtext('duration')), 2)
                p = note.find('pitch')
                expected_pitch = p.findtext('step'), int(p.findtext('octave')), int(p.findtext('alter', '0'))
                assert (event['step'], event['octave'], event.get('alter', 0)) == expected_pitch
                assert (event['onset'], event['beats']) == (float(onset), float(duration))
                assert event['rest'] is False
                assert event['notehead'] == note.findtext('notehead')
                assert not event.get('lyrics')
                onset += duration
            assert onset == 16
        assert not build_draft_playback_validation('sacredharptunes-glimpse-v1', score, {})
    assert sha(SOURCE) == SOURCE_SHA
    return {
        'candidateSha256': sha(CANDIDATE), 'sourceSha256': SOURCE_SHA,
        'exportedXmlAndAtlasParsersAccept': True, 'playbackDurationFailures': 0,
        'parts': 4, 'completeMeasuresPerPart': 4, 'completeWrittenMeasures': 16,
        'pitchedNotes': 60, 'explicitNoteheads': 60, 'rests': 0, 'lyrics': 0,
        'allWrittenBarsFourQuarters': True, 'independentStaffCoordinatePitchParity': True,
        'sourceBytesPreserved': True, 'canonicalDataChangedByThisPackage': False,
        'newSourceScansPublished': False, 'safeToPromote': False,
    }


def main():
    build()
    receipt = verify()
    limits = [
        'Only the first four printed measures in all four voices are encoded; the remaining tune is omitted, not silence.',
        'Lyrics, including the page\'s printed verse numbers and multi-line underlay, remain unencoded pending voice-specific review.',
        'The repeat and first/second endings occur later on the page and are outside this excerpt; no terminal final barline is invented.',
        'One-sharp signature is preserved, including written F-sharps; mode remains unknown and printed treble clefs receive no unprinted octave adjustment.',
        'Source title is A GLIMPSE OF THEE. L.M.D.; the catalogue record says A Glimpse of Thee L.M. The stable catalogue identity is referenced, not silently relabeled.',
        'Direct visual observations support a correctable opening draft, not a complete tune or verified-edition claim.',
        'The copyrighted source PDF and all new renders remain local-only. Use the original external source URL for public comparison; do not publish a new source copy.',
    ]
    evidence = {
        'version': 1, 'title': 'A Glimpse of Thee', 'bookId': 'sacredharptunes',
        'recordId': 'sacredharptunes a-glimpse-of-thee — A Glimpse of Thee L.M.',
        'candidate': CANDIDATE.name, 'candidateSha256': sha(CANDIDATE),
        'sourcePath': str(SOURCE.relative_to(ROOT)), 'sourceSha256': SOURCE_SHA,
        'sourceUrl': 'https://media.sacredharptunes.com/jesse_325.pdf',
        'sourceLandingPage': 'https://www.sacredharptunes.com/author/jesse/a-glimpse-of-thee/',
        'sourcePdfPage': 1, 'sourcePrintedPage': None, 'directVisualReview': True,
        'reviewDate': '2026-09-11', 'status': 'isolated-review-candidate',
        'coverage': 'First four complete opening measures across all four printed voices',
        'completeMeasuresPerPart': 4, 'pitchedNotes': 60, 'explicitNoteheads': 60,
        'reviewRequired': True, 'safeToPromote': False, 'canonical_promotion': False,
        'mode': 'unknown', 'keySignatureFifths': 1,
        'sourceIdentity': {'printedTitle': 'A GLIMPSE OF THEE. L.M.D.',
                           'printedTextAttribution': 'Isaac Watts, 1707',
                           'printedMusicAttribution': 'Jesse Pearlman Karlsberg, 2009',
                           'catalogueTitle': 'A Glimpse of Thee L.M.',
                           'discrepancy': 'Printed source meter suffix L.M.D. differs from catalogue L.M.; no catalogue change by this package.'},
        'coordinateSystem': {
            'origin': 'top-left of exact 400-DPI Poppler crop',
            'dimensions': [1510, 1110], 'cropRectangle': [250, 540, 1510, 1110],
            'sourcePagePoints': [792, 612], 'renderDpi': 400,
            'image': 'renders/source-opening-400dpi.png',
            'renderSha256': sha(CROP), 'barBoundariesX': BAR_X,
            'noteCenterAccuracy': 'Approximate manually observed centers; up to one pixel vertical rounding. Triangle glyph y is its printed staff position, not its asymmetric visual centroid.',
            'reproductionCommand': 'pdftoppm -f 1 -l 1 -r 400 -x 250 -y 540 -W 1510 -H 1110 -png -singlefile ' + str(SOURCE.relative_to(ROOT)) + ' ' + str(CROP.with_suffix('').relative_to(ROOT)),
        },
        'voiceObservations': [{k: v[k] for k in ['part', 'clef', 'clefLine', 'staffBottomY']}
                              | {'staffLineSpacing': 26.5} for v in VOICES],
        'measureObservations': observations(),
        'glyphObservations': 'All 60 noteheads are directly legible: open/filled normal ovals, triangles, squares, or diamonds. Stem orientation is not treated as a different shape. All four m4 voices show two paired eighth-note beams.',
        'verification': receipt, 'limitations': limits,
        'publicationPolicy': {'newSourceScanPublication': False,
                              'publicSourceComparison': 'Original external source URL only; retained PDF/renders remain ignored local evidence.'},
    }
    write_once(EVIDENCE, (json.dumps(evidence, indent=2) + '\n').encode())
    assert json.loads(EVIDENCE.read_text())['candidateSha256'] == sha(CANDIDATE)
    write_once(RECEIPT, (json.dumps(receipt, indent=2) + '\n').encode())
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
