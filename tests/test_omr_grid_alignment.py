"""Grid/graph integration contracts, not real-source accuracy fixtures."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_grid_alignment as alignment
import omr_score_audit as audit

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = ImageDraw = None


class AlignmentTests(unittest.TestCase):
    bands = [[10, 10, 190, 60], [10, 70, 190, 120]]

    def grid(self, bars):
        return {'staffLattices': [{'status': 'proposal'}]*2,
                'proposals': [{'x': x} for x in bars], 'unresolved': []}

    def stacks(self, edges):
        return [{'stackIndex': i, 'displayId': str(i+1), 'special': None,
                 'left': a, 'right': b} for i, (a, b) in enumerate(zip(edges, edges[1:]))]

    def test_small_offset_matches_without_sliver_or_automatic_mapping(self):
        result = alignment.align(self.grid([70, 130]), self.stacks([0, 72, 128, 200]), self.bands)
        self.assertEqual(result['boundaryComparison']['matched'], 2)
        self.assertEqual([r['draftStacks'] for r in result['proposedSpans']], [[0], [1], [2]])
        self.assertEqual(result['status'], 'geometry-consistent-proposal')
        self.assertEqual([r['edgeClipped'] for r in result['proposedSpans']], [True, False, True])
        self.assertIsNone(result['measureMap'])
        self.assertFalse(result['safeToPromote'])

    def test_missing_boundary_retains_split_relationship(self):
        result = alignment.align(self.grid([70, 130]), self.stacks([0, 130, 200]), self.bands)
        self.assertEqual(result['findingCounts']['image-boundary-missing-in-draft'], 1)
        self.assertEqual(result['findingCounts']['split-draft-measure-proposal'], 2)
        self.assertEqual([r['draftStacks'] for r in result['proposedSpans']], [[0], [0], [1]])

    def test_native_rounding_joins_do_not_create_false_overlap(self):
        stacks = self.stacks([0, 71, 130, 200])
        stacks[1]['left'] = 70
        result = alignment.align(self.grid([70.25, 130]), stacks, self.bands)
        self.assertEqual([r['draftStacks'] for r in result['proposedSpans']], [[0], [1], [2]])
        self.assertEqual(result['status'], 'geometry-consistent-proposal')
        self.assertEqual(result['draftStacks'][1]['left'], 70)
        self.assertEqual(result['alignedDraftExtents'][1]['left'], 70.25)

    def test_extra_boundary_retains_merge_relationship(self):
        result = alignment.align(self.grid([130]), self.stacks([0, 70, 130, 200]), self.bands)
        self.assertEqual(result['findingCounts']['draft-boundary-without-image-consensus'], 1)
        self.assertEqual(result['proposedSpans'][0]['status'], 'merge-draft-measures-proposal')

    def test_equal_counts_do_not_hide_displaced_grid(self):
        result = alignment.align(self.grid([70, 130]), self.stacks([0, 90, 130, 200]), self.bands)
        self.assertEqual(result['status'], 'review-required')
        self.assertEqual(result['boundaryComparison']['matched'], 1)
        self.assertEqual(result['proposedSpans'][1]['status'], 'complex-overlap-review')

    def test_nearby_candidates_abstain_instead_of_greedy_pairing(self):
        result = alignment.align(self.grid([70]), self.stacks([0, 68, 72, 200]), self.bands)
        self.assertEqual(result['boundaryComparison']['matched'], 0)
        self.assertEqual(result['findingCounts']['ambiguous-boundary-match'], 1)

    def test_duplicate_display_ids_and_special_stack_stay_distinct(self):
        stacks = self.stacks([0, 70, 130, 200])
        stacks[-1].update(displayId='2', special='CAUTIONARY')
        result = alignment.align(self.grid([70, 130]), stacks, self.bands)
        self.assertEqual(result['proposedSpans'][-1]['draftStacks'], [2])
        self.assertEqual(result['proposedSpans'][-1]['status'], 'special-stack-review')

    def test_missing_lattice_and_empty_evidence_do_not_pass(self):
        grid = self.grid([])
        grid['staffLattices'][1] = {'status': 'unresolved'}
        result = alignment.align(grid, self.stacks([0, 200]), self.bands)
        self.assertIn('unresolved-staff-lattice', result['findingCounts'])
        self.assertIn('no-internal-grid-evidence', result['findingCounts'])
        self.assertEqual(result['status'], 'review-required')

    def test_inputs_remain_unchanged(self):
        grid, stacks = self.grid([70]), self.stacks([0, 200])
        before = copy.deepcopy((grid, stacks, self.bands))
        alignment.align(grid, stacks, self.bands)
        self.assertEqual((grid, stacks, self.bands), before)


@unittest.skipIf(Image is None, 'Pillow optional locally; required in image integration CI')
class RunnerTests(unittest.TestCase):
    def fixture(self, root, *, bars=(70, 130), wrong_path=False, width=200, reverse_bands=False):
        image_path = root/'source.png'
        image = Image.new('L', (200, 130), 255)
        draw = ImageDraw.Draw(image)
        for y in (15, 75):
            for dy in range(0, 41, 10):
                draw.line((0, y+dy, 199, y+dy), fill=0)
            for x in bars:
                draw.line((x, y, x, y+40), fill=0)
        image.save(image_path)
        source_hash = alignment.archive.digest(image_path)
        boxes = AlignmentTests.bands
        (root/'bands.json').write_text(json.dumps({'sourceSha256': source_hash,
                                                  'bands': boxes[::-1] if reverse_bands else boxes}))
        parts = ''
        for index, y in enumerate((15, 75), 1):
            lines = ''.join(f'<line><point x="0" y="{y+dy}"/></line>' for dy in range(0, 41, 10))
            parts += f'<part id="{index}"><staff left="0" right="199"><lines>{lines}</lines></staff>'
            parts += '<measure id="1"/><measure id="2"/></part>'
        with zipfile.ZipFile(root/'graph.omr', 'w') as z:
            path = root/'unrelated.png' if wrong_path else image_path
            z.writestr('book.xml', f'<book><sheet number="1"><input><path>{path}</path><number>1</number></input></sheet></book>')
            z.writestr('sheet#1/sheet#1.xml', f'<sheet><picture width="{width}" height="130"/>'
                       '<page><system id="1"><stack id="1" left="0" right="130"/>'
                       f'<stack id="2" left="130" right="199"/>{parts}</system></page></sheet>')
        score = root/'score.musicxml'
        score.write_text('<score-partwise><part id="P1"><measure number="1"/></part></score-partwise>')
        manifest = {'coordinates': alignment.RECIPE['coordinates'], 'sheetNumber': 1,
                    'systemId': '1', 'scoreSha256': alignment.archive.digest(score)}
        for name, filename in [('source', 'source.png'), ('graph', 'graph.omr'), ('bands', 'bands.json')]:
            manifest[name] = {'path': filename, 'sha256': alignment.archive.digest(root/filename)}
        (root/'manifest.json').write_text(json.dumps(manifest))
        return root/'manifest.json', score

    def test_native_graph_integration_and_exact_reuse(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest, score = self.fixture(root)
            inputs = {p.name: p.read_bytes() for p in root.iterdir()}
            result = alignment.run(manifest, score, root/'out')
            self.assertEqual(result['boundaryComparison'], {'image': 2, 'draft': 1, 'matched': 1, 'pairs': [[130.0, 130.0]]})
            self.assertEqual(result['findingCounts']['image-boundary-missing-in-draft'], 1)
            with patch.object(alignment.geometry, 'shared_bar_grid', side_effect=AssertionError('must reuse')):
                self.assertEqual(alignment.run(manifest, score, root/'out'), result)
            self.assertEqual(inputs, {name: (root/name).read_bytes() for name in inputs})

    def test_hash_drift_rejected_before_image_work(self):
        for name in ('source.png', 'bands.json', 'graph.omr', 'score.musicxml'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                root = Path(d); manifest, score = self.fixture(root)
                alignment.run(manifest, score, root/'out')
                with (root/name).open('ab') as f:
                    f.write(b'changed')
                with patch.object(alignment.geometry, 'shared_bar_grid', side_effect=AssertionError('must not infer')):
                    with self.assertRaises(ValueError):
                        alignment.run(manifest, score, root/'out')

    def test_source_registration_and_staff_order_fail_closed(self):
        for options in ({'wrong_path': True}, {'width': 201}, {'reverse_bands': True}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as d:
                root = Path(d); manifest, score = self.fixture(root, **options)
                with self.assertRaises(ValueError):
                    alignment.run(manifest, score, root/'out')

    def test_audit_cli_includes_alignment_and_preserves_default(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest, score = self.fixture(root)
            audit.main([str(score), '--output', str(root/'plain.json')])
            plain = json.loads((root/'plain.json').read_text())
            self.assertNotIn('gridAlignment', plain)
            audit.main([str(score), '--grid-manifest', str(manifest), '--output', str(root/'integrated.json')])
            integrated = json.loads((root/'integrated.json').read_text())
            self.assertEqual(integrated.pop('gridAlignment')['status'], 'review-required')
            self.assertEqual(integrated, plain)


if __name__ == '__main__':
    unittest.main()
