#!/usr/bin/env python3
"""Afton v26: move the directly inspected dis- anchor; preserve all other semantics."""
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
OLD = ROOT / 'work/openclaw-afton-20260907/afton-full-song-candidate-v25.musicxml'
PUBLISHED_OLD = ROOT / 'public/review-publications/mnharmony-afton-v25-musicXml.musicxml'
SOURCE = ROOT / 'public/review-publications/mnharmony-afton-v25-source.pdf'
NEW = OUT / 'afton-full-song-candidate-v26.musicxml'
REVIEW = OUT / 'afton-v26-review.json'
SHA_SOURCE = '6ba40c10dbdfa9b93e16f67ae34619254c88004367d802f07a6eddd156047192'
SHA_OLD = '7db156b17f9bb126415c0816bf9919fa4c43e4c738bbb7e597d2a9ea87b0d444'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def signature(node):
    return (node.tag, tuple(sorted(node.attrib.items())), (node.text or '').strip(),
            tuple(signature(child) for child in node))

def notes(root, part, measure):
    return root.find(f"part[@id='{part}']/measure[@number='{measure}']").findall('note')

assert sha(SOURCE) == SHA_SOURCE, 'Retained source bytes changed'
assert sha(OLD) == SHA_OLD and sha(PUBLISHED_OLD) == SHA_OLD, 'v25 predecessor changed'
old = ET.parse(OLD).getroot()
new = copy.deepcopy(old)
new.find('work/work-title').text = 'Afton — full-song source-review candidate (v26)'
m12 = notes(new, 'P3', 12)
lyric = m12[2].find('lyric')
assert lyric is not None and lyric.findtext('text') == 'dis'
assert lyric.findtext('syllabic') == 'begin' and not lyric.attrib
assert not m12[4].findall('lyric')
m12[2].remove(lyric)
m12[4].append(lyric)
ET.indent(new, space='  ')
payload = ET.tostring(new, encoding='utf-8', xml_declaration=True) + b'\n'
if NEW.exists():
    assert NEW.read_bytes() == payload, 'Never overwrite an issued candidate'
else:
    NEW.write_bytes(payload)

# Parse the exported file and reverse only the declared edits. This compares every
# old pitch/duration/shape/fill/rest/barline and lyric, not a copied note table.
actual = ET.parse(NEW).getroot()
restored = copy.deepcopy(actual)
restored.find('work/work-title').text = old.findtext('work/work-title')
restored_m12 = notes(restored, 'P3', 12)
assert restored_m12[2].find('lyric') is None
moved = restored_m12[4].find('lyric')
assert signature(moved) == signature(notes(old, 'P3', 12)[2].find('lyric'))
restored_m12[4].remove(moved)
restored_m12[2].append(moved)
assert signature(restored) == signature(old), 'Undocumented XML change'
assert len(actual.findall('.//note/pitch')) == 251
assert len(actual.findall('.//note/notehead')) == 251
assert len(actual.findall('.//note/rest')) == 12
assert len(actual.findall('.//lyric')) == 150
assert len(actual.findall('part')) == 4
assert all(len(p.findall('measure')) == 17 for p in actual.findall('part'))
assert not actual.findall('.//extend') and not actual.findall('.//lyric[@number]')
assert not actual.findall('.//key/mode')
assert not actual.find("part[@id='P4']").findall('.//lyric')
assert not actual.find("part[@id='P1']/measure[@number='8']").findall('.//lyric')
assert signature(notes(actual, 'P3', 13)[0]) == signature(notes(old, 'P3', 13)[0])
# Each written 4/4 measure contains exactly eight divisions, including rests.
for part in actual.findall('part'):
    for measure in part.findall('measure'):
        assert sum(int(n.findtext('duration')) for n in measure.findall('note')) == 8

sys.path.insert(0, str(ROOT / 'scripts'))
from agent_11_lyrics_repeats import parse_musicxml_semantics
from build_data import parse_score, build_draft_playback_validation
semantic = parse_musicxml_semantics(NEW, source_id='mnharmony afton', authority='isolated-review-candidate')
assert semantic
(OUT / 'local-only').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=OUT / 'local-only') as tmp:
    mxl = Path(tmp) / 'score.mxl'
    with zipfile.ZipFile(mxl, 'w') as archive:
        archive.writestr('score.xml', NEW.read_bytes())
    score = parse_score('/review-publications/mnharmony-afton-v26-musicXml.musicxml', mxl)
    assert score and not build_draft_playback_validation('mnharmony-afton-v26', score, {})
# Hashes rechecked after all parsing. Current package never mutates predecessors.
assert sha(OLD) == SHA_OLD and sha(PUBLISHED_OLD) == SHA_OLD and sha(SOURCE) == SHA_SOURCE
review = json.loads(REVIEW.read_text())
assert review['safeToPromote'] is False and review['canonical_promotion'] is False
assert review['source']['sha256'] == SHA_SOURCE
assert review['supersedes']['sha256'] == SHA_OLD
assert review['candidate']['sha256'] == sha(NEW)
assert review['correctedLyricAnchors'] == [{
    'part': 'P3', 'measure': 12, 'oldNoteIndex': 3, 'noteIndex': 5,
    'text': 'dis', 'syllabic': 'begin', 'onsetDivisions': 6,
    'followingAnchor': {'part': 'P3', 'measure': 13, 'noteIndex': 1, 'text': 'play,', 'syllabic': 'end'}
}]
print(json.dumps({
    'candidateSha256': sha(NEW), 'sourceSha256': SHA_SOURCE,
    'exportedXmlAndAtlasParsersAccept': True, 'playbackDurationFailures': 0,
    'all68WrittenMeasuresHaveEightDivisions': True,
    'exactV25StructureAfterReversingDeclaredChanges': True,
    'allPriorSourceAndPublishedCandidateHashesPreserved': True,
    'pitchedNotes': 251, 'explicitNoteheads': 251, 'rests': 12, 'lyrics': 150,
    'safeToPromote': False,
}, indent=2))
