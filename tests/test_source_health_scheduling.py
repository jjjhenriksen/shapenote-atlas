"""Exercise network scheduling without contacting source hosts."""
import importlib.util
import threading
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'scheduled_health', Path(__file__).resolve().parents[1] / 'scripts/check_source_health.py')
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)


class SchedulingTests(unittest.TestCase):
    def test_busy_host_does_not_starve_other_hosts_or_exceed_limits(self):
        fast_started = threading.Event()
        lock = threading.Lock()
        active, peaks = Counter(), Counter()
        slow_observations = []
        total_peak = 0

        def request(url, timeout):
            nonlocal total_peak
            host = health.host_name(url)
            with lock:
                active[host] += 1
                peaks[host] = max(peaks[host], active[host])
                total_peak = max(total_peak, sum(active.values()))
            if host == 'a-slow.test':
                slow_observations.append(fast_started.wait(1))
            else:
                fast_started.set()
            with lock:
                active[host] -= 1
            return {'status': 'reachable'}

        urls = [f'https://a-slow.test/{i}' for i in range(4)] + ['https://z-fast.test/1']
        with patch.object(health, 'request_url', side_effect=request):
            results, checked, hosts = health.check_network_urls(urls, 1, 2, 1, 0)
        self.assertTrue(all(slow_observations), 'fast host was starved behind slow host locks')
        self.assertEqual(checked, set(urls))
        self.assertEqual(set(results), set(urls))
        self.assertEqual(hosts, {'a-slow.test': 4, 'z-fast.test': 1})
        self.assertLessEqual(total_peak, 2)
        self.assertEqual(peaks, {'a-slow.test': 1, 'z-fast.test': 1})

    def test_deadline_leaves_undispatched_urls_unchecked(self):
        release = threading.Event()
        finished = threading.Event()
        requested = []

        def request(url, timeout):
            requested.append(url)
            release.wait(2)
            finished.set()
            return {'status': 'reachable'}

        urls = [f'https://slow.test/{i}' for i in range(8)]
        try:
            with patch.object(health, 'request_url', side_effect=request):
                results, checked, hosts = health.check_network_urls(urls, 1, 4, 1, 0.05)
                self.assertEqual((results, checked, hosts), ({}, set(), {}))
                self.assertEqual(requested, urls[:1])
                release.set()
                self.assertTrue(finished.wait(1))
                self.assertEqual(requested, urls[:1])
        finally:
            release.set()


if __name__ == '__main__':
    unittest.main()
