"""
Test the TIND fetch record functionality of Willa.
"""

import os
import unittest

import requests_mock
from willa.errors import RecordNotFoundError
from willa.tind import fetch


class TindFetchMetadataTest(unittest.TestCase):
    """Test the fetch_metadata method of the willa.tind.fetch module."""
    def setUp(self):
        os.environ['TIND_API_KEY'] = 'Test_Key'

    def test_fetch(self):
        """Test a simple record fetch."""
        record = os.path.join(os.path.dirname(__file__), 'example_record.xml')
        with open(record, encoding='UTF-8') as data_f:
            data = data_f.read()

        with requests_mock.mock() as r_mock:
            r_mock.get('https://digicoll.lib.berkeley.edu/api/v1/record/test/', text=data)
            record = fetch.fetch_metadata('test')

        self.assertEqual(record.title,
                         'Thalia Zepatos on Research and Messaging in Freedom to Marry')

    def test_invalid_record(self):
        """Ensure an error is raised when a record does not exist."""
        with requests_mock.mock() as r_mock:
            r_mock.get('https://digicoll.lib.berkeley.edu/api/v1/record/nothere/',
                       status_code=404)
            self.assertRaises(RecordNotFoundError, fetch.fetch_metadata, 'nothere')
