"""
Test the functionality of willa.tind.format_validata_pymarc 
"""
from io import StringIO
import unittest

from pymarc import parse_xml_to_array

from willa.tind import format_validate_pymarc
from . import setup_files


class TindFormatValidatePymarc(unittest.TestCase):
    """Tests the output of the willa.tind.format_validate_pymarc module."""

    def setUp(self):
        """Get a pymarc record for testing"""
        marc_xml = setup_files.setup_text_file('example_for_pymarc.xml')
        self.pymarc_records = parse_xml_to_array(StringIO(marc_xml))


    def test_expected_size(self):
        """Test that the returned result has the expected size"""
        result = format_validate_pymarc.parse_pymarc(self.pymarc_records[0])
        self.assertEqual(len(result), 15)


    def test_expected_values(self):
        """Test that source MARC fields with values are set properly"""
        result = format_validate_pymarc.parse_pymarc(self.pymarc_records[0])
        self.assertEqual(result['tind_id'], '19217')
        self.assertEqual(result['type'], 'Image')


    def test_missing_field_none(self):
        """Test that a required field that is not in source MARC is set to None"""
        result = format_validate_pymarc.parse_pymarc(self.pymarc_records[1])
        self.assertEqual(result['language'], None)


    def test_raises_exception(self):
        """Test that KeyError is raised if MARC is missing required fields""" 
        with self.assertRaises(KeyError):
            format_validate_pymarc.parse_pymarc(self.pymarc_records[2])


    def test_fields_with_indicators_and_subs(self):
        """Test that it properly retrieves fields with indicators and subfields specified"""
        result = format_validate_pymarc.parse_pymarc(self.pymarc_records[1])
        self.assertEqual(result['references'], 'https://oac.link.org')
        self.assertEqual(result['isPartOf'], 'Fritz-Metcalf Photograph Collection')
        self.assertEqual(result['date'], '1920')
        self.assertEqual(result['publisher'],
                        'Bioscience, Natural Resources & Public Health Library')


    def test_multiple_subfields_returns_array_of_values(self):
        """Test that multiple values will be an array for a given key"""      
        result = format_validate_pymarc.parse_pymarc(self.pymarc_records[0])
        self.assertIsInstance(result['subject'], list)
        self.assertEqual(result['subject'][1], 'Persea americana')
        self.assertEqual(len(result['subject']), 3)
