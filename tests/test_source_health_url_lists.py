import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('health', ROOT / 'scripts/check_source_health.py')
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)
sys.modules['check_source_health'] = health
validate_spec = importlib.util.spec_from_file_location('validate_source_health', ROOT / 'scripts/validate_source_health.py')
validate_source_health = importlib.util.module_from_spec(validate_spec)
validate_spec.loader.exec_module(validate_source_health)

class UrlInventoryTests(unittest.TestCase):
    def test_nested_urls_roles_and_duplicate_references(self):
        inventory = {}
        health.walk_urls({'sourceUrls': ['https://example.org/page', ['https://example.org/nested']],
                          'recordings': ['https://example.org/audio'],
                          'sourceUrl': 'https://example.org/page',
                          'ignore': [None, 42, '/local.json']}, '', 'fixture', inventory)
        self.assertEqual(set(inventory), {'https://example.org/page', 'https://example.org/nested', 'https://example.org/audio'})
        self.assertEqual(inventory['https://example.org/audio']['roles'], {'recording'})
        self.assertEqual(len(inventory['https://example.org/page']['references']), 2)
        self.assertEqual(inventory['https://example.org/page']['localEvidence'], [])

    def test_every_book_matches_independent_recursive_url_inventory(self):
        corpus = json.loads((ROOT / 'public/corpus.json').read_text())
        def urls(value):
            if isinstance(value, str): return {value} if value.startswith(('http://','https://')) else set()
            children = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
            return set().union(*(urls(child) for child in children))
        for book in corpus['books']:
            with self.subTest(book=book):
                songs = [song for song in corpus['songs'] if book in song['books']]
                inventory = {}
                for song in songs: health.walk_urls(song, '/songs', song['id'], inventory)
                self.assertEqual(set(inventory), urls(songs))
                self.assertTrue(inventory)

    def test_retention_state_is_separate_from_network_state(self):
        self.assertEqual(health.retention_status([]), 'missing-retention')
        self.assertEqual(health.retention_status([{'status': 'exact'}]), 'retained-exact')
        self.assertEqual(health.retention_status([{'status': 'exact'}, {'status': 'drifted'}]), 'local-drift')
        self.assertEqual(health.retention_status([{'status': 'unavailable'}]), 'retention-unavailable')

    def test_budget_exclusion_survives_offline_carry_forward(self):
        carried = health.previous_network({'status': 'not-checked-budget', 'finalUrl': 'https://example.org/a'})
        self.assertEqual(carried['status'], 'not-checked-budget')
        self.assertEqual(carried['remoteBodyStatus'], 'not-checked-budget')

    def test_offline_carry_forward_does_not_invent_network_timestamp(self):
        carried = health.previous_network({
            'status': 'not-checked-offline',
            'checkedAt': '2026-09-05T00:00:00+00:00',
            'networkCheckedAt': '2026-09-04T00:00:00+00:00',
            'finalUrl': 'https://example.org/a',
        })
        self.assertIsNone(carried['networkCheckedAt'])
        self.assertIsNone(validate_source_health.network_timestamp_error({
            'status': 'not-checked-offline',
            'url': 'https://example.org/a',
            'networkCheckedAt': None,
        }))
        self.assertIsNotNone(validate_source_health.network_timestamp_error({
            'status': 'not-checked-offline',
            'url': 'https://example.org/a',
            'networkCheckedAt': '2026-09-04T00:00:00+00:00',
        }))

    def test_cloud_placeholder_is_not_read_as_exact(self):
        path = next((candidate for candidate in (ROOT / 'work/shapenote-musicxml').glob('*.mxl') if getattr(candidate.stat(), 'st_flags', 0) & health.CLOUD_PLACEHOLDER_FLAG), None)
        if path is None:
            self.skipTest('retained cloud-placeholder is not present in this checkout')
        result = health.local_evidence_status({'kind': 'fixture', 'path': str(path.relative_to(ROOT)), 'expectedSha256': '', 'expectedBytes': None, 'immutable': True})
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['availability'], 'cloud-placeholder')

    def test_full_inventory_keeps_song_count_and_book_assets_distinct(self):
        inventory = health.inventory_sources()
        song_urls = {
            url for url, item in inventory.items()
            if any(reference.startswith('corpus:') and ':book:' not in reference for reference in item['references'])
        }
        book_urls = {
            url for url, item in inventory.items()
            if any(reference.startswith('corpus:book:') for reference in item['references'])
        }
        expected_song_urls = set()
        corpus = json.loads((ROOT / 'public/corpus.json').read_text())
        def collect(value):
            if isinstance(value, str):
                return {value} if value.startswith(('http://', 'https://')) else set()
            children = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
            result = set()
            for child in children:
                result.update(collect(child))
            return result
        expected_song_urls = collect(corpus['songs'])
        self.assertEqual(song_urls, expected_song_urls)
        self.assertGreater(len(song_urls), 0)
        self.assertEqual(len(book_urls), 10)
        self.assertTrue(song_urls.isdisjoint(book_urls))

    def test_inventory_declarations_match_current_collector(self):
        declarations = health.inventory_declarations(health.inventory_sources())
        self.assertEqual(declarations['corpusSongUrls'], 7600)
        self.assertEqual(declarations['fullManifestUrls'], 7619)
        self.assertEqual(declarations['bookCount'], 11)
        self.assertEqual(declarations['bookUrlCounts']['ch7'], 683)

    def test_stale_inventory_declarations_are_rejected(self):
        fixture = {
            'https://example.org/song': {
                'books': {'ch7'},
                'references': {'corpus:song-1'},
            },
        }
        stale = {'inventory': {
            'corpusSongUrls': 0,
            'fullManifestUrls': 1,
            'bookCount': 1,
            'books': {'ch7': {'totalUrls': 0}},
        }, 'summary': {'corpusSongUrls': 0}}
        errors = validate_source_health.inventory_declaration_errors(stale, fixture)
        self.assertIn("inventory corpusSongUrls is stale (0 != 1)", errors)
        self.assertTrue(any("inventory book URL attribution is stale" in error for error in errors))
        self.assertIn("summary corpusSongUrls is stale (0 != 1)", errors)

    def test_fresh_inventory_declarations_are_accepted(self):
        fixture = {
            'https://example.org/song': {
                'books': {'ch7'},
                'references': {'corpus:song-1'},
            },
        }
        fresh = {'inventory': {
            'corpusSongUrls': 1,
            'fullManifestUrls': 1,
            'bookCount': 1,
            'books': {'ch7': {'totalUrls': 1}},
        }, 'summary': {'corpusSongUrls': 1}}
        self.assertEqual(validate_source_health.inventory_declaration_errors(fresh, fixture), [])

    def test_host_bounded_checker_records_only_completed_urls(self):
        calls = []
        def fake_request(url, timeout):
            calls.append(url)
            return {'status': 'reachable', 'httpStatus': 200, 'finalUrl': url, 'contentType': 'text/plain', 'method': 'HEAD', 'redirects': []}
        with patch.object(health, 'request_url', side_effect=fake_request):
            results, checked, hosts = health.check_network_urls(
                ['https://one.example/a', 'https://one.example/b', 'https://two.example/c'],
                timeout=1, workers=3, per_host=1, max_seconds=5,
            )
        self.assertEqual(set(results), checked)
        self.assertEqual(set(calls), checked)
        self.assertEqual(hosts, {'one.example': 2, 'two.example': 1})

if __name__ == '__main__': unittest.main()
