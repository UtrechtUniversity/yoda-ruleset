# -*- coding: utf-8 -*-
"""JSON schema transformation functions."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re

import meta

# No rules are exported by this module.
__all__ = []


# Transformation functions {{{

# Naming scheme: _FROMSCHEMA_TOSCHEMA
#
# A transformation function takes a JSON object (OrderedDict) as an argument,
# and returns a new JSON object.
#
# The docstring of a transformation function should describe the transformation
# in a human-readable manner: it is provided to the user executing the transformation.

def _default0_default1(m):
    """
    A Data type field is added to be used for publication purposes to DataCite.

    This makes it possible to specify the type of data that is being published.
    The default data type is Dataset.

    The version number for the data package is no longer required.

    Furthermore, the metadata schema is extended with a remarks field.
    These remarks are intended for communication between researchers and datamanager.

    Finally, the creator and contributor name fields have been split into first
    and last names, to comply with the OpenAIRE standard.

    :param m: Metadata to transform (default-0)

    :returns: Transformed (default-1) JSON object
    """
    def fixup_name(n):
        """Split a name into a first and last name, error-prone, but acceptable."""
        n.strip()  # Trim whitespace, if any.

        # Name contains comma? Parse as: last, first, first, first.
        ns = re.split(r'\s*,\s*', n, 1)
        if len(ns) == 2:
            return {'Given_Name': ns[1], 'Family_Name': ns[0]}

        # Name contains whitespace? Parse as: first last last last.
        ns = re.split(r'\s+', n, 1)
        if len(ns) == 2:
            return {'Given_Name': ns[0], 'Family_Name': ns[1]}

        # Neither? Parse as lastname.
        return {'Given_Name': '', 'Family_Name': n}

    for person in m['Creator']:
        if 'Name' in person:
            person['Name'] = fixup_name(person['Name'])

    if m.get('Contributor', False):
        for person in m['Contributor']:
            if 'Name' in person:
                person['Name'] = fixup_name(person['Name'])

    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/default-1/metadata.json')

    return m


def _default1_default2(m):
    """
    Metadata fields Discipline, Language and tags have become required fields.

    This to enable datapackages to be found more easily.

    Prequisite: 
    Discipline -> should be present in all vault packages before migration
    I.e. discipline must be manually added if not present yet.
    This requires a manual intervention by the responsible datamanager

    If not present yet Language is set to 'en - English'

    If not present yet a default Tag will be added containing 'yoda'

    :param m: Metadata to transform (default-1)

    :returns: Transformed (default-2) JSON object
    """
    # Only add default value when Language not yet present
    if not m.get('Language', False) or m['Language'] == "":
        m['Language'] = 'en - English'

    # Only add default value when Tag not yet present or present as a list with an empty string
    if not m.get('Tag', False) or m['Tag'] == [""]:
       m['Tag'] = ['yoda']

    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/default-2/metadata.json')

    return m


# }}}


def get(src_id, dst_id):
    """
    Get a transformation function that maps metadata from the given src schema id to the dst schema id.

    :param src_id: The metadata's current schema id
    :param dst_id: The metadata's destination schema id

    :return: A transformation function, or None if no mapping exists for the given ids
    """
    transformations = {'https://yoda.uu.nl/schemas/default-0/metadata.json':
                       {'https://yoda.uu.nl/schemas/default-1/metadata.json': _default0_default1},
                       'https://yoda.uu.nl/schemas/default-1/metadata.json':
                       {'https://yoda.uu.nl/schemas/default-2/metadata.json': _default1_default2}}

    x = transformations.get(src_id)
    return None if x is None else x.get(dst_id)
