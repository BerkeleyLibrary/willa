"""
Utility functions to gather pdf files, use langchain pypdf loader to load them,
and split them into chunks for vectorization.
"""

import os
from functools import reduce
from operator import add

from langchain_community.document_loaders import PyPDFDirectoryLoader
# from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.vectorstores.base import VectorStore
from pymarc.record import Record

import willa.config  # pylint: disable=W0611
from willa.tind.format_validate_pymarc import pymarc_to_metadata


def load_pdf(name: str, record: Record | None) -> list[Document]:
    """Load a given single PDF from storage, including optional PyMARC record.

    :param str name: The name of the file.
    :param record: The PyMARC record that pertains to the file.
    :returns: A ``list`` of ``Document``s that can be further used in the pipeline.
    """
    directory_path = os.getenv('DEFAULT_STORAGE_DIR', 'tmp/files/')
    loader = PyPDFDirectoryLoader(directory_path, glob=name, mode="single")

    docs = loader.load()
    if not docs:
        print(f"Requested file {name} not found.")
    else:
        print(f"Loaded {name} as a document.")
        if record:
            for doc in docs:
                doc.metadata['tind_metadata'] = pymarc_to_metadata(record)

    return docs


def load_pdfs() -> list[Document]:
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


def split_doc(doc: Document, chunk_size: int = 1000, chunk_overlap: int = 200) -> list:
    """Split a document into chunks for vectorization."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True
    )
    return text_splitter.split_documents([doc])


def split_all_docs(docs: list, chunk_size: int = 1000, chunk_overlap: int = 200) -> list:
    """Split all documents into chunks."""
    return reduce(add, [split_doc(doc, chunk_size, chunk_overlap) for doc in docs])


def embed_docs(chunked_docs: list, vector_store: VectorStore) -> list:
    """Embed documents using Ollama embeddings and store them in a vector store."""
    document_ids = vector_store.add_documents(documents=chunked_docs)
    return document_ids
