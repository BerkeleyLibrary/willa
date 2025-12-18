"""
Test suite for the entire ETL pipeline, including external actors.

This differs from ``tests.etl.test_pipeline`` in the following ways:

* We do not mock TIND; we connect to the real thing.
* We use a LanceDB vector store instead of an in-memory vector store.
* We embed documents using the actual configured embeddings provider.
  This defaults to ollama to prevent cost issues with Bedrock.
* We process multiple PDF transcripts into the vector store.
* We ensure retrieval of all documents, to prevent AP-503 recurring.
"""

import os.path
import shutil
import tempfile
import unittest

from willa.config import CONFIG
import willa.etl.pipeline


class E2ETest(unittest.TestCase):
    """Test the entire pipeline.

    1. Extract - Fetch three records from TIND.
    2. Transform/Load - Process them into a LanceDB vector store.
    3. Perform a number of queries to ensure the process was successful.

    The queries we run ensure results from every document are included.
    """
    def setUp(self) -> None:
        """Initialise the environment for the end-to-end test."""
        self.temp_dir = tempfile.mkdtemp(prefix='willatest')

        storage_dir = os.path.join(self.temp_dir, 'pdfs')
        os.mkdir(storage_dir)
        CONFIG['DEFAULT_STORAGE_DIR'] = storage_dir

        data_dir = os.path.join(self.temp_dir, 'lancedb')
        os.mkdir(data_dir)
        CONFIG['LANCEDB_URI'] = data_dir

    @unittest.skipUnless(os.getenv("RUN_E2E_TESTS"), "requires network, keys, ollama")
    def test_e2e_pipeline(self) -> None:
        """Test the pipeline."""
        self.assertIn('TIND_API_KEY', CONFIG, 'You must configure TIND API access')
        self.assertIn('TIND_API_URL', CONFIG, 'You must configure TIND API access')
        self.assertIn('OLLAMA_URL', CONFIG, 'You must have ollama running')
        self.assertEqual(CONFIG['EMBED_BACKEND'], 'ollama',
                         'You must use ollama embeddings for the E2E test')

        willa.etl.pipeline.fetch_one_from_tind('219376')  # Sierra Club
        willa.etl.pipeline.fetch_one_from_tind('218207')  # Genentech
        willa.etl.pipeline.fetch_one_from_tind('103806')  # One from outside our present collections

        store = willa.etl.pipeline.run_pipeline()

        # The interviewee's name should only appear in their document.
        expected = {'Perrault': '219376', 'Itakura': '218207', 'Parnell': '103806'}
        # We can reuse the same retriever for each query to save time and memory.
        retriever = store.as_retriever(search_kwargs={"k": int(CONFIG['K_VALUE'])})
        for name, tind_id in expected.items():
            results = retriever.invoke(name)
            self.assertEqual(len(results), 4)  # default number of docs to return.
            metadata = results[0].metadata
            self.assertIn('tind_metadata', metadata, "TIND metadata missing!")
            tind_md = metadata['tind_metadata']
            self.assertIn('tind_id', tind_md,"TIND ID missing!")
            self.assertListEqual(tind_md['tind_id'], [tind_id],
                                 f"TIND ID {tind_md['tind_id'][0]} doesn't match {tind_id}")

    def tearDown(self) -> None:
        """Remove files, unless `KEEP_E2E_FILES` is present in the environment."""
        if os.getenv('KEEP_E2E_FILES'):
            print(f"Files in {self.temp_dir} remain for your inspection.")
            return

        shutil.rmtree(self.temp_dir)
