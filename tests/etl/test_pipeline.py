"""
Test suite for end-to-end pipeline routines.
"""

import os.path
import pathlib
import tempfile
import unittest
from unittest.mock import Mock

from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings
from pymarc.record import Record
import requests_mock

from willa.config import CONFIG
import willa.etl.pipeline
from willa.etl.pipeline import fetch_one_from_tind, fetch_all_from_search_query


__dirname__ = os.path.dirname(__file__)
"""Keep our dirname close so we don't have to call os.path.dirname so much."""


def _load_mock_files(name: str) -> tuple[str, bytes, str]:
    """Load mock files for a record.

    :param str name: The name of the mock files.
    :returns: A tuple of (MARC XML, PDF, file metadata as JSON)
    :rtype: tuple[str, bytes, str]
    """
    with open(os.path.join(__dirname__, f'{name}.xml'), encoding='utf-8') as xml_f:
        xml = xml_f.read()

    with open(os.path.join(__dirname__, f'{name}.pdf'), 'rb') as pdf_f:
        pdf = pdf_f.read()

    with open(os.path.join(__dirname__, f'{name}.json'), encoding='utf-8') as json_f:
        json = json_f.read()

    return xml, pdf, json


class PipelineTest(unittest.TestCase):
    """Test the pipeline routines."""
    def setUp(self) -> None:
        """Initialise the environment for our test case."""
        CONFIG['TIND_API_KEY'] = 'Test_Key'
        CONFIG['TIND_API_URL'] = 'https://ucb.tind.example/api/v1'
        CONFIG['DEFAULT_STORAGE_DIR'] = tempfile.mkdtemp(prefix='willatest')

    def test_fetch_from_tind(self) -> None:
        """Test fetching a record from TIND and saving it, and its metadata, to storage."""
        kerby_xml, kerby_pdf, kerby_json = _load_mock_files('parnell_kerby')

        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/record/103806/', text=kerby_xml)
            r_mock.get('https://ucb.tind.example/api/v1/record/103806/files', text=kerby_json)
            url = 'https://ucb.tind.example/api/v1/record/103806/files/parnell_kerby.pdf'\
                  '/download/?version=1'
            r_mock.get(url, content=kerby_pdf)

            fetch_one_from_tind('103806')

        store_dir = pathlib.Path(os.path.join(CONFIG['DEFAULT_STORAGE_DIR'], '103806'))
        self.assertTrue(store_dir.is_dir(), "Should have created the record directory")

        marc_xml_file = store_dir.joinpath('103806.xml')
        self.assertTrue(marc_xml_file.is_file(), "Should have saved MARC XML record")
        marc_xml_file.unlink()

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
        kerby_xml, kerby_pdf, kerby_json = _load_mock_files('parnell_kerby')

        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/record/103806/', text=kerby_xml)
            r_mock.get('https://ucb.tind.example/api/v1/record/103806/files', text=kerby_json)
            url = 'https://ucb.tind.example/api/v1/record/103806/files/parnell_kerby.pdf'\
                  '/download/?version=1'
            r_mock.get(url, content=kerby_pdf)

            store = InMemoryVectorStore(OllamaEmbeddings(model='nomic-embed-text',
                                                         base_url=CONFIG['OLLAMA_URL']))
            fetch_one_from_tind('103806', store)

        results = store.search('Arkansas', 'similarity')
        self.assertGreater(len(results), 0, "Search should match at least one document.")
        first_doc_md = results[0].metadata['tind_metadata']
        self.assertEqual(first_doc_md['tind_id'], '103806',
                         "Document metadata should match TIND record.")

        store_dir = pathlib.Path(os.path.join(CONFIG['DEFAULT_STORAGE_DIR'], '103806'))
        store_dir.joinpath('103806.xml').unlink()
        store_dir.joinpath('103806.json').unlink()
        store_dir.joinpath('parnell_kerby.pdf').unlink()
        store_dir.rmdir()

    def test_fetch_from_search(self) -> None:
        """Test searching TIND and fetching the records in the search result."""
        tind_ids = ['219031', '219040', '219042', '219043', '219045', '219048', '219052',
                    '219055', '219069', '219071', '219080', '219081', '219085', '219086',
                    '219097', '219099', '219102', '219104', '219108', '219109', '219112']

        def process_tind_mock(record: Record, _: None) -> None:
            """Mock the TIND record processor from the ETL pipeline."""
            tind_ids.remove(record['001'].value())

        # pylint: disable=protected-access
        mock_processor = Mock(side_effect=process_tind_mock)
        old_processor = willa.etl.pipeline._process_one_tind_record
        willa.etl.pipeline._process_one_tind_record = mock_processor

        with open(os.path.join(__dirname__, 'example_search.xml'), encoding='utf-8') as xml_f:
            search_response = xml_f.read()

        with open(os.path.join(__dirname__, 'empty_search.xml'), encoding='utf-8') as empty_f:
            empty_response = empty_f.read()

        with requests_mock.mock() as r_mock:
            r_mock.get('https://ucb.tind.example/api/v1/search', response_list=[
                {'text': search_response}, {'text': empty_response}
            ])
            fetch_all_from_search_query('collection:"Freedom to Marry Oral Histories"')

        self.assertEqual(mock_processor.call_count, 21, "Should have processed all results")
        self.assertListEqual(tind_ids, [], "Should have processed exactly the TIND IDs returned")
        willa.etl.pipeline._process_one_tind_record = old_processor
        # pylint: enable=protected-access

    def tearDown(self) -> None:
        pathlib.Path(CONFIG['DEFAULT_STORAGE_DIR']).rmdir()
