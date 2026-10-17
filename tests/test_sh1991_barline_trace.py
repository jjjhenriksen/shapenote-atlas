import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sh1991_barline_trace import parse_trace, geometry, compact_trace
from sh1991_barline_run import immutable
import tempfile


STAGES = ('HEADS/ENTER', 'HEADS/EXIT', 'STEMS/EXIT', 'REDUCTION/EXIT', 'MEASURES/ENTER', 'MEASURES/EXIT')


def fixture():
    return '\n'.join('BARCOUNT|' + key.replace('/', '|') + '|1|0' for key in STAGES)


class BarlineTraceTests(unittest.TestCase):
    def test_empty_stages_are_retained_not_treated_as_missing(self):
        trace = parse_trace(fixture())
        self.assertEqual(trace['counts']['MEASURES/EXIT'], 0)

    def test_incomplete_run_is_not_a_completed_trace(self):
        with self.assertRaisesRegex(ValueError, 'missing completed stage'):
            parse_trace(fixture().replace('BARCOUNT|STEMS|EXIT|1|0', ''))

    def test_duplicate_identity_is_rejected(self):
        bar = 'BARTRACE|HEADS|EXIT|1|7|2|9|300|400|3|50|0.8'
        with self.assertRaisesRegex(ValueError, 'duplicate physical bar'):
            parse_trace(fixture() + '\n' + bar + '\n' + bar)

    def test_ids_do_not_define_cross_run_witnesses(self):
        a = dict(system=1, staff=2, glyph=9, x=300, y=400, width=3, height=50, id=7)
        b = {**a, 'id':888}
        self.assertEqual(geometry([a]), geometry([b]))
        self.assertNotEqual(geometry([a]), geometry([{**b, 'glyph':10}]))

    def test_conflicts_preserve_support_and_line_provenance(self):
        log = fixture() + '\nBARCONFLICT|source=BarlineInter#7|target=StemInter#8|removed=BarlineInter#7|stemHeads=[HeadInter#9 NOTEHEAD_FA_LEFT_FILLED]\nBARREMOVE|7|box|glyph=9|SIGraph.reduceExclusions'
        trace = parse_trace(log)
        self.assertTrue(trace['conflicts'][0]['faOnlyStemSupport'])
        self.assertEqual(trace['conflicts'][0]['line'], 7)
        self.assertEqual(trace['removals'][0]['line'], 8)
        mixed = log.replace('FILLED]', 'FILLED, HeadInter#10 NOTEHEAD_BLACK]')
        self.assertFalse(parse_trace(mixed)['conflicts'][0]['faOnlyStemSupport'])

    def test_absent_support_diagnostics_are_not_empty_support_proof(self):
        trace = parse_trace(fixture() + '\nBARCONFLICT|source=BarlineInter#7|target=StemInter#8|removed=BarlineInter#7')
        self.assertIsNone(trace['conflicts'][0]['supportShapes'])

    def test_inventory_deltas_preserve_geometry_at_every_stage(self):
        log = '\n'.join('BARTRACE|' + s.replace('/', '|') + '|1|7|2|9|300|400|3|50|0.8' for s in STAGES)
        trace = parse_trace(log); compact = compact_trace(trace); indices = set()
        self.assertEqual(len(compact['physicalBarInventory']), 1)
        for stage, delta in compact['snapshotDeltas'].items():
            indices.difference_update(delta['removed']); indices.update(delta['added'])
            records = [dict(zip(compact['inventoryColumns'], compact['physicalBarInventory'][i])) for i in indices]
            self.assertEqual(geometry(records), geometry(trace['snapshots'][stage]))

    def test_environment_cache_key_cannot_silently_switch_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'execution.json'
            immutable(path, {'JAVA_OPTS':'-Datlas.faStemBarGuard=false'})
            original = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'changed configuration'):
                immutable(path, {'JAVA_OPTS':'-Datlas.faStemBarGuard=true'})
            self.assertEqual(path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
