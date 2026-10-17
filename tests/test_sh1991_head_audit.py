"""Clone-safe tests of localization, fill denominators and explicit adjudication."""
from pathlib import Path
import sys
import unittest
from xml.etree import ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'scripts'))
from sh1991_head_audit import literal_point, heads_in_graph, match, strata, adjudicate


def observation(key='n1', x=100, shape='triangle', fill='filled'):
    return {'id':key,'x':x,'y':100,'interline':10,'shape':shape,'fill':fill,'staffId':'1','songNo':'sample'}


def head(key='h1', x=100, shape='NOTEHEAD_VOID', staff='1'):
    return {'id':key,'x':x,'y':100,'shape':shape,'staffId':staff,'inHeadChord':True}


class HeadAuditTest(unittest.TestCase):
    def test_shape_and_fill_do_not_influence_coordinate_matching(self):
        a=match([observation()], [head()], .5)
        b=match([observation(shape='round',fill='open')], [head()], .5)
        self.assertEqual(a,b)

    def test_head_cannot_be_reused_and_out_of_radius_points_stay_unmatched(self):
        rows=[observation('n1',100),observation('n2',102),observation('n3',130)]
        self.assertEqual(set(match(rows,[head()],.5)),{'n1'})
        self.assertEqual(match([observation(x=106)],[head()],.5),{})
        self.assertIn('n1',match([observation(x=106)],[head()],.75))

    def test_missing_heads_keep_detection_denominator_but_not_fill_denominator(self):
        rows=[{**observation(),'match':head()}, {**observation('n2',120),'match':None}]
        result=strata(rows,['shape'])[0]
        self.assertEqual((result['observed'],result['retainedHead'],result['missingHead']),(2,1,1))
        self.assertEqual(result['fillJudgedAmongDetected'],1)
        self.assertEqual(result['fillMatchesAmongDetected'],0)
        self.assertEqual(result['retainedHeadRate'],.5)

    def test_staff_assignment_is_separate_from_localization(self):
        result=strata([{**observation(),'match':head(staff='2')}],['shape'])[0]
        self.assertEqual(result['retainedHead'],1)
        self.assertEqual(result['staffAssignmentMatches'],0)

    def test_graph_reader_requires_actual_head_nodes_and_chord_containment(self):
        sheet=ET.fromstring('<sheet><head-chord id="c"/><head id="h" staff="1" shape="NOTEHEAD_BLACK"><bounds x="91" y="94" w="18" h="12"/></head><flag id="f"><bounds x="91" y="94" w="18" h="12"/></flag><relation source="c" target="h"><containment/></relation></sheet>')
        result=heads_in_graph(sheet)
        self.assertEqual(len(result),1)
        self.assertEqual((result[0]['x'],result[0]['y']),(100,100))
        self.assertTrue(result[0]['inHeadChord'])

    def test_source_staff_position_uses_sloped_lines_not_pitch_or_key(self):
        staff=ET.Element('staff');lines=ET.SubElement(staff,'lines')
        for i in range(5):
            line=ET.SubElement(lines,'line')
            ET.SubElement(line,'point',x='0',y=str(100+i*10))
            ET.SubElement(line,'point',x='200',y=str(104+i*10))
        self.assertEqual(literal_point(staff,100,3),(117,10))
        self.assertEqual(literal_point(staff,100,-1),(97,10))
        self.assertEqual(literal_point(staff,100,10),(152,10))

    def test_adjudication_preserves_automatic_record_and_rejects_reused_head(self):
        original=[{**observation(),'match':None}]
        case={'observationId':'n1','retainedHead':head(x=110)}
        revised=adjudicate(original,[case],{'sample':[head(x=110)]})
        self.assertIsNone(original[0]['match'])
        self.assertEqual(revised[0]['match']['id'],'h1')
        with self.assertRaises(ValueError):adjudicate(original,[case],{'sample':[]})
        taken=[*original,{**observation('n2',110),'match':head(x=110)}]
        with self.assertRaises(ValueError):adjudicate(taken,[case],{'sample':[head(x=110)]})


if __name__=='__main__':unittest.main()
