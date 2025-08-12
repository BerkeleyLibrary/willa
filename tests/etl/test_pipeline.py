"""
Test suite for end-to-end pipeline routines.
"""

import os
import unittest

import requests_mock
from willa.etl.pipeline import fetch_one_from_tind


class PipelineTest(unittest.TestCase):
    """Test the pipeline routines."""
    def setUp(self) -> None:
        """Initialise the environment for our test case."""
        os.environ['TIND_API_KEY'] = 'Test_Key'
        os.environ['TIND_API_URL'] = 'https://ucb.tind.example/api/v1'

    @unittest.skipUnless(os.getenv("RUN_OLLAMA_TESTS"), "requires running ollama")
    def test_fetch_from_tind(self) -> None:
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

            store = fetch_one_from_tind('test')

        results = store.search('Arkansas', 'similarity')
        self.assertGreater(len(results), 0, "Search should match at least one document.")
        first_doc_md = results[0].metadata['tind_metadata']
        self.assertEqual(first_doc_md['tind_id'], '103806',
                         "Document metadata should match TIND record.")
