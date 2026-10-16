import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from omr_point_eval import ratio, threshold_check, summarize_points, negative_diagnostic, paired_proposals
from sh1991_eval_diagnostics import selection_for


class PointEvaluationTests(unittest.TestCase):
    def point(self, key, prediction=None, fill='open'):
        return {'id': key, 'group': 'page', 'shape': 'triangle', 'fill': fill, 'prediction': prediction}

    def prediction(self, fill='filled'):
        return {'nativeLabel': 'NOTEHEAD_FA_LEFT_FILLED', 'fill': fill, 'stages': {'timedSlot': True, 'exportWitness': None}}

    def test_empty_ratio_is_unavailable_not_zero_or_pass(self):
        self.assertIsNone(ratio(0, 0)['value'])
        self.assertEqual(threshold_check(0, 0, .8)['status'], 'not_evaluable')
        with self.assertRaises(ValueError):
            ratio(2, 1)

    def test_gate_does_not_round_borderline_retention_into_pass(self):
        self.assertEqual(threshold_check(145, 148, '.98')['status'], 'fail')
        self.assertEqual(threshold_check(146, 148, '.98')['status'], 'pass')
        self.assertEqual(threshold_check(48, 60, '.8')['status'], 'pass')

    def test_conditional_fill_does_not_hide_missing_heads(self):
        row = summarize_points([self.point('a', self.prediction('open')), self.point('b')])[0]
        self.assertEqual(row['fillCorrectAmongJudgedRetained']['value'], 1)
        self.assertEqual(row['retainedWithCorrectFillAmongSource']['value'], .5)
        self.assertEqual(row['missingSourceIds'], ['b'])
        self.assertEqual(row['stages']['exportWitness']['unavailableRetained'], 1)

    def test_unknown_fill_is_not_an_error_or_a_correct_label(self):
        row = summarize_points([self.point('a', self.prediction(None), 'unknown')])[0]
        self.assertIsNone(row['fillCorrectAmongJudgedRetained']['value'])
        self.assertIsNone(row['retainedWithCorrectFillAmongSource'])
        self.assertEqual(row['unjudgedRetainedFill'], 1)

    def test_native_label_is_not_invented_four_shape_prediction(self):
        p = self.point('a', {'nativeLabel': 'NOTEHEAD_BLACK', 'fill': 'filled', 'stages': {}}, 'filled')
        p['shape'] = 'square'
        row = summarize_points([p])[0]
        self.assertEqual(row['nativeLabelCounts'], {'NOTEHEAD_BLACK': 1})
        self.assertNotIn('shapeAccuracy', row)

    def test_duplicate_identity_and_malformed_stage_fail_closed(self):
        with self.assertRaises(ValueError):
            summarize_points([self.point('a'), self.point('a')])
        p = self.prediction(); p['stages']['timedSlot'] = 'true'
        with self.assertRaises(ValueError):
            summarize_points([self.point('a', p)])

    def test_final_negative_floor_cannot_establish_reduction(self):
        result = negative_diagnostic({'before': [0, 0], 'after': [0, 0]})
        self.assertTrue(result['allArmsAtFinalDetectionFloor'])
        self.assertFalse(result['finalReductionMeasurable'])
        self.assertIsNone(result['populationPrecision'])
        self.assertTrue(negative_diagnostic({'before': [1], 'after': [0]})['finalReductionMeasurable'])
        with self.assertRaises(ValueError):
            negative_diagnostic({'before': [0], 'after': []})

    def event(self, fill, **kw):
        return {'pointId': 'a', 'shape': 'NOTEHEAD_FA_LEFT_' + fill, 'x': 10., 'y': 20.,
                'distance': .2, 'anchor': 'MIDDLE_LEFT', 'seed': True, 'veto': False, **kw}

    def test_only_like_center_anchor_orientation_and_path_are_paired(self):
        for difference in ({'x': 11.}, {'anchor': 'TOP_LEFT'}, {'seed': False},
                           {'shape': 'NOTEHEAD_FA_UP_RIGHT_VOID'}):
            rows = paired_proposals([self.event('FILLED'), self.event('VOID', **difference)])
            self.assertEqual(rows['a'].get('pairedGroups', 0), 0)

    def test_duplicates_and_vetoes_are_not_hidden_by_best_distance(self):
        events = [self.event('FILLED', distance=.1), self.event('VOID', veto=True)]
        row = paired_proposals(events)['a']
        self.assertEqual(row['pairedGroups'], 1)
        self.assertEqual(row['filledLower'], 1)
        self.assertEqual(row['bothAllowed'], 0)
        row = paired_proposals(events + [events[0]])['a']
        self.assertEqual(row['duplicateGroupsExcluded'], 1)
        self.assertEqual(row.get('pairedGroups', 0), 0)
        with self.assertRaises(ValueError):
            paired_proposals([self.event('FILLED', distance=float('nan'))])

    def test_review_selection_preserves_singletons_and_is_label_blind(self):
        queue = [{'id': str(i), 'arm': 'candidate', 'songNo': 'a', 'windowId': 'w',
                  'x': i, 'y': 1, 'nativeLabel': 'ignored'} for i in range(4)]
        benchmark = {'sourceImages': {'a': {'split': 'train'}}}
        selected = selection_for(queue, benchmark)
        self.assertEqual([r['id'] for r in selected['rows']], ['1', '2'])
        self.assertEqual(len(selection_for(queue[:1], benchmark)['rows']), 1)


if __name__ == '__main__':
    unittest.main()
