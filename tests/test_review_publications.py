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
from review_publications import publish, score_xml, preserved_notation, external_source_receipt
from review_dispositions import published_review_disposition


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
        queue = json.loads((self.public / 'transcription-queue.json').read_text())
        for record in queue['records']:
            self.assertEqual(record['disposition'], published_review_disposition())
            self.assertTrue(record['humanReviewRequired'])
            self.assertFalse(record['safeToPromote'])
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
                if field == 'source' and entry[field].get('publicationPolicy') == 'external-link-only':
                    self.assertEqual(metadata[key], entry[field]['url'])
                    self.assertEqual(metadata['sourceSha256'], entry[field]['sha256'])
                    receipt = (self.public / metadata['sourceVerificationUrl'].lstrip('/')).read_bytes()
                    self.assertEqual(hashlib.sha256(receipt).hexdigest(), metadata['sourceVerificationSha256'])
                    self.assertEqual(json.loads(receipt), external_source_receipt(
                        entry['songId'], entry['bookId'], entry['version'], entry[field]['url'],
                        entry[field]['sha256'], entry['musicXml']['sha256'], entry['evidence']['sha256']))
                    continue
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
                # The parser title-cases labels and disambiguates duplicates.
                self.assertTrue(part['name'].startswith(declaration.findtext('part-name').title()))
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


    def external_fixture(self):
        # No additional source/candidate assets need to be committed for tests.
        entry = copy.deepcopy(next(e for e in self.entries if e['source'].get('publicationPolicy', 'copy') == 'copy'))
        private = tempfile.TemporaryDirectory()
        self.addCleanup(private.cleanup)
        source = Path(private.name) / 'private-source.pdf'
        original = ROOT / entry['source']['path']
        if not original.exists():
            original = ROOT / 'public/review-publications' / (
                entry['slug'] + '-' + entry['version'] + '-source' + Path(entry['source']['path']).suffix)
        source.write_bytes(original.read_bytes())
        entry['source'] = {
            'path': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'publicationPolicy': 'external-link-only', 'url': 'https://example.org/original.pdf',
        }
        return {'publications': [entry]}, source

    def write_manifest(self, data):
        manifest = self.public / 'fixture-manifest.json'
        manifest.write_text(json.dumps(data))
        return manifest

    def public_snapshot(self):
        return {p.relative_to(self.public): p.read_bytes() for p in self.public.rglob('*') if p.is_file()}

    def test_external_source_stays_private_and_prior_receipt_supports_regeneration(self):
        data, source = self.external_fixture()
        entry = data['publications'][0]
        source_bytes = source.read_bytes()
        manifest = self.write_manifest(data)
        publish(ROOT, self.public, manifest)
        song = next(s for s in json.loads((self.public / 'corpus.json').read_text())['songs'] if s['id'] == entry['songId'])
        metadata = song['draftScoreByBook'][entry['bookId']]['reviewPublication']
        self.assertEqual(metadata['sourceUrl'], entry['source']['url'])
        self.assertEqual(metadata['sourcePublicationPolicy'], 'external-link-only')
        self.assertEqual(source.read_bytes(), source_bytes)
        downloads = self.public / 'review-publications'
        self.assertFalse(any(p.name.startswith(entry['slug'] + '-' + entry['version'] + '-source.') for p in downloads.iterdir()))
        self.assertFalse(any(p.read_bytes() == source_bytes for p in downloads.iterdir()))
        receipt = json.loads((self.public / metadata['sourceVerificationUrl'].lstrip('/')).read_text())
        self.assertEqual(receipt['verification'], {
            'method': 'local-retained-source-sha256', 'scope': 'retained-bytes-at-initial-publication',
            'remoteContentVerified': False, 'remoteAvailabilityVerified': False, 'sourceCopyPublished': False,
        })
        # No network or absent-source recheck claim: only reuse initial proof.
        source.unlink()
        before = self.public_snapshot()
        publish(self.public / 'fresh-checkout-without-private-inputs', self.public, manifest)
        self.assertEqual(before, self.public_snapshot())

    def test_external_initial_publication_requires_actual_source_not_just_manifest(self):
        data, source = self.external_fixture()
        source.unlink()
        manifest = self.write_manifest(data)
        before = self.public_snapshot()
        with self.assertRaisesRegex(ValueError, 'retained bytes or a prior verification receipt'):
            publish(ROOT, self.public, manifest)
        self.assertEqual(before, self.public_snapshot())

    def test_external_scheme_policy_and_pinned_source_changes_reject_before_writes(self):
        data, _ = self.external_fixture()
        for patch in [
            {'url': url} for url in ('http://example.org/source.pdf', 'javascript:alert(1)',
                                    'data:application/pdf;base64,YQ==', '/source.pdf', '//example.org/source.pdf',
                                    'https:///source.pdf', 'https://user:secret@example.org/source.pdf',
                                    'https://example.org\\@elsewhere/source.pdf', 'https://example.org/\nsource.pdf',
                                    'https://example.org/\x7fsource.pdf',
                                    'https://example.org:bad/source.pdf')
        ] + [{'publicationPolicy': value} for value in ('external', None, 'copy')
        ] + [{'sha256': '0' * 64}]:
            with self.subTest(patch=patch):
                changed = copy.deepcopy(data)
                changed['publications'][0]['source'].update(patch)
                manifest = self.write_manifest(changed)
                before = self.public_snapshot()
                with self.assertRaises(ValueError):
                    publish(ROOT, self.public, manifest)
                self.assertEqual(before, self.public_snapshot())

    def test_external_receipt_does_not_hide_changed_local_source(self):
        data, source = self.external_fixture()
        manifest = self.write_manifest(data)
        publish(ROOT, self.public, manifest)
        source.write_bytes(b'changed private source')
        before = self.public_snapshot()
        with self.assertRaisesRegex(ValueError, 'Pinned publication input changed'):
            publish(ROOT, self.public, manifest)
        self.assertEqual(before, self.public_snapshot())

    def test_external_regeneration_rejects_changed_receipt_or_source_identity(self):
        data, source = self.external_fixture()
        manifest = self.write_manifest(data)
        publish(ROOT, self.public, manifest)
        source.unlink()
        entry = data['publications'][0]
        receipt_path = self.public / 'review-publications' / (entry['slug'] + '-' + entry['version'] + '-source-verification.json')
        original = receipt_path.read_bytes()
        for field in ('sourceSha256', 'musicXmlSha256', 'evidenceSha256', 'sourceUrl'):
            with self.subTest(field=field):
                changed = json.loads(original)
                changed[field] = 'changed'
                receipt_path.write_text(json.dumps(changed))
                before = self.public_snapshot()
                with self.assertRaisesRegex(ValueError, 'verification receipt changed'):
                    publish(ROOT, self.public, manifest)
                self.assertEqual(before, self.public_snapshot())
        receipt_path.write_bytes(original)
        data['publications'][0]['source']['url'] = 'https://example.org/different.pdf'
        manifest = self.write_manifest(data)
        before = self.public_snapshot()
        with self.assertRaisesRegex(ValueError, 'verification receipt changed'):
            publish(ROOT, self.public, manifest)
        self.assertEqual(before, self.public_snapshot())


if __name__ == '__main__':
    unittest.main()
