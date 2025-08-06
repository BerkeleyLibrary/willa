"""
Utility functions to gather pdf files, use langchain pypdf loader to load them,
and split them into chunks for vectorization.
"""

import os

from langchain_community.document_loaders import PyPDFDirectoryLoader
# from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.vectorstores.base import VectorStore
import willa.config


def load_pdfs() -> list:
    """Load PDF files from a specified directory using a langchain loader."""
    directory_path = os.getenv('DEFAULT_STORAGE_DIR', 'tmp/files/')
    loader = PyPDFDirectoryLoader(directory_path, mode="single")
    # loader = DirectoryLoader(directory_path, glob="**/*.pdf")

    docs = loader.load()
    if not docs:
        print("No documents found in the specified directory.")
    else:
        print(f"Loaded {len(docs)} documents from {directory_path}.")
    return docs

def split_doc(doc: dict, chunk_size: int = 1000, chunk_overlap: int = 200) -> list:
    """Split a document into chunks for vectorization."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True
    )
    return text_splitter.split_documents([doc])

def split_all_docs(docs: list, chunk_size: int = 1000, chunk_overlap: int = 200) -> list:
    """Split all documents into chunks."""
    all_splits = []
    for doc in docs:
        splits = split_doc(doc, chunk_size, chunk_overlap)
        all_splits.extend(splits)
    return all_splits

def embed_docs(chunked_docs: list, vector_store: VectorStore) -> list:
    """Embed documents using Ollama embeddings and store them in a vector store."""
    document_ids = vector_store.add_documents(documents=chunked_docs)
    return document_ids
