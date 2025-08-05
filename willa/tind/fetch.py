"""
Provides routines to fetch information from the TIND API.
"""

import os

from io import StringIO
from pymarc.marcxml import parse_xml_to_array
from pymarc import Record
from willa.errors import RecordNotFoundError
from .api import tind_get, tind_download


def fetch_metadata(record: str) -> Record:
    """Fetch the MARC XML metadata for a given record.

    :param str record: The record ID for which to fetch metadata.
    :raises AuthorizationError: When the TIND API key is invalid.
    :raises RecordNotFoundError: When the record ID is invalid or not found.
    :returns: A PyMARC MARC record of the requested record.
    """
    status, response = tind_get(f"record/{record}/", {'of': 'xm'})
    if status == 404 or len(response.strip()) == 0:
        raise RecordNotFoundError(f"Record {record} not found in TIND.")

    records = parse_xml_to_array(StringIO(response))
    # When the record does not match any records, we may receive a zero-length array of records.
    # Additionally, if the XML is malformed, the parser function may return multiple records.
    # We need to ensure that exactly one record is parsed out of the TIND API response.
    if len(records) != 1:
        raise RecordNotFoundError(f"Record {record} did not match exactly one record in TIND.")

    return records[0]


def fetch_file(file_url: str, output_dir: str = '') -> str:
    """Fetch the given file from TIND.

    :param str file_url: The URL to the file to download from TIND.
                         This must be a TIND file download URL.
    :param str output_dir: The directory in which to save the file.
    :raises AuthorizationError: When the TIND API key is invalid, or the file is restricted.
    :raises ValueError: When the URL is not a valid TIND file download URL.
    :raises RecordNotFoundError: When the file is invalid or not found.
    :raises IOError: When the file cannot be saved to the given output directory.
    :returns str: The full path to the file successfully downloaded to the output directory.
    """
    if not file_url.endswith('/download/'):
        raise ValueError('URL is not a valid TIND file download URL.')

    if output_dir == '':
        # This cannot be put as the default value for the parameter because it would set
        # the value at the time this file is imported.  Changes in the environment (whether
        # via config reload, the test infrastructure, etc) would not appear.
        output_dir = os.environ['DEFAULT_STORAGE_DIR']

    (status, saved_to) = tind_download(file_url, output_dir)

    if status != 200:
        raise RecordNotFoundError('Referenced file could not be downloaded.')

    return saved_to
