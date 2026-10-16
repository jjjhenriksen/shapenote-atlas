"""Clone-safe failure-mode tests; source accuracy is not inferred from fixtures."""
from collections import Counter
import copy
from pathlib import Path
import sys
import unittest
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_score_audit as audit
import omr_source_repair as repair
import sh1991_symbol_classifier as classifier


def note(step='C', duration=1, kind='quarter', extra='', voice=1):
    return (f'<note><pitch><step>{step}</step><octave>5</octave></pitch>'
            f'<duration>{duration}</duration><voice>{voice}</voice><type>{kind}</type>{extra}</note>')


def score(content=None, second=None, attrs=''):
    if content is None:
        content = note()
    measures = ('<measure number="1"><attributes><divisions>1</divisions>'
                '<time><beats>4</beats><beat-type>4</beat-type></time>' + attrs + '</attributes>' + content + '</measure>')
    if second is not None:
        measures += '<measure number="2">'+second+'</measure>'
    return ET.fromstring('<score-partwise><part id="P1">'+measures+'</part></score-partwise>')


def observations(events=None):
    return {'expectedMeasuresPerPart': [1], 'independent': False, 'segments': [
        {'part': 0, 'measure': 0, 'cropBox': [0, 0, 100, 100], 'events': events or [['C5', '1']],
         'absentMarkings': ['dynamics', 'articulations', 'ornaments']}]}


class StructureTest(unittest.TestCase):
    def test_rational_tuplet_dotted_duration(self):
        xml = score(note(duration=3, kind='half', extra='<dot/>'))
        self.assertNotIn('symbol-duration-conflict', audit.inspect(xml)['findingCounts'])
        xml = score(note(duration='2', extra='<time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>'))
        xml.find('.//divisions').text = '3'
        self.assertNotIn('symbol-duration-conflict', audit.inspect(xml)['findingCounts'])

    def test_parallel_voices_not_summed_as_overflow(self):
        xml = score(note(duration=4, kind='whole')+'<backup><duration>4</duration></backup>'+note('E', 4, 'whole', voice=2))
        result = audit.inspect(xml)
        self.assertNotIn('overfull-voice', result['findingCounts'])
        self.assertEqual([r['onset'] for r in result['segments'][0]['events']], ['0', '0'])

    def test_real_overflow_and_symbol_conflict(self):
        result = audit.inspect(score(note(duration=5)))
        self.assertEqual(result['findingCounts']['overfull-voice'], 1)
        self.assertEqual(result['findingCounts']['symbol-duration-conflict'], 1)

    def test_short_pickup_is_review_not_fabricated_rest(self):
        xml = score(note())
        before = ET.tostring(xml)
        result = audit.inspect(xml)
        self.assertEqual(result['findings'][0]['kind'], 'short-measure-review')
        self.assertTrue(result['findings'][0]['partialHint'])
        self.assertEqual(ET.tostring(xml), before)

    def test_duplicate_notes_are_not_collapsed_by_evaluator(self):
        event = audit.source_events(observations()['segments'][0])[0]
        self.assertEqual(sum(audit.errors([event], [event, event]).values()), 1)

    def test_chord_without_anchor_fails(self):
        with self.assertRaisesRegex(ValueError, 'Chord'):
            audit.inspect(score(note(extra='<chord/>')))

    def test_tie_orphans_are_reported(self):
        result = audit.inspect(score(note(extra='<tie type="stop"/>')+note('E', extra='<tie type="start"/>')))
        self.assertEqual(result['findingCounts']['orphan-tie-stop'], 1)
        self.assertEqual(result['findingCounts']['unclosed-tie-start'], 1)


class RepairTest(unittest.TestCase):
    def test_missing_bar_cannot_shift_comparison_silently(self):
        obs = observations()
        obs['expectedMeasuresPerPart'] = [2]
        obs['segments'].append({**copy.deepcopy(obs['segments'][0]), 'measure': 1})
        with self.assertRaisesRegex(ValueError, 'explicit reviewed measure map'):
            repair.repair(score(), obs)
        corrected, result = repair.repair(score(), obs, [[0, None]])
        self.assertEqual(audit.inspect(corrected)['measureCounts'], [2])
        self.assertEqual(result['checkedStaffMeasures'], 2)

    def test_duplicate_or_discarded_draft_measure_map_fails(self):
        obs = observations()
        for mapping, actual in [([[0, 0]], [1]), ([[1]], [2]), ([[True]], [1])]:
            with self.assertRaises(ValueError):
                audit.measure_map(obs, actual, mapping)

    def test_partial_or_duplicate_source_coverage_fails(self):
        obs = observations()
        obs['segments'] *= 2
        with self.assertRaisesRegex(ValueError, 'coverage'):
            repair.repair(score(), obs)

    def test_removes_false_marks_not_other_directions_and_keeps_exact_note(self):
        extra = '<notehead>fa</notehead><notations><articulations><staccato/></articulations><fermata/></notations><lyric><text>keep</text></lyric>'
        direction = '<direction><direction-type><dynamics><sf/></dynamics><words>keep words</words></direction-type><sound dynamics="80" tempo="90"/></direction>'
        original = score(note(extra=extra)+direction)
        before = ET.tostring(original)
        fixed, result = repair.repair(original, observations())
        self.assertEqual(ET.tostring(original), before)
        self.assertEqual(fixed.findtext('.//lyric/text'), 'keep')
        self.assertEqual(fixed.findtext('.//notehead'), 'fa')
        self.assertIsNotNone(fixed.find('.//fermata'))
        self.assertIsNone(fixed.find('.//articulations'))
        self.assertIsNone(fixed.find('.//dynamics'))
        self.assertEqual(fixed.findtext('.//words'), 'keep words')
        self.assertEqual(fixed.find('.//sound').get('tempo'), '90')
        self.assertIsNone(fixed.find('.//sound').get('dynamics'))
        self.assertEqual(result['summary']['beforeUnsupportedMarkings'], 2)
        self.assertEqual(result['summary']['afterUnsupportedMarkings'], 0)

    def test_fix_count_and_introduced_error_count_are_distinct(self):
        obs = observations([['C5', '1'], ['D5', '1']])
        before = audit.inspect(score(note()+note('E')))
        # Fix E->D, but delete the previously correct C: one removed error,
        # plus a newly introduced missing event; never net these away.
        after = audit.inspect(score('<forward><duration>1</duration></forward>'+note('D')))
        result = audit.evaluate(obs, before, after)
        self.assertEqual(result['summary']['errorsRemoved'], 2)
        self.assertEqual(result['summary']['errorsIntroduced'], 1)
        self.assertFalse(result['independentSourceGold'])

    def test_new_rest_preserves_matching_note_lyrics(self):
        original = score(note(extra='<lyric><text>word</text></lyric>'))
        fixed, result = repair.repair(original, observations([['rest', '2'], ['C5', '1']]))
        self.assertEqual(fixed.findtext('.//lyric/text'), 'word')
        self.assertEqual(result['summary']['afterMatching'], 2)
        self.assertEqual(result['summary']['errorsIntroduced'], 0)
        self.assertFalse(result['wholeScoreAcceptance'])

    def test_exact_no_change_measure_preserved_except_explicit_number(self):
        original = score(note(extra='<notehead>diamond</notehead><lyric><text>word</text></lyric>'))
        fixed, _ = repair.repair(original, observations())
        self.assertEqual(ET.tostring(original.find('./part/measure')), ET.tostring(fixed.find('./part/measure')))

    def test_matching_encoded_duration_cannot_hide_wrong_written_type(self):
        original = score(note(duration=2, kind='quarter', extra='<lyric><text>keep</text></lyric>'))
        fixed, result = repair.repair(original, observations([['C5', '2']]))
        self.assertEqual(fixed.findtext('.//note/type'), 'half')
        self.assertEqual(fixed.findtext('.//lyric/text'), 'keep')
        self.assertNotIn('symbol-duration-conflict', result['afterStructure'])

    def test_missing_opening_attributes_not_guessed(self):
        obs = observations()
        obs['expectedMeasuresPerPart'] = [2]
        obs['segments'].append({**copy.deepcopy(obs['segments'][0]), 'measure': 1})
        with self.assertRaisesRegex(ValueError, 'source attribute map'):
            repair.repair(score(), obs, [[None, 0]])

    def test_source_ties_not_guessed_from_adjacent_same_pitch(self):
        obs = observations([['C5', '1'], ['C5', '1']])
        obs['ties'] = []
        original = score(note(extra='<tie type="start"/>')+note(extra='<tie type="stop"/>'))
        fixed, result = repair.repair(original, obs)
        self.assertEqual(audit.score_ties(fixed), Counter())
        self.assertEqual(result['ties']['errorsRemoved'], 2)
        self.assertEqual(result['ties']['errorsIntroduced'], 0)

    def test_explicit_source_ties_added_and_bad_pitches_rejected(self):
        obs = observations([['C5', '1'], ['C5', '1']])
        obs['ties'] = [{'part': 0, 'fromMeasure': 0, 'fromNote': 0, 'toMeasure': 0, 'toNote': 1}]
        fixed, result = repair.repair(score(note()+note()), obs)
        self.assertEqual(result['ties']['afterMatching'], 2)
        self.assertEqual(len(fixed.findall('.//notations/tied')), 2)
        obs['segments'][0]['events'][1][0] = 'D5'
        with self.assertRaisesRegex(ValueError, 'tie pitches'):
            repair.repair(score(note()+note()), obs)

    def test_multistaff_and_grace_edits_fail_closed(self):
        for xml in [score(attrs='<staves>2</staves>'), score(note(extra='<grace/>'))]:
            with self.assertRaises(ValueError):
                repair.repair(xml, observations())


class ClassifierSplitTest(unittest.TestCase):
    def test_nearby_crops_stay_together(self):
        rows = [{'id': str(i), 'songNo': page, 'sourceSha256': page} for i, page in enumerate(['a', 'a', 'b', 'c'])]
        for page, train, test in classifier.grouped_folds(rows):
            self.assertTrue(all(r['songNo'] != page for r in train))
            self.assertTrue(all(r['songNo'] == page for r in test))

    def test_source_alias_leakage_and_duplicate_samples_rejected(self):
        for rows in [[{'id': '1', 'songNo': 'a', 'sourceSha256': 'same'}, {'id': '2', 'songNo': 'b', 'sourceSha256': 'same'}],
                     [{'id': '1', 'songNo': 'a', 'sourceSha256': 'a'}, {'id': '1', 'songNo': 'b', 'sourceSha256': 'b'}]]:
            with self.assertRaises(ValueError):
                list(classifier.grouped_folds(rows))


if __name__ == '__main__':
    unittest.main()
