"""
Provides low-level access to the TIND API.
"""

import os
import requests

import willa.config  # pylint: disable=W0611
from willa.errors import AuthorizationError


TIMEOUT: int = 30
"""The number of seconds to wait for an HTTP connection to respond."""


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

    resp = requests.get(f"https://digicoll.lib.berkeley.edu/api/v1/{endpoint}",
                        headers=_auth_header(), params=params, timeout=TIMEOUT)
    if resp.status_code == 401:
        raise AuthorizationError('Invalid TIND API key provided')
    if resp.status_code >= 500:
        resp.raise_for_status()
    return resp.status_code, resp.text


def tind_download(url: str, output_path: str) -> int:
    """Download a file from TIND.

    :param str url: The TIND file download URL.
    :param str output_path: The full path in which to save the file, including name.
    :returns: The HTTP status code.
    """
    resp = requests.get(url, headers=_auth_header(), timeout=TIMEOUT)
    status = resp.status_code
    if status == 401:
        raise AuthorizationError('Invalid TIND API key provided')
    if status >= 500:
        resp.raise_for_status()
    if status != 200:
        return status

    with open(output_path, 'wb') as out_f:
        for chunk in resp.iter_content():
            out_f.write(chunk)

    return status
