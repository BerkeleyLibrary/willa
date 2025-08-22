"""
Test the functionality of willa.tind.format_tind_context
"""

import os
from io import StringIO
import unittest

from pymarc import parse_xml_to_array

from willa.tind import format_tind_context
from willa.tind import format_validate_pymarc
from willa.etl.doc_proc import load_pdf
from . import setup_files


class TindFormatValidatePymarc(unittest.TestCase):
    """Tests the output of the willa.tind.format_validate_pymarc module."""

    def setUp(self) -> None:
        """Get a pymarc record for testing"""

        marc_xml = setup_files.setup_text_file('example_billups.xml')
        self.pymarc_records = parse_xml_to_array(StringIO(marc_xml))
        self.tind_dict = format_validate_pymarc.pymarc_to_metadata(self.pymarc_records[0])


    def test_process_fields(self) -> None:
        """Test that Tind record is parsed with formatted fields""" 

        result = format_tind_context.process_fields(self.tind_dict)

        self.assertIn("Contributor: Meeker, Martin interviewer.\n", result)
        self.assertIn("Contributor: Billups, Richard,  1943- interviewee.\n", result)


    def test_format_tind_context(self) -> None:
        """Chatbot document with associated Tind Metadata should return formatted Tind data"""  

        docs = load_pdf(os.path.join(os.path.dirname(__file__), 'billups_rich.pdf'),
                        self.pymarc_records[0])
        tind_context = format_tind_context.get_tind_context(docs)

        self.assertIn('Tind ID: 103508', tind_context)
        self.assertIn('Catalogue Link: https://digicoll.lib.berkeley.edu/record/103508',
                      tind_context)

    def test_get_tind_url(self) -> None:
        """A Tind ID should return a Url to a Tind record"""

        tind_url = format_tind_context.get_tind_url(103508)
        self.assertEqual('https://digicoll.lib.berkeley.edu/record/103508', tind_url)
