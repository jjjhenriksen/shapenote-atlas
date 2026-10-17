import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sh1991_anchor_probe import read_scores

LINE='ANCHOR5|point-1|2|40|anchor|LEFT_STEM|0|0|NOTEHEAD_FA_LEFT_VOID|101|202|90|190|100.5|201.0|21|22|0.25|0.75|[20, 5, 8, 2, 4, 1, 3, 0]'
class ForcedAnchorReceiptTests(unittest.TestCase):
    def test_keeps_pivot_origin_and_slim_center_distinct(self):
        row=next(iter(read_scores('normal log\n'+LINE).values()))
        self.assertEqual(row['pivot'],[101,202]);self.assertEqual(row['origin'],[90,190]);self.assertEqual(row['center'],[100.5,201.0]);self.assertEqual(row['line'],2)
    def test_duplicate_positions_rejected_not_favorably_collapsed(self):
        with self.assertRaisesRegex(ValueError,'duplicate'): read_scores(LINE+'\n'+LINE)
    def test_nonfinite_score_rejected(self):
        with self.assertRaisesRegex(ValueError,'invalid'): read_scores(LINE.replace('|0.25|','|nan|'))
    def test_truncated_counter_rejected(self):
        with self.assertRaisesRegex(ValueError,'invalid'): read_scores(LINE.replace('[20, 5, 8, 2, 4, 1, 3, 0]','[20, 5]'))
    def test_anchor_grid_and_shape_are_part_of_identity(self):
        self.assertEqual(len(read_scores(LINE+'\n'+LINE.replace('|LEFT_STEM|','|RIGHT_STEM|'))),2)
if __name__=='__main__':unittest.main()
