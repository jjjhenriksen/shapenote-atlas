"""Clone-safe correction tests: real archive corruption and semantic failure modes."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import sh1991_agent_correction as loop


def note(step='C', duration=2, extra=''):
    return f'<note>{extra}<pitch><step>{step}</step><octave>5</octave></pitch><duration>{duration}</duration><voice>1</voice><type>quarter</type></note>'


def archive(first=None, second=None, initial_number='1', attributes=''):
    if first is None:
        first = note() + '<backup><duration>2</duration></backup>' + note('G')
    if second is None:
        second = note('D')
    xml = (f'<score-partwise version="4.0"><part-list>'
           '<score-part id="P1"><part-name>Top</part-name></score-part>'
           '<score-part id="P2"><part-name>Bass</part-name></score-part>'
           '</part-list><part id="P1">'
           f'<measure number="{initial_number}"><attributes><divisions>2</divisions>'
           '<time><beats>4</beats><beat-type>4</beat-type></time>'
           f'<clef><sign>G</sign><line>2</line></clef>{attributes}</attributes>{first}</measure>'
           f'<measure number="2">{second}</measure><measure number="3">{note("E")}</measure>'
           f'</part><part id="P2"><measure number="1">{note("F")}</measure></part></score-partwise>')
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w') as z:
        z.writestr('META-INF/container.xml', '<container><rootfiles><rootfile full-path="score.xml"/></rootfiles></container>')
        z.writestr('score.xml', xml)
        z.writestr('retained.txt', b'original non-score bytes')
    return result.getvalue()


class CorrectionTest(unittest.TestCase):
    def test_real_repair_removes_spurious_voice_adds_rest_and_preserves_other_music(self):
        original = archive()
        fixed, receipts = loop.repair_archive(original, [[['rest', '1/2'], ['E5', '3/2']]])
        self.assertTrue(receipts[0]['changed'])
        self.assertEqual(receipts[0]['expected'][1]['onset'], '1/2')
        self.assertTrue(loop.verify_structure(original, fixed, receipts))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'fixed.mxl'; path.write_bytes(fixed)
            result = loop.verify_semantics(path, receipts)
        self.assertEqual(result['segmentsChecked'], 1)
        self.assertFalse(result['independentSourceRecognition'])
        # A second repair from original inputs is byte-identical, not just a count.
        self.assertEqual(loop.repair_archive(original, [[['rest', '1/2'], ['E5', '3/2']]])[0], fixed)

    def test_non_target_part_and_measure_mutations_fail_closed(self):
        original = archive()
        fixed, receipts = loop.repair_archive(original, [[['E5', '2']]])
        root, member = loop.read_archive(fixed)
        for node in [root.findall('part')[1].find('.//step'),
                     root.findall('part')[0].findall('measure')[1].find('.//step')]:
            old = node.text; node.text = 'A'
            with self.assertRaisesRegex(ValueError, 'Out-of-scope'):
                loop.verify_structure(original, loop.archive_copy(fixed, root, member), receipts)
            node.text = old

    def test_verifier_catches_wrong_pitch_duration_and_onset(self):
        original = archive()
        fixed, receipts = loop.repair_archive(original, [[['C5', '1'], ['E5', '1']]])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'corrupt.mxl'
            for tag, value in [('step', 'G'), ('duration', '3')]:
                root, member = loop.read_archive(fixed)
                root.find(f'./part/measure/note//{tag}').text = value
                path.write_bytes(loop.archive_copy(fixed, root, member))
                with self.assertRaisesRegex(ValueError, 'Verifier pitch/duration/onset'):
                    loop.verify_semantics(path, receipts)
            root, member = loop.read_archive(fixed)
            measure = root.find('./part/measure')
            forward = ET.fromstring('<forward><duration>1</duration></forward>')
            measure.insert(1, forward)
            path.write_bytes(loop.archive_copy(fixed, root, member))
            with self.assertRaisesRegex(ValueError, 'Verifier pitch/duration/onset'):
                loop.verify_semantics(path, receipts)

    def test_dotted_half_rest_and_nonzero_octave_are_literal(self):
        fixed, receipts = loop.repair_archive(archive(), [[['rest', '3'], ['Bb3', '1/2']]])
        root, _ = loop.read_archive(fixed)
        notes = root.findall('./part/measure')[0].findall('note')
        self.assertEqual(notes[0].findtext('type'), 'half')
        self.assertIsNotNone(notes[0].find('dot'))
        self.assertEqual(notes[1].findtext('pitch/alter'), '-1')
        self.assertEqual(notes[1].findtext('pitch/octave'), '3')
        self.assertEqual(receipts[0]['expected'][1]['onset'], '3')

    def test_implicit_zero_measure_number_does_not_shift_the_scope(self):
        fixed, receipts = loop.repair_archive(archive(initial_number='0'), [[['E5', '2']]])
        self.assertEqual(receipts[0]['measureNumber'], '0')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'fixed.mxl'; path.write_bytes(fixed)
            loop.verify_semantics(path, receipts)

    def test_unchanged_segment_keeps_shapes_lyrics_and_ties_verbatim(self):
        first = note(extra='<tie type="start"/>')
        original = archive(first=first)
        fixed, receipts = loop.repair_archive(original, [[['C5', '1']]])
        self.assertFalse(receipts[0]['changed'])
        a, _ = loop.read_archive(original); b, _ = loop.read_archive(fixed)
        self.assertEqual(loop.canonical(a.find('./part/measure')), loop.canonical(b.find('./part/measure')))

    def test_replaced_note_decorations_are_audited_not_guessed(self):
        original = archive(first=note(extra='<notehead>fa</notehead><lyric><text>word</text></lyric>'))
        fixed, receipts = loop.repair_archive(original, [[['E5', '2']]])
        self.assertEqual(receipts[0]['rewrite']['removedNoteFields'], ['lyric', 'notehead'])
        self.assertIn('<lyric>', receipts[0]['rewrite']['originalMeasureXml'])
        root, _ = loop.read_archive(fixed)
        self.assertIsNone(root.find('./part/measure/note/lyric'))
        fields = {e.get('name'):e.text for e in root.findall('./identification/miscellaneous/miscellaneous-field')}
        self.assertEqual(fields['atlas-agent-loop-safe-to-promote'], 'false')

    def test_direction_absolute_anchor_is_not_silently_moved(self):
        direction = '<direction><direction-type><dynamics><p/></dynamics></direction-type></direction>'
        original = archive(first=note()+direction+note('D'))
        fixed, receipts = loop.repair_archive(original, [[['rest', '1'], ['E5', '2']]])
        root, _ = loop.read_archive(fixed)
        measure = root.find('./part/measure')
        self.assertEqual(loop.direction_anchors(measure, 2), [1])
        self.assertEqual(measure.findtext('direction/offset'), '-4')
        loop.verify_structure(original, fixed, receipts)

    def test_unsupported_source_is_quarantined_instead_of_inferred(self):
        for observations in [[[]], [[['H5','1']]], [[['C5','0']]], [[['C5','1/3']]]]:
            with self.subTest(observations=observations), self.assertRaises(ValueError):
                loop.repair_archive(archive(), observations)
        with self.assertRaisesRegex(ValueError, 'exceed draft'):
            loop.repair_archive(archive(), [[['C5','1']]]*4)
        with self.assertRaisesRegex(ValueError, 'Multi-staff'):
            loop.repair_archive(archive(attributes='<staves>2</staves>'), [[['E5','1']]])

    def test_wrong_root_member_and_scope_labels_fail_closed(self):
        original = archive()
        fixed, receipts = loop.repair_archive(original, [[['E5','2']]])
        root, member = loop.read_archive(fixed)
        root.find('./identification/miscellaneous/miscellaneous-field').text = 'accepted'
        with self.assertRaisesRegex(ValueError, 'quarantine/scope'):
            loop.verify_structure(original, loop.archive_copy(fixed,root,member), receipts)

    def test_immutable_artifact_replay_and_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'receipt.json'
            loop.immutable(path,b'original'); loop.immutable(path,b'original')
            with self.assertRaisesRegex(ValueError, 'Immutable artifact differs'):
                loop.immutable(path,b'changed')
            with self.assertRaisesRegex(ValueError, 'escapes local'):
                loop.resolve_local(Path(tmp), '../outside')

    def test_end_to_end_bound_inputs_replay_and_policy_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            work = base/'pilot'
            candidate = work/'candidate'
            candidate.mkdir(parents=True)
            raw = base/'raw.mxl'; raw.write_bytes(archive())
            source = base/'scan.jpg'; source.write_bytes(b'local source bytes')
            card = base/'crop.png'; card.write_bytes(b'local crop bytes')
            row = {'songNo':'1', 'title':'Fixture',
                   'image':{'path':str(source),'sha256':loop.digest(source)}}
            source_card = {'songNo':'1','sourceSha256':loop.digest(source),
                           'card':str(card),'cardSha256':loop.digest(card)}
            def save(path, value):
                path.write_bytes(loop.json_bytes(value))
            save(candidate/'dataset.json', {'records':[row]})
            save(candidate/'baseline-results.json', {'records':[{
                'songNo':'1','output':str(raw),'outputSha256':loop.digest(raw)}]})
            save(work/'review-selection.json', {'cards':[source_card]})
            save(work/'source-observations.json', {'sourceCards':[source_card],
                'expectedTopStaffMeasures':{'1':[[['rest','1'],['E5','1']]]}})
            # This fixture intentionally has NO label XML, proving the repair
            # cannot depend on an unreviewed candidate-reference answer key.
            bind = loop.bind_inputs
            with patch.object(loop, 'bind_inputs', side_effect=lambda p: bind(p,root=base)):
                out = base/'new-repair'
                report = loop.run(work, out)
                self.assertEqual(report['summary']['mismatchingSegmentsBefore'], 1)
                loop.verify(work,out)
                self.assertEqual(loop.run(work,out),report)
                for key, bad in [('safeToPromote',True), ('humanReviewRequired',True),
                                 ('summary', {**report['summary'],'wholeScoresAccepted':1})]:
                    changed=copy.deepcopy(report); changed[key]=bad
                    save(out/'report.json',changed)
                    with self.subTest(key=key), self.assertRaises(ValueError):
                        loop.verify(work,out)
                save(out/'report.json',report)
                tasks=json.loads((out/'agent-tasks.json').read_text())
                tasks['tasks'][0]['owner']='human';save(out/'agent-tasks.json',tasks)
                with self.assertRaisesRegex(ValueError,'ownership/cohort'):
                    loop.verify(work,out)
                source.write_bytes(b'changed source')
                with self.assertRaisesRegex(ValueError,'hash drift'):
                    loop.verify(work,out)
            self.assertEqual(raw.read_bytes(), archive())


if __name__ == '__main__':
    unittest.main()
