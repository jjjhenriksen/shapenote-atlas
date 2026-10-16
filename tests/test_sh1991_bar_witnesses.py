import sys,tempfile,zipfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import sh1991_pilot as pilot
from sh1991_v7_bar_witnesses import inventory

class PhysicalWitnessTests(unittest.TestCase):
    def graph(self,root,second_staff):
        p=root/'page.omr'
        body=f'<sheet><page><system id="1"><sig><inters><barline id="1" staff="1" glyph="41"><bounds x="2" y="3" w="2" h="10"/></barline><barline id="2" staff="{second_staff}" glyph="41"><bounds x="2" y="30" w="2" h="10"/></barline></inters></sig></system></page></sheet>'
        with zipfile.ZipFile(p,'w') as z:z.writestr('sheet#1/sheet#1.xml',body)
        return {'page.omr':pilot.digest(p.read_bytes())}
    def test_shared_start_glyph_on_different_staffs_not_collapsed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);evidence=self.graph(root,'2')
            with patch.object(pilot,'ROOT',root):result,_=inventory(root,evidence)
            self.assertEqual(len(result),2);self.assertIn(('1','1','41'),result);self.assertIn(('1','2','41'),result)
    def test_duplicate_same_staff_identity_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);evidence=self.graph(root,'1')
            with patch.object(pilot,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'duplicate'):inventory(root,evidence)
if __name__=='__main__':unittest.main()
