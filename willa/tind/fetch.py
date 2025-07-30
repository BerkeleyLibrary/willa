"""
Provides routines to fetch information from the TIND API.
"""

import os
from io import StringIO
from argparse import ArgumentError
from typing import List
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
    :returns: A PyMARC MARC record of the requested record.
    """

    status, response = tind_get(f"record/{record}/", {'of': 'xm'})
    if status == 404 or len(response.strip()) == 0:
        raise RecordNotFoundError(f"Record {record} not found in TIND.")

    records: List[Record] = parse_xml_to_array(StringIO(response))
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


def fetch_file_metadata(record: str) -> list:
    """Fetch file metadata for a given Tind record.

    :raises AuthorizationError: When the TIND API key is invalid.
    :raises Exception: for any response other then 200. 
    :returns: A list of file metadata for a given TIND record.
    """

    status, files = tind_get(f"record/{record}/files")

    if status != 200:
        j = json.loads(files)
        reason = j['reason']
        raise TINDError(f"Status: {status} Message: {reason}.")

    return json.loads(files)


def fetch_ids_search(srch: str) -> list:
    """Returns a list or Tind record ids for a given search.

    :param str srch: Tind query string
    :returns a list of Tind record ids
    """
    status, rec_ids = tind_get("search", {'p': srch})

    if status != 200:
        j = json.loads(rec_ids)
        reason = j['reason']
        raise TINDError(f"Status: {status}, Message: {reason}")

    j = json.loads(rec_ids)
    return j['hits']


def fetch_marc_by_ids(ids: list):
    """Fetch Tind marc from a list of Tind record ids

    :returns: a list of PYMARC records 
    """
    records = []
    for item in ids:
        m = fetch_metadata(item)
        records.append(m)

    return records


def fetch_search_metadata(srch: str) -> List[Record]:
    """Returns PyMARC records that match a given search.

    :param str srch: The Tind search query.
    :returns: A list of PyMARC records that match the given query.
    """
    ids = fetch_ids_search(srch)

    return fetch_marc_by_ids(ids)


def _search_request(srch: str, search_id=None) -> str:
    """retrieves a page of marc data records

    :params str srch: The Tind search query.
    :params str search_id: The search_id for each page of Tind results for pagination.
    :returns: a page of marc records
    """
    if search_id:
        status, response = tind_get('search', {'format': 'xml', 'p': srch, 'search_id': search_id})
    else:
        status, response = tind_get('search', {'format': 'xml', 'p': srch})

    if status != 200:
        raise TINDError(f"Status: {status} Problem retrieving Tind record.")

    return response


def _retrieve_xml_search_id(response: str):
    """Creates a parsable XML and retrieves search_ID from the Tind resultset for pagination

    :param response: The string returned from the Tind search call.
    :returns: a Search Id and a parsable XML document
    """
    E.register_namespace('', "http://www.loc.gov/MARC21/slim")
    xml = E.fromstring(response)
    search_id = xml.find('search_id').text

    return xml, search_id

def search(srch: str, result_format='xml') -> List[Record]:
    """Searches Tind and retrieves a list of eithe XML or Pymarc

    :param srch: A Tind search string
    :param result_format: ``xml`` for XML string, ``pymarc`` for list of pymarc records.
    :returns: a list of records as either xml strings or pymarc records
    """

    if result_format not in ('xml', 'pymarc'):
        raise ArgumentError(result_format,
                            "Unexpected result format should be either 'xml' or 'pymarc'")

    recs = []
    search_id = None

    while True:
        if search_id:
            response = _search_request(srch, search_id)
        else:
            response = _search_request(srch)

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
