"""Fresh-cohort guard tests; no retained scans, recognizer, or reference XML needed."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import sh1991_agent_unseen as unseen
import sh1991_agent_correction as correction


class UnseenGuardsTest(unittest.TestCase):
    def fixture(self, base):
        work=base/'fresh'; work.mkdir()
        original=base/'old'; original.mkdir()
        image=base/'scan.jpg'; image.write_bytes(b'new local scan')
        card=base/'card.png'; card.write_bytes(b'new local crop')
        def save(path,data):
            path.write_bytes(correction.json_bytes(data))
        self.save=save
        save(original/'dataset.json', {'records':[{'page':26,'image':{'sha256':'old-image'}}]})
        protocol={'cohort':[{'songNo':'144','page':144,'title':'Jubilee'}],
                  'correctionSha256':correction.digest(correction.__file__),
                  'rendererSha256':correction.digest(unseen.pilot.ROOT/'scripts/sh1991_agent_render.mjs'),
                  'engineExecutable':'/not-used-in-fixture/Audiveris','engine':{'fixture':True}}
        save(work/'protocol.json',protocol)
        source={'records':[{'songNo':'144','image':{'path':str(image),'sha256':correction.digest(image)}}],
                'protocolSha256':correction.digest(work/'protocol.json')}
        save(work/'sources.json',source)
        cards=[{'songNo':'144','card':str(card),'cardSha256':correction.digest(card)}]
        save(work/'review-selection.json',{'cards':cards})
        save(work/'source-observations.json',{'sourceCards':cards,
             'expectedTopStaffMeasures':{'144':[[['C5','1']],[['D5','1']]]}})
        return work,original,protocol,source,image,card

    def test_source_only_fixture_requires_no_reference_label_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            work,old,*_=self.fixture(Path(tmp))
            with patch.object(unseen.pilot,'DEFAULT_WORK',old), patch.object(unseen.pilot,'engine_identity',return_value={'fixture':True}):
                protocol,sources=unseen.check(work)
            self.assertEqual(len(sources['records']),1)
            self.assertNotIn('label',sources['records'][0])

    def test_known_page_leakage_is_rejected_even_with_a_different_scan_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            work,old,protocol,source,*_=self.fixture(Path(tmp))
            protocol['cohort'][0]['page']=26
            self.save(work/'protocol.json',protocol)
            source['protocolSha256']=correction.digest(work/'protocol.json')
            self.save(work/'sources.json',source)
            with patch.object(unseen.pilot,'DEFAULT_WORK',old), patch.object(unseen.pilot,'engine_identity',return_value={'fixture':True}):
                with self.assertRaisesRegex(ValueError,'consumed page leakage'):
                    unseen.check(work)

    def test_frozen_code_and_source_pixels_cannot_silently_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            work,old,protocol,source,image,card=self.fixture(Path(tmp))
            with patch.object(unseen.pilot,'DEFAULT_WORK',old), patch.object(unseen.pilot,'engine_identity',return_value={'fixture':True}):
                card.write_bytes(b'changed crop')
                with self.assertRaisesRegex(ValueError,'Source card drift'):
                    unseen.check(work)
                protocol['correctionSha256']='wrong'
                self.save(work/'protocol.json',protocol)
                with self.assertRaisesRegex(ValueError,'correction implementation drift'):
                    unseen.check(work)

    def test_post_inference_source_label_edits_are_rejected_before_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            work,old,protocol,source,*_=self.fixture(Path(tmp))
            self.save(work/'execution.json',{'sourceObservationSha256':'old-not-current'})
            with patch.object(unseen,'check',return_value=(protocol,source)), patch.object(correction,'run') as run:
                with self.assertRaisesRegex(ValueError,'observations changed after recognition'):
                    unseen.evaluate(work)
                run.assert_not_called()

    def test_recognition_failures_stay_in_fixed_cohort_and_never_become_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            work,old,protocol,source,*_=self.fixture(Path(tmp))
            protocol['cohort'].append({'songNo':'204','page':204,'title':'Mission'})
            records=[{'songNo':'144','status':'exported'},{'songNo':'204','status':'recognition-failed'}]
            self.save(work/'execution.json',{'sourceObservationSha256':correction.digest(work/'source-observations.json')})
            self.save(work/'recognition-complete.json',{'failedPages':1,'records':records})
            with patch.object(unseen,'check',return_value=(protocol,source)):
                result=unseen.evaluate(work)
            self.assertEqual(len(result['records']),2)
            self.assertFalse(result['scopedCyclePass'])
            self.assertFalse(result['wholeScoreAcceptance'])
            self.assertFalse(result['humanReviewRequired'])


if __name__=='__main__':
    unittest.main()
