"""
Test the TIND fetch record functionality of Willa.
"""
import os
import unittest

import requests_mock

from willa.errors import TINDError
from willa.tind import fetch
from . import setup_files

class TindFetchFileMetadataTest(unittest.TestCase):
    """Test the fetch_file_metadata method of the willa.tind.fetch module."""
    def setUp(self):
        """Create a fake Tind API key"""
        os.environ['TIND_API_KEY'] = 'Test_Key'

    def test_fetch_file_metadata(self):
        """Fetch a Tind record with a single file.
        verify list contains value and list has one value."""
        json_object = setup_files.setup_json('example_file_metadata_single.json')
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/record/219112/files', json=json_object)
            record = fetch.fetch_file_metadata('219112')

            # pylint: disable=line-too-long
            self.assertEqual(record[0]['url'],
                             'https://digicoll.lib.berkeley.edu/api/v1/record/219112/files/zepatos_thalia_2017.pdf/download/?version=1')
            # pylint: enable=line-too-long

            self.assertEqual(len(record), 1)

    def test_fetch_multiple_file_metadata(self):
        """Fetch a Tind record with multiple files and verify response contains a list of files."""
        json_object = setup_files.setup_json('example_file_metadata_multiple.json')
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/record/101218/files', json=json_object)
            record = fetch.fetch_file_metadata('101218')

            self.assertEqual(record[0]['url'],
                # pylint: disable=line-too-long
                'https://digicoll.lib.berkeley.edu/api/v1/record/101218/files/casl0010490010_ii.jpg/download/?version=1')
                # pylint: enable=line-too-long

            self.assertEqual(record[2]['url'],
                # pylint: disable=line-too-long
                'https://digicoll.lib.berkeley.edu/api/v1/record/101218/files/casl0010490030_ii.jpg/download/?version=1')
                # pylint: enable=line-too-long

            self.assertEqual(len(record), 10)

    def test_fetch_file_metadata_empty(self):
        """A record with no files should return and empty lists of file url's."""
        json_object = setup_files.setup_json('example_file_metadata_empty.json')
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/record/9810289/files', json=json_object)
            record = fetch.fetch_file_metadata('9810289')

            self.assertEqual(len(record), 0)

    def test_invalid_response(self):
        """Ensure an exception is raised when a record does not return 200."""
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/record/921923925/files', status_code='404',
                       text='{"Success": "False", "reason": "Not Found"}')
            self.assertRaises(Exception, fetch.fetch_file_metadata, '921923925')

    def test_fetch_file_metadata_tind_error(self):
        """Ensure a TINDError is raised when the Tind API returns an error response."""
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/record/123456/files', status_code=404,
                       text='{"Success": "False", "reason": "Internal Server Error"}')
            with self.assertRaises(TINDError):
                fetch.fetch_file_metadata('123456')
