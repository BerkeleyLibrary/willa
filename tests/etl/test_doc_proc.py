"""
Test suite for document processing utilities.
"""

import os
import shutil
import tempfile
import unittest

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings
from pymarc import parse_xml_to_array

from willa.config import CONFIG
from willa.etl.doc_proc import (
    load_pdf, load_pdfs,
    split_doc, split_all_docs,
    embed_docs,
)
from willa.tind.format_validate_pymarc import pymarc_to_metadata


class DocumentProcessingTest(unittest.TestCase):
    """Test suite for document processing utilities."""

    def setUp(self) -> None:
        CONFIG['DEFAULT_STORAGE_DIR'] = tempfile.mkdtemp(prefix='willatest')
        tind_dir = os.path.join(CONFIG['DEFAULT_STORAGE_DIR'], '103806')
        os.mkdir(tind_dir)
        shutil.copyfile(os.path.join(os.path.dirname(__file__), 'parnell_kerby.pdf'),
                        os.path.join(tind_dir, 'parnell_kerby.pdf'))
        shutil.copyfile(os.path.join(os.path.dirname(__file__), 'parnell_kerby.json'),
                        os.path.join(tind_dir, '103806.json'))
        self.embedding_model = 'nomic-embed-text'

    def test_load_pdf(self) -> None:
        """Test loading a single PDF with metadata."""
        with (open(os.path.join(os.path.dirname(__file__), 'parnell_kerby.xml'), encoding='utf-8')
              as xml):
            record = parse_xml_to_array(xml)[0]

        metadata = pymarc_to_metadata(record)
        docs = load_pdf(os.path.join(os.path.dirname(__file__), 'parnell_kerby.pdf'), record)
        self.assertGreater(len(docs), 0, "Should load the document.")
        tind_md = docs[0].metadata['tind_metadata']
        self.assertDictEqual(tind_md, metadata)

    def test_load_pdfs(self) -> None:
        """Test loading PDF files."""
        docs = load_pdfs()
        self.assertGreater(len(docs), 0, "Should load at least one document.")

    def test_split_doc(self) -> None:
        """Test splitting a document into chunks."""
        docs = load_pdfs()
        if docs:
            doc = docs[0]
            chunks = split_doc(doc)
            self.assertGreater(len(chunks), 0, "Should create at least one chunk.")

    def test_split_all_docs(self) -> None:
        """Test splitting all documents into chunks."""
        docs = load_pdfs()
        if docs:
            chunked_docs = split_all_docs(docs)
            self.assertGreater(len(chunked_docs), 0, "Should create chunks from all documents.")
            self.assertIsInstance(chunked_docs[0], Document, "Should return the chunks.")

    @unittest.skipUnless(os.getenv("RUN_OLLAMA_TESTS"), "requires running ollama")
    def test_embed_docs(self) -> None:
        """Test embedding documents."""
        docs = load_pdfs()
        if docs:
            chunked_docs = split_all_docs(docs)
            embeddings = OllamaEmbeddings(model=self.embedding_model, base_url=CONFIG['OLLAMA_URL'])
            vector_store = InMemoryVectorStore(embeddings)
            embed_ids = embed_docs(chunked_docs, vector_store)
            self.assertGreater(len(embed_ids), 0, "Should return IDs for embedded documents.")
