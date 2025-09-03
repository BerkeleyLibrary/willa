"""
Load the configuration for Willa into the environment.
"""

__copyright__ = "© 2025 The Regents of the University of California.  MIT license."

import os
from dotenv import load_dotenv

from langchain_community.vectorstores import LanceDB
from langchain_ollama import OllamaEmbeddings


load_dotenv()


OLLAMA_URL: str = os.getenv('OLLAMA_URL', 'http://localhost:11434')
"""The URL to use to connect to Ollama."""


LANCEDB_URI: str = os.getenv('LANCEDB_URI', '/tmp/lancedb-storage')
"""The URI to use to connect to LanceDB."""


def get_lance() -> LanceDB:
    """Return a configured instance of a LanceDB class."""
    embeddings = OllamaEmbeddings(model='nomic-embed-text', base_url=OLLAMA_URL)
    return LanceDB(embedding=embeddings, uri=LANCEDB_URI, table_name='willa')
