"""Synthetic source-only inventory accounting; no real source observations."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import audit_social_harp_inventory as audit


def encoded(value):
    return (json.dumps(value, sort_keys=True) + '\n').encode()


class SocialHarpInventoryAudit(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.packet = self.root / 'packet'
        self.packet.mkdir()
        source = b'synthetic PDF placeholder; hash check only, not a rendered source'
        (self.packet / 'source.pdf').write_bytes(source)
        image = b'synthetic image placeholder'
        (self.packet / 'leaf-001.png').write_bytes(image)
        self.protocol = {'schemaVersion': 1, 'kind': 'social-harp-source-only-inventory-protocol',
            'sourceSha256': audit.digest(source), 'sourceBytes': len(source), 'sourcePageCount': 1,
            'coordinates': {'pdfLeafBase': 1, 'pdfIndexBase': 0}, 'targetPdfLeaves': [1],
            'pages': [{'pdfLeaf': 1, 'pdfIndex': 0, 'imageFile': 'leaf-001.png', 'imageSha256': audit.digest(image)}]}
        self.a_path = self.root / 'reader-a.json'
        self.b_path = self.root / 'reader-b.json'
        self.refresh_protocol()
        self.a = {'schemaVersion': 1, 'kind': 'social-harp-source-only-inventory-reading',
            'readerId': 'reader-a', 'protocolSha256': self.protocol_pin,
            'sourceSha256': self.protocol['sourceSha256'], 'notes': ['Synthetic scope.'],
            'pages': [{'pdfLeaf': 1, 'pdfIndex': 0, 'printedPageLabel': '1',
                'pageDisposition': 'continuation-only',
                'headings': [{'text': 'PRIVATE_SYNTHETIC_HEADING Continued.', 'role': 'continuation',
                              'bbox': [0.1, 0.1, 0.8, 0.2]}],
                'continuationEvidence': 'PRIVATE_SYNTHETIC_NOTES', 'uncertainties': []}]}
        self.b = {**deepcopy(self.a), 'readerId': 'reader-b'}
        self.refresh_readers()

    def refresh_protocol(self):
        raw = encoded(self.protocol)
        (self.packet / 'protocol.json').write_bytes(raw)
        self.protocol_pin = audit.digest(raw)

    def refresh_readers(self):
        self.a_path.write_bytes(encoded(self.a))
        self.b_path.write_bytes(encoded(self.b))
        self.a_pin = audit.digest(self.a_path.read_bytes())
        self.b_pin = audit.digest(self.b_path.read_bytes())

    def compare(self):
        return audit.compare(self.packet, self.protocol_pin, self.a_path, self.a_pin, self.b_path, self.b_pin)

    def test_aggregate_agreement_never_certifies_inventory_or_exposes_raw_observations(self):
        result = self.compare()
        self.assertEqual(result['status'], 'compared')
        self.assertEqual(result['agreedTargetDispositionCounts'], {'continuation-only': 1})
        self.assertEqual(result['unresolvedLeaves'], [])
        self.assertNotIn('PRIVATE_SYNTHETIC', json.dumps(result))
        for key in ('inventoryReconciled', 'wholeBookReviewed', 'sourceCertified',
                    'safeToPromote', 'readerIndependenceVerified'):
            self.assertIs(result[key], False)
        self.assertTrue(result['humanReviewRequired'])

    def test_heading_disposition_and_uncertainty_disagreements_remain_unresolved(self):
        self.b['pages'][0]['pageDisposition'] = 'uncertain'
        self.b['pages'][0]['headings'][0]['text'] = 'Different synthetic heading'
        self.b['pages'][0]['uncertainties'] = ['Unknown layout.']
        self.refresh_readers()
        result = self.compare()
        self.assertEqual(result['unresolvedLeaves'], [1])
        self.assertEqual(result['agreedTargetDispositionCounts'], {})
        self.assertEqual(result['pages'][0]['disagreements'], ['pageDisposition', 'headings'])
        self.assertEqual(result['pages'][0]['uncertaintyCounts'], [0, 1])

    def test_predeclared_normalization_is_limited_to_case_and_whitespace(self):
        self.b['pages'][0]['headings'][0]['text'] = ' private_synthetic_heading  continued. '
        self.refresh_readers()
        self.assertEqual(self.compare()['unresolvedLeaves'], [])
        self.b['pages'][0]['headings'][0]['text'] = 'private_synthetic_heading continued'
        self.refresh_readers()
        self.assertEqual(self.compare()['unresolvedLeaves'], [1])

    def test_source_image_and_reader_mutations_fail_pins(self):
        for path in (self.packet / 'source.pdf', self.packet / 'leaf-001.png', self.a_path, self.b_path):
            original = path.read_bytes()
            path.write_bytes(original + b'changed')
            with self.subTest(path=path.name), self.assertRaises(ValueError):
                self.compare()
            path.write_bytes(original)

    def test_complete_unique_coverage_and_correct_coordinate_conversion_are_required(self):
        original = deepcopy(self.a)
        for pages in ([], [original['pages'][0], original['pages'][0]],
                      [{**original['pages'][0], 'pdfIndex': 1}],
                      [{**original['pages'][0], 'pdfLeaf': 2}],
                      [{**original['pages'][0], 'headings': [{**original['pages'][0]['headings'][0], 'bbox': [1,0,0,1]}]}],
                      [{**original['pages'][0], 'headings': [{**original['pages'][0]['headings'][0], 'bbox': [10**500,0,1,1]}]}]):
            self.a = {**deepcopy(original), 'pages': pages}
            self.refresh_readers()
            with self.subTest(pages=pages), self.assertRaises(ValueError):
                self.compare()

    def test_malformed_protocol_and_readings_fail_closed(self):
        for field, value in (('coordinates', []), ('sourceBytes', True),
                             ('targetPdfLeaves', [1,1]), ('pages', [])):
            old = deepcopy(self.protocol)
            self.protocol[field] = value
            self.refresh_protocol()
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.compare()
            self.protocol = old
            self.refresh_protocol()
        del self.a['readerId']
        self.refresh_readers()
        with self.assertRaisesRegex(ValueError, 'reader identity'):
            self.compare()

    def test_readers_must_have_distinct_identities_and_declared_opening_evidence(self):
        self.b['readerId'] = self.a['readerId']
        self.refresh_readers()
        with self.assertRaisesRegex(ValueError, 'identities'):
            self.compare()
        self.b['readerId'] = 'reader-b'
        self.a['pages'][0]['pageDisposition'] = 'opening-present'
        self.refresh_readers()
        with self.assertRaisesRegex(ValueError, 'Opening disposition'):
            self.compare()

    def test_cli_is_read_only_and_reports_blocked_malformed_inputs(self):
        command = [sys.executable, str(ROOT / 'scripts/audit_social_harp_inventory.py'), str(self.packet),
            '--expected-protocol-sha256', self.protocol_pin, '--reader-a', str(self.a_path),
            '--expected-reader-a-sha256', self.a_pin, '--reader-b', str(self.b_path),
            '--expected-reader-b-sha256', self.b_pin]
        def snapshot():
            return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        before = snapshot()
        result = subprocess.run(command, capture_output=True, text=True, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'compared')
        self.assertEqual(snapshot(), before)
        self.a_path.write_bytes(b'{')
        result = subprocess.run(command, capture_output=True, text=True, cwd=self.root)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['status'], 'blocked')


if __name__ == '__main__':
    unittest.main()
