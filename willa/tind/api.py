"""
Provides low-level access to the TIND API.
"""


import os
import re
from typing import Tuple

import requests

import willa.config  # pylint: disable=W0611
from willa.errors import AuthorizationError


TIMEOUT: int = 30
"""The number of seconds to wait for an HTTP connection to respond."""


def _auth_header() -> dict:
    """Returns the Authorization header needed for TIND API calls.

    :raises AuthorizationError: If no TIND API key is provided in the environment.
    :returns dict: The ``Authorization`` header to use for the HTTP request.
    """
    token = os.getenv('TIND_API_KEY', None)
    if token is None:
        raise AuthorizationError('Missing TIND API key')

    return {'Authorization': f"Token {token}"}


def tind_get(endpoint: str, params: dict | None = None) -> Tuple[int, str]:
    """Run a GET API request, returning its response.

    :param str endpoint: The TIND API endpoint to query.
                         For example, ``'record/1/'``.
    :param dict|None params: Extra query parameters to send.
                             For example, ``{'of': 'xm'}``.
    :raises AuthorizationError: If an invalid TIND API key is provided.
    :returns: A tuple of the HTTP status code and response text (if any).
    :rtype: Tuple[int, str]
    """
    if params is None:
        params = {}

    api_base = os.getenv('TIND_API_URL', 'https://digicoll.lib.berkeley.edu/api/v1')

    resp = requests.get(f"{api_base}/{endpoint}",
                        headers=_auth_header(), params=params, timeout=TIMEOUT)
    if resp.status_code == 401:
        raise AuthorizationError('Invalid TIND API key provided')
    if resp.status_code >= 500:
        resp.raise_for_status()
    return resp.status_code, resp.text


def tind_download(url: str, output_dir: str) -> Tuple[int, str]:
    """Download a file from TIND.

    :param str url: The TIND file download URL.
    :param str output_dir: The path to the directory in which to save the file.
    :raises AuthorizationError: If an invalid TIND API key is provided.
    :returns: The HTTP status code.
    :rtype: Tuple[int, str]
    """
    resp = requests.get(url, headers=_auth_header(), timeout=TIMEOUT)
    status = resp.status_code
    if status == 401:
        raise AuthorizationError('Invalid TIND API key provided')
    if status >= 500:
        resp.raise_for_status()
    if status != 200:
        return status, ''

    # Fall-back to the file name in the URL if it isn't included in the response.
    output_filename = url.split('/')[-3]

    # See if we can extract the filename from the response headers.
    if 'Content-Disposition' in resp.headers:
        match = re.findall('filename=\"(.+)\"', resp.headers['Content-Disposition'])
        if len(match) == 1:
            output_filename = match[0]

    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, 'wb') as out_f:
        for chunk in resp.iter_content():
            out_f.write(chunk)

    return status, output_path
