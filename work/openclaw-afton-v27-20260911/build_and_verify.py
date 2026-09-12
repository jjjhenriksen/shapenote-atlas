#!/usr/bin/env python3
"""Afton v27: export eight inspected m4 onsets; preserve v26 otherwise."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OLD = ROOT / 'work/openclaw-afton-v26-20260911/afton-full-song-candidate-v26.musicxml'
PUBLISHED_OLD = ROOT / 'public/review-publications/mnharmony-afton-v26-musicXml.musicxml'
SOURCE = ROOT / 'public/review-publications/mnharmony-afton-v25-source.pdf'
NEW = OUT / 'afton-full-song-candidate-v27.musicxml'
REVIEW = OUT / 'afton-v27-review.json'
SHA_SOURCE = '6ba40c10dbdfa9b93e16f67ae34619254c88004367d802f07a6eddd156047192'
SHA_OLD = '168d501730ef27027bc8e304f34a9c8d450794399aefac3212fe0141d8cc7d2b'
# One-based note indices include every written note element. All m4 events are pitched.
ADDITIONS = [
    ('P1', 4, 1, 'vides', 'end', 0),
    ('P1', 4, 2, 'the', 'single', 2),
    ('P1', 4, 3, 'sun', 'single', 4),
    ('P1', 4, 4, 'and', 'single', 6),
    ('P2', 4, 3, 'joy', 'single', 4),
    ('P2', 4, 4, 'and', 'single', 6),
    ('P3', 4, 1, 'we', 'single', 0),
    ('P3', 4, 2, 'but', 'single', 2),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signature(node):
    return (node.tag, tuple(sorted(node.attrib.items())), (node.text or '').strip(),
            tuple(signature(child) for child in node))


def notes(root, part, measure):
    return root.find(f"part[@id='{part}']/measure[@number='{measure}']").findall('note')


def build_candidate():
    assert sha(SOURCE) == SHA_SOURCE, 'Source bytes changed'
    assert sha(OLD) == SHA_OLD, 'v26 predecessor changed'
    assert sha(PUBLISHED_OLD) == SHA_OLD, 'Published v26 changed'
    old = ET.parse(OLD).getroot()
    new = copy.deepcopy(old)
    new.find('work/work-title').text = 'Afton — full-song source-review candidate (v27)'
    for part, measure, index, text, syllabic, onset in ADDITIONS:
        measure_notes = notes(new, part, measure)
        note = measure_notes[index - 1]
        assert note.find('pitch') is not None and not note.findall('lyric')
        assert sum(int(n.findtext('duration')) for n in measure_notes[:index - 1]) == onset
        lyric = ET.SubElement(note, 'lyric')
        ET.SubElement(lyric, 'syllabic').text = syllabic
        ET.SubElement(lyric, 'text').text = text
    ET.indent(new, space='  ')
    payload = ET.tostring(new, encoding='utf-8', xml_declaration=True) + b'\n'
    if NEW.exists():
        assert NEW.read_bytes() == payload, 'Never overwrite an issued candidate'
    else:
        NEW.write_bytes(payload)
    return old


def main():
    old = build_candidate()
    # The actual exported XML, not a sidecar or in-memory table, is the subject
    # of all preservation, inventory, and parser checks below.
    actual = ET.parse(NEW).getroot()
    restored = copy.deepcopy(actual)
    restored.find('work/work-title').text = old.findtext('work/work-title')
    for part, measure, index, text, syllabic, onset in ADDITIONS:
        note = notes(restored, part, measure)[index - 1]
        lyrics = note.findall('lyric')
        assert len(lyrics) == 1
        lyric = lyrics[0]
        assert not lyric.attrib and [child.tag for child in lyric] == ['syllabic', 'text']
        assert lyric.findtext('text') == text and lyric.findtext('syllabic') == syllabic
        note.remove(lyric)
    assert signature(restored) == signature(old), 'Undocumented XML change'
    assert len(actual.findall('.//note/pitch')) == 251
    assert len(actual.findall('.//note/notehead')) == 251
    assert len(actual.findall('.//note/rest')) == 12
    assert len(actual.findall('.//lyric')) == 158
    assert len(actual.findall('part')) == 4
    assert all(len(part.findall('measure')) == 17 for part in actual.findall('part'))
    assert not actual.findall('.//extend') and not actual.findall('.//lyric[@number]')
    assert not actual.findall('.//key/mode')
    assert not actual.find("part[@id='P4']").findall('.//lyric')
    assert not actual.find("part[@id='P1']/measure[@number='8']").findall('.//lyric')
    assert all(not n.findall('lyric') for n in notes(actual, 'P2', 4)[:2])
    assert all(not n.findall('lyric') for n in notes(actual, 'P3', 4)[2:])
    assert notes(actual, 'P1', 3)[3].findtext('lyric/text') == 'pro'
    assert notes(actual, 'P1', 3)[3].findtext('lyric/syllabic') == 'begin'
    assert notes(actual, 'P3', 12)[4].findtext('lyric/text') == 'dis'
    assert notes(actual, 'P3', 12)[2].find('lyric') is None
    for part in actual.findall('part'):
        for measure in part.findall('measure'):
            assert sum(int(n.findtext('duration')) for n in measure.findall('note')) == 8

    sys.path.insert(0, str(ROOT / 'scripts'))
    from agent_11_lyrics_repeats import parse_musicxml_semantics
    from build_data import parse_score, build_draft_playback_validation
    semantic = parse_musicxml_semantics(NEW, source_id='mnharmony afton',
                                        authority='isolated-review-candidate')
    assert semantic
    (OUT / 'local-only').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUT / 'local-only') as tmp:
        mxl = Path(tmp) / 'score.mxl'
        with zipfile.ZipFile(mxl, 'w') as archive:
            archive.writestr('score.xml', NEW.read_bytes())
        score = parse_score('/review-publications/mnharmony-afton-v27-musicXml.musicxml', mxl)
        assert score and not build_draft_playback_validation('mnharmony-afton-v27', score, {})

    assert sha(OLD) == SHA_OLD and sha(PUBLISHED_OLD) == SHA_OLD and sha(SOURCE) == SHA_SOURCE
    review = json.loads(REVIEW.read_text())
    assert review['safeToPromote'] is False and review['canonical_promotion'] is False
    assert review['source']['sha256'] == SHA_SOURCE
    assert review['supersedes']['sha256'] == SHA_OLD
    assert review['candidate']['sha256'] == sha(NEW)
    assert review['addedLyricAnchors'] == [
        {'part': p, 'measure': m, 'noteIndex': n, 'text': t,
         'syllabic': s, 'onsetDivisions': o} for p, m, n, t, s, o in ADDITIONS
    ]
    print(json.dumps({
        'candidateSha256': sha(NEW), 'sourceSha256': SHA_SOURCE,
        'exportedXmlAndAtlasParsersAccept': True, 'playbackDurationFailures': 0,
        'all68WrittenMeasuresHaveEightDivisions': True,
        'exactV26StructureAfterReversingEightAdditionsAndTitleUpdate': True,
        'sourceAndBothV26CandidateHashesPreserved': True,
        'pitchedNotes': 251, 'explicitNoteheads': 251, 'rests': 12,
        'lyrics': 158, 'newLyricAnchors': 8, 'newExtenders': 0, 'newVerseIds': 0,
        'canonicalDataChangedByThisPackage': False, 'newSourceScansPublished': False,
        'safeToPromote': False,
    }, indent=2))


if __name__ == '__main__':
    main()
