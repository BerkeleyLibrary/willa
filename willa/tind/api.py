"""
Provides low-level access to the TIND API.
"""

import os
import requests

import willa.config  # pylint: disable=W0611
from willa.errors import AuthorizationError


def _auth_header() -> dict:
    """Returns the Authorization header needed for TIND API calls."""
    token = os.getenv('TIND_API_KEY', None)
    if token is None:
        raise AuthorizationError('Missing TIND API key')

    return {'Authorization': f"Token {token}"}


def tind_get(endpoint: str, params: dict = None) -> (int, str):
    """Run a GET API request, returning its response.

    :param str endpoint: The TIND API endpoint to query.
                         For example, ``'record/1/'``.
    :param dict params: Extra query parameters to send.
                        For example, ``{'of': 'xm'}``.
    :returns: A tuple of the HTTP status code and response text (if any).
    """
    if params is None:
        params = {}

    resp = requests.request('GET',
                            f"https://digicoll.lib.berkeley.edu/api/v1/{endpoint}",
                            headers=_auth_header(), params=params, timeout=30)
    return resp.status_code, resp.text
