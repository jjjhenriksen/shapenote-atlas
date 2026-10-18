from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import omr_stemless_analysis as analysis

class StemlessAnalysisTest(unittest.TestCase):
    def test_native_cautionary_duplicate_is_not_an_export_identity(self):
        sheet=ET.fromstring('<sheet><page><system><stack id="1" left="10" right="20"/><stack id="1" left="20" right="30" special="CAUTIONARY"/></system></page></sheet>')
        inspected={'segments':[dict(part=0,number='1',events=['retained'])]}
        with patch.object(analysis.audit,'inspect',return_value=inspected):
            self.assertEqual(analysis.span_inventory(sheet,None),{(0,10,20):['retained']})

    def test_duplicate_actual_export_identity_still_fails(self):
        sheet=ET.fromstring('<sheet><page><system><stack id="1" left="10" right="20"/><stack id="1" left="20" right="30"/></system></page></sheet>')
        with self.assertRaisesRegex(ValueError,'Ambiguous'):
            analysis.span_inventory(sheet,None)

    def test_cautionary_only_export_reference_cannot_be_dropped(self):
        sheet=ET.fromstring('<sheet><page><system><stack id="1" left="10" right="20" special="CAUTIONARY"/></system></page></sheet>')
        inspected={'segments':[dict(part=0,number='1',events=['extra'])]}
        with patch.object(analysis.audit,'inspect',return_value=inspected):
            with self.assertRaisesRegex(ValueError,'without physical span'):
                analysis.span_inventory(sheet,None)

if __name__ == '__main__':unittest.main()
