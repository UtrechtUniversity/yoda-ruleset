# -*- coding: utf-8 -*-
"""JSON schema transformation functions."""

__copyright__ = 'Copyright (c) 2019-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import re

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

def _default0_default1(ctx, m):
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


def _default1_default2(ctx, m):
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


def _default2_default3(ctx, m):
    """
    Add affiliation identifiers to creators and contributors.

    Tags are renamed to Keywords, Related Datapackage renamed to Related Resource and improved Affiliation and Person Identifiers.

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to transform (default-2)

    :returns: Transformed (default-3) JSON object
    """
    if m.get('Creator', False):
        # For this creator step through all its affiliations
        for creator in m['Creator']:
            affiliations = []
            for affiliation in creator['Affiliation']:
                affiliations.append({"Affiliation_Name": affiliation, "Affiliation_Identifier": ""})
            creator['Affiliation'] = affiliations

            person_identifiers = []
            for person_identifier in creator.get('Person_Identifier', []):
                if person_identifier.get('Name_Identifier_Scheme', None) == 'ORCID':
                    # Check for incorrect ORCID format.
                    if not re.search("^(https://orcid.org/)[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$", person_identifier.get('Name_Identifier', None)):
                        corrected_orcid = correctify_orcid(person_identifier['Name_Identifier'])
                        # Only it an actual correction took place change the value and mark this data as 'changed'.
                        if corrected_orcid is None:
                            log.write(ctx, "Warning: could not correct ORCID %s during schema transformation. It needs to be fixed manually."
                                      % (person_identifier['Name_Identifier']))
                        elif corrected_orcid != person_identifier['Name_Identifier']:
                            person_identifier['Name_Identifier'] = corrected_orcid
                elif person_identifier.get('Name_Identifier_Scheme', None) == 'ResearcherID (Web of Science)':
                    # Check for incorrect ResearcherID format.
                    if not re.search("^(https://www.researcherid.com/rid/)[A-Z]-[0-9]{4}-[0-9]{4}$", person_identifier.get('Name_Identifier', None)):
                        corrected_researcher_id = correctify_researcher_id(person_identifier['Name_Identifier'])
                        # Only it an actual correction took place change the value and mark this data as 'changed'.
                        if corrected_researcher_id != person_identifier['Name_Identifier']:
                            person_identifier['Name_Identifier'] = corrected_researcher_id
                elif 'Name_Identifier_Scheme' not in person_identifier:
                    continue

                person_identifiers.append({"Name_Identifier_Scheme": person_identifier['Name_Identifier_Scheme'], "Name_Identifier": person_identifier['Name_Identifier']})

            if len(person_identifiers) > 0:
                creator['Person_Identifier'] = person_identifiers

    if m.get('Contributor', False):
        # For this contributor step through all its affiliations
        for contributor in m['Contributor']:
            affiliations = []
            if contributor.get('Affiliation', False):
                for affiliation in contributor['Affiliation']:
                    affiliations.append({"Affiliation_Name": affiliation, "Affiliation_Identifier": ""})
                contributor['Affiliation'] = affiliations

            person_identifiers = []
            for person_identifier in contributor.get('Person_Identifier', []):
                if person_identifier.get('Name_Identifier_Scheme', None) == 'ORCID':
                    # Check for incorrect ORCID format.
                    if not re.search("^(https://orcid.org/)[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$", person_identifier.get('Name_Identifier', None)):
                        corrected_orcid = correctify_orcid(person_identifier['Name_Identifier'])
                        # Only it an actual correction took place change the value and mark this data as 'changed'.
                        if corrected_orcid is None:
                            log.write(ctx, "Warning: could not correct ORCID %s during schema transformation. It needs to be fixed manually."
                                      % (person_identifier['Name_Identifier']))
                        elif corrected_orcid != person_identifier['Name_Identifier']:
                            person_identifier['Name_Identifier'] = corrected_orcid
                elif person_identifier.get('Name_Identifier_Scheme', None) == 'ResearcherID (Web of Science)':
                    # Check for incorrect ResearcherID format.
                    if not re.search("^(https://www.researcherid.com/rid/)[A-Z]-[0-9]{4}-[0-9]{4}$", person_identifier.get('Name_Identifier', None)):
                        corrected_researcher_id = correctify_researcher_id(person_identifier['Name_Identifier'])
                        # Only it an actual correction took place change the value and mark this data as 'changed'.
                        if corrected_researcher_id != person_identifier['Name_Identifier']:
                            person_identifier['Name_Identifier'] = corrected_researcher_id
                elif 'Name_Identifier_Scheme' not in person_identifier:
                    continue

                person_identifiers.append({"Name_Identifier_Scheme": person_identifier['Name_Identifier_Scheme'], "Name_Identifier": person_identifier['Name_Identifier']})

            if len(person_identifiers) > 0:
                contributor['Person_Identifier'] = person_identifiers

    # Rename Tags to Keywords
    if m.get('Tag', False):
        keywords = []
        for tag in m['Tag']:
            keywords.append(tag)
        m['Keyword'] = keywords
        m.pop('Tag')

    # Rename Related_Datapackage to Related_Resource
    if m.get('Related_Datapackage', False):
        resources = []
        for resource in m['Related_Datapackage']:
            # Only use the identifier regarding relation type
            if resource.get('Relation_Type', False):
                resource['Relation_Type'] = resource['Relation_Type'].split(':')[0]
            resources.append(resource)
        m['Related_Resource'] = resources
        m.pop('Related_Datapackage')

    # Restricted or closed data packages can't have open license.
    data_access_restriction = m.get('Data_Access_Restriction', "")
    if data_access_restriction == "Restricted - available upon request" or data_access_restriction == "Closed":
        m['License'] = "Custom"

    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/default-3/metadata.json')

    return m


def _core1_core2(ctx, m):
    """
    Add affiliation identifiers to creators.

    Tags are renamed to Keywords.

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to transform (core-1)

    :returns: Transformed (core-2) JSON object
    """
    if m.get('Creator', False):
        # For this creator step through all its affiliations
        for creator in m['Creator']:
            new_affiliations = []
            for affiliation in creator['Affiliation']:
                new_affiliations.append({"Affiliation_Name": affiliation, "Affiliation_Identifier": ""})
            creator['Affiliation'] = new_affiliations

    # Rename Tags to Keywords
    if m.get('Tag', False):
        keywords = []
        for tag in m['Tag']:
            keywords.append(tag)
        m['Keyword'] = keywords
        m.pop('Tag')

    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/core-2/metadata.json')

    return m


def _dag0_default2(ctx, m):
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


def _default1_teclab0(ctx, m):
    """
    Transform Default-1 data to the teclab-0 schema definition

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to be transformed (default-1)

    :returns: Transformed (teclab-0) JSON object
    """

    # First bring to default2 level
    m = _default1_default2(ctx, m)

    # 1) REQUIRED FIELDS
    m['Discipline'] = ['Analogue modelling of geologic processes']
    m['Lab'] = ['aa45f98e5c098237d0c57b58e5f953e1']

    m['Main_Setting'] = ['basin plain setting']
    m['Process_Hazard'] = ['deformation']
    m['Geological_Structure'] = ['fault']
    m['Geomorphological_Feature'] = ['alluvial and fluvial features']
    m['Material'] = ['sedimentary rock - limestone - Solnhofen limestone']
    m['Apparatus'] = ['2D Convection box']
    m['Software'] = ['CloudCompare']
    m['Measured_Property'] = ['Bulk modulus']

    if not m.get('Data_Type', False):
        m['Data_Type'] = 'Dataset'

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

    # Funding reference is not a required field, but if present in def1 then an extra field is required
    if m.get('Funding_Reference', False):
        for fun_ref in m['Funding_Reference']:
            fun_ref['Funder_Reference'] = 'Funder_Reference'

    # 3) REMOVE ATTRIBUTES that are not part of teclab-0
    try:
        m.pop('Covered_Geolocation_Place')
    except KeyError:
        pass

    try:
        m.pop('Covered_Period')
    except KeyError:
        pass

    try:
        m.pop('Retention_Information')
    except KeyError:
        pass

    try:
        m.pop('Collection_Name')
    except KeyError:
        pass

    # 4) SET CORRECT META SCHEMA
    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/teclab-0/metadata.json')

    return m


def _default1_hptlab0(ctx, m):
    """
    Transform Default-1 data to the hptlab-0 schema definition

    :param ctx: Combined type of a callback and rei struct
    :param m:   Metadata to be transformed (default-1)

    :returns: Transformed (hptlab-0) JSON object

    """
    # First bring to default2 level
    m = _default1_default2(ctx, m)

    # 1) REQUIRED FIELDS
    m['Discipline'] = ['Rock and melt physical properties']
    m['Lab'] = ['e3a4f5d02528d02c516dbea19c20b32c']

    # Material, Apparatus and Apparatus might get different default values (email Vincent Brunst 15 oct)
    # Pore_Fluid list still to be defined
    m['Material'] = ['sedimentary rock - limestone - Solnhofen limestone']
    m['Apparatus'] = ['deformation testing - compression testing - confining pressure vessel']
    m['Measured_Property'] = ['strength  - tensile strength']
    m['Pore_Fluid'] = ['vacuum']

    if not m.get('Data_Type', False):
        m['Data_Type'] = 'Dataset'

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

    # Funding reference is not a required field, but if present in def1 then an extra field is required
    if m.get('Funding_Reference', False):
        for fun_ref in m['Funding_Reference']:
            fun_ref['Funder_Reference'] = 'Funder_Reference'

    # 3) REMOVE ATTRIBUTES that are not part of hptlab-0
    try:
        m.pop('Covered_Geolocation_Place')
    except KeyError:
        pass

    try:
        m.pop('Covered_Period')
    except KeyError:
        pass

    try:
        m.pop('Retention_Information')
    except KeyError:
        pass

    try:
        m.pop('Collection_Name')
    except KeyError:
        pass

    # 4) SET CORRECT META SCHEMA
    meta.metadata_set_schema_id(m, 'https://yoda.uu.nl/schemas/hptlab-0/metadata.json')

    return m


def _hptlab0_hptlab1(ctx, m):
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
                for i, elem in enumerate(reference_list):
                    if item_search.lower() in elem.lower():
                        found = True
                        new_list.append(elem)
                        break
                if not found:
                    for i, elem in enumerate(reference_list):
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


def _teclab0_teclab1(ctx, m):
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
                for i, elem in enumerate(reference_list):
                    if item_search.lower() in elem.lower():
                        found = True
                        new_list.append(elem)
                        break
                if not found:
                    for i, elem in enumerate(reference_list):
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

    transformations = {'https://yoda.uu.nl/schemas/dag-0/metadata.json':
                       {'https://yoda.uu.nl/schemas/default-2/metadata.json': _dag0_default2},
                       'https://yoda.uu.nl/schemas/default-0/metadata.json':
                       {'https://yoda.uu.nl/schemas/default-1/metadata.json': _default0_default1},
                       'https://yoda.uu.nl/schemas/default-1/metadata.json':
                       {'https://yoda.uu.nl/schemas/default-2/metadata.json': _default1_default2},
                       'https://yoda.uu.nl/schemas/default-2/metadata.json':
                       {'https://yoda.uu.nl/schemas/default-3/metadata.json': _default2_default3},
                       'https://yoda.uu.nl/schemas/core-1/metadata.json':
                       {'https://yoda.uu.nl/schemas/core-2/metadata.json': _core1_core2},
                       'https://yoda.uu.nl/schemas/hptlab-0/metadata.json':
                       {'https://yoda.uu.nl/schemas/hptlab-1/metadata.json': _hptlab0_hptlab1},
                       'https://yoda.uu.nl/schemas/teclab-0/metadata.json':
                       {'https://yoda.uu.nl/schemas/teclab-1/metadata.json': _teclab0_teclab1}}

    x = transformations.get(src_id)
    return None if x is None else x.get(dst_id)


def correctify_orcid(org_orcid):
    """Correct illformatted ORCID."""
    # Get rid of all spaces.
    orcid = org_orcid.replace(' ', '')

    # Upper-case X.
    orcid = org_orcid.replace('x', 'X')

    # The last part should hold a valid id like eg: 1234-1234-1234-123X.
    # If not, it is impossible to correct it to the valid orcid format
    orcs = orcid.split('/')
    if not re.search("^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$", orcs[-1]):
        # Return original value.
        return org_orcid

    return "https://orcid.org/{}".format(orcs[-1])


def correctify_researcher_id(org_researcher_id):
    """Correct illformatted ResearcherID."""
    # Get rid of all spaces.
    researcher_id = org_researcher_id.replace(' ', '')

    # The last part should hold a valid id like eg: A-1234-1234
    # If not, it is impossible to correct it to the valid ResearcherID format
    orcs = researcher_id.split('/')
    if not re.search("^[A-Z]-[0-9]{4}-[0-9]{4}$", orcs[-1]):
        # Return original value.
        return org_researcher_id

    return "https://www.researcherid.com/rid/{}".format(orcs[-1])
