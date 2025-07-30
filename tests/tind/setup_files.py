"""Methods for processing files"""

import os
import json

def setup_json(file):
    """Load a file of test json
    params: a file containing json as text 
    returns: a json object
    """
    record = os.path.join(os.path.dirname(__file__), file)
    with open(record, encoding='UTF-8') as data_f:
        data = data_f.read()
    return json.loads(data)


def setup_text_file(file) -> str:
    """Load a file of test xml
    params: file
    returns: A file as text
    """
    record = os.path.join(os.path.dirname(__file__), file)
    with open(record, encoding='UTF-8') as data_f:
        data = data_f.read()
    return data
