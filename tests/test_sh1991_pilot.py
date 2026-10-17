"""Clone-safe pilot scoring tests: actual XML timing, missing/extra notes and gates."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sh1991_pilot import score, compare, original_image_url, align, validate_dataset
from sh1991_staff_probe import single_part, staff_bounds
from xml.etree import ElementTree as ET


def xml(notes, divisions=1, name='Tenor'):
    return (f'<score-partwise><part-list><score-part id="P1"><part-name>{name}</part-name></score-part></part-list>'
            f'<part id="P1"><measure number="0"><attributes><divisions>{divisions}</divisions></attributes>{notes}</measure></part></score-partwise>').encode()

def note(step='C', octave=4, duration=1, extra=''):
    return f'<note>{extra}<pitch><step>{step}</step><octave>{octave}</octave></pitch><duration>{duration}</duration></note>'

class PilotScoringTest(unittest.TestCase):
    def test_normalizes_divisions_and_does_not_score_part_name_as_music(self):
        a=score(xml(note(duration=1),1,'Tenor'));b=score(xml(note(duration=4),4,'Voice 1'))
        result=compare(a,b)
        self.assertTrue(result['exactWrittenEvents'])
        self.assertEqual(result['counts']['durationMatches'],1)

    def test_insertions_are_not_truncated_or_mistaken_for_every_later_note(self):
        a=score(xml(note('C')+note('D')+note('E')))
        b=score(xml(note('C')+note('G')+note('D')+note('E')))
        result=compare(a,b)['counts']
        self.assertEqual(result['insertions'],1)
        self.assertEqual(result['pitchMatches'],3)
        self.assertEqual(result['observedPitched'],4)
        self.assertEqual(result['onsetMatches'],1)

    def test_deletions_and_missing_parts_keep_reference_mass(self):
        a=score(xml(note('C')+note('D')));b=score(xml(note('C')))
        result=compare(a,b)
        self.assertEqual(result['counts']['deletions'],1)
        self.assertEqual(result['counts']['referencePitched'],2)
        a['parts'].append(a['parts'][0]);result=compare(a,b)
        self.assertFalse(result['partCountMatch'])
        self.assertEqual(result['counts']['referencePitched'],4)
        self.assertEqual(result['counts']['deletions'],3)

    def test_octave_errors_are_not_pitch_matches(self):
        r=compare(score(xml(note(octave=4))),score(xml(note(octave=5))))
        self.assertEqual(r['counts'].get('pitchMatches',0),0)
        self.assertEqual(r['counts']['durationMatches'],1)

    def test_backup_and_chords_preserve_rational_onsets(self):
        p=score(xml(note('C',duration=2)+note('E',duration=2,extra='<chord/>')+
                    '<backup><duration>2</duration></backup>'+note('G',duration=1),2))['parts'][0]
        self.assertEqual([e['onset'] for e in p['events']],['0','0','0'])
        self.assertEqual(p['measureDurations'],['1'])

    def test_invalid_durations_and_negative_backups_fail_closed(self):
        with self.assertRaises(ValueError):score(xml(note(duration=0)))
        with self.assertRaises(ValueError):score(xml('<backup><duration>1</duration></backup>'+note()))

    def test_original_page_picker_rejects_foreign_or_ambiguous_images(self):
        base='https://sh1991.sacredharpbremen.org/26'
        url='https://sh1991.sacredharpbremen.org/wp-content/uploads/songs/001-099/026-Samaria/26-Samaria.jpg'
        self.assertEqual(original_image_url(f'<a href="{url}"><img src="{url}"></a>',base),url)
        with self.assertRaises(ValueError):original_image_url('<img src="https://sacredharpbremen.org/wp-content/uploads/songs/26.jpg">',base)
        with self.assertRaises(ValueError):original_image_url(f'<a href="{url}"></a><img src="{url.replace("26-Samaria.jpg","27.jpg")}">',base)

    def test_empty_alignment_does_not_drop_predicted_events(self):
        self.assertEqual(align([], [{'pitch':['C','0',4],'duration':'1'}]),[(None,0)])

    def test_known_group_leakage_and_duplicate_ids_fail_before_reading_sources(self):
        # Empty source fields: duplicate/split checks must fail before source I/O.
        first={'songNo':'1','split':'train','group':'g'}
        # Use a real tiny, hashed file for the first accepted record.
        import tempfile, hashlib
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'tiny';path.write_bytes(b'tiny')
            first.update(image={'path':str(path),'sha256':hashlib.sha256(b'tiny').hexdigest()},
                         label={'path':str(path),'sha256':hashlib.sha256(b'tiny').hexdigest()})
            with self.assertRaisesRegex(ValueError,'group split leakage'):
                validate_dataset({'records':[first,{**first,'songNo':'2','split':'test'}]})
            with self.assertRaisesRegex(ValueError,'duplicate record ID'):
                validate_dataset({'records':[first,first]})

    def test_part_extraction_retains_only_requested_music_and_part_metadata(self):
        root=ET.fromstring(xml(note('C')))
        second=ET.SubElement(root.find('part-list'),'score-part',id='P2')
        ET.SubElement(second,'part-name').text='Bass'
        part=ET.SubElement(root,'part',id='P2');measure=ET.SubElement(part,'measure',number='0')
        measure.append(ET.fromstring(note('G',octave=3)))
        data=ET.tostring(root)
        result=score(single_part(data,1))
        self.assertEqual(result['parts'],[score(data)['parts'][1]])
        self.assertEqual(len(ET.fromstring(single_part(data,1)).findall('./part-list/score-part')),1)

    def test_geometry_preserves_staff_margins_and_rejects_wrong_frame_or_count(self):
        sheet=ET.Element('sheet');ET.SubElement(sheet,'picture',width='300',height='400')
        system=ET.SubElement(ET.SubElement(sheet,'page'),'system')
        for top in (80,240):
            staff=ET.SubElement(ET.SubElement(system,'part'),'staff');lines=ET.SubElement(staff,'lines')
            for y in range(top,top+41,10):
                line=ET.SubElement(lines,'line');ET.SubElement(line,'point',x='0',y=str(y))
        self.assertEqual(staff_bounds(sheet,300,400,2),[[[0,40,300,160]],[[0,200,300,320]]])
        with self.assertRaises(ValueError):staff_bounds(sheet,300,400,4)
        with self.assertRaises(ValueError):staff_bounds(sheet,301,400,2)

if __name__=='__main__':unittest.main()
