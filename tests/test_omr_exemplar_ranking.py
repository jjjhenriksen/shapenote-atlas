"""Recipe-level witnesses independent of Pillow/NumPy distance extraction."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from omr_exemplar_ranking import nearest_class


class RankingTests(unittest.TestCase):
    def variant(self, id, label='square/filled', scale=1., offset=(0, 0)):
        return {'id': id, 'label': label, 'scale': scale, 'offset': list(offset)}

    def rank(self, rows):
        return nearest_class(iter(rows), minimum_relative_margin=.08)

    def test_class_minimum_not_variant_vote_and_exact_witness(self):
        rows = [(9., self.variant('s')), (100., self.variant('s2')),
                (10., self.variant('r', 'round/open'))]
        self.assertEqual(self.rank(rows), {
            'prediction': 'square/filled', 'selectivePrediction': 'square/filled',
            'relativeMargin': .1, 'neighborId': 's', 'scale': 1.,
            'offset': [0, 0], 'distance': 9.})

    def test_full_tie_break_is_independent_of_input_order(self):
        rows = [(1., self.variant('b')), (1., self.variant('a', scale=1.3)),
                (1., self.variant('a', scale=.6, offset=(1, 0))),
                (1., self.variant('a', scale=.6, offset=(-1, 1))),
                (1., self.variant('a', scale=.6, offset=(-1, -1))),
                (1., self.variant('z', 'round/open'))]
        result = self.rank(rows)
        self.assertEqual(result, self.rank(list(reversed(rows))))
        self.assertEqual((result['neighborId'], result['scale'], result['offset']), ('a', .6, [-1, -1]))
        self.assertEqual(result['relativeMargin'], 0)
        self.assertIsNone(result['selectivePrediction'])

    def test_margin_floor_and_inclusive_threshold_are_preserved(self):
        rows = [(0., self.variant('s')), (.08, self.variant('r', 'round/open'))]
        result = self.rank(rows)
        self.assertEqual(result['relativeMargin'], .08)
        self.assertEqual(result['selectivePrediction'], 'square/filled')
        rows[1] = (.079, rows[1][1])
        self.assertIsNone(self.rank(rows)['selectivePrediction'])

    def test_one_class_has_no_discriminative_margin(self):
        result = self.rank([(0., self.variant('s'))])
        self.assertEqual(result['prediction'], 'square/filled')
        self.assertIsNone(result['relativeMargin'])
        self.assertIsNone(result['selectivePrediction'])

    def test_empty_bank_is_rejected(self):
        with self.assertRaises(ValueError):
            self.rank([])


if __name__ == '__main__':
    unittest.main()
