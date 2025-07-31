"""
Test the low-level TIND API functionality of Willa.
"""

import os
import unittest

import requests_mock
from willa.errors import AuthorizationError
from willa.tind import api


class TindApiGetTest(unittest.TestCase):
    """Test the tind_get method of the willa.tind.api module."""
    def setUp(self):
        os.environ['TIND_API_KEY'] = 'Test_Key'
        os.environ['TIND_API_URL'] = 'https://ucb.tind.example/api/v1'

    def test_url_building(self):
        """Ensure URL building works correctly."""
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/test', text='Example')
            self.assertEqual(api.tind_get('test'), (200, 'Example'))

    def test_url_config(self):
        """Ensure that changing the config changes the URL."""
        os.environ['TIND_API_URL'] = 'https://berkeley-test.tind.io/api/v1'
        with requests_mock.mock() as r_mock:
            r_mock.get('https://berkeley-test.tind.io/api/v1/test', text='Example')
            self.assertEqual(api.tind_get('test'), (200, 'Example'))

    def test_param_passing(self):
        """Ensure that params are passed correctly to API endpoints."""
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/test', text='Example')
            api.tind_get('test', {'param1': 'testing'})
            self.assertEqual(r_mock.last_request.qs, {'param1': ['testing']})

    def test_key(self):
        """Ensure that the TIND API key is passed properly."""
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/test', text='Example')
            api.tind_get('test')
            headers = r_mock.last_request.headers
            self.assertIn('Authorization', headers)
            self.assertEqual('Token Test_Key', headers['Authorization'])

    def test_without_key(self):
        """Ensure that an error is raised when the TIND API key is missing."""
        del os.environ['TIND_API_KEY']
        self.assertRaises(AuthorizationError, api.tind_get, 'test')

    def test_invalid_key(self):
        """Ensure that an error is raised when an invalid TIND API key is provided."""
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/test', status_code=401)
            self.assertRaises(AuthorizationError, api.tind_get, 'test')
