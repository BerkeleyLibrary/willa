"""
Format Tind fields for context in Chat response
"""

DISPLAY_MAPPINGS: dict = {
    'tind_id': 'Tind ID:',
    'isPartOf': 'Project Name:',
    'title': 'Title:',
    'contributor': 'Contributor:'
}


def get_tind_url(tind_id: str) -> str:
    """Create a Tind link using the Tind ID

    :param str tind_id: A tind_id string
    :returns str: A URL to Tind record
    """

    return f"https://digicoll.lib.berkeley.edu/record/{tind_id}"


def get_tind_context(docs: list) -> str:
    """Provide formatted Tind metadata for chatbot responses.

    :param list docs: Array of documents from chatbot.
    :returns str: Formatted text of select TIND data.
    """

    tind_data = ''
    tind_ids = {}
    for doc in docs:
        tind_id = doc.metadata['tind_metadata']['tind_id'][0]
        if tind_id in tind_ids:
            continue

        tind_data += f"\n\n{process_fields(doc.metadata['tind_metadata'])}\n___________\n\n"
        tind_ids[tind_id] = tind_id

    return tind_data


def process_fields(tind_rec: dict) -> str:
    """Provide formatted select Tind fields to include in Chat response

    :param dict tind_rec: dict of Tind metadata
    :returns str: A formatted string to be included in chat display
    """

    fields = ['tind_id', 'title', 'contributor', 'isPartOf']

    formatted_str = ''
    for field in fields:
        if isinstance(tind_rec.get(field), list):
            formatted_str += '\n'.join(
                             [f"{DISPLAY_MAPPINGS[field]} {value}"
                              for value in tind_rec[field]]) + '\n'
        elif tind_rec[field] is not None:
            formatted_str += f"{DISPLAY_MAPPINGS[field]} {tind_rec[field]}\n\n"

    formatted_str += f"Catalogue Link: {get_tind_url(tind_rec['tind_id'][0])}"

    return formatted_str
