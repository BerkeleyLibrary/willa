"""
Test suite for end-to-end pipeline routines.
"""

import os
import pathlib
import tempfile
import unittest

from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings
import requests_mock

from willa.config import OLLAMA_URL
from willa.etl.pipeline import fetch_one_from_tind


class PipelineTest(unittest.TestCase):
    """Test the pipeline routines."""
    def setUp(self) -> None:
        """Initialise the environment for our test case."""
        os.environ['TIND_API_KEY'] = 'Test_Key'
        os.environ['TIND_API_URL'] = 'https://ucb.tind.example/api/v1'
        os.environ['DEFAULT_STORAGE_DIR'] = tempfile.mkdtemp(prefix='willatest')

    def test_fetch_from_tind(self) -> None:
        """Test fetching a record from TIND and saving it, and its metadata, to storage."""
        with (open(os.path.join(os.path.dirname(__file__), 'parnell_kerby.xml'), encoding='utf-8')
              as xml_f):
            kerby_xml = xml_f.read()

        with open(os.path.join(os.path.dirname(__file__), 'parnell_kerby.pdf'), 'rb') as pdf_f:
            kerby_pdf = pdf_f.read()

        with (open(os.path.join(os.path.dirname(__file__), 'parnell_kerby.json'), encoding='utf-8')
              as json_f):
            kerby_json = json_f.read()

        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/record/103806/', text=kerby_xml)
            r_mock.get('https://ucb.tind.example/api/v1/record/103806/files', text=kerby_json)
            url = 'https://ucb.tind.example/api/v1/record/103806/files/parnell_kerby.pdf'\
                  '/download/?version=1'
            r_mock.get(url, content=kerby_pdf)

            fetch_one_from_tind('103806')

        store_dir = pathlib.Path(os.path.join(os.environ['DEFAULT_STORAGE_DIR'], '103806'))
        self.assertTrue(store_dir.is_dir(), "Should have created the record directory")

        metadata_file = store_dir.joinpath('103806.json')
        self.assertTrue(metadata_file.is_file(), "Should have saved metadata")
        metadata_file.unlink()

        pdf_file = store_dir.joinpath('parnell_kerby.pdf')
        self.assertTrue(pdf_file.is_file(), "Should have saved PDF")
        pdf_file.unlink()

        store_dir.rmdir()

    @unittest.skipUnless(os.getenv("RUN_OLLAMA_TESTS"), "requires running ollama")
    def test_e2e_fetch_from_tind(self) -> None:
        """Test fetching a record from TIND and embedding it in a vector store."""
        with (open(os.path.join(os.path.dirname(__file__), 'parnell_kerby.xml'), encoding='utf-8')
              as xml_f):
            kerby_xml = xml_f.read()

        with open(os.path.join(os.path.dirname(__file__), 'parnell_kerby.pdf'), 'rb') as pdf_f:
            kerby_pdf = pdf_f.read()

        with (open(os.path.join(os.path.dirname(__file__), 'parnell_kerby.json'), encoding='utf-8')
              as json_f):
            kerby_json = json_f.read()

        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/record/test/', text=kerby_xml)
            r_mock.get('https://ucb.tind.example/api/v1/record/test/files', text=kerby_json)
            url = 'https://ucb.tind.example/api/v1/record/test/files/parnell_kerby.pdf'\
                  '/download/?version=1'
            r_mock.get(url, content=kerby_pdf)

            store = InMemoryVectorStore(OllamaEmbeddings(model='nomic-embed-text',
                                                         base_url=OLLAMA_URL))
            fetch_one_from_tind('test', store)

        results = store.search('Arkansas', 'similarity')
        self.assertGreater(len(results), 0, "Search should match at least one document.")
        first_doc_md = results[0].metadata['tind_metadata']
        self.assertEqual(first_doc_md['tind_id'], '103806',
                         "Document metadata should match TIND record.")

        store_dir = pathlib.Path(os.path.join(os.environ['DEFAULT_STORAGE_DIR'], '103806'))
        store_dir.joinpath('103806.json').unlink()
        store_dir.joinpath('parnell_kerby.pdf').unlink()
        store_dir.rmdir()

    def tearDown(self) -> None:
        pathlib.Path(os.environ['DEFAULT_STORAGE_DIR']).rmdir()
