"""Methods for processing files"""

from typing import Any
import json
import os


def setup_json(file: str) -> Any:
    """Load a mock JSON object from a text file.

    :param file: The name of the file containing the JSON object as text.
    :returns: A loaded JSON object.
    """
    record = os.path.join(os.path.dirname(__file__), file)
    with open(record, encoding='UTF-8') as data_f:
        data = data_f.read()
    return json.loads(data)


def setup_text_file(file: str) -> str:
    """Load a mock text file.

    :param file: The name of the file containing the text.
    :returns: The contents of the file as text.
    """
    record = os.path.join(os.path.dirname(__file__), file)
    with open(record, encoding='UTF-8') as data_f:
        data = data_f.read()
    return data
