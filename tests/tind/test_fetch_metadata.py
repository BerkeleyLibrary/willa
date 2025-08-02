"""
Test the TIND fetch record functionality of Willa.
"""

import os
import unittest
import requests_mock
import json
from willa.tind import fetch
import xml.etree.ElementTree as ET


class TindFetchMetadataTest(unittest.TestCase):
    """Test the fetch_file_metadata method of the willa.tind.fetch module."""
    def setUp(self):
        os.environ['TIND_API_KEY'] = 'Test_Key'


    def setup_json(self, file):
        record = os.path.join(os.path.dirname(__file__), file)
        with open(record, encoding='UTF-8') as data_f:
            data = data_f.read()
        return json.loads(data)

    def setup_xml(self, file):
        record = os.path.join(os.path.dirname(__file__), file) 
        with open(record, encoding='UTF-8') as data_f:
            data = data_f.read()
        return data 

    """Verify that an xml string is returned"""
    def test_search_request(self):
        """Test a simple record fetch."""
        xml_string = self.setup_xml('example_fetch_metadata.xml')
        with requests_mock.mock() as r_mock:
            r_mock.get('https://digicoll.lib.berkeley.edu/api/v1/search', text=xml_string) 
            record = fetch.search_request('alligator')
            
        self.assertEqual(record, xml_string)

    """fetch_ids_search should return a list of Tind Id's if there are results"""
    def test_fetch_search_id(self):
        json_object = self.setup_json('example_search_id.json')
        mock_array = [34059, 34060, 34061, 34062, 34063, 34064, 34065, 34066, 34067, 34068, 34069, 34070, 34071, 34072, 34073, 34074]
        with requests_mock.mock() as r_mock:
            r_mock.get('https://digicoll.lib.berkeley.edu/api/v1/search', json=json_object) 
            r = fetch.fetch_ids_search('980:"CalHer: LA Harbor"')

        self.assertEqual(r, mock_array)

    """Test that a search_id and ElementTree are returned from an xml string"""
    def test_retrieve_xml_search_id(self):
        xml_string = self.setup_xml('example_fetch_metadata.xml')
        xml, search_id = fetch.retrieve_xml_search_id(xml_string)
       
        self.assertIsInstance(xml, ET.Element) 
        self.assertEqual(search_id, 'FGluY2x1ZGVfY29udGV4dF91dWlkDnF1ZXJ5VGhlbkZldGNoAhZZcnN1ckhib1RxV1k2QTdIUVQzeFVRAAAAAAFYVTQWY3VZUi1tZW9TNGVGaWF5TnQ1NWVhdxZfc0FSV1YzMVE5S0wtQy1La240M0pnAAAAAACO4YwWclV3TXdJR09RQkdxU3cxN2RXU2wyQQ==')
