"""
Formats and validates PyMARC records for Willa.
"""

from typing import Any

from pymarc import Record


def field_required(pymarc_record: Record) -> None:
    """Ensure the given record has values for fields 001 and 245.

    :param Record pymarc_record: The record to check.
    :raises KeyError: If required values are not present.
    """
    errors = []
    if '245' not in pymarc_record or pymarc_record['245']['a'] is None:
        errors.append("245 missing or None")

    if '001' not in pymarc_record or pymarc_record['001'].data is None:
        errors.append("001 missing or None")

    if len(errors) > 0:
        raise KeyError(", ".join(errors))


def get_generic_fields(pymarc_record: Record) -> dict:
    """Process a record into a ``dict``; missing values will be set to None.

    :param Record pymarc_record: The record to process.
    :returns dict: The processed PyMARC record as a ``dict`` of values.
    """

    fields_hash: dict[str, Any] = {}
    arr = ['001', '041', '100', '110', '111', '245', '336', '520', '540', '600',
           '610', '611', '650', '651', '700', '710', '711', '909']

    for key in arr:
        if key not in pymarc_record:
            fields_hash[key] = None
        else:
            fields = pymarc_record.get_fields(key)
            if len(fields) > 1:
                fields_hash[key] = [rec.value() for rec in fields]
            else:
                fields_hash[key] = pymarc_record[key].value()

    return fields_hash


def get_sub_by_field_and_indicators(record: Record, field_tag: str,
                                    ind1: str | None = None, ind2: str | None = None,
                                    subfield_code: str | None = None) -> list | str | None:
    """
    Retrieve subfields from a PyMARC record based on field tag, indicators, and subfield code.

    :param Record record: The record to process.
    :param str field_tag: The field tag.
    :param str|None ind1: The first indicator (or None for no indicator).
    :param str|None ind2: The second indicator (or None for no indicator).
    :param str|None subfield_code: The subfield code (or None for no code).

    :returns: Either a ``list`` of fields or a ``str`` for a single field.
    :rtype: list | str | None
    """
    results: list[str] = []

    for field in record.get_fields(field_tag):
        if (ind1 is None or field.indicator1 == ind1) and \
           (ind2 is None or field.indicator2 == ind2):
            if subfield_code:
                results.extend(field.get_subfields(subfield_code))
            else:
                results.extend(subfield.value for subfield in field.subfields)

    if not results:
        return None
    if len(results) == 1:
        return results[0]

    return results


def parse_pymarc(pymarc_record: Record) -> dict:
    """Parse a PyMARC record into a ``dict`` suitable for document parsing.

    :param Record pymarc_record: The record to parse.
    :returns dict: A ``dict`` containing all relevant MARC fields.
                   Missing fields will be set to None.
    """

    # Will raise error if there is no '001' or '245'
    field_required(pymarc_record)

    marc_values = get_generic_fields(pymarc_record)

    marc_values['85642u'] = get_sub_by_field_and_indicators(pymarc_record, '856', '4', '2', 'u')
    marc_values['852__c'] = get_sub_by_field_and_indicators(pymarc_record, '852', ' ', ' ', 'c')
    marc_values['982__b'] = get_sub_by_field_and_indicators(pymarc_record, '982', None, None, 'b')
    marc_values['260__c'] = get_sub_by_field_and_indicators(pymarc_record, '260', None, None, 'c')

    return marc_values


KEY_MAPPINGS: dict = {
    '001': 'tind_id',
    '041': 'language',
    '100': 'creator',
    '110': 'creator',
    '111': 'creator',
    '245': 'title',
    '260__c': 'date',
    '336': 'type',
    '520': 'description',
    '540': 'rights',
    '600': 'subject',
    '610': 'subject',
    '611': 'subject',
    '650': 'subject',
    '651': 'coverage',
    '700': 'contributor',
    '710': 'contributor',
    '711': 'contributor',
    '852__c': 'publisher',
    '85642u': 'references',
    '909': 'source',
    '982__b': 'isPartOf'
}
"""The mapping of MARC fields/subfields into metadata keys."""


def pymarc_to_metadata(record: Record) -> dict:
    """Parse a PyMARC record into document metadata.

    :param Record record: The record to parse.
    :returns dict: A ``dict`` containing document metadata.
    """
    marc_values = parse_pymarc(record)

    metadata: dict[str, str | list | None] = {}
    for key, value in marc_values.items():
        meta_key = KEY_MAPPINGS[key]
        if meta_key in metadata:
            if value is None:
                continue  # Skip adding blanks to existing content.

            if isinstance(metadata[meta_key], str):
                metadata[meta_key] = [metadata[meta_key]]  # Turn our str into a one-element list.
            elif metadata[meta_key] is None:
                metadata[meta_key] = []

            if isinstance(value, list):
                # Add our list to the list.
                metadata[meta_key].extend(value)  # type: ignore[union-attr]
            else:
                # Add our value to the list.
                metadata[meta_key].append(value)  # type: ignore[union-attr]
        else:
            metadata[meta_key] = value

    for meta_key in set(KEY_MAPPINGS.values()):
        if meta_key not in metadata:
            metadata[meta_key] = None

    return metadata
