"""
Run the Willa ETL pipeline.
"""

from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.vectorstores.base import VectorStore
from langchain_ollama import OllamaEmbeddings

from .doc_proc import load_pdfs, split_all_docs, embed_docs


def run_pipeline(vector_store: VectorStore | None = None) -> VectorStore:
    """Run the ETL pipeline for Willa.

    :param vector_store: The vector store in which to store processed documents.
                         If no vector store is specified, a new
                         in-memory vector store will be created.
    :returns: The vector store where processed documents are stored.
    """
    if vector_store is None:
        embeddings = OllamaEmbeddings(model='nomic-embed-text')
        vector_store = InMemoryVectorStore(embeddings)

    docs = load_pdfs()
    splits = split_all_docs(docs)
    embed_docs(splits, vector_store)

    return vector_store
