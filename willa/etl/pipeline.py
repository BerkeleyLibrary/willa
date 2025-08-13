"""
Run the Willa ETL pipeline.
"""

import os.path

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.vectorstores.base import VectorStore
from langchain_ollama import OllamaEmbeddings
from pymarc.record import Record

from willa.tind.fetch import fetch_metadata, fetch_file_metadata, fetch_file
from willa.config import OLLAMA_URL
from .doc_proc import load_pdf, load_pdfs, split_all_docs, embed_docs


def _create_vector_store() -> VectorStore:
    """Create the vector store if it wasn't specified.

    This is a separate method so we can change properties later.
    """
    embeddings = OllamaEmbeddings(model='nomic-embed-text', base_url=OLLAMA_URL)
    return InMemoryVectorStore(embeddings)


def run_pipeline(vector_store: VectorStore | None = None) -> VectorStore:
    """Run the ETL pipeline for Willa.

    :param vector_store: The vector store in which to store processed documents.
                         If no vector store is specified, a new
                         in-memory vector store will be created.
    :returns: The vector store where processed documents are stored.
    """
    if vector_store is None:
        vector_store = _create_vector_store()

    docs = load_pdfs()
    splits = split_all_docs(docs)
    embed_docs(splits, vector_store)

    return vector_store


def fetch_one_from_tind(tind_id: str, vector_store: VectorStore | None = None) -> VectorStore:
    """Fetch the files for a TIND record, then load them into the VectorStore.

    :param str tind_id: The ID of the TIND record.
    :param vector_store: The vector store in which to store the documents.
                         If no vector store is specified, a new in-memory
                         vector store will be created.
    :returns: The vector store where the processed document(s) were stored.
    """
    if vector_store is None:
        vector_store = _create_vector_store()

    record: Record = fetch_metadata(tind_id)
    files: list[dict] = fetch_file_metadata(tind_id)
    file_names: list[str] = []
    docs: list[Document] = []

    for file in files:
        file_names.append(os.path.basename(fetch_file(file['url'])))

    for name in file_names:
        docs.extend(load_pdf(name, record))

    splits = split_all_docs(docs)
    embed_docs(splits, vector_store)

    return vector_store


def fetch_from_tind(tind_ids: list[str], vector_store: VectorStore | None = None) -> VectorStore:
    """Fetch files from a list of TIND records, then load them into a given VectorStore.

    :param list[str] tind_ids: The IDs of the TIND records.
    :param vector_store: The vector store in which to store the documents.
                         If no vector store is specified, a new in-memory
                         vector store will be created.
    :returns: The vector store where the processed documents were stored.
    """
    if vector_store is None:
        vector_store = _create_vector_store()

    for tind_id in tind_ids:
        fetch_one_from_tind(tind_id, vector_store)

    return vector_store
