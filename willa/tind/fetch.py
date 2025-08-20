"""
Provides routines to fetch information from the TIND API.
"""

import os
import re
from io import StringIO
from typing import Any, Tuple
import json

import xml.etree.ElementTree as E
from pymarc.marcxml import parse_xml_to_array
from pymarc import Record

from willa.errors import RecordNotFoundError, TINDError
from .api import tind_get, tind_download


def fetch_metadata(record: str) -> Record:
    """Fetch the MARC XML metadata for a given record.

    :param str record: The record ID for which to fetch metadata.
    :raises AuthorizationError: When the TIND API key is invalid.
    :raises RecordNotFoundError: When the record ID is invalid or not found.
    :returns Record: A PyMARC MARC record of the requested record.
    """

    status, response = tind_get(f"record/{record}/", {'of': 'xm'})
    if status == 404 or len(response.strip()) == 0:
        raise RecordNotFoundError(f"Record {record} not found in TIND.")

    records: list[Record] = parse_xml_to_array(StringIO(response))
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
    if not re.match(r'^http.*/download(/)?(\?version=\d+)?$', file_url):
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


def fetch_file_metadata(record: str) -> list:
    """Fetch file metadata for a given TIND record.

    :param str record: The record ID in TIND to fetch file metadata for.
    :raises AuthorizationError: When the TIND API key is invalid.
    :raises TINDError: For any response other than 200.
    :returns list: A list of file metadata for a given TIND record.
    """

    status, files = tind_get(f"record/{record}/files")

    if status != 200:
        raise TINDError.from_json(status, files)

    return json.loads(files)  # type: ignore[no-any-return]


def fetch_ids_search(query: str) -> list:
    """Returns a list of TIND record IDs for a given search query.

    :param str query: The query string to search for in TIND.
    :returns list: A list of TIND record IDs.
    """
    status, rec_ids = tind_get("search", {'p': query})

    if status != 200:
        raise TINDError.from_json(status, rec_ids)

    j = json.loads(rec_ids)
    return j['hits']  # type: ignore[no-any-return]


def fetch_marc_by_ids(ids: list) -> list[Record]:
    """Fetch MARC records from a list of TIND record IDs.

    :param list ids: The TIND record IDs to fetch.
    :returns list[Record]: A list of PyMARC records.
    """
    records = []
    for item in ids:
        m = fetch_metadata(item)
        records.append(m)

    return records


def fetch_search_metadata(query: str) -> list[Record]:
    """Returns PyMARC records that match a given search.

    :param str query: The TIND search query.
    :returns list[Record]: A list of PyMARC records that match the given query.
    """
    ids = fetch_ids_search(query)

    return fetch_marc_by_ids(ids)


def _search_request(query: str, search_id: str | None = None) -> str:
    """Retrieve a page of MARC data records.

    :param str query: The TIND search query.
    :param str|None search_id: The search_id for each page of TIND results for pagination.
    :returns str: A page of MARC records in XML format.
    """
    if search_id:
        status, response = tind_get('search', {'format': 'xml', 'p': query, 'search_id': search_id})
    else:
        status, response = tind_get('search', {'format': 'xml', 'p': query})

    if status != 200:
        raise TINDError(f"Status {status} while retrieving TIND record")

    return response


def _retrieve_xml_search_id(response: str) -> Tuple[Any, str]:
    """Creates a parsable XML and retrieves search_id from the TIND result set for pagination.

    :param str response: The string returned from the Tind search call.
    :returns Tuple[Any,str]: A Search ID and a parsable XML document.
    """
    E.register_namespace('', "http://www.loc.gov/MARC21/slim")
    xml = E.fromstring(response)
    search_id = xml.findtext('search_id', default='')

    return xml, search_id


def search(query: str, result_format: str = 'xml') -> list[Any]:
    """Searches TIND and retrieves a list of either XML or PyMARC.

    :param str query: A Tind search string
    :param str result_format: ``xml`` for XML string, ``pymarc`` for list of pymarc records.
    :returns list[Any]: a list of records as either xml strings or pymarc records
    """

    if result_format not in ('xml', 'pymarc'):
        raise ValueError(f"Unexpected result format: {result_format} is neither 'xml' nor 'pymarc'")

    recs: list[Any] = []
    search_id = None

    while True:
        if search_id:
            response = _search_request(query, search_id)
        else:
            response = _search_request(query)

        xml, search_id = _retrieve_xml_search_id(response)

        records = list(xml.find('{http://www.loc.gov/MARC21/slim}collection'))

        if result_format == 'pymarc':
            recs = recs + parse_xml_to_array(StringIO(response))
        else:
            for record in records:
                recs.append(E.tostring(record, encoding='unicode'))

        if not records:
            break

    return recs
