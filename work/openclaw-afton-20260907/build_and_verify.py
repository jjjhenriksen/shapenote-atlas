"""Isolated Afton v25: source-observed m8 anchors, never canonical promotion."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OLD = ROOT / 'work/luna-program-20260904/source_only/manual-transcription/afton-full-song-candidate-v24.musicxml'
SOURCE = ROOT / 'work/luna-program-20260904/source_only/retained-sources/mnharmony-afton.pdf'
NEW = OUT / 'afton-full-song-candidate-v25.musicxml'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(OLD) == '92c6ea431ffbb44141d87b9a028ce9ec1a6986592977b7fcda0b5c582aa20ad8'
assert sha(SOURCE) == '6ba40c10dbdfa9b93e16f67ae34619254c88004367d802f07a6eddd156047192'

# Direct review of the retained PDF, page 1 rendered by Poppler at 300 DPI.
# Coordinates refer to crop x=2535,y=300,width=440,height=950.
# Eighth-note n3 has no new text or inferred extender.
anchors = {
    'P2': {1: ('all', 'single'), 2: ('the', 'single'), 4: ('harps', 'single'), 5: ('a', 'begin')},
    'P3': {1: ('sing', 'single'), 2: ('the', 'single'), 4: ('reign', 'single'), 5: ('of', 'single')},
}
old = ET.parse(OLD).getroot()
new = copy.deepcopy(old)
for part, notes in anchors.items():
    measure = new.find(f"part[@id='{part}']/measure[@number='8']")
    for index, (word, syllabic) in notes.items():
        note = measure.findall('note')[index - 1]
        assert note.find('lyric') is None
        lyric = ET.SubElement(note, 'lyric')
        ET.SubElement(lyric, 'syllabic').text = syllabic
        ET.SubElement(lyric, 'text').text = word
ET.indent(new, space='  ')
payload = ET.tostring(new, encoding='utf-8', xml_declaration=True) + b'\n'
if NEW.exists():
    assert NEW.read_bytes() == payload, 'Never overwrite a released candidate'
else:
    NEW.write_bytes(payload)

# Verify exported bytes, not just the builder's in-memory tree.
actual = ET.parse(NEW).getroot()
def signature(node):
    return (node.tag, tuple(sorted(node.attrib.items())), (node.text or '').strip(), tuple(signature(c) for c in node))
stripped = copy.deepcopy(actual)
added = []
for part, notes in anchors.items():
    measure = stripped.find(f"part[@id='{part}']/measure[@number='8']")
    for index in notes:
        note = measure.findall('note')[index - 1]
        lyrics = note.findall('lyric')
        assert len(lyrics) == 1
        added.append({'part': part, 'measure': 8, 'noteIndex': index,
                      'text': lyrics[0].findtext('text'), 'syllabic': lyrics[0].findtext('syllabic')})
        note.remove(lyrics[0])
assert signature(stripped) == signature(old), 'Unexpected change beyond eight approved lyric anchors'
assert len(actual.findall('.//note/pitch')) == 251
assert len(actual.findall('.//note/notehead')) == 251
for part in actual.findall('part'):
    m8 = part.find("measure[@number='8']")
    assert [n.findtext('duration') for n in m8.findall('note')] == ['2','1','1','2','2']
    assert not m8.findall('.//extend')
    if part.get('id') in ('P1','P4'):
        assert not m8.findall('.//lyric')
sys.path.insert(0, str(ROOT / 'scripts'))
from agent_11_lyrics_repeats import parse_musicxml_semantics
parsed = parse_musicxml_semantics(NEW, source_id='mnharmony afton', authority='isolated-review-candidate')
assert parsed

receipt = {
    'date': '2026-09-07', 'status': 'isolated-review-candidate',
    'safeToPromote': False, 'canonical_promotion': False,
    'source': {'path': str(SOURCE.relative_to(ROOT)), 'sha256': sha(SOURCE), 'page': 1},
    'supersedes': {'path': str(OLD.relative_to(ROOT)), 'sha256': sha(OLD)},
    'candidate': {'path': str(NEW.relative_to(ROOT)), 'sha256': sha(NEW)},
    'sourceCrop': {'path': 'afton-m8-source-300dpi.png', 'page': 1, 'dpi': 300, 'rectangle': [2535,300,440,950]},
    'addedLyricAnchors': added,
    'observations': [
        'P2 and P3 notehead centers in the fresh crop are approximately x=79,154,190,228,303. Word starts and spacing support n1/n2/n4/n5 anchors; n3 receives no extra text.',
        'P2 printed a- continues to the already encoded bove; in m9 n1. No verse number is inferred.',
        'P3 source reads sing, not the singing phrase in the old sidecar lyric window.',
        'P3 m8 is five events, quarter/eighth/eighth/quarter/quarter. The v24 sidecar six-duration list is stale; actual v24 XML already matches the source. No rhythm correction was made.',
        'The old sidecar is retained unchanged and is not a v25 serialization authority.'
    ],
    'verification': {
        'exportedXmlParses': True, 'atlasSemanticParserAccepts': True,
        'pitchedNotes': 251, 'explicitNoteheads': 251,
        'exactPriorXmlStructureAfterRemovingEightNewLyrics': True,
        'allPriorLyricsPitchesDurationsNoteheadsTopologyPreserved': True,
        'canonicalDataChanged': False
    },
    'remainingGaps': [
        'P1 m8 printed ripened harvest is unhyphenated. Exact syllable-to-note boundaries remain withheld; no invented splitting or extension.',
        'P2/P3 m8 n3 has no new lyric or melisma marker. Anchor presence does not prove complete melisma semantics.',
        'P3 m12 dis- / play, boundary and other second-system lyric spans remain unreviewed in this pass.',
        'No bass lyric line is printed in the reviewed m8 source crop; do not copy upper-voice text.',
        'Mode/tonal interpretation and full candidate promotion gates remain unresolved.'
    ]
}
(OUT / 'afton-v25-review.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt['verification'], indent=2))
