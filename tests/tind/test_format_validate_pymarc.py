"""
Test the functionality of willa.tind.format_validata_pymarc.
"""

from io import StringIO
from unittest.mock import Mock
import unittest

from pymarc import parse_xml_to_array

from willa.tind import format_validate_pymarc
from . import setup_files


class TindFormatValidatePymarc(unittest.TestCase):
    """Tests the output of the willa.tind.format_validate_pymarc module."""

    def setUp(self) -> None:
        """Get a PyMARC record for testing."""
        marc_xml = setup_files.setup_text_file('example_for_pymarc.xml')
        self.pymarc_records = parse_xml_to_array(StringIO(marc_xml))

    def test_expected_size(self) -> None:
        """Test that the returned result has the expected size."""
        result = format_validate_pymarc.parse_pymarc(self.pymarc_records[0])
        self.assertEqual(len(result), 22)

    def test_expected_values(self) -> None:
        """Test that source MARC fields with values are set properly."""
        result = format_validate_pymarc.parse_pymarc(self.pymarc_records[0])
        self.assertEqual(result['001'], '19217')
        self.assertEqual(result['336'], 'Image')

    def test_missing_field_none(self) -> None:
        """Test that a required field that is not in source MARC is set to None."""
        result = format_validate_pymarc.parse_pymarc(self.pymarc_records[1])
        self.assertEqual(result['600'], None)
        self.assertEqual(result['041'], None)

    def test_raises_exception(self) -> None:
        """Test that KeyError is raised if MARC is missing required fields."""
        with self.assertRaises(KeyError):
            format_validate_pymarc.parse_pymarc(self.pymarc_records[2])

    def test_fields_with_indicators_and_subs(self) -> None:
        """Test that it properly retrieves fields with indicators and subfields specified."""
        result = format_validate_pymarc.parse_pymarc(self.pymarc_records[1])
        self.assertEqual(result['85642u'], 'https://oac.link.org')
        self.assertEqual(result['982__b'], 'Fritz-Metcalf Photograph Collection')
        self.assertEqual(result['260__c'], '1920')
        self.assertEqual(result['852__c'], 'Bioscience, Natural Resources & Public Health Library')

    def test_multiple_subfields_returns_array_of_values(self) -> None:
        """Test that multiple values will be an array for a given key."""
        result = format_validate_pymarc.parse_pymarc(self.pymarc_records[0])
        self.assertIsInstance(result['650'], list)
        self.assertEqual(result['650'][1], 'Persea americana')
        self.assertEqual(len(result['650']), 3)

    def test_metadata_simple(self) -> None:
        """Test parsing of a simple record into metadata."""
        result = format_validate_pymarc.pymarc_to_metadata(self.pymarc_records[0])
        self.assertEqual(result['tind_id'], '19217')
        self.assertListEqual(result['subject'], ['Ranches', 'Persea americana', 'Agriculture'])

    def test_metadata_multi_subject(self) -> None:
        """Test parsing of a record that has multiple subject codes."""
        parse_pymarc = format_validate_pymarc.parse_pymarc
        format_validate_pymarc.parse_pymarc = Mock(return_value={
            '001': '19217', '336': 'Image', '650': ['Ranches', 'Persea americana', 'Agriculture'],
            '610': 'Testing'
        })

        result = format_validate_pymarc.pymarc_to_metadata(self.pymarc_records[0])
        self.assertEqual(result['tind_id'], '19217')
        self.assertListEqual(result['subject'], ['Ranches', 'Persea americana', 'Agriculture',
                                                 'Testing'])

        format_validate_pymarc.parse_pymarc = parse_pymarc

    def test_metadata_multi_lists(self) -> None:
        """Test what happens when the metadata has two lists in the MARC record."""
        parse_pymarc = format_validate_pymarc.parse_pymarc
        format_validate_pymarc.parse_pymarc = Mock(return_value={
            '001': '19217', '336': 'Image', '650': ['Ranches', 'Persea americana', 'Agriculture'],
            '610': ['Element 1', 'Element 2']
        })

        result = format_validate_pymarc.pymarc_to_metadata(self.pymarc_records[0])
        self.assertEqual(result['tind_id'], '19217')
        self.assertListEqual(result['subject'], ['Ranches', 'Persea americana', 'Agriculture',
                                                 'Element 1', 'Element 2'])

        format_validate_pymarc.parse_pymarc = parse_pymarc

    def test_metadata_multi_none(self) -> None:
        """Test what happens when a metadata key list is followed by None."""
        parse_pymarc = format_validate_pymarc.parse_pymarc
        format_validate_pymarc.parse_pymarc = Mock(return_value={
            '001': '19217', '336': 'Image', '650': ['Ranches', 'Persea americana', 'Agriculture'],
            '610': None
        })

        result = format_validate_pymarc.pymarc_to_metadata(self.pymarc_records[0])
        self.assertEqual(result['tind_id'], '19217')
        self.assertListEqual(result['subject'], ['Ranches', 'Persea americana', 'Agriculture'])

        format_validate_pymarc.parse_pymarc = parse_pymarc
