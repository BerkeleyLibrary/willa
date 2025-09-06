"""
Test the TIND fetch record functionality of Willa.
"""

import os.path
import pathlib
import tempfile
import unittest

import requests_mock
from willa.config import CONFIG
from willa.errors import AuthorizationError, RecordNotFoundError
from willa.tind import fetch


class TindFetchMetadataTest(unittest.TestCase):
    """Test the fetch_metadata method of the willa.tind.fetch module."""
    def setUp(self) -> None:
        CONFIG['TIND_API_KEY'] = 'Test_Key'
        CONFIG['TIND_API_URL'] = 'https://ucb.tind.example/api/v1'

    def test_fetch(self) -> None:
        """Test a simple record fetch."""
        rec_data = os.path.join(os.path.dirname(__file__), 'example_record.xml')
        with open(rec_data, encoding='UTF-8') as data_f:
            data = data_f.read()

        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/record/test/', text=data)
            record = fetch.fetch_metadata('test')

        self.assertEqual(record.title,
                         'Thalia Zepatos on Research and Messaging in Freedom to Marry')

    def test_invalid_record(self) -> None:
        """Ensure an error is raised when a record does not exist and the response is a 404."""
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/record/nothere/',
                       status_code=404)
            self.assertRaises(RecordNotFoundError, fetch.fetch_metadata, 'nothere')

    def test_empty_record(self) -> None:
        """Ensure an error is raised when a record does not exist and the response is empty."""
        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/record/99999999/',
                       text=' \n')
            self.assertRaises(RecordNotFoundError, fetch.fetch_metadata, '99999999')


class TindFetchFileTest(unittest.TestCase):
    """Test the fetch_file method of the willa.tind.fetch module."""
    def setUp(self) -> None:
        CONFIG['TIND_API_KEY'] = 'Test_Key'
        CONFIG['TIND_API_URL'] = 'https://ucb.tind.example/api/v1'
        CONFIG['DEFAULT_STORAGE_DIR'] = tempfile.mkdtemp(prefix='willatest')

    def test_file_fetch(self) -> None:
        """Test a simple file fetch."""
        dl_path = 'https://ucb.tind.example/api/v1/record/1234/files/test.txt/download/'
        expected = 'Hello world, from Python\n'

        with requests_mock.mock() as r_mock:
            r_mock.get(dl_path, text=expected)
            fetch.fetch_file(dl_path)

        path = pathlib.Path(CONFIG['DEFAULT_STORAGE_DIR'], 'test.txt')
        self.assertTrue(path.is_file(), 'File should be saved to default path')
        self.assertEqual(path.read_text(encoding='utf-8'), expected,
                         'File should have expected contents')
        path.unlink()

    def test_file_fetch_with_name(self) -> None:
        """Test a file fetch ensuring the TIND-returned name is used."""
        dl_path = 'https://ucb.tind.example/api/v1/record/1234/files/notthisname.txt/download/'
        expected = 'Hello world, from Python\n'

        with requests_mock.mock() as r_mock:
            r_mock.get(dl_path, text=expected,
                       headers={'Content-Disposition': 'attachment; filename="usethis.txt"'})
            fetch.fetch_file(dl_path)

        path = pathlib.Path(CONFIG['DEFAULT_STORAGE_DIR'], 'notthisname.txt')
        self.assertFalse(path.is_file(), 'File should be saved to correct name')
        path = pathlib.Path(CONFIG['DEFAULT_STORAGE_DIR'], 'usethis.txt')
        self.assertTrue(path.is_file(), 'File should be saved to correct name')
        self.assertEqual(path.read_text(encoding='utf-8'), expected,
                         'File should have expected contents')
        path.unlink()

    def test_fetch_to_custom_path(self) -> None:
        """Test a file fetch to a custom path instead of the default."""
        with tempfile.TemporaryDirectory(prefix='willa2') as custom_path:
            dl_path = 'https://ucb.tind.example/api/v1/record/1234/files/custom.txt/download/'
            expected = 'Fetched to a custom path\n'

            with requests_mock.mock() as r_mock:
                r_mock.get(dl_path, text=expected)
                fetch.fetch_file(dl_path, custom_path)

            path = pathlib.Path(CONFIG['DEFAULT_STORAGE_DIR'], 'custom.txt')
            self.assertFalse(path.is_file(), 'File should not be saved in default path')

            path = pathlib.Path(custom_path, 'custom.txt')
            self.assertTrue(path.is_file(), 'File should be saved in custom path')
            self.assertEqual(path.read_text(encoding='utf-8'), expected,
                             'File should have expected contents')
            path.unlink()

    def test_invalid_url(self) -> None:
        """Ensure an error is raised when an invalid URL is specified."""
        self.assertRaises(ValueError, fetch.fetch_file, 'https://www.freebsd.org/')

    def test_missing_file(self) -> None:
        """Ensure an error is raised when a file does not exist."""
        dl_path = 'https://ucb.tind.example/api/v1/record/1234/files/nothere.txt/download/'
        with requests_mock.mock() as r_mock:
            r_mock.get(dl_path, status_code=404)
            self.assertRaises(RecordNotFoundError, fetch.fetch_file, dl_path)

    def test_write_error(self) -> None:
        """Ensure an error is raised when attempting to write a file to an invalid location."""
        dl_path = 'https://ucb.tind.example/api/v1/record/1234/files/error.txt/download/'

        with tempfile.TemporaryDirectory() as temp_dir:
            # At the end of this block, the directory will be removed.
            custom_path = temp_dir

        with requests_mock.mock() as r_mock:
            r_mock.get(dl_path, text='This file will not be saved.\n')
            self.assertRaises(IOError, fetch.fetch_file, dl_path, custom_path)

    def test_insufficient_perm(self) -> None:
        """Ensure an error is raised when a file cannot be accessed by the given API key."""
        dl_path = 'https://ucb.tind.example/api/v1/record/1234/files/restricted.txt/download/'
        with requests_mock.mock() as r_mock:
            r_mock.get(dl_path, status_code=401)
            self.assertRaises(AuthorizationError, fetch.fetch_file, dl_path)

    def tearDown(self) -> None:
        pathlib.Path(CONFIG['DEFAULT_STORAGE_DIR']).rmdir()
