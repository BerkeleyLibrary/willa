"""
Test the functionality of willa.tind.format_tind_context
"""

from io import StringIO
from unittest.mock import Mock
import unittest

from pymarc import parse_xml_to_array

from willa.tind import format_tind_context
from willa.tind import format_validate_pymarc
from . import setup_files


class TindFormatValidatePymarc(unittest.TestCase):
    """Tests the output of the willa.tind.format_validate_pymarc module."""

    def setUp(self) -> None:
        """Get a pymarc record for testing"""
        marc_xml = setup_files.setup_text_file('example_billups.xml')
        self.pymarc_records = parse_xml_to_array(StringIO(marc_xml))
        self.tind_dict = format_validate_pymarc.pymarc_to_metadata(self.pymarc_records[0])

    def test_process_fields(self) -> None:
        """Test array in pymarc metadata dictonary is separated into newlines."""
        result = format_tind_context.process_fields(self.tind_dict)
        
        self.assertIn("Contributor: Meeker, Martin interviewer.\n", result)
        self.assertIn("Contributor: Billups, Richard,  1943- interviewee.\n", result)
