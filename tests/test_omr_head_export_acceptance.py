"""Clone-safe export/acceptance boundaries; no scans or recognition needed."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_acceptance_audit as acceptance
import omr_export_trace as trace
from test_sh1991_fa_survival import fixture


def source_and_score():
    score = ET.fromstring('''<score-partwise><part id="P1"><measure number="1">
      <attributes><divisions>2</divisions><key><fifths>0</fifths></key>
      <time><beats>1</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type></note>
      </measure></part></score-partwise>''')
    observed = {'source': {'sha256': 'not-used-in-pure-comparison'},
                'observer': 'Fixture source reader', 'scope': 'Entire one-bar fixture',
                'expectedMeasuresPerPart': [1],
                'segments': [{'part': 0, 'measure': 0, 'cropBox': [0,0,100,100],
                              'events': [['C4','1']],
                              'absentMarkings': ['dynamics','articulations','ornaments']}],
                'headers': [{'fifths':0, 'beats':'1', 'beatType':'4', 'clef':{'sign':'G','line':2}}],
                'ties': []}
    return observed, score


class TraceTest(unittest.TestCase):
    def setup_native(self):
        sheet, score = fixture()
        graph, _ = trace.survival.graph_rows(sheet, score)
        exported, _ = trace.export_details(score)
        observations = [{'id':'a','label':'round/open'}, {'id':'b','label':'square/open'}]
        predictions = [{'id':'1:h1','rawNativeId':'h1','origin':'native','prediction':'round/open'}]
        pairs = [{'sourceId':'a','predictionId':'1:h1'}]
        return observations, predictions, pairs, graph, exported

    def test_research_addition_is_not_a_graph_head_or_an_export_deletion(self):
        observed, predicted, pairs, graph, exported = self.setup_native()
        predicted.append({'id':'hole:0:1','origin':'image-enclosed-white','prediction':'square/open'})
        pairs.append({'sourceId':'b','predictionId':'hole:0:1'})
        result = trace.trace_arm(observed,predicted,pairs,graph,exported)
        self.assertEqual(result['statusCounts'], {'export-witness':1,'not-integrated':1})
        self.assertEqual(result['stages']['retained'],1)
        self.assertIsNone(result['rows'][1]['exportedEvent'])

    def test_undetected_source_heads_and_unmatched_predictions_are_retained(self):
        args = self.setup_native()
        args[1].append({'id':'hole:extra','origin':'image-enclosed-white'})
        result = trace.trace_arm(*args)
        self.assertEqual(result['sourceHeads'],2)
        self.assertEqual(result['statusCounts']['not-detected'],1)
        self.assertEqual(result['unmatchedPredictions'],['hole:extra'])

    def test_native_identity_requires_system_not_just_reused_number(self):
        args = self.setup_native()
        args[1][0]['id']='2:h1'; args[2][0]['predictionId']='2:h1'
        with self.assertRaisesRegex(ValueError,'exact retained graph identity'):
            trace.trace_arm(*args)

    def test_pair_reuse_and_unknown_origin_fail_closed(self):
        args = self.setup_native(); args[2].append({'sourceId':'b','predictionId':'1:h1'})
        with self.assertRaisesRegex(ValueError,'reused geometric pair'):
            trace.trace_arm(*args)
        args = self.setup_native(); args[1][0]['origin']='future-unreviewed-bridge'
        with self.assertRaisesRegex(ValueError,'Unknown prediction origin'):
            trace.trace_arm(*args)

    def test_export_presence_does_not_prove_correct_source_pitch(self):
        args = self.setup_native()
        result = trace.trace_arm(*args)
        self.assertEqual(result['rows'][0]['exportedEvent']['pitch'],['F','0',5])
        self.assertIsNone(result['sourceEventAccuracy'])

    def test_pickup_witness_extension_is_explicit_without_changing_original_graph(self):
        sheet,score=fixture(number='0',special='special="PICKUP"')
        rows,summary=trace.graph_export_rows(sheet,score)
        self.assertTrue(rows['h1']['exportWitness'])
        self.assertEqual(rows['h1']['witnessKind'],'pickup-exact-label-layout')
        self.assertEqual(summary['legacyStages']['exportWitness'],0)
        self.assertEqual(sheet.find('.//stack').get('special'),'PICKUP')
        score.find('.//measure').set('number','1')
        self.assertFalse(trace.graph_export_rows(sheet,score)[0]['h1']['exportWitness'])
        sheet,score=fixture(number='0',special='special="CAUTIONARY"')
        self.assertFalse(trace.graph_export_rows(sheet,score)[0]['h1']['exportWitness'])

    def test_event_details_follow_rational_cursor_and_backups(self):
        _,score=source_and_score(); measure=score.find('.//measure')
        ET.SubElement(ET.SubElement(measure,'backup'),'duration').text='2'
        n=ET.SubElement(measure,'note',{'default-x':'120'})
        pitch=ET.SubElement(n,'pitch'); ET.SubElement(pitch,'step').text='E'; ET.SubElement(pitch,'octave').text='4'
        ET.SubElement(n,'duration').text='1'; ET.SubElement(n,'voice').text='2'
        details,_=trace.export_details(score)
        self.assertEqual(details['P1/m1/n2']['onset'],'0')
        self.assertEqual(details['P1/m1/n2']['duration'],'1/2')

    def test_raw_artifact_drift_rejected_even_with_unchanged_receipts(self):
        with tempfile.TemporaryDirectory() as d:
            study=Path(d); save=trace.immutable
            for name in ['protocol.json','report.json','receipt.json','inference-lock.json','recognition.json','source-observations.json']:
                save(study/name,{})
            # Build the receipt links in dependency order, retaining a raw byte hash.
            raw=study/'raw.omr'; raw.write_bytes(b'original')
            protocol={'sourceSha256':'source'}; labels={'sourceSha256':'source','completeHeadCensus':True}
            (study/'protocol.json').write_text(json.dumps(protocol));(study/'source-observations.json').write_text(json.dumps(labels))
            lock={'protocolSha256':trace.digest(study/'protocol.json'),'labelsSha256':trace.digest(study/'source-observations.json')}
            (study/'inference-lock.json').write_text(json.dumps(lock))
            rec={'status':'graph-ready','exitCode':0,'inferenceLockSha256':trace.digest(study/'inference-lock.json'),'artifactsSha256':{'raw.omr':trace.digest(raw)}}
            (study/'recognition.json').write_text(json.dumps(rec))
            report={'protocolSha256':lock['protocolSha256'],'inferenceLockSha256':rec['inferenceLockSha256'],'recognitionSha256':trace.digest(study/'recognition.json')}
            (study/'report.json').write_text(json.dumps(report))
            receipt={'reportSha256':trace.digest(study/'report.json'),'recognitionSha256':report['recognitionSha256']}
            (study/'receipt.json').write_text(json.dumps(receipt))
            trace.verify_study(study)
            raw.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'recognition artifact drift'):
                trace.verify_study(study)


class AcceptanceTest(unittest.TestCase):
    def test_full_event_agreement_and_independent_flag_never_authorize_promotion(self):
        observed,score=source_and_score(); observed['independent']=True
        result=acceptance.compare(observed,score)
        self.assertEqual(result['gates']['pitchRhythm']['matched'],1)
        self.assertEqual(result['gates']['pitchRhythm']['status'],'pass')
        self.assertEqual(result['gates']['literalHeads']['status'],'unavailable')
        self.assertEqual(result['gates']['independentSourceVerification']['status'],'unavailable')
        self.assertFalse(result['safeToPromote']);self.assertEqual(result['status'],'incomplete')

    def test_grid_mismatch_is_blocked_without_silently_zipping(self):
        observed,score=source_and_score();observed.pop('segments');observed['expectedMeasuresPerPart']=[2]
        result=acceptance.compare(observed,score)
        self.assertEqual(result['gates']['sourceGrid']['actual'],[1])
        self.assertEqual(result['gates']['measureAlignment']['status'],'blocked')
        self.assertEqual(result['gates']['pitchRhythm']['status'],'blocked')

    def test_wrong_pitch_counts_missing_and_extra_not_one_hidden_substitution(self):
        observed,score=source_and_score();score.find('.//step').text='D'
        gate=acceptance.compare(observed,score)['gates']['pitchRhythm']
        self.assertEqual((gate['matched'],gate['missingEventUnits'],gate['extraEventUnits']),(0,1,1))

    def test_orphan_measure_events_and_markings_cannot_escape_denominator(self):
        observed,score=source_and_score();part=score.find('part');extra=copy.deepcopy(part.find('measure'))
        extra.set('number','orphan');ET.SubElement(ET.SubElement(ET.SubElement(extra,'direction'),'direction-type'),'dynamics')
        ET.SubElement(extra.find('.//dynamics'),'f');part.append(extra)
        result=acceptance.compare(observed,score,{'mapping':[[0]],'orphanDraftMeasures':[[1]]})
        self.assertEqual(result['gates']['pitchRhythm']['extraEventUnits'],1)
        self.assertEqual(result['gates']['observedAbsentMarkings']['unsupported'],1)
        self.assertEqual(result['gates']['sourceGrid']['status'],'fail')

    def test_full_source_measure_coverage_is_required(self):
        observed,score=source_and_score();observed['expectedMeasuresPerPart']=[2]
        with self.assertRaisesRegex(ValueError,'Full declared source coverage'):
            acceptance.compare(observed,score)

    def test_explicit_lyric_absence_detects_candidate_lyric_and_no_auto_shape_inference(self):
        observed,score=source_and_score();s=observed['segments'][0]
        s['lyrics']=[[]];s['literalHeads']=[{'tag':'notehead','attributes':{'filled':'yes'},'text':'square','children':[]}]
        ET.SubElement(ET.SubElement(score.find('.//note'),'lyric'),'text').text='invented'
        result=acceptance.compare(observed,score)
        self.assertEqual(result['gates']['lyrics']['status'],'fail')
        self.assertEqual(result['gates']['literalHeads']['status'],'fail')

    def test_partial_layer_is_unavailable_not_a_scoped_pass(self):
        observed,score=source_and_score();observed['segments'][0]['lyrics']=[[]]
        m=copy.deepcopy(score.find('.//measure'));m.set('number','2');score.find('part').append(m)
        observed['expectedMeasuresPerPart']=[2]
        s=copy.deepcopy(observed['segments'][0]);s['measure']=1;s.pop('lyrics');observed['segments'].append(s)
        gate=acceptance.compare(observed,score)['gates']['lyrics']
        self.assertEqual(gate,{'status':'unavailable','observedStaffMeasures':1,'requiredStaffMeasures':2})

    def test_source_grid_duplicate_edges_and_annotation_length_fail_closed(self):
        observed,score=source_and_score();observed['writtenGrid']={'edges':[0,50,50],'staffBands':[[0,100]]}
        with self.assertRaisesRegex(ValueError,'source grid coverage'):
            acceptance.compare(observed,score)
        observed.pop('writtenGrid');observed['segments'][0]['lyrics']=[]
        with self.assertRaisesRegex(ValueError,'Per-event annotation coverage'):
            acceptance.compare(observed,score)

    def test_tie_presence_is_not_visual_tie_certification(self):
        observed,score=source_and_score();ET.SubElement(score.find('.//note'),'tie',type='start')
        result=acceptance.compare(observed,score)
        self.assertEqual(result['gates']['ties']['extraEndpoints'],1)
        self.assertEqual(result['gates']['visualTieNotation']['status'],'unavailable')

    def test_unscored_grace_and_unknown_source_heads_cannot_be_a_clean_layer(self):
        observed,score=source_and_score();observed['segments'][0]['literalHeads']=[None]
        grace=ET.SubElement(score.find('.//measure'),'note');ET.SubElement(grace,'grace')
        p=ET.SubElement(grace,'pitch');ET.SubElement(p,'step').text='D';ET.SubElement(p,'octave').text='4'
        result=acceptance.compare(observed,score)
        self.assertEqual(result['gates']['unscoredGraceEvents']['status'],'blocked')
        self.assertEqual(result['gates']['literalHeads']['status'],'unavailable')

    def test_input_hash_drift_and_in_place_output_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);obs,score=source_and_score()
            src=root/'source.jpg';src.write_bytes(b'fixture source')
            obs['source']['sha256']=trace.digest(src)
            trace.immutable(root/'source.json',obs)
            (root/'score.xml').write_bytes(ET.tostring(score))
            manifest={'identity':'fixture',**{k:{'path':n,'sha256':trace.digest(root/n)} for k,n in
                      [('source','source.jpg'),('score','score.xml'),('observations','source.json')]}}
            trace.immutable(root/'manifest.json',manifest)
            acceptance.run(root/'manifest.json',root/'output')
            acceptance.run(root/'manifest.json',root/'output')
            with self.assertRaisesRegex(ValueError,'input evidence directory'):
                acceptance.run(root/'manifest.json',root)
            (root/'score.xml').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Manifest input drift'):
                acceptance.run(root/'manifest.json',root/'new-output')


if __name__ == '__main__':
    unittest.main()
