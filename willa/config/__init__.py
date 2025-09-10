"""
Load the configuration for Willa into the environment.
"""

__copyright__ = "© 2025 The Regents of the University of California.  MIT license."

import os.path
from dotenv import dotenv_values

from langchain_community.vectorstores import LanceDB
from langchain_ollama import ChatOllama, OllamaEmbeddings

from willa.errors.config import ImproperConfigurationError


DEFAULTS: dict[str, str] = {
    'CALNET_ENV': 'test',
    'CHAT_MODEL': 'gemma3n:e4b',
    'CHAT_TEMPERATURE': '0.5',
    'LANCEDB_URI': '/lancedb',
    'OLLAMA_URL': 'http://localhost:11434',
    'PROMPT_TEMPLATE': os.path.join(os.path.dirname(__package__),
                                    'prompt_templates', 'initial_prompt.txt'),
    'TIND_API_URL': 'https://digicoll.lib.berkeley.edu/api/v1',
}
"""The defaults for configuration variables not set in the .env file."""


VALID_VARS: set[str] = {'TIND_API_KEY', 'TIND_API_URL', 'DEFAULT_STORAGE_DIR', 'PROMPT_TEMPLATE',
                        'OLLAMA_URL', 'CHAT_MODEL', 'CHAT_TEMPERATURE', 'CALNET_ENV',
                        'CALNET_OIDC_CLIENT_ID', 'CALNET_OIDC_CLIENT_SECRET', 'LANCEDB_URI'}
"""Valid configuration variables that could be in the environment."""


_RAW: dict[str, str | None] = dotenv_values()
"""The configuration variables from the .env file."""


_PROCESSED: dict[str, str] = {key: val or '' for key, val in _RAW.items()}
"""Configuration variables from the .env file, with Nones replaced with an empty string."""


_ENVIRON: dict[str, str] = {key: val or '' for key, val in os.environ.items() if key in VALID_VARS}
"""Configuration variables pulled from the environment, as specified in ``VALID_VARS``."""


CONFIG: dict[str, str] = {
    **DEFAULTS,
    **_PROCESSED,
    **_ENVIRON
}
"""The loaded configuration variables."""


if CONFIG.get('DEFAULT_STORAGE_DIR') is None:
    raise ImproperConfigurationError('A storage directory must be set.')


def get_lance() -> LanceDB:
    """Return a configured instance of a LanceDB class."""
    embeddings = OllamaEmbeddings(model='nomic-embed-text', base_url=CONFIG['OLLAMA_URL'])
    return LanceDB(embedding=embeddings, uri=CONFIG['LANCEDB_URI'], table_name='willa')

def get_ollama() -> ChatOllama:
    """Return a configured instance of a ChatOllama chat model."""
    return ChatOllama(
                model=CONFIG['CHAT_MODEL'],
                temperature=float(CONFIG['CHAT_TEMPERATURE']),
                base_url=CONFIG['OLLAMA_URL']
            )
