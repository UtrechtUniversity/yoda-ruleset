"""JSON schema transformation functions."""
from __future__ import annotations

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re
from typing import Callable, Dict

import requests
from schema_transformations_utils import add_affiliation_identifier, correctify_personal_identifiers, merge_geo_keywords, rename_related_datapackage

import meta
from util import *


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

def _default0_default1(ctx: rule.Context, m: Dict) -> Dict:
    """
    A Data type field is added to be used for publication purposes to DataCite.

    This makes it possible to specify the type of data that is being published.
    The default data type is Dataset.

    The version number for the data package is no longer required.

    Furthermore, the metadata schema is extended with a remarks field.
    These remarks are intended for communication between researchers and datamanager.

    Finally, the creator and contributor name fields have been split into first
    and last names, to comply with the OpenAIRE standard.

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to transform (default-0)

    :returns: Transformed (default-1) JSON object
    """
    def fixup_name(n: str) -> Dict:
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


def _default1_default2(ctx: rule.Context, m: Dict) -> Dict:
    """
    Metadata fields Discipline, Language and Tags have become required fields.

    This to enable datapackages to be filtered and found more easily.

    If not present yet Language is defaulted to 'en - English'

    If not present yet a default Tag will be added containing 'yoda'

    Discipline must be present in all vault packages before migration.
    I.e. discipline must be manually added if not present yet.
    This requires an intervention by the responsible datamanager beforehand

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to transform (default-1)

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


def _default2_default3(ctx: rule.Context, m: Dict) -> Dict:
    """
    Add affiliation identifiers to creators and contributors.

    Tags are renamed to Keywords, Related Datapackage renamed to Related Resource and improved Affiliation and Person Identifiers.

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to transform (default-2)

    :returns: Transformed (default-3) JSON object
    """
    m = add_affiliation_identifier(m)
    m = correctify_personal_identifiers(m)
    m = rename_related_datapackage(m)

    # Rename Tags to Keywords
    if m.get('Tag', False):
        keywords = []
        for tag in m['Tag']:
            keywords.append(tag)
        m['Keyword'] = keywords
        m.pop('Tag')

    # Restricted or closed data packages can't have open license.
    data_access_restriction = m.get('Data_Access_Restriction', "")
    if data_access_restriction == "Restricted - available upon request" or data_access_restriction == "Closed":
        m['License'] = "Custom"

    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/default-3/metadata.json')

    return m


def _core1_core2(ctx: rule.Context, m: Dict) -> Dict:
    """
    Add affiliation identifiers to creators.

    Tags are renamed to Keywords.

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to transform (core-1)

    :returns: Transformed (core-2) JSON object
    """
    m = add_affiliation_identifier(m)

    # Rename Tags to Keywords
    if m.get('Tag', False):
        keywords = []
        for tag in m['Tag']:
            keywords.append(tag)
        m['Keyword'] = keywords
        m.pop('Tag')

    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/core-2/metadata.json')

    return m


def _dag0_default2(ctx: rule.Context, m: Dict) -> Dict:
    """
    Transform dag-0 data to the default-2 schema definition

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to be transformed (dag-0)

    :returns: Transformed (default-2) JSON object
    """
    # dag0-research group => def2
    if m.get('Research_Group', False):
        resrch_grp_2_contrib = {'Name': {'Given_Name': m['Research_Group'], 'Family_Name': ''},
                                'Affiliation': ['Affiliation'],
                                'Contributor_Type': 'ResearchGroup'}
        if m.get('Contributor', False):
            m['Contributor'].append(resrch_grp_2_contrib)
        else:
            m['Contributor'] = [resrch_grp_2_contrib]
        # Finally, get rid of Research_Group element.
        m.pop("Research_Group")

    # dag0=> def2 collection name

    # dag0-GeoLocation => def2-Covered_Geolocation_Place
    geo_places = []
    for location in m['GeoLocation']:
        if 'Description_Spatial' in location:
            geo_places.append(location['Description_Spatial'])
    if len(geo_places):
        m['Covered_Geolocation_Place'] = geo_places
    else:
        m['Covered_Geolocation_Place'] = [""]
    m.pop('GeoLocation')

    # dag0-Retention => def2-Retention
    # Get the entire metadata schema to be able to get some proper values based on the previous saved values
    old_schema = jsonutil.read(ctx, '/{}/yoda/schemas/dag-0/metadata.json'.format(user.zone(ctx)))
    retention_years_list = old_schema['definitions']['optionsRetentionPeriod']['enum']
    retention_names_list = old_schema['definitions']['optionsRetentionPeriod']['enumNames']
    m["Retention_Information"] = ""

    if m.get('Retention_Period', False):
        for i, value in enumerate(retention_years_list):
            if value == m["Retention_Period"]:
                m["Retention_Information"] = retention_names_list[i]
                break
        m["Retention_Period"] = int(m["Retention_Period"])
    else:
        m["Retention_Period"] = 0

    # dag0-Creator => def2-Creator
    for creator in m['Creator']:
        creator['Affiliation'] = [creator['Affiliation']]
        if 'Owner_Role' in creator:
            creator.pop('Owner_Role')

    # Missing data in dag0 - License  "Internal License Data Archive Geosciences 2021-01"
    m["License"] = "Custom"

    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/default-2/metadata.json')

    return m


def _hptlab0_hptlab1(ctx: rule.Context, m: Dict) -> Dict:
    """
    Transform hptlab-0 data to the hptlab-1 schema definition which holds better qualified lists.

    :param ctx: Combined type of a callback and rei struct
    :param m: Metadata to transform (hptlab-0)

    :returns: Transformed (hptlab-1) JSON object
    """
    try:
        m.pop('Monitoring')
    except KeyError:
        pass

    # Get the entire metadata schema to be able to get some proper values based on the previous saved values
    new_schema = jsonutil.read(ctx, '/{}/yoda/schemas/hptlab-1/metadata.json'.format(user.zone(ctx)))

    attributes = {'Material': 'optionsMaterial',
                  'Apparatus': 'optionsApparatus',
                  'Measured_Property': 'optionsMeasuredProperty'}

    for attribute, option_list in attributes.items():
        new_list = []
        reference_list = new_schema['definitions'][option_list]['enum']
        try:
            for item_search in m[attribute]:
                found = False
                for _i, elem in enumerate(reference_list):
                    if item_search.lower() in elem.lower():
                        found = True
                        new_list.append(elem)
                        break
                if not found:
                    for _i, elem in enumerate(reference_list):
                        # Split on ' ' an compare based on the first token
                        if item_search.split(' ')[0].lower() in elem.lower():
                            found = True
                            new_list.append(elem)
                            break
        except KeyError:
            pass

        if len(new_list):
            m[attribute] = new_list
        else:
            # Take first in the corresponding list as a default value
            m[attribute] = [new_schema['definitions'][option_list]['enum'][0]]

    # Newly introduced - no previous value present
    m['Pore_Fluid'] = [new_schema['definitions']['optionsPoreFluid']['enum'][0]]

    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/hptlab-1/metadata.json')

    return m


def _teclab0_teclab1(ctx: rule.Context, m: Dict) -> Dict:
    """
    Transform teclab-0 data to the teclab-1 schema definition which holds better qualified lists.

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to transform (teclab-0)

    :returns: Transformed (teclab-1) JSON object
    """
    new_schema = jsonutil.read(ctx, '/{}/yoda/schemas/teclab-1/metadata.json'.format(user.zone(ctx)))

    if 'Geomorphical_Feature' in m:
        # Name is no longer in use.
        m['Geomorphological_Feature'] = m['Geomorphical_Feature']
        m.pop('Geomorphical_Feature')

    attributes = {'Material': 'optionsMaterial',
                  'Apparatus': 'optionsApparatus',
                  'Measured_Property': 'optionsMeasuredProperty',
                  'Main_Setting': 'optionsMainSetting',
                  'Process_Hazard': 'optionsProcessHazard',
                  'Geological_Structure': 'optionsGeologicalStructure',
                  'Geomorphological_Feature': 'optionsGeomorphologicalFeature',
                  'Software': 'optionsSoftware'}

    for attribute, option_list in attributes.items():
        new_list = []
        reference_list = new_schema['definitions'][option_list]['enum']
        try:
            for item_search in m[attribute]:
                found = False
                for _i, elem in enumerate(reference_list):
                    if item_search.lower() in elem.lower():
                        found = True
                        new_list.append(elem)
                        break
                if not found:
                    for _i, elem in enumerate(reference_list):
                        # Split on ' ' an compare based on the first token
                        if item_search.split(' ')[0].lower() in elem.lower():
                            found = True
                            new_list.append(elem)
                            break
        except KeyError:
            pass

        if len(new_list):
            m[attribute] = new_list
        else:
            # Take first in the corresponding list as a default value
            m[attribute] = [new_schema['definitions'][option_list]['enum'][0]]

    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/teclab-1/metadata.json')

    return m


def _teclab0_eposmsl0(ctx: rule.Context, m: Dict) -> Dict:
    """
    Add affiliation identifiers to creators, contributors and contacts.
    Rename Related Datapackage field to Related Resource field.
    Merge several geo keywords into single keyword field.

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to transform (teclab-0)

    :returns: Transformed (epos-msl-0) JSON object
    """
    m = add_affiliation_identifier(m)
    m = correctify_personal_identifiers(m)
    m = rename_related_datapackage(m)
    m = merge_geo_keywords(m)
    m.pop('Dataset_Created', None)
    m.pop('Additional_Lab', None)

    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/epos-msl-0/metadata.json')

    return m


def _hptlab0_eposmsl0(ctx: rule.Context, m: Dict) -> Dict:
    """
    Add affiliation identifiers to creators, contributors and contacts.
    Rename Related Datapackage field to Related Resource field.
    Merge several geo keywords into single keyword field.

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to transform (hptlab-0)

    :returns: Transformed (epos-msl-0) JSON object
    """
    m = add_affiliation_identifier(m)
    m = correctify_personal_identifiers(m)
    m = rename_related_datapackage(m)
    m = merge_geo_keywords(m)
    m.pop('Dataset_Created', None)
    m.pop('Additional_Lab', None)

    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/epos-msl-0/metadata.json')

    return m


def _teclab1_eposmsl0(ctx: rule.Context, m: Dict) -> Dict:
    """
    Add affiliation identifiers to creators, contributors and contacts.
    Rename Related Datapackage field to Related Resource field.
    Merge several geo keywords into single keyword field.

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to transform (teclab-1)

    :returns: Transformed (epos-msl-0) JSON object
    """
    m = add_affiliation_identifier(m)
    m = correctify_personal_identifiers(m)
    m = rename_related_datapackage(m)
    m = merge_geo_keywords(m)
    m.pop('Dataset_Created', None)
    m.pop('Additional_Lab', None)

    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/epos-msl-0/metadata.json')

    return m


def _hptlab1_eposmsl0(ctx: rule.Context, m: Dict) -> Dict:
    """
    Add affiliation identifiers to creators, contributors and contacts.
    Rename Related Datapackage field to Related Resource field.
    Merge several geo keywords into single keyword field.

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to transform (hptlab-1)

    :returns: Transformed (epos-msl-0) JSON object
    """
    m = add_affiliation_identifier(m)
    m = correctify_personal_identifiers(m)
    m = rename_related_datapackage(m)
    m = merge_geo_keywords(m)
    m.pop('Dataset_Created', None)
    m.pop('Additional_Lab', None)

    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/epos-msl-0/metadata.json')

    return m


def _eposmsl0_eposmsl1(ctx: rule.Context, m: Dict) -> Dict:
    """
    Added Period covered field to indicate the temporal coverage of the resource.
    Removed Period covered field as part of Sample location(s) or modeled location(s).

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to transform (epos-msl-0)

    :returns: Transformed (epos-msl-1) JSON object
    """
    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/epos-msl-1/metadata.json')

    new_uischema = jsonutil.read(ctx, f"/{user.zone(ctx)}/yoda/schemas/epos-msl-1/uischema.json")
    vocab_url = new_uischema.get('Lab', {}).get('items', {}).get('ui:data')

    current_labs = m.get('Lab', [])
    m['Lab'] = []

    try:
        # Read the Lab vocabulary.
        labs_vocab = jsonutil.read_from_url(vocab_url)
        labs_by_id = {lab.get('identifier'): lab for lab in labs_vocab}

        for lab_value in current_labs:
            if isinstance(lab_value, str) and lab_value in labs_by_id:
                m['Lab'].append(labs_by_id[lab_value])
    except (requests.RequestException, ValueError):
        pass

    # Remove temporal description from geo locations.
    for location in m.get('GeoLocation', []):
        if 'Description_Temporal' in location:
            location.pop('Description_Temporal', None)

    return m

# }}}


def get(src_id: str, dst_id: str) -> Callable | None:
    """
    Get a transformation function that maps metadata from the given src schema id to the dst schema id.

    :param src_id: The metadata's current schema id
    :param dst_id: The metadata's destination schema id

    :return: A transformation function, or None if no mapping exists for the given ids
    """
    transformations = {
        'https://yoda.uu.nl/schemas/dag-0/metadata.json': {
            'https://yoda.uu.nl/schemas/default-2/metadata.json': _dag0_default2
        },
        'https://yoda.uu.nl/schemas/default-0/metadata.json': {
            'https://yoda.uu.nl/schemas/default-1/metadata.json': _default0_default1
        },
        'https://yoda.uu.nl/schemas/default-1/metadata.json': {
            'https://yoda.uu.nl/schemas/default-2/metadata.json': _default1_default2
        },
        'https://yoda.uu.nl/schemas/default-2/metadata.json': {
            'https://yoda.uu.nl/schemas/default-3/metadata.json': _default2_default3
        },
        'https://yoda.uu.nl/schemas/core-1/metadata.json': {
            'https://yoda.uu.nl/schemas/core-2/metadata.json': _core1_core2
        },
        'https://yoda.uu.nl/schemas/hptlab-0/metadata.json': {
            'https://yoda.uu.nl/schemas/hptlab-1/metadata.json': _hptlab0_hptlab1,
            'https://yoda.uu.nl/schemas/epos-msl-0/metadata.json': _hptlab0_eposmsl0
        },
        'https://yoda.uu.nl/schemas/teclab-0/metadata.json': {
            'https://yoda.uu.nl/schemas/teclab-1/metadata.json': _teclab0_teclab1,
            'https://yoda.uu.nl/schemas/epos-msl-0/metadata.json': _teclab0_eposmsl0
        },
        'https://yoda.uu.nl/schemas/hptlab-1/metadata.json': {
            'https://yoda.uu.nl/schemas/epos-msl-0/metadata.json': _hptlab1_eposmsl0
        },
        'https://yoda.uu.nl/schemas/teclab-1/metadata.json': {
            'https://yoda.uu.nl/schemas/epos-msl-0/metadata.json': _teclab1_eposmsl0
        },
        'https://yoda.uu.nl/schemas/epos-msl-0/metadata.json': {
            'https://yoda.uu.nl/schemas/epos-msl-1/metadata.json': _eposmsl0_eposmsl1
        }
    }

    x = transformations.get(src_id)
    return None if x is None else x.get(dst_id)
