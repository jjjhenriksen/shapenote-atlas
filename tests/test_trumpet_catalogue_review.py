import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from trumpet_catalogue_review import apply


class CatalogueReviewTest(unittest.TestCase):
    def test_embedded_and_indexed_coverage_stay_equal(self):
        manifest = json.loads((ROOT / 'scripts/trumpet-catalogue-review.json').read_text())
        entry = manifest['records'][0]
        manifest['records'] = [entry]
        coverage = {'status': 'source-only', 'draftScoreAvailable': False}
        song = dict(id=entry['songId'], songNo='p116', title=entry['originalTitle'],
                    books=['trumpet'], sourceCoverageByBook={'trumpet': copy.deepcopy(coverage)},
                    sourceCoverage=copy.deepcopy(coverage))
        row = dict(songId=song['id'], songNo=song['songNo'], title=song['title'],
                   bookId='trumpet', **coverage)
        documents = {'corpus': {'songs': [song]},
                     'source-coverage': {'records': [row]},
                     'transcription-queue': {'records': [copy.deepcopy(row)]}}
        result = apply(documents, manifest)
        updated = result['corpus']['songs'][0]
        expected = dict(songId=updated['id'], songNo=updated['songNo'], title=updated['title'],
                        bookId='trumpet', **updated['sourceCoverageByBook']['trumpet'])
        self.assertEqual(updated['sourceCoverage'], updated['sourceCoverageByBook']['trumpet'])
        for name in ('source-coverage', 'transcription-queue'):
            self.assertEqual(result[name]['records'][0], expected)
        self.assertEqual(updated['sourceCoverage']['status'], coverage['status'])
        self.assertEqual(apply(result, manifest), result)

    def test_preserves_identity_music_counts_and_unrelated_records(self):
        manifest = json.loads((ROOT / 'scripts/trumpet-catalogue-review.json').read_text())
        songs = [dict(id=e['songId'], title=e['originalTitle'], books=['trumpet'],
                      scoreByBook={'trumpet': {'sentinel': 'music unchanged'}} if e['contentKind'] == 'notation' else {})
                 for e in manifest['records']]
        songs.append({'id': 'unrelated', 'title': 'Keep me'})
        original = {'corpus': {'songs': songs, 'coverage': {'sentinel': 105}},
                    'source-coverage': {'records': []}, 'transcription-queue': {'records': []}}
        snapshot = copy.deepcopy(original)
        result = apply(original, manifest)
        self.assertEqual(original, snapshot)
        self.assertEqual(result['corpus']['songs'][-1], songs[-1])
        self.assertEqual(result['corpus']['coverage'], original['corpus']['coverage'])
        for before, after in zip(songs[:-1], result['corpus']['songs'][:-1]):
            self.assertEqual(before['id'], after['id'])
            self.assertEqual(before['scoreByBook'], after['scoreByBook'])
            self.assertEqual(before['title'], after['sourceIdentityReview']['originalTitle'])
        self.assertEqual(apply(result, manifest), result)
        original['corpus']['songs'][0]['title'] = 'A concurrent correction'
        with self.assertRaises(ValueError):
            apply(original, manifest)

class ProseMigrationTest(unittest.TestCase):
    def test_migration_updates_counts_and_queue_without_removing_catalogue_rows(self):
        manifest = json.loads((ROOT / 'scripts/trumpet-catalogue-review.json').read_text())
        songs = [dict(id=e['songId'], songNo='p' + str(e['pdfLeaf']),
                      title=e['originalTitle'], books=['trumpet'],
                      rawFirstLine='Historical OCR stays untouched',
                      sourceCoverageByBook={'trumpet': {'status': 'source-reference'}},
                      sourceCoverage={'status': 'source-reference'}) for e in manifest['records']]
        rows = [dict(songId=s['id'], bookId='trumpet', songNo=s['songNo'],
                     title=s['title'], status='source-reference') for s in songs]
        documents = {'corpus': {'songs': songs, 'coverage': {'byBook': {'trumpet': {
            'records': 10, 'localScoreRecords': 0, 'sourceReferenceRecords': 10}}}},
            'source-coverage': {'records': rows, 'summary': {'editionRecords': 10, 'sourceReferences': 10}},
            'transcription-queue': {'records': copy.deepcopy(rows), 'summary': {}}}
        result = apply(documents, manifest)
        self.assertEqual(result['corpus']['coverage']['byBook']['trumpet'], {
            'records': 10, 'localScoreRecords': 0, 'sourceReferenceRecords': 7,
            'proseRecords': 3, 'tuneRecords': 7})
        self.assertEqual(result['source-coverage']['summary'], {
            'editionRecords': 10, 'sourceReferences': 7, 'proseRecords': 3, 'notationRecords': 7})
        self.assertEqual(result['transcription-queue']['summary'], {
            'total': 7, 'byStatus': {'source-reference': 7}, 'byBook': {'trumpet': 7}})
        self.assertEqual(len(result['source-coverage']['records']), 10)
        self.assertEqual(len(result['corpus']['songs']), 10)
        for before, after in zip(songs, result['corpus']['songs']):
            self.assertEqual(before['id'], after['id'])
            self.assertEqual(before['rawFirstLine'], after['rawFirstLine'])
        for s in result['corpus']['songs']:
            if s['sourceIdentityReview']['contentKind'] == 'prose':
                self.assertEqual(s['sourceCoverage']['status'], 'non-notation')
                self.assertEqual(s['sourceCoverage']['nextAction'], 'preserve-prose-reference')
        self.assertEqual(apply(result, manifest), result)

    def test_refuses_to_hide_notation_as_prose(self):
        manifest = json.loads((ROOT / 'scripts/trumpet-catalogue-review.json').read_text())
        entry = next(e for e in manifest['records'] if e['contentKind'] == 'prose')
        manifest['records'] = [entry]
        song = dict(id=entry['songId'], title=entry['originalTitle'], books=['trumpet'],
                    draftScoreByBook={'trumpet': {'scoreRef': '/preserve-me.json'}})
        with self.assertRaisesRegex(ValueError, 'unexpectedly has notation'):
            apply({'corpus': {'songs': [song]}, 'source-coverage': {'records': []},
                   'transcription-queue': {'records': []}}, manifest)

    def test_committed_inventory_joins_and_regeneration_are_consistent(self):
        manifest = json.loads((ROOT / 'scripts/trumpet-catalogue-review.json').read_text())
        documents = {name: json.loads((ROOT / 'public' / (name + '.json')).read_text())
                     for name in ('corpus', 'source-coverage', 'transcription-queue')}
        self.assertEqual(apply(documents, manifest), documents)
        songs = documents['corpus']['songs']
        rows = documents['source-coverage']['records']
        indexed = {(row['songId'], row['bookId']): row for row in rows}
        expected_queue = set()
        for song in songs:
            for book in song['books']:
                coverage = song['sourceCoverageByBook'][book]
                self.assertEqual(indexed[(song['id'], book)], dict(
                    songId=song['id'], songNo=song['songNo'], title=song['title'], bookId=book, **coverage))
                if coverage['status'] not in ('structured-score', 'non-notation'):
                    expected_queue.add((song['id'], book))
        actual = documents['transcription-queue']['records']
        self.assertEqual(len(actual), len(expected_queue))
        self.assertEqual({(row['songId'], row['bookId']) for row in actual}, expected_queue)
        self.assertEqual(len(actual), 3044)
        self.assertEqual(len(rows), 4202)
        self.assertEqual(documents['corpus']['coverage']['byBook']['trumpet']['tuneRecords'], 102)
        review = json.loads((ROOT / manifest['review']).read_text())
        self.assertEqual(manifest['sourceSha256'], review['source_sha256'])
        original = {row['record_id']: row for row in review['reviewed_records']}
        for entry in manifest['records']:
            self.assertEqual(entry['contentKind'], original[entry['songId']]['content_kind'])
            self.assertEqual(entry['pdfLeaf'], original[entry['songId']]['pdf_leaf'])

if __name__ == '__main__':
    unittest.main()
