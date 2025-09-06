"""
Run the Willa ETL pipeline.
"""

import json
import os.path

from langchain_core.documents import Document
from langchain_core.vectorstores.base import VectorStore
from pymarc.marcxml import record_to_xml
from pymarc.record import Record

from willa.config import CONFIG, get_lance
from willa.tind.fetch import fetch_metadata, fetch_file_metadata, fetch_file, search
from willa.tind.format_validate_pymarc import pymarc_to_metadata
from .doc_proc import load_pdf, load_pdfs, split_all_docs, embed_docs


def _create_vector_store() -> VectorStore:
    """Create the vector store if it wasn't specified.

    This is a separate method so that we can change properties later.
    """
    return get_lance()


def run_pipeline(vector_store: VectorStore | None = None) -> VectorStore:
    """Run the ETL pipeline for Willa.

    :param VectorStore|None vector_store: The vector store in which to store processed documents.
                                          If no vector store is specified, a new
                                          in-memory vector store will be created.
    :returns VectorStore: The vector store where processed documents are stored.
    """
    if vector_store is None:
        vector_store = _create_vector_store()

    docs = load_pdfs()
    splits = split_all_docs(docs)
    embed_docs(splits, vector_store)

    return vector_store


def _process_one_tind_record(record: Record, vector_store: VectorStore | None = None) -> None:
    """Process a TIND record that has been fetched.

    This allows us to have two ways into this common code: calling
    ``fetch_one_from_tind`` allows us to fetch by TIND ID; while calling
    ``from_from_search_query`` allows the query's matches to be used as
    the PyMARC Record.  This saves a TIND API call to ``fetch_metadata``
    for each record returned in the search.

    :param Record record: The PyMARC Record object associated with the TIND record.
    :param VectorStore|None vector_store: The vector store in which to store the documents.
                                          If None, vector processing will be skipped.
    """
    tind_id: str = record['001'].value()
    files: list[dict] = fetch_file_metadata(tind_id)
    file_names: list[str] = []
    docs: list[Document] = []

    tind_dir = os.path.join(CONFIG['DEFAULT_STORAGE_DIR'], tind_id)
    os.mkdir(tind_dir)

    marc: bytes = record_to_xml(record)
    with open(os.path.join(tind_dir, f"{tind_id}.xml"), 'w+', encoding='utf-8') as mdx_file:
        mdx_file.write(marc.decode('utf-8'))

    metadata = pymarc_to_metadata(record)
    with open(os.path.join(tind_dir, f"{tind_id}.json"), 'w+', encoding='utf-8') as md_file:
        md_file.write(json.dumps(metadata))

    for file in files:
        file_names.append(fetch_file(file['url'], tind_dir))

    if vector_store is not None:
        for name in file_names:
            docs.extend(load_pdf(name, record))

        splits = split_all_docs(docs)
        embed_docs(splits, vector_store)


def fetch_one_from_tind(tind_id: str, vector_store: VectorStore | None = None) -> None:
    """Fetch the files for a TIND record, then load them into the VectorStore.

    :param str tind_id: The ID of the TIND record.
    :param VectorStore|None vector_store: The vector store in which to store the documents.
                                          If no vector store is specified, files will be fetched
                                          but not processed into a vector store.
    """
    record: Record = fetch_metadata(tind_id)
    _process_one_tind_record(record, vector_store)


def fetch_from_tind(tind_ids: list[str], vector_store: VectorStore | None = None) -> None:
    """Fetch files from a list of TIND records, then load them into a given VectorStore.

    :param list[str] tind_ids: The IDs of the TIND records.
    :param VectorStore|None vector_store: The vector store in which to store the documents.
                                          If no vector store is specified, files will be fetched
                                          but not processed into a vector store.
    """
    for tind_id in tind_ids:
        fetch_one_from_tind(tind_id, vector_store)


def fetch_all_from_search_query(query: str, vector_store: VectorStore | None = None) -> None:
    """Fetch all TIND records that match a given search query, then download them.

    :param str query: The search query to run against the TIND catalogue.
    :param VectorStore|None vector_store: The vector store in which to store the documents.
                                          If no vector store is specified, files will be fetched
                                          but not processed into a vector store.
    """
    results = search(query, 'pymarc')
    for record in results:
        _process_one_tind_record(record, vector_store)


if __name__ == "__main__":
    run_pipeline()
