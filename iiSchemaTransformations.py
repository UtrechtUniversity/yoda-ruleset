# \file      iiTransformations.py
# \brief     JSON schema transformation functions.
# \author    Chris Smeele
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.


# Transformation functions {{{

# Naming scheme: _transform_FROMSCHEMA_TOSCHEMA
#
# A transformation function takes a JSON object (OrderedDict) as an argument,
# and returns a new JSON object.
#
# The docstring of a transformation function should describe the transformation
# in a human-readable manner: it is provided to the user executing the transformation.

def _transform_default0_default1(m):
    """
    A Data type field is added to be used for publication purposes to DataCite.
    This makes it possible to specify the type of data that is being published.
    The default data type is Dataset.

    Furthermore, the metadata schema is extended with a remarks field.
    These remarks are intended for communication between researchers and datamanager.

    Finally, the creator and contributor name fields have been split into first
    and last names, to comply with the OpenAIRE standard.
    """

    # XXX (WIP)

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

    metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/default-1/metadata.json')

    return m

# }}}


def transformation_html(f):
    """Get a human-readable HTML description of a transformation function.
       The text is derived from the function's docstring.
    """

    return '\n'.join(map(lambda paragraph:
                     '<p>{}</p>'.format(  # Trim whitespace.
                         re.sub('\s+', ' ', paragraph).strip()),
                         # Docstring paragraphs are separated by blank lines.
                         re.split('\n{2,}', f.__doc__)))


# Maps old schemas to new schemas with their accompanying transformation function.
transformations = {'https://yoda.uu.nl/schemas/default-0/metadata.json':
                   {'https://yoda.uu.nl/schemas/default-1/metadata.json': _transform_default0_default1}}
