"""
Format Tind fields for context in Chat response
"""

DISPLAY_MAPPINGS: dict = {
    'tind_id': 'Tind ID:',
    'isPartOf': 'Project Name:',
    'title': 'Title:',
    'contributor': 'Contributor:'
}


# Need this to be a hyperlink in the response. Just making
# it text for now.
def tind_link(tind_id):
    """Create a Tind link using the Tind ID

    :param: tind_id
    :returns: link to Tind record
    """

    tind_url = f"https://digicoll.lib.berkeley.edu/record/{tind_id}"
    return tind_url


def process_fields(tind_rec: dict) -> str:
    """Provide formatted select Tind fields to include in Chat response
    
    :param: Json object of Tind Metdata
    :returns: A formatted string to be included in chat display
    """

    fields = ['tind_id', 'contributor', 'title', 'isPartOf']

    formatted_str = ''
    for field in fields:
        if tind_rec[field] is not None and isinstance(tind_rec[field], list):
            for value in tind_rec[field]:
                formatted_str += f"{DISPLAY_MAPPINGS[field]} {value}\n"

            formatted_str += "\n"
        elif tind_rec[field] is not None:
            formatted_str += f"{DISPLAY_MAPPINGS[field]} {tind_rec[field]}\n\n"

    formatted_str += f"Tind Link: {tind_link(tind_rec['tind_id'])}"

    return formatted_str
