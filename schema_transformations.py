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
    Metadata fields Discipline, Language and Tags have become required fields.

    This to enable datapackages to be filtered and found more easily.

    If not present yet Language is defaulted to 'en - English'

    If not present yet a default Tag will be added containing 'yoda'

    Discipline must be present in all vault packages before migration.
    I.e. discipline must be manually added if not present yet.
    This requires an intervention by the responsible datamanager beforehand


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


def _default1_teclab0(m):
    """
    Transform Default-1 data to the teclab-0 schema definition


    :param m: Metadata to be transformed (default-1)

    :returns: Transformed (teclab-0) JSON object
    """

    # First bring to default2 level
    m = _default1_default2(m)

    # 1) REQUIRED FIELDS
    m['Discipline'] = ['Analogue modelling of geologic processes']
    m['Lab'] = ['aa45f98e5c098237d0c57b58e5f953e1']

    m['Main_Setting'] = ['basin plain setting']
    m['Process_Hazard'] = ['deformation']
    m['Geological_Structure'] = ['fault']
    m['Geomorphical_Feature'] = ['crest']
    m['Material'] = ['Air']
    m['Apparatus'] = ['Densimeter']
    m['Software'] = ['CloudCompare']
    m['Measured_Property'] = ['Cohesion']

    if not m.get('Related_Datapackage', False):
        m['Related_Datapackage'] = [{'Relation_Type': 'IsSupplementTo',
                                     'Title': 'RDP title',
                                     'Persistent_Identifier': {'Identifier_Scheme': 'ARK',
                                                               'Identifier': 'ARK123'}}]
    else:
        # Relation types of default1 have additional information in string 'IsSupplementTo: Is supplement to'
        # Stripping is required for teclab/hptlab
        for rdp in m['Related_Datapackage']:
            try:
                rdp['Relation_Type'] = rdp['Relation_Type'].split(':')[0]
            except Exception:
                rdp['Relation_Type'] = 'IsSupplementTo'

    # Contact is a special contributor of contributor type 'ContactPerson'
    # First check whether present Contributors contain contact persons.
    # If not, add a placeholder Contact
    # Loop through present Contributors.
    # If ContactPerson is present, add as a Contacts and remove from Contributors list
    new_contacts = []
    contributors_remaining = []
    if m.get('Contributor', False):
        for contributor in m['Contributor']:
            if contributor['Contributor_Type'] == 'ContactPerson':
                # Add this contributor-contact-person to contacts list
                new_contacts.append({'Name': {'Given_Name': contributor['Name']['Given_Name'], 'Family_Name': contributor['Name']['Family_Name']},
                                     'Position': 'Position',
                                     'Email': 'Email',
                                     'Affiliation': ['Affiliation'],
                                     'Person_Identifier': [{'Name_Identifier_Scheme': contributor['Person_Identifier'][0]['Name_Identifier_Scheme'],
                                                           'Name_Identifier': contributor['Person_Identifier'][0]['Name_Identifier']}]})
            else:
                # remaining list contains non-contactpersons only
                contributors_remaining.append(contributor)

    if len(new_contacts):
        # If new contacts are present
        m['Contact'] = new_contacts
        m['Contributor'] = contributors_remaining
    else:
        m['Contact'] = [{'Name': {'Given_Name': 'Contact given name', 'Family_Name': 'Contact family name'},
                         'Position': 'Position',
                         'Email': 'Email',
                         'Affiliation': ['Affiliation'],
                         'Person_Identifier': [{'Name_Identifier_Scheme': '',
                                               'Name_Identifier': ''}]}]

    # 2) SPECIFIC TRANSFORMATION combining different attributes
    # GeoBox - derived from Covered_Geolocation_Place and Covered_Period
    # spatial = ', '.join(m['Covered_Geolocation_Place'])
    try:
        m['GeoLocation'] = [{'geoLocationBox': {'northBoundLatitude': 0.0,
                                                'westBoundLongitude': 0.0,
                                                'southBoundLatitude': 0.0,
                                                'eastBoundLongitude': 0.0},
                             'Description_Spatial': ', '.join(m['Covered_Geolocation_Place']),
                             'Description_Temporal': {'Start_Date': m['Covered_Period']['Start_Date'], 'End_Date': m['Covered_Period']['End_Date']}}]
    except Exception:
        pass

    # 3) REMOVE ATTRIBUTES that are not part of teclab-0
    m.pop('Covered_Geolocation_Place')
    m.pop('Covered_Period')
    m.pop('Retention_Information')
    m.pop('Collection_Name')

    # 4) SET CORRECT META SCHEMA
    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/teclab-0/metadata.json')

    return m


def _default1_hptlab0(m):
    """
    Transform Default-1 data to the hptlab-0 schema definition


    :param m: Metadata to be transformed (default-1)

    :returns: Transformed (hptlab-0) JSON object

    """
    # First bring to default2 level
    m = _default1_default2(m)

    # 1) REQUIRED FIELDS
    m['Discipline'] = ['Rock and melt physical properties']
    m['Lab'] = ['e3a4f5d02528d02c516dbea19c20b32c']

    m['Material'] = ['Concrete']
    m['Apparatus'] = ['Uniaxial']
    m['Measured_Property'] = ['Hardness']

    if not m.get('Related_Datapackage', False):
        m['Related_Datapackage'] = [{'Relation_Type': 'IsSupplementTo',
                                     'Title': 'RDP title',
                                     'Persistent_Identifier': {'Identifier_Scheme': 'ARK',
                                                               'Identifier': 'ARK123'}}]
    else:
        # Relation types of default1 have additional information in string 'IsSupplementTo: Is supplement to'
        # Stripping is required for teclab/hptlab
        for rdp in m['Related_Datapackage']:
            try:
                rdp['Relation_Type'] = rdp['Relation_Type'].split(':')[0]
            except Exception:
                rdp['Relation_Type'] = 'IsSupplementTo'

    # Contact is a special contributor of contributor type 'ContactPerson'
    # First check whether present Contributors contain contact persons.
    # If not, add a placeholder Contact
    # Loop through present Contributors.
    # If ContactPerson is present, add as a Contacts and remove from Contributors list
    new_contacts = []
    contributors_remaining = []
    if m.get('Contributor', False):
        for contributor in m['Contributor']:
            if contributor['Contributor_Type'] == 'ContactPerson':
                # Add this contributor-contact-person to contacts list
                new_contacts.append({'Name': {'Given_Name': contributor['Name']['Given_Name'], 'Family_Name': contributor['Name']['Family_Name']},
                                     'Position': 'Position',
                                     'Email': 'Email',
                                     'Affiliation': ['Affiliation'],
                                     'Person_Identifier': [{'Name_Identifier_Scheme': contributor['Person_Identifier'][0]['Name_Identifier_Scheme'],
                                                           'Name_Identifier': contributor['Person_Identifier'][0]['Name_Identifier']}]})
            else:
                # remaining list contains non-contactpersons only
                contributors_remaining.append(contributor)

    if len(new_contacts):
        # If new contacts are present
        m['Contact'] = new_contacts
        m['Contributor'] = contributors_remaining
    else:
        m['Contact'] = [{'Name': {'Given_Name': 'Contact given name', 'Family_Name': 'Contact family name'},
                         'Position': 'Position',
                         'Email': 'Email',
                         'Affiliation': ['Affiliation'],
                         'Person_Identifier': [{'Name_Identifier_Scheme': '',
                                               'Name_Identifier': ''}]}]

    # 2) SPECIFIC TRANSFORMATION combining different attributes
    # GeoBox - derived from Covered_Geolocation_Place and Covered_Period
    # spatial = ', '.join(m['Covered_Geolocation_Place'])
    try:
        m['GeoLocation'] = [{'geoLocationBox': {'northBoundLatitude': 0.0,
                                                'westBoundLongitude': 0.0,
                                                'southBoundLatitude': 0.0,
                                                'eastBoundLongitude': 0.0},
                             'Description_Spatial': ', '.join(m['Covered_Geolocation_Place']),
                             'Description_Temporal': {'Start_Date': m['Covered_Period']['Start_Date'], 'End_Date': m['Covered_Period']['End_Date']}}]
    except Exception:
        pass

    # 3) REMOVE ATTRIBUTES that are not part of hptlab-0
    m.pop('Covered_Geolocation_Place')
    m.pop('Covered_Period')
    m.pop('Retention_Information')
    m.pop('Collection_Name')

    # 4) SET CORRECT META SCHEMA
    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/hptlab-0/metadata.json')

    return m

# }}}


def get(src_id, dst_id):
    """
    Get a transformation function that maps metadata from the given src schema id to the dst schema id.

    :param src_id: The metadata's current schema id
    :param dst_id: The metadata's destination schema id

    :return: A transformation function, or None if no mapping exists for the given ids
    """
    # Simplified shortcut as these are once in a lifetime!
    if src_id == 'https://yoda.uu.nl/schemas/default-1/metadata.json':
        if dst_id == 'https://yoda.uu.nl/schemas/hptlab-0/metadata.json':
            return _default1_hptlab0
        if dst_id == 'https://yoda.uu.nl/schemas/teclab-0/metadata.json':
            return _default1_teclab0

    transformations = {'https://yoda.uu.nl/schemas/default-0/metadata.json':
                       {'https://yoda.uu.nl/schemas/default-1/metadata.json': _default0_default1},
                       'https://yoda.uu.nl/schemas/default-1/metadata.json':
                       {'https://yoda.uu.nl/schemas/default-2/metadata.json': _default1_default2}}

    x = transformations.get(src_id)
    return None if x is None else x.get(dst_id)
