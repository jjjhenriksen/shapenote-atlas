import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('resume_health', ROOT / 'scripts/check_source_health.py')
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)

OLD_CHECK = '2026-09-04T00:00:00+00:00'
NEW_CHECK = '2026-09-11T00:00:00+00:00'


class ResumeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.output = root / 'public/source-health.json'
        self.output.parent.mkdir()
        for patcher in (patch.object(health, 'ROOT', root),
                        patch.object(health, 'OUTPUT', self.output),
                        patch.object(health, 'utc_now', return_value=NEW_CHECK)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def prior_record(self, url, status, **extra):
        return {
            'url': url,
            'status': status,
            'checkedAt': OLD_CHECK,
            'networkCheckedAt': None if status.startswith('not-checked-') else OLD_CHECK,
            'finalUrl': url,
            **extra,
        }

    def run_report(self, urls, *arguments):
        inventory = {url: health.empty_item(url) for url in urls}
        requested = []

        def check(urls, **kwargs):
            requested.extend(urls)
            results = {
                url: {'status': 'reachable', 'httpStatus': 200, 'finalUrl': url,
                      'contentType': 'text/plain', 'method': 'HEAD', 'redirects': []}
                for url in urls
            }
            return results, set(urls), {'example.org': len(urls)}

        with patch.object(health, 'inventory_sources', return_value=inventory), \
                patch.object(health, 'check_network_urls', side_effect=check), \
                patch.object(sys, 'argv', ['check_source_health.py', *arguments]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(health.main(), 0)
        report = json.loads(self.output.read_text())
        return requested, {record['url']: record for record in report['records']}

    def test_resume_checks_new_and_retryable_urls_but_reuses_actual_results(self):
        statuses = {
            'budget': ('not-checked-budget', {}),
            'offline': ('not-checked-offline', {}),
            'error': ('network-error', {}),
            'cached-error': ('cached', {'networkStatus': 'network-error'}),
            'legacy-cached-error': ('cached', {'cachedStatus': 'network-error'}),
            'reachable': ('reachable', {}),
            'redirected': ('redirected', {}),
            'unreachable': ('unreachable', {}),
            'cached-good': ('cached', {'networkStatus': 'reachable'}),
        }
        prior = [self.prior_record(f'https://example.org/{name}', status, **extra)
                 for name, (status, extra) in statuses.items()]
        self.output.write_text(json.dumps({'records': prior}))
        new_url = 'https://example.org/new'
        requested, records = self.run_report([new_url, *(item['url'] for item in prior)], '--resume')
        expected = {f'https://example.org/{name}' for name in
                    ('new', 'budget', 'offline', 'error', 'cached-error', 'legacy-cached-error')}
        self.assertEqual(set(requested), expected)
        for url, record in records.items():
            with self.subTest(url=url):
                self.assertEqual(record['checkedAt'], NEW_CHECK)
                self.assertEqual(record['networkCheckedAt'], NEW_CHECK if url in expected else OLD_CHECK)
                self.assertEqual(record['evidenceAge'], 'current' if url in expected else 'cached')

    def test_error_remains_retryable_after_offline_and_budget_carry_forward(self):
        new_url, error_url, good_url = [f'https://example.org/{name}' for name in ('a-new', 'b-error', 'c-good')]
        self.output.write_text(json.dumps({'records': [
            self.prior_record(error_url, 'network-error'),
            self.prior_record(good_url, 'reachable'),
        ]}))
        urls = [new_url, error_url, good_url]
        requested, records = self.run_report(urls, '--offline')
        self.assertEqual(requested, [])
        self.assertEqual(records[new_url]['status'], 'not-checked-offline')
        self.assertIsNone(records[new_url]['networkCheckedAt'])
        self.assertEqual(records[error_url]['status'], 'cached')
        self.assertEqual(records[error_url]['networkStatus'], 'network-error')
        self.assertEqual(records[error_url]['networkCheckedAt'], OLD_CHECK)

        requested, records = self.run_report(urls, '--resume', '--max-urls', '1')
        self.assertEqual(requested, [new_url])
        self.assertEqual(records[error_url]['status'], 'cached')
        self.assertEqual(records[error_url]['networkStatus'], 'network-error')
        self.assertEqual(records[error_url]['networkCheckedAt'], OLD_CHECK)

        requested, records = self.run_report(urls, '--resume')
        self.assertEqual(requested, [error_url])
        self.assertEqual(records[error_url]['status'], 'reachable')
        self.assertEqual(records[error_url]['networkCheckedAt'], NEW_CHECK)
        self.assertEqual(records[good_url]['networkCheckedAt'], OLD_CHECK)


if __name__ == '__main__':
    unittest.main()
