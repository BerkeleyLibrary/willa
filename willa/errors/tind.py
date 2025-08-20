"""
Defines TIND error classes for Willa.
"""

import json


class TINDError(Exception):
    """Represents a general TIND API error."""
    @classmethod
    def from_json(cls, status: int, maybe_json: str) -> Exception:
        """Create a TIND error from what should be a JSON response.

        :param int status: The HTTP status code associated with the response.
        :param str maybe_json: The response text, hopefully in JSON format.
        :returns Exception: A TINDError with a suitable message based on the response.
                            If the response wasn't JSON, "Non-JSON response" will be used.
        """
        try:
            j = json.loads(maybe_json)
            reason = j.get('reason', j.get('error', 'Unknown error'))
        except json.decoder.JSONDecodeError:
            reason = 'Non-JSON response'
        return cls(f"HTTP status {status}, Message: {reason}")


class AuthorizationError(TINDError):
    """Represents an error with TIND API authorization."""


class RecordNotFoundError(TINDError):
    """Represents an error where the given record was not found in TIND."""
