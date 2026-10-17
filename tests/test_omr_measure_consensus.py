"""Clone-safe structural-map, control-isolation and no-retry contracts."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_measure_consensus_run as strict
import omr_measure_consensus_paired as paired
import omr_measure_consensus_study as study


def layout_fixture(spans=((0,100,'1',None),),measures=('1',)):
    sheet=ET.Element('sheet');system=ET.SubElement(ET.SubElement(sheet,'page'),'system',id='1')
    for a,b,label,special in spans:
        s=ET.SubElement(system,'stack',id=label,left=str(a),right=str(b))
        if special:s.set('special',special)
    p=ET.SubElement(system,'part',id='1');ET.SubElement(p,'staff',id='1')
    for _ in spans:ET.SubElement(p,'measure')
    xml=ET.Element('score-partwise');part=ET.SubElement(xml,'part',id='P1')
    for label in measures:
        m=ET.SubElement(part,'measure',number=label)
        n=ET.SubElement(m,'note');pitch=ET.SubElement(n,'pitch')
        ET.SubElement(pitch,'step').text='C';ET.SubElement(pitch,'octave').text='4'
        ET.SubElement(n,'duration').text='1'
    observed={'observer':'Fixture source reader','scope':'Entire written fixture',
              'expectedMeasuresPerPart':[2],
              'writtenGrid':{'edges':[10,50,100],'staffBands':[[0,60]]}}
    return observed,sheet,xml


class GeometryTests(unittest.TestCase):
    def test_merged_region_does_not_become_an_index_zip(self):
        observed,sheet,xml=layout_fixture()
        r=study.geometry_map(observed,sheet,xml)
        self.assertEqual(r['map'],{'mapping':[[None,None]],'orphanDraftMeasures':[[0]]})
        self.assertEqual(r['boundaries']['missed'],1)

    def test_cautionary_region_never_counts_as_exported_source_measure(self):
        observed,sheet,xml=layout_fixture(((0,50,'0','PICKUP'),(50,100,'0','CAUTIONARY')),('0',))
        r=study.geometry_map(observed,sheet,xml)
        self.assertEqual(r['map']['mapping'],[[0,None]])
        self.assertEqual(r['geometricallyAlignedSourceMeasures'],[1])

    def test_equal_counts_cannot_hide_merged_and_extra_regions(self):
        observed,sheet,xml=layout_fixture(((0,75,'1',None),(75,100,'2',None)),('1','2'))
        r=study.geometry_map(observed,sheet,xml)
        self.assertEqual(r['map']['mapping'],[[None,None]])
        self.assertEqual(r['map']['orphanDraftMeasures'],[[0,1]])

    def test_header_orphan_is_explicit_in_complete_map(self):
        observed,sheet,xml=layout_fixture(((0,9,'1',None),(9,50,'2',None),(50,100,'3',None)),('1','2','3'))
        r=study.geometry_map(observed,sheet,xml)
        self.assertEqual(r['map'],{'mapping':[[1,2]],'orphanDraftMeasures':[[0]]})

    def test_duplicate_export_labels_and_unsupported_part_mapping_fail(self):
        observed,sheet,xml=layout_fixture(((0,50,'1',None),(50,100,'2',None)),('1','1'))
        with self.assertRaisesRegex(ValueError,'Duplicate exported'):
            study.geometry_map(observed,sheet,xml)
        xml.find('part').set('id','P2')
        with self.assertRaisesRegex(ValueError,'physical/logical'):
            study.geometry_map(observed,sheet,xml)

    def test_net_error_gain_does_not_hide_introduced_error_units(self):
        observed,before_sheet,before=layout_fixture()
        observed['segments']=[{'part':0,'measure':i,'events':[[pitch,'1']],
                               'cropBox':[10+40*i,0,50+40*i,60]} for i,pitch in enumerate(['C4','E4'])]
        _,after_sheet,after=layout_fixture(((0,50,'1',None),(50,100,'2',None)),('1','2'))
        after.findall('.//step')[1].text='D'
        inventories=[]
        for sheet,score in [(before_sheet,before),(after_sheet,after)]:
            inventories.append(study.mapped_errors(observed,study.acceptance.audit.inspect(score),
                                                   study.geometry_map(observed,sheet,score)))
        old,new=inventories
        self.assertEqual((sum(old.values()),sum(new.values())),(3,2))
        self.assertEqual(sum((new-old).values()),1)
        self.assertEqual(sum((old-new).values()),2)


class ControlTests(unittest.TestCase):
    def test_header_normalization_retains_every_source_overlapping_event(self):
        _,sheet,xml=layout_fixture(((0,9,'1',None),(9,50,'2',None),(50,100,'3',None)),('1','2','3'))
        n=xml.find('part/measure/note');n.remove(n.find('pitch'));ET.SubElement(n,'rest')
        before,orphan=paired.normalized_music(sheet,xml,10,100)
        self.assertEqual(len(orphan),1)
        newer_sheet=copy.deepcopy(sheet);system=newer_sheet.find('page/system');system.remove(system.find('stack'))
        system.find('stack').set('left','0')
        newer=copy.deepcopy(xml);newer.find('part').remove(newer.find('part/measure'))
        after,other=paired.normalized_music(newer_sheet,newer,10,100)
        self.assertEqual(before,after);self.assertEqual(other,[])
        newer.find('.//step').text='D'
        self.assertNotEqual(before,paired.normalized_music(newer_sheet,newer,10,100)[0])

    def test_pitched_or_trailing_orphan_cannot_use_header_exception(self):
        _,sheet,xml=layout_fixture(((0,9,'1',None),(9,100,'2',None)),('1','2'))
        with self.assertRaisesRegex(ValueError,'pitched event'):
            paired.normalized_music(sheet,xml,10,100)
        _,sheet,xml=layout_fixture(((0,100,'1',None),(100,120,'2',None)),('1','2'))
        with self.assertRaisesRegex(ValueError,'Trailing orphan'):
            paired.normalized_music(sheet,xml,0,100)

    def test_both_protocols_block_candidate_before_failed_control(self):
        for module in (strict,paired):
            case={'id':'469'}
            with patch.object(module,'check',return_value={'cases':[case]}), \
                 patch.object(module,'digest',return_value='frozen'), \
                 patch.object(module,'verify_controls',return_value={'allControlsMatch':False}), \
                 patch.object(module.subprocess,'Popen',side_effect=AssertionError('must not run')):
                with self.assertRaisesRegex(ValueError,'control regression'):
                    module.recognize(Path('/unused-study'),case,'on')

    def test_started_without_receipt_never_retries(self):
        for module in (strict,paired):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);case={'id':'469'}
                folder=root/'off/469';folder.mkdir(parents=True);(folder/'started.json').write_text('{}')
                with patch.object(module,'check',return_value={'cases':[case]}), \
                     patch.object(module,'digest',return_value='frozen'), \
                     patch.object(module.subprocess,'Popen',side_effect=AssertionError('must not retry')):
                    with self.assertRaisesRegex(ValueError,'already started'):
                        module.recognize(root,case,'off')

    def test_completed_artifact_drift_and_path_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();(root/'raw').mkdir();f=root/'raw/a.mxl';f.write_bytes(b'original')
            strict.immutable(root/'recognition.json',{'protocolSha256':'p','artifactsSha256':{'raw/a.mxl':strict.digest(f)}})
            strict.verify_receipt(root,'p');f.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'artifact drift'):
                strict.verify_receipt(root,'p')
            with self.assertRaisesRegex(ValueError,'protocol drift'):
                strict.verify_receipt(root,'other-protocol')

    def test_receipt_cannot_bind_an_artifact_outside_its_run(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();child=root/'run';child.mkdir();f=root/'outside.mxl';f.write_bytes(b'outside')
            strict.immutable(child/'recognition.json',{'protocolSha256':'p','artifactsSha256':{'../outside.mxl':strict.digest(f)}})
            with self.assertRaisesRegex(ValueError,'artifact drift'):
                strict.verify_receipt(child,'p')

    def test_failed_export_is_unavailable_not_zero_events(self):
        with patch.object(strict,'verify_receipt',return_value={'status':'recognition-failed'}), \
             patch.object(study,'digest',return_value='p'):
            r=study.case_analysis(Path('/unused'),{}, {'id':'501t'},'on',None,None)
        self.assertIsNone(r['exportedMeasures']);self.assertIsNone(r['eventComparison'])


if __name__=='__main__':unittest.main()
