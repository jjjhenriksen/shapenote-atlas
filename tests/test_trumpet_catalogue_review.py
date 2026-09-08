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
                      scoreByBook={'trumpet': {'sentinel': 'music unchanged'}})
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


if __name__ == '__main__':
    unittest.main()
