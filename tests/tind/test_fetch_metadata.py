"""
Test the TIND search and fetch functionality of Willa.
"""

import os
import unittest

# import xml.etree.ElementTree as ET
import requests_mock

from willa.errors import TINDError
from willa.tind import fetch
from . import setup_files


class TindSearchTest(unittest.TestCase):
    """Test the search methods of the willa.tind.fetch module."""
    def setUp(self) -> None:
        """Provide a fake Tind API key"""
        os.environ['TIND_API_KEY'] = 'Test_Key'

    def test_fetch_search_id(self) -> None:
        """fetch_ids_search should return a list of Tind ID's if there are results"""
        json_object = setup_files.setup_json('example_search_id.json')
        mock_array = [34059, 34060, 34061, 34062, 34063, 34064, 34065,
                      34066, 34067, 34068, 34069, 34070, 34071, 34072, 34073, 34074]
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/search', json=json_object)
            r = fetch.fetch_ids_search('980:"CalHer: LA Harbor"')

            self.assertEqual(r, mock_array)

#    def test_retrieve_xml_search_id(self):
#        """Test that a search_id and ElementTree are returned from an xml string"""
#        xml_string = self.setup_xml('example_fetch_metadata.xml')
#        xml, search_id = fetch._retrieve_xml_search_id(xml_string)
#
#        self.assertIsInstance(xml, ET.Element)
#        self.assertEqual(search_id, 'FGluY2x1ZGVfY29udGV4dF91dWlkDnF1ZXJ5VGhlbkZldGNoAhZZcnN1ck'
#                                    'hib1RxV1k2QTdIUVQzeFVRAAAAAAFYVTQWY3VZUi1tZW9TNGVGaWF5TnQ1'
#                                    'NWVhdxZfc0FSV1YzMVE5S0wtQy1La240M0pnAAAAAACO4YwWclV3TXdJR0'
#                                    '9RQkdxU3cxN2RXU2wyQQ==')

    def test_search_with_xml_format(self) -> None:
        """Test the search method with result_format='xml'."""
        response_xml = setup_files.setup_text_file('example_fetch_metadata.xml')
        response_no_records = setup_files.setup_text_file('example_no_records.xml')
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/search',
                       [{'text': response_xml}, {'text': response_no_records}])
            records = fetch.search('alligator', result_format='xml')

            self.assertEqual(len(records), 29)
            self.assertIn('<datafield tag="245"', records[5])

    def test_search_with_pymarc_format(self) -> None:
        """Test the search method with result_format='pymarc'."""
        response_xml = setup_files.setup_text_file('example_fetch_metadata.xml')
        response_no_records = setup_files.setup_text_file('example_no_records.xml')
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/search',
                       [{'text': response_xml}, {'text': response_no_records}])
            records = fetch.search('alligator', result_format='pymarc')

            self.assertEqual(len(records), 29)
            self.assertEqual(records[4]['245']['a'],
                             'The Simple Alligator Rider in Court of Pacifica')

    def test_search_error(self) -> None:
        """Test the search method with an error response."""
        error_resp = '{"error": "User guest is not authorized to perform runapi with parameters '\
                     'endpoint=search,operation=read"}'
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/search', status_code=403, text=error_resp)
            self.assertRaises(TINDError, fetch.search, 'alligator', result_format='pymarc')
