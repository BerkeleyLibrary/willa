"""
Defines TIND error classes for Willa.
"""


class TINDError(Exception):
    """Represents a general TIND API error."""


class AuthorizationError(TINDError):
    """Represents an error with TIND API authorization."""


class RecordNotFoundError(TINDError):
    """Represents an error where the given record was not found in TIND."""
