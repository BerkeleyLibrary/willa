"""
Defines the errors possibly raised by Willa.
"""

__copyright__ = "© 2025 The Regents of the University of California.  MIT license."

from .config import ImproperConfigurationError
from .tind import AuthorizationError, RecordNotFoundError, TINDError
