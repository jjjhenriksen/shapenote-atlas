import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('corrections', ROOT / 'scripts/catalogue_source_corrections.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CatalogueCorrectionsTests(unittest.TestCase):
    def test_retained_overlay_is_idempotent_and_scoped(self):
        corrected = json.loads((ROOT / 'public/corpus.json').read_text())
        evidence = json.loads((ROOT / 'public/catalogue-source-corrections.json').read_text())['records']
        baseline = copy.deepcopy(corrected)
        for song in baseline['songs']:
            if song['id'] in evidence:
                raw = song.pop('catalogueCorrection')['originalCatalogue']
                for key, value in raw.items():
                    if value is None:
                        song.pop(key, None)
                    else:
                        song[key] = value
        expected = copy.deepcopy(baseline)
        for song in expected['songs']:
            module.correct_song(song, evidence)
        self.assertEqual(expected, corrected)
        for song in expected['songs']:
            module.correct_song(song, evidence)
        self.assertEqual(expected, corrected)
        for old, new in zip(baseline['songs'], corrected['songs']):
            self.assertEqual(old['id'], new['id'])
            for key in ('scoreByBook', 'draftScoreByBook', 'referenceScoreByBook'):
                old_score = copy.deepcopy(old.get(key))
                if old['id'] == module.GLIMPSE:
                    module.replace_limit(old_score)
                self.assertEqual(old_score, new.get(key))

    def test_meter_is_consistent_and_source_is_external_only(self):
        corpus = json.loads((ROOT / 'public/corpus.json').read_text())
        song = next(s for s in corpus['songs'] if s['id'] == module.GLIMPSE)
        self.assertEqual(song['metadata']['meter'], 'L.M.D.')
        self.assertEqual(song['metadataByBook']['sacredharptunes']['meter'], 'L.M.D.')
        self.assertEqual(song['sourceCoverage']['reviewPublication']['sourcePublicationPolicy'], 'external-link-only')
        self.assertEqual(song['draftScoreByBook']['sacredharptunes']['reviewPublication']['completeness'], 'partial')
        for name in ('transcription-queue', 'source-coverage'):
            data = json.loads((ROOT / f'public/{name}.json').read_text())
            record = next(r for r in data['records'] if r['songId'] == module.GLIMPSE)
            self.assertEqual(record['title'], song['title'])
            if name == 'transcription-queue':
                self.assertEqual(record['meter'], 'L.M.D.')


if __name__ == '__main__':
    unittest.main()
