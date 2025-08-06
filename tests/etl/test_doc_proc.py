"""
Test suite for document processing utilities.
"""

import os
import unittest
import tempfile
import shutil
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings, OllamaLLM 
from willa.etl.doc_proc import (
    load_pdfs,
    split_doc,
    split_all_docs,
    embed_docs,
)

class DocumentProcessingTest(unittest.TestCase):
    """Test suite for document processing utilities."""

    def setUp(self) -> None:
        os.environ['DEFAULT_STORAGE_DIR'] = tempfile.mkdtemp(prefix='willatest')
        shutil.copyfile(os.path.join(os.path.dirname(__file__), 'parnell_kerby.pdf'),
                        os.path.join(os.environ['DEFAULT_STORAGE_DIR'], 'parnell_kerby.pdf'))
        self.embedding_model = 'nomic-embed-text'
        
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

    @unittest.skipUnless(os.getenv("RUN_OLLAMA_TESTS"), "requires running ollama")
    def test_embed_docs(self) -> None:
        """Test embedding documents."""
        docs = load_pdfs()
        if docs:
            chunked_docs = split_all_docs(docs)
            embeddings = OllamaEmbeddings(model=self.embedding_model)
            vector_store = InMemoryVectorStore(embeddings)
            embed_ids = embed_docs(chunked_docs, vector_store)
            self.assertGreater(len(embed_ids), 0, "Should return IDs for embedded documents.")