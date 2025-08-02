"""
Provides routines to fetch information from the TIND API.
"""

from io import StringIO
from pymarc.marcxml import parse_xml_to_array
from pymarc import Record
from willa.errors import RecordNotFoundError
from .api import tind_get
import json
import xml.etree.ElementTree as E

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
    if len(records) > 1:
        raise RecordNotFoundError(f"Record {record} matched more than one record in TIND.")
    
    return records[0]

def fetch_file_metadata(record: str) -> Record:
    """Fetch file metadata for a given Tind record.
    :raises AuthorizationError: When the TIND API key is invalid.
    :raises Exception: for any response other then 200. 
    :returns a json list of metadata for a given Tind record
    """ 

    status, files = tind_get(f"record/{record}/files")
    if status != 200:
        j = json.loads(files)
        reason = j['reason']
        raise Exception(f"Status: {status} Message: {reason}.")
    
    return json.loads(files)

def fetch_ids_search(search: str):
    status, rec_ids = tind_get(f"search", {'p': search})

    if status >= 400:
        j = json.loads(rec_ids)
        reason = j['reason']
        raise HTTPError(f"Status: {status}, Message: {reason}")

    j = json.loads(rec_ids) 
    return j['hits']

def fetch_marc_by_ids(ids: list):
    """Fetch Tind marc from a list of Tind record ids
    :returns a list of PYMARC records 
    """ 
    records = []
    for item in ids:
      m = fetch_metadata(item)
      records.append(m)

    return records

def fetch_search_metadata(search: str):
    ids = fetch_ids_search(search)

    return fetch_marc_by_ids(ids)

def search_request(search: str, search_id=None ):
    if search_id:
      status, response = tind_get('search', {'format': 'xml', 'p': search, 'search_id': search_id})
    else:
      status, response = tind_get('search', {'format': 'xml', 'p': search})
    
    return response

def retrieve_xml_search_id(response):
  E.register_namespace('', "http://www.loc.gov/MARC21/slim")
  xml = E.fromstring(response)
  search_id = xml.find('search_id').text

  return xml, search_id

def search(search: str, result_format='xml' ):
    recs = []
    search_id = None

    while True: 
      if search_id:
        response = search_request(search, search_id) 
      else:
        response = search_request(search) 

      xml, search_id = retrieve_xml_search_id(response)

      records = list(xml.find('{http://www.loc.gov/MARC21/slim}collection'))
      if result_format == 'pymarc':
        recs = recs + parse_xml_to_array(StringIO(response))
      else:
        for record in records:
          recs.append(E.tostring(record, encoding='unicode'))
      
      if not records:
        break

    return recs
