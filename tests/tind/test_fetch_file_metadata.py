"""
Test the TIND fetch record functionality of Willa.
"""

import os
import unittest
import json

import requests_mock
from willa.errors import RecordNotFoundError
from willa.tind import fetch


class TindFetchFileMetadataTest(unittest.TestCase):
    """Test the fetch_file_metadata method of the willa.tind.fetch module."""
    def setUp(self):
        os.environ['TIND_API_KEY'] = 'Test_Key'

    def test_fetch_file_metadata(self):
        """Test a simple record fetch."""
        record = os.path.join(os.path.dirname(__file__), 'example_file_metadata_single.json')
        with open(record, encoding='UTF-8') as data_f:
            data = data_f.read()
        json_object = json.loads(data)
        with requests_mock.mock() as r_mock:
            r_mock.get('https://digicoll.lib.berkeley.edu/api/v1/record/219112/files', json=json_object)
            record = fetch.fetch_file_metadata('219112')

        self.assertEqual(record[0]['url'],
                         'https://digicoll.lib.berkeley.edu/api/v1/record/219112/files/zepatos_thalia_2017.pdf/download/?version=1')

    def test_fetch_multiple_file_metadata(self):
        """Test a simple record fetch."""
        record = os.path.join(os.path.dirname(__file__), 'example_file_metadata_multiple.json')
        with open(record, encoding='UTF-8') as data_f:
            data = data_f.read()
        json_object = json.loads(data)
        with requests_mock.mock() as r_mock:
            r_mock.get('https://digicoll.lib.berkeley.edu/api/v1/record/101218/files', json=json_object)
            record = fetch.fetch_file_metadata('101218')

        self.assertEqual(record[0]['url'],
          'https://digicoll.lib.berkeley.edu/api/v1/record/101218/files/casl0010490010_ii.jpg/download/?version=1')

        self.assertEqual(record[2]['url'],
          'https://digicoll.lib.berkeley.edu/api/v1/record/101218/files/casl0010490030_ii.jpg/download/?version=1')

        self.assertEqual(len(record), 10)

    def test_fetch_file_metadata_empty(self):
        """Test a simple record fetch."""
        record = os.path.join(os.path.dirname(__file__), 'example_file_metadata_empty.json')
        with open(record, encoding='UTF-8') as data_f:
            data = data_f.read()
        json_object = json.loads(data)
        with requests_mock.mock() as r_mock:
            r_mock.get('https://digicoll.lib.berkeley.edu/api/v1/record/9810289/files', json=json_object)
            record = fetch.fetch_file_metadata('9810289')

        self.assertEqual(len(record), 0)

    def test_invalid_response(self):
        """Ensure an exception is raised when a record does not return 200."""
        with requests_mock.mock() as r_mock:
            r_mock.get('https://digicoll.lib.berkeley.edu/api/v1/record/9219239e25/files', status_code='404',
                       text='{"success": false, "reason": "Not Found"}')
            self.assertRaises(Exception, fetch.fetch_file_metadata, '9219239e25')
