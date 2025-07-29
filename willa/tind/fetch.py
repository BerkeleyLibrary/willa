"""
Provides routines to fetch information from the TIND API.
"""

from io import StringIO
from pymarc.marcxml import parse_xml_to_array
from pymarc import Record
from willa.errors import RecordNotFoundError
from .api import tind_get


def fetch_metadata(record: str) -> Record:
    """Fetch the MARC XML metadata for a given record.

    :param str record: The record ID for which to fetch metadata.
    :raises AuthorizationError: When the TIND API key is invalid.
    :raises RecordNotFoundError: When the record ID is invalid or not found.
    :returns: A PyMARC MARC record of the requested record.
    """
    status, response = tind_get(f"record/{record}/", {'of': 'xm'})
    if status == 404:
        raise RecordNotFoundError(f"Record {record} not found in TIND.")

    records = parse_xml_to_array(StringIO(response))
    if len(records) > 1:
        raise RecordNotFoundError(f"Record {record} matched more than one record in TIND.")

    return records[0]
