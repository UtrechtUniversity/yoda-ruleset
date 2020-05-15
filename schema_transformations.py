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

    Furthermore, the metadata schema is extended with a remarks field.
    These remarks are intended for communication between researchers and datamanager.

    Finally, the creator and contributor name fields have been split into first
    and last names, to comply with the OpenAIRE standard.
    """

    def fixup_name(n):
        """Split a name into a first and last name.
           This algo is error-prone, but acceptable.
        """
        n.strip()  # Trim whitespace, if any.

        # Name contains comma? Parse as: last, first, first, first.
        ns = re.split(r'\s*,\s*', n, 1)
        if len(ns) == 2:
            return {'First_Name': ns[1], 'Last_Name': ns[0]}

        # Name contains whitespace? Parse as: first last last last.
        ns = re.split(r'\s+', n, 1)
        if len(ns) == 2:
            return {'First_Name': ns[0], 'Last_Name': ns[1]}

        # Neither? Parse as lastname.
        return {'First_Name': '', 'Last_Name': n}

    for person in m['Creator'] + m['Contributor']:
        if 'Name' in person:
            person['Name'] = fixup_name(person['Name'])

    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/default-1/metadata.json')

    return m

# }}}


def get(src_id, dst_id):
    """Get a transformation function that maps metadata from the given src schema id to the dst schema id.

    :param src_id: The metadata's current schema id
    :param dst_id: The metadata's destination schema id

    :return: A transformation function, or None if no mapping exists for the given ids
    """

    transformations = {'https://yoda.uu.nl/schemas/default-0/metadata.json':
                       {'https://yoda.uu.nl/schemas/default-1/metadata.json': _default0_default1}}

    x = transformations.get(src_id)
    return None if x is None else x.get(dst_id)
