"""
Formats and validates PyMARC records for Willa.
"""

from pymarc import Record


def field_required(pymarc_record: Record) -> None:
    """Ensure the given record has values for fields 001 and 245.

    :param pymarc_record: The record to check.
    :raises: KeyError if required values are not present.
    """
    errors = []
    if not '245' in pymarc_record or pymarc_record['245']['a'] is None:
        errors.append("245 missing or None")

    if not '001' in pymarc_record or pymarc_record['001'].data is None:
        errors.append("001 missing or None")

    if len(errors) > 0:
        raise KeyError(", ".join(errors))


def get_generic_fields(pymarc_record: Record) -> dict:
    """Process a record into a ``dict``; missing values will be set to None.

    :param pymarc_record: The record to process.
    :returns: The processed PyMARC record as a ``dict`` of values.
    """

    fields_hash = {}
    field_arr = ['001', '041', '100', '110', '111', '245', '336', '520', '540', '600',
           '610', '611', '650', '651', '700', '710', '711', '909']

    h = {"001": "tind_id", "041": "language", "100": "creator", "110": "creator",
         "111": "creator", "245": "title", "336": "type", "520": "description",
         "540":"rights", "600": "subject", "610": "subject", "611": "subject",
         "650": "subject", "651": "coverage", "700": "contributor", "710": "contributor",
         "711": "contributor", "909": "source"}

    for key in field_arr:
        if not key in pymarc_record:
            fields_hash[h[key]] = None
        else:
            fields = pymarc_record.get_fields(key)
            if(len(fields)) > 1:
                fields_hash[h[key]] = [rec.value() for rec in fields]
            else:
                fields_hash[h[key]] = pymarc_record[key].value()

    return fields_hash



def get_sub_by_field_and_indicators(record, field_tag, ind1=None, ind2=None, subfield_code=None) \
                                    -> list:
    """
    Retrieve subfields from a pymarc record based on field tag, indicators, and subfield code.

    :param pymarc_record: The record to process.
    :param field_tag: The field tag.
    :param ind1: first indicator
    :param ind2: second indicator 
    :param subfield_code: subfield code

    :returns: Either a ``list`` of fields or a ``str`` for a single field.
    """
    results = []
    for field in record.get_fields(field_tag):
        if (ind1 is None or field.indicator1 == ind1) and \
           (ind2 is None or field.indicator2 == ind2):
            if subfield_code:
                results.extend(field.get_subfields(subfield_code))
            else:
                results.extend(field.subfields)

    if not results:
        return None
    if len(results) == 1:
        return results[0]

    return results


def parse_pymarc(pymarc_record: Record) -> dict:
    """Parse a PyMARC record into a ``dict`` suitable for document parsing.

    :param pymarc_record: The record to parse.
    :returns: A ``dict`` containing all relevant MARC fields.
              Missing fields will be set to None.
    """

    # Will raise error if there is no '001' or '245'
    field_required(pymarc_record)

    marc_values = get_generic_fields(pymarc_record)

    marc_values['references'] = get_sub_by_field_and_indicators(pymarc_record, '856', '4','2', 'u')
    marc_values['publisher'] = get_sub_by_field_and_indicators(pymarc_record, '852', ' ',' ', 'c')
    marc_values['isPartOf'] = get_sub_by_field_and_indicators(pymarc_record, '982', None, None, 'b')
    marc_values['date'] = get_sub_by_field_and_indicators(pymarc_record, '260', None, None, 'c')

    return marc_values
