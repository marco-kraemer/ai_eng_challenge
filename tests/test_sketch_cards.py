import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

class SketchTests(unittest.TestCase):
    def test_category_art_is_monochrome_line_study(self):
        root=ET.parse('app/static/instruments.svg').getroot()
        self.assertEqual(root.attrib.get('data-style'),'ink-study')
        self.assertFalse(root.findall('.//{http://www.w3.org/2000/svg}linearGradient'))
        for node in root.iter():
            self.assertNotIn('url(#wood)',node.attrib.get('fill',''))
