"""
Load the configuration for Willa into the environment.
"""

__copyright__ = "© 2025 The Regents of the University of California.  MIT license."

import os
from dotenv import load_dotenv

load_dotenv()


OLLAMA_URL: str = os.getenv('OLLAMA_URL', 'http://localhost:11434')
"""The URL to use to connect to Ollama."""