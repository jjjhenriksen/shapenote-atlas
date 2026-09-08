"""Publication must be usable, reproducible, and must not certify a draft."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from review_publications import publish, score_xml, preserved_notation


class ReviewPublicationsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.public = Path(self.temp.name)
        self.entries = json.loads((ROOT / 'scripts/review-publications.json').read_text())['publications']
        rows = [dict(id=e['songId'], books=[e['bookId']], songNo=e['slug'],
                     scoreByBook={e['bookId']: {'sentinel': 'verified score stays untouched'}}) for e in self.entries]
        rows.append({'id': 'unrelated', 'books': ['other'], 'sentinel': [1, 2, 3]})
        self.original = {'songs': rows, 'coverage': {'localScoreSongs': 88, 'byBook': {
            e['bookId']: {'localScoreRecords': 44} for e in self.entries}}}
        records = [dict(songId=e['songId'],bookId=e['bookId'],status='source-reference') for e in self.entries]
        for name, value in [('corpus', self.original), ('source-coverage', {'records':records}),
                            ('transcription-queue', {'records':records})]:
            (self.public / (name+'.json')).write_text(json.dumps(value))

    def test_published_event_stream_downloads_and_idempotency(self):
        publish(ROOT, self.public)
        corpus = json.loads((self.public / 'corpus.json').read_text())
        self.assertEqual(corpus['songs'][-1], self.original['songs'][-1])
        self.assertEqual(corpus['coverage']['localScoreSongs'], 88)
        for entry, song, original in zip(self.entries, corpus['songs'], self.original['songs']):
            self.assertEqual(song['scoreByBook'], original['scoreByBook'])
            draft = song['draftScoreByBook'][entry['bookId']]
            score = json.loads((self.public / draft['scoreRef'].lstrip('/')).read_text())
            metadata = score['reviewPublication']
            self.assertEqual(metadata, draft['reviewPublication'])
            self.assertEqual(score['keySignature'], '')
            self.assertEqual(score['keyEvidence']['status'], 'unknown')
            self.assertTrue(score['transposition']['manualKeyAllowed'])
            xml = score_xml((self.public / metadata['musicXmlUrl'].lstrip('/')).read_bytes())
            has_lyrics = bool(xml.findall('.//lyric/text'))
            self.assertEqual(score['availability']['lyrics']['status'] == 'encoded', has_lyrics)
            self.assertFalse(score['provenance']['sourceKeyVerified'])
            self.assertEqual(score['provenance']['transcriptionMethod'], entry.get('transcriptionMethod', 'manual'))
            for field, key in [('musicXml','musicXmlUrl'),('source','sourceUrl'),('evidence','evidenceUrl')]:
                payload = (self.public / metadata[key].lstrip('/')).read_bytes()
                self.assertEqual(hashlib.sha256(payload).hexdigest(), entry[field]['sha256'])
            if 'originalMusicXml' in entry:
                payload = (self.public / metadata['originalMusicXmlUrl'].lstrip('/')).read_bytes()
                self.assertEqual(hashlib.sha256(payload).hexdigest(), entry['originalMusicXml']['sha256'])
                source = score_xml(payload)
                self.assertEqual([preserved_notation(p) for p in xml.findall('part')],
                                 [preserved_notation(p) for p in source.findall('part')])
            self.assertEqual(len(score['parts']), len(xml.findall('part')))
            for part, declaration in zip(score['parts'], xml.findall('./part-list/score-part')):
                # Duplicate printed voice labels receive disambiguating numeric suffixes.
                self.assertTrue(part['name'].startswith(declaration.findtext('part-name')))
            for part, xml_part in zip(score['parts'], xml.findall('part')):
                pitches = [(e['step'], e.get('alter',0), e['octave']) for e in part['events'] if not e.get('rest')]
                expected = [(n.findtext('pitch/step'), int(n.findtext('pitch/alter','0')), int(n.findtext('pitch/octave'))) for n in xml_part.findall('./measure/note') if n.find('pitch') is not None]
                self.assertEqual(pitches, expected)
                self.assertTrue(all(isinstance(e['beats'], (int,float)) and e['beats'] > 0 for e in part['events']))
        before = {p.relative_to(self.public):p.read_bytes() for p in self.public.rglob('*') if p.is_file()}
        publish(ROOT, self.public)
        self.assertEqual(before, {p.relative_to(self.public):p.read_bytes() for p in self.public.rglob('*') if p.is_file()})

    def test_published_assets_support_regeneration_without_local_sources(self):
        publish(ROOT, self.public)
        before = {p.relative_to(self.public): p.read_bytes() for p in self.public.rglob("*") if p.is_file()}
        publish(self.public / "no-local-sources", self.public, ROOT / "scripts/review-publications.json")
        self.assertEqual(before, {p.relative_to(self.public): p.read_bytes() for p in self.public.rglob("*") if p.is_file()})

    def test_changed_pinned_input_rejected_before_writes(self):
        data = json.loads((ROOT / 'scripts/review-publications.json').read_text())
        data['publications'][1]['musicXml']['sha256'] = '0'*64
        manifest = self.public / 'bad-manifest.json'
        manifest.write_text(json.dumps(data))
        before = {p.name:p.read_bytes() for p in self.public.iterdir()}
        with self.assertRaisesRegex(ValueError, 'Pinned publication input changed'):
            publish(ROOT, self.public, manifest)
        self.assertEqual(before, {p.name:p.read_bytes() for p in self.public.iterdir()})

    def test_rehashed_pitch_change_rejected_before_writes(self):
        data = json.loads((ROOT / 'scripts/review-publications.json').read_text())
        entry = next(e for e in data['publications'] if e['bookId'] == 'sh2025')
        packaged = ROOT / 'public/review-publications' / (entry['slug'] + '-' + entry['version'] + '-musicXml' + Path(entry['musicXml']['path']).suffix)
        xml = score_xml(packaged.read_bytes())
        xml.find('.//pitch/octave').text = '9'
        candidate = self.public / 'altered.musicxml'
        payload = ET.tostring(xml)
        candidate.write_bytes(payload)
        entry['musicXml'] = {'path': str(candidate), 'sha256': hashlib.sha256(payload).hexdigest()}
        manifest = self.public / 'bad-notation-manifest.json'
        manifest.write_text(json.dumps(data))
        before = {p.name:p.read_bytes() for p in self.public.iterdir()}
        with self.assertRaisesRegex(ValueError, 'Source notation changed'):
            publish(ROOT, self.public, manifest)
        self.assertEqual(before, {p.name:p.read_bytes() for p in self.public.iterdir()})


if __name__ == '__main__':
    unittest.main()
