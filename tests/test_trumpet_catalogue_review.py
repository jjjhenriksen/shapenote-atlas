import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from trumpet_catalogue_review import apply


class CatalogueReviewTest(unittest.TestCase):
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
