"""
Utility functions to gather pdf files, use langchain pypdf loader to load them,
and split them into chunks for vectorization.
"""

import json
import os.path
from functools import reduce
from operator import add
from pathlib import Path
from typing import Any

from langchain_community.document_loaders import PyPDFDirectoryLoader
# from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.vectorstores.base import VectorStore
from pymarc.record import Record

from willa.config import CONFIG
from willa.tind.format_validate_pymarc import pymarc_to_metadata


def load_pdf(name: str, record: Record | None) -> list[Document]:
    """Load a given single PDF from storage, including optional PyMARC record.

    :param str name: The name of the file.
    :param Record|None record: The PyMARC record that pertains to the file.
    :returns list[Document]: A ``list`` of ``Document``s that can be further used in the pipeline.
    """
    directory_path = os.path.dirname(name)
    loader = PyPDFDirectoryLoader(directory_path, glob=os.path.basename(name), mode="single")

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
    """Load all PDF files from the storage directory.

    This assumes the storage directory is laid out in the following manner:

    [/storage-root]/
        [tind_id]/
            [tind_id].json: The JSON metadata for this TIND record.

            [tind_id].xml: The MARC XML version of this TIND record.

            [...]: One or more PDF files that comprise the TIND record.

    :returns list[Document]: All documents successfully loaded.
    """
    docs: list[Document] = []

    for tind_path in Path(CONFIG['DEFAULT_STORAGE_DIR']).iterdir():
        if not tind_path.is_dir():
            continue  # We only want directories.

        tind_id = tind_path.name
        metadata: dict[str, Any] = {}

        md_path = tind_path.joinpath(f"{tind_id}.json")
        if md_path.is_file():
            with open(md_path, 'r', encoding='utf-8') as md_json:
                metadata = json.loads(md_json.read())
        else:
            print(f"No metadata stored for {tind_id}!")

        loader = PyPDFDirectoryLoader(tind_path, mode="single")
        # loader = DirectoryLoader(tind_path, glob="**/*.pdf")

        new_docs = loader.load()
        if not new_docs:
            print(f"No documents found in the {tind_id} directory.")
            continue

        if len(metadata) > 0:
            for doc in new_docs:
                doc.metadata['tind_metadata'] = metadata
        docs.extend(new_docs)
        print(f"Loaded {len(new_docs)} document(s) from {tind_id}.")

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
