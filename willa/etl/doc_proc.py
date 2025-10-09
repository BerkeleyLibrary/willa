"""
Utility functions to gather pdf files, use langchain pypdf loader to load them,
and split them into chunks for vectorization.
"""

import json
import logging
import re
from contextlib import nullcontext
from functools import reduce
from operator import add
from pathlib import Path
from typing import Any, Optional, Union
from unittest.mock import MagicMock

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.vectorstores.base import VectorStore
from opentelemetry.util._decorator import _AgnosticContextManager
from pymarc.record import Record

from willa.config import CONFIG, get_langfuse_client
from willa.lcvendor.pypdf import PyPDFLoader, PyPDFDirectoryLoader
from willa.tind.format_validate_pymarc import pymarc_to_metadata


LOGGER = logging.getLogger(__name__)
"""The logging object for this module."""


FOOTER_RE = re.compile(r'Copyright © 20\d\d by The Regents of the University of California ?')
"""The compiled regular expression for matching footer text."""


def _filter_docs(docs: list[Document]) -> list[Document]:
    """Run filters on a list of ``Document`` to remove header/footer and other undesired content.

    :param list[Document] docs: The document(s) to filter.
    :returns list[Document]: The same document(s), filtered and sanitised.
    """
    for doc in docs:
        content = doc.page_content
        content = content.replace(
            'Oral History Center, The Bancroft Library, University of California, Berkeley ', ''
        )
        doc.page_content = FOOTER_RE.sub('', content)

    return docs


def load_pdf(name: str, record: Record | None) -> list[Document]:
    """Load a given single PDF from storage, including optional PyMARC record.

    :param str name: The name of the file.
    :param Record|None record: The PyMARC record that pertains to the file.
    :returns list[Document]: A ``list`` of ``Document``s that can be further used in the pipeline.
    """
    loader = PyPDFLoader(name, mode='single')

    docs = loader.load()
    if not docs:
        LOGGER.warning("Requested file %s not found.", name)
    else:
        LOGGER.info("Loaded %s as a document.", name)
        if record:
            for doc in docs:
                doc.metadata['tind_metadata'] = pymarc_to_metadata(record)

    return _filter_docs(docs)


def load_pdfs() -> dict[str, list[Document]]:
    """Load all PDF files from the storage directory.

    This assumes the storage directory is laid out in the following manner:

    [/storage-root]/
        [tind_id]/
            [tind_id].json: The JSON metadata for this TIND record.

            [tind_id].xml: The MARC XML version of this TIND record.

            [...]: One or more PDF files that comprise the TIND record.

    :returns: All documents successfully loaded.
    :rtype: dict[str, list[Document]]
    """
    docs: dict[str, list[Document]] = {}

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
            LOGGER.error("No metadata stored for %s!", tind_id)

        loader = PyPDFDirectoryLoader(tind_path, mode="single")
        # loader = DirectoryLoader(tind_path, glob="**/*.pdf")

        new_docs = loader.load()
        if not new_docs:
            LOGGER.warning("No documents found in the %s directory.", tind_id)
            continue

        if len(metadata) > 0:
            for doc in new_docs:
                doc.metadata['tind_metadata'] = metadata
        docs[tind_id] = _filter_docs(new_docs)
        LOGGER.info("Loaded %d document(s) from %s.", len(new_docs), tind_id)

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


def _embed_observation(**kwargs: Any) -> Union[nullcontext, _AgnosticContextManager]:
    """Retrieve the Langfuse observation object, or an inert object if tracing is disabled."""
    if CONFIG['ETL_TRACING'].lower() == 'true':
        langfuse = get_langfuse_client()
        return langfuse.start_as_current_observation(**kwargs)

    return nullcontext(MagicMock())


def embed_docs(chunked_docs: list, vector_store: VectorStore, doc_id: Optional[str] = None) -> list:
    """Embed documents using configured embeddings and store them in a vector store.

    :param list chunked_docs: The chunked ``Document``s processed by ``split_doc``.
    :param VectorStore vector_store: The vector store to write the embedded documents into.
    :param Optional[str] doc_id: The document ID to use for tracing.
    :returns list: The document IDs in the vector store (unrelated to the doc_id).
    """

    # pylint: disable=E1129
    with _embed_observation(as_type='embedding', name='embed_docs', input=chunked_docs) as span:
        span.update_trace(tags=['etl'])
        if doc_id is not None:
            span.update(metadata={'doc_id': doc_id})
        document_ids = vector_store.add_documents(documents=chunked_docs)
        span.update(output=document_ids)
    # pylint: enable=E1129
    return document_ids
