import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sh1991_fa_proximity import probes


class TemplateProbeTests(unittest.TestCase):
    def test_vetoed_raw_winner_is_not_an_allowed_winner(self):
        text='\n'.join([
            'FAPROBE|point|NOTEHEAD_FA_LEFT_FILLED|10|20|0.1|NaN|MIDDLE_LEFT|true|true',
            'FAPROBE|point|NOTEHEAD_FA_LEFT_FILLED|11|20|0.2|NaN|MIDDLE_LEFT|false|false',
            'FAPROBE|point|NOTEHEAD_VOID|10|20|0.3|0.8|MIDDLE_LEFT|true|false'])
        row=probes(text)['point']
        self.assertEqual(row['evaluations'],3)
        self.assertEqual(row['vetoes'],1)
        self.assertEqual(row['bestByShape']['NOTEHEAD_FA_LEFT_FILLED']['distance'],.1)
        self.assertEqual(row['bestAllowedByShape']['NOTEHEAD_FA_LEFT_FILLED']['distance'],.2)
        self.assertIsNone(row['bestByShape']['NOTEHEAD_FA_LEFT_FILLED']['holeWhiteRatio'])
        self.assertEqual(row['bestByShape']['NOTEHEAD_VOID']['holeWhiteRatio'],.8)

    def test_no_proposals_is_not_a_negative_distance_measurement(self):
        self.assertEqual(probes('normal log output'),{})

    def test_best_match_keeps_its_actual_anchor_and_line(self):
        row=probes('other log\nFAPROBE|point|NOTEHEAD_VOID|12|20|0.2|0.6|TOP_RIGHT|false|false')['point']
        event=row['bestByShape']['NOTEHEAD_VOID']
        self.assertEqual(event['anchor'],'TOP_RIGHT')
        self.assertEqual(event['line'],2)
        self.assertFalse(event['seed'])

    def test_malformed_or_nonfinite_distance_is_rejected(self):
        for text in ('FAPROBE|short',
                     'FAPROBE|point|NOTEHEAD_VOID|10|20|NaN|0.8|TOP_LEFT|true|false',
                     'FAPROBE|point|NOTEHEAD_VOID|10|20|0.2|0.8|TOP_LEFT|true|maybe'):
            with self.assertRaises(ValueError):probes(text)


if __name__=='__main__':unittest.main()
