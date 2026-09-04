"""Functions for transforming Yoda JSON to DataCite 4.4 JSON."""

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from typing import List, Optional

from dateutil import parser

from util import *

# Mapping between Yoda metadata license names and SPDX License Identifiers.
spdx_map = {
    "Creative Commons Attribution 4.0 International Public License": "CC-BY-4.0",
    "Creative Commons Attribution-ShareAlike 4.0 International Public License": "CC-BY-SA-4.0",
    "Creative Commons Attribution-NonCommercial 4.0 International Public License": "CC-BY-NC-4.0",
    "Creative Commons Attribution-NoDerivs 4.0 International Public License": "CC-BY-ND-4.0",
    "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International Public License": "CC-BY-NC-SA-4.0",
    "Creative Commons Attribution-NonCommercial-NoDerivs 4.0 International Public License": "CC-BY-NC-ND-4.0",
    "Creative Commons Zero v1.0 Universal": "CC0-1.0",
    "Open Data Commons Attribution License (ODC-By) v1.0": "ODC-By-1.0"
}


def create_datacite_json(ctx: rule.Context, landing_page_url: str, combi_path: str) -> dict:
    """Based on content of combi json, get Datacite metadata as a dict.

    :param ctx:              Combined type of a callback and rei struct
    :param landing_page_url: URL of the landing page
    :param combi_path:       Path to the combined JSON file that holds both user and system metadata

    :returns: dict -- Holding Datacite formatted metadata of Yoda
    """

    combi = jsonutil.read(ctx, combi_path)

    doi = get_DOI(combi)
    doi_parts = doi.split('/')

    # Collect the metadata in datacite format
    metadata = {}
    metadata['data'] = {
        "id": get_DOI(combi),
        "type": "dois",
        "attributes": {
            "event": "publish",
            "doi": doi,
            "prefix": doi_parts[0],
            "suffix": doi_parts[1],
            "identifiers": get_identifiers(combi),
            "creators": get_creators(combi),
            "titles": get_titles(combi),
            "publisher": get_publisher(combi),
            "publicationYear": get_publication_year(combi),
            "subjects": get_subjects(combi),
            "contributors": get_contributors(combi),
            "dates": get_dates(combi),
            "language": get_language(combi),
            "types": get_resource_type(combi),
            "relatedIdentifiers": get_related_resources(combi),
            "version": get_version(combi),
            "rightsList": get_rights_list(combi),
            "descriptions": get_descriptions(combi),
            "geoLocations": get_geo_locations(combi),
            "fundingReferences": get_funders(combi),
            "url": landing_page_url,
            "schemaVersion": "http://datacite.org/schema/kernel-4"    # schemaversion to be adjusted!!!!
        }
    }
    return metadata


def get_DOI(combi: dict) -> str:
    return combi['System']['Persistent_Identifier_Datapackage']['Identifier']


def get_identifiers(combi: dict) -> List:
    return [{'identifier': combi['System']['Persistent_Identifier_Datapackage']['Identifier'],
             'identifierType': 'DOI'}]


def get_titles(combi: dict) -> List:
    return [{'title': combi['Title'], 'language': 'en-us'}]


def get_descriptions(combi: dict) -> List:
    return [{'description': combi['Description'], 'descriptionType': 'Abstract'}]


def get_publisher(combi: dict) -> str:
    return config.datacite_publisher


def get_publication_year(combi: dict) -> str:
    return combi['System']['Publication_Date'][0:4]


def get_subjects(combi: dict) -> List:
    """Get list in DataCite format containing:

       1) standard objects like tags/discipline
       2) free items, for now specifically for GEO schemas

    :param combi: Combined JSON file that holds both user and system metadata

    :returns: list of subjects in DataCite format
    """
    def format_fos(s: str) -> Optional[str]:
        if not isinstance(s, str) or '-' not in s:
            return None
        sub = s.split('-', 1)[1].split('(', 1)[0].strip()
        return f"FOS: {sub}" if sub else None

    subjects = []
    for discipline in combi.get('Discipline', []):
        if fos_discipline := format_fos(discipline):
            subjects.append({'subject': fos_discipline, 'subjectScheme': 'Fields of Science and Technology (FOS)', 'schemeUri': 'http://www.oecd.org/science/inno/38235147.pdf'})
        else:
            subjects.append({'subject': discipline})

    # Assume that there is only one keyword field,
    # either called TreeKeyword or Keyword
    if "TreeKeyword" in combi:
        subjects.extend(combi["TreeKeyword"])
    else:
        for keyword in combi.get('Keyword', []):
            subjects.append({'subject': keyword, 'subjectScheme': 'Keyword'})

    # for backward compatibility. Tag will become obsolete
    for tag in combi.get('Tag', []):
        subjects.append({'subject': tag, 'subjectScheme': 'Keyword'})

    # Geo schemas have some specific fields that need to be added as subject.
    # Sort of freely usable fields
    subject_fields = ['Main_Setting',
                      'Process_Hazard',
                      'Geological_Structure',
                      'Geomorphological_Feature',
                      'Material',
                      'Apparatus',
                      'Monitoring',
                      'Software',
                      'Measured_Property',
                      'Pore_Fluid',
                      'Ancillary_Equipment',
                      'Inferred_Deformation_Behaviour']

    # for each subject field that exists in the metadata...
    for field in subject_fields:
        for x in combi.get(field, []):
            subjects.append({'subject': x, 'subjectScheme': field})

    return subjects


def get_funders(combi: dict) -> List:
    funders = []
    try:
        for funder in combi.get('Funding_Reference', []):
            funders.append({'funderName': funder['Funder_Name'],
                            'awardNumber': {'awardNumber': funder['Award_Number']}})
    except KeyError:
        pass

    return funders


def _process_affiliations_list(inputdata: List) -> List[dict]:
    """Internal function for processing a list of affiliations

    :param inputdata: List of affiliations in Yoda metadata format

    :returns: List of dictionaries with affiliation data in DataCite format
    """
    affiliations: List[dict] = []
    for aff in inputdata:
        affiliation_data = {}
        if isinstance(aff, dict):
            if "Affiliation_Name" in aff and len(aff["Affiliation_Name"]):
                affiliation_data["name"] = str(aff['Affiliation_Name'])
            if "Affiliation_Identifier" in aff and len(aff["Affiliation_Identifier"]):
                affiliation_data["affiliationIdentifier"] = aff['Affiliation_Identifier']
                affiliation_data["affiliationIdentifierScheme"] = "ROR"
        elif isinstance(aff, str) and len(aff):
            affiliation_data["name"] = aff

        if len(affiliation_data) > 0:
            affiliations.append(affiliation_data)

    return affiliations


def get_creators(combi: dict) -> List:
    """Return creator information in DataCite format.

    :param combi: Combined JSON file that holds both user and system metadata

    :returns: JSON element with creators in DataCite format
    """
    all_creators = []

    for creator in combi.get('Creator', []):
        affiliations = []

        aff_list = creator.get('Affiliation', [])
        # if affiliation is string, transform it to list to process
        if isinstance(aff_list, str):
            aff_list = [aff_list]

        affiliations = _process_affiliations_list(aff_list)

        name_ids = []
        for pid in creator.get('Person_Identifier', []):
            if 'Name_Identifier' in pid and 'Name_Identifier_Scheme' in pid:
                name_ids.append({'nameIdentifier': pid['Name_Identifier'],
                                 'nameIdentifierScheme': pid['Name_Identifier_Scheme']})

        all_creators.append({'creatorName': creator['Name']['Family_Name'] + ', ' + creator['Name']['Given_Name'],
                             'nameType': 'Personal',
                             'givenName': creator['Name']['Given_Name'],
                             'familyName': creator['Name']['Family_Name'],
                             'affiliation': affiliations,
                             'nameIdentifiers': name_ids})
    return all_creators


def get_contributors(combi: dict) -> List:
    """Get string in DataCite format containing contributors,
       including contact persons if these were added explicitly (GEO).

    :param combi: Combined JSON file that holds both user and system metadata

    :returns: JSON element with contributors in DataCite format
    """
    all = []
    # 1) Contributor
    for person in combi.get('Contributor', []):
        aff_list = person.get('Affiliation', [])
        # if affiliation is string, transform it to list to process
        if isinstance(aff_list, str):
            aff_list = [aff_list]

        affiliations = _process_affiliations_list(aff_list)

        name_ids = []
        for pid in person.get('Person_Identifier', []):
            if 'Name_Identifier' in pid and 'Name_Identifier_Scheme' in pid:
                name_ids.append({'nameIdentifier': pid['Name_Identifier'],
                                 'nameIdentifierScheme': pid['Name_Identifier_Scheme']})

        try:
            all.append({'name': person['Name']['Family_Name'] + ', ' + person['Name']['Given_Name'],
                        'nameType': 'Personal',
                        # 'givenName': person['Name']['Given_Name'],
                        # 'familyName': person['Name']['Family_Name'],
                        'affiliation': affiliations,
                        'contributorType':  person['Contributor_Type'],
                        'nameIdentifiers': name_ids})
        except KeyError:
            pass

    # 2) Contactperson
    for person in combi.get('ContactPerson', []):
        aff_list = person.get('Affiliation', [])
        # if affiliation is string, transform it to list to process
        if isinstance(aff_list, str):
            aff_list = [aff_list]

        affiliations = _process_affiliations_list(aff_list)

        name_ids = []
        for pid in person.get('Person_Identifier', []):
            if 'Name_Identifier' in pid and 'Name_Identifier_Scheme' in pid:
                name_ids.append({'nameIdentifier': pid['Name_Identifier'],
                                 'nameIdentifierScheme': pid['Name_Identifier_Scheme']})

        try:
            all.append({'name': person['Name']['Family_Name'] + ', ' + person['Name']['Given_Name'],
                        'nameType': 'Personal',
                        'givenName': person['Name']['Given_Name'],
                        'familyName': person['Name']['Family_Name'],
                        'affiliation': affiliations,
                        'contributorType': 'Contact',
                        'nameIdentifiers': name_ids})
        except KeyError:
            pass

    return all


def get_dates(combi: dict) -> List:
    """Return list of dates in DataCite format.

    :param combi: Combined JSON file that holds both user and system metadata

    :returns: JSON element with dates in DataCite format
    """

    # Format dates for DataCite: https://datacite-metadata-schema.readthedocs.io/en/4.6/properties/date/
    publication_date = combi.get('System', {}).get('Publication_Date')
    publication_date = parser.parse(publication_date)
    publication_date = publication_date.strftime('%Y-%m-%dT%H:%M:%S%z')

    last_modified_date = combi.get('System', {}).get('Last_Modified_Date')
    last_modified_date = parser.parse(last_modified_date)
    last_modified_date = last_modified_date.strftime('%Y-%m-%dT%H:%M:%S%z')

    dates = [
        {
            'date': publication_date,
            'dateType': 'Issued'
        },
        {
            'date': last_modified_date,
            'dateType': 'Updated'
        }
    ]

    embargo_end_date = combi.get('Embargo_End_Date')
    if embargo_end_date is not None:
        dates.append({'date': embargo_end_date, 'dateType': 'Available'})

    collected = combi.get('Collected')
    if collected is not None:
        try:
            x = collected.get('Start_Date')
            y = collected.get('End_Date')
            if x is not None and y is not None:
                dates.append({'date': f'{x}/{y}', 'dateType': 'Collected'})
        except KeyError:
            pass

    coverage = combi.get('Coverage')
    if coverage is not None:
        try:
            x = coverage.get('Start_Date')
            y = coverage.get('End_Date')
            if x is not None and y is not None:
                dates.append({'date': f'{x}/{y}', 'dateType': 'Coverage'})
        except KeyError:
            pass

    withdrawn_date = combi['System'].get('Withdrawn_Date')
    if withdrawn_date is not None:
        dates.append({'date': withdrawn_date, 'dateType': 'Withdrawn'})

    return dates


def get_version(combi: dict) -> str:
    """Get string in DataCite format containing version info."""
    return combi.get('Version', '')


def get_rights_list(combi: dict) -> List:
    """Get list in DataCite format containing rights related information."""
    data_access_restriction = combi['Data_Access_Restriction']
    options = {'Open':       'info:eu-repo/semantics/openAccess',
               'Restricted': 'info:eu-repo/semantics/restrictedAccess',
               'Closed':     'info:eu-repo/semantics/closedAccess'}

    rights_list = [{'rights': data_access_restriction,
                    'rightsUri': options[data_access_restriction.split()[0]]}]

    license = combi['License']
    if license == 'Custom' and data_access_restriction.startswith('Open'):
        rights_list.append({'rights': license,
                            'rightsUri': f"{combi['System']['Open_access_Link']}"})
    elif license != 'Custom':
        # Map license name to SPDX identifier.
        if license in spdx_map:
            rights_list.append({'rights': license,
                                'rightsUri': combi['System']['License_URI'],
                                'schemeUri': 'https://spdx.org/licenses/',
                                'rightsIdentifier': spdx_map[license],
                                'rightsIdentifierScheme': 'SPDX'})
        else:
            rights_list.append({'rights': license,
                                'rightsUri': combi['System']['License_URI']})

    return rights_list


def get_language(combi: dict) -> str:
    """Get string in DataCite format containing language."""
    language = ""

    try:
        if 'Language' in combi:
            language = combi['Language'].split('-')[0].strip()
    except KeyError:
        pass

    return language


def get_resource_type(combi: dict) -> dict:
    """Get dict in DataCite format containing Resource type and default handling."""
    """
    "types": {
        "ris": "DATA",
        "bibtex": "misc",
        "citeproc": "dataset",
        "schemaOrg": "Dataset",
        "resourceType": "Research Data",
        "resourceTypeGeneral": "Dataset"}
    """
    types = {'Dataset':   'Research Data',
             'DataPaper': 'Method Description',
             'Software':  'Computer code',
             'Model':     'Model'}

    # if not in combi or not in types default to 'Text'
    type = combi.get('Data_Type', 'Text')
    if type not in types:
        type = 'Text'

    descr = {'Dataset':   'Research Data',
             'DataPaper': 'Method Description',
             'Software':  'Computer code',
             'Model':     'Model'}\
        .get(type, 'Other Document')

    return {"resourceTypeGeneral": type, "resourceType": descr}


def get_related_resources(combi: dict) -> List:
    """Get list in DataCite format containing related datapackages."""
    """
  "relatedIdentifiers": [
    {
      "relationType": "IsSupplementTo",
      "relatedIdentifier": "Identifier: 02-09-2019 02:30:59",
      "relatedIdentifierType": "ARK"
    }
  ],
    """
    related_dps = []

    # For backwards compatibility.
    if "Related_Datapackage" in combi:
        for rel in combi['Related_Datapackage']:
            try:
                related_dps.append({'relatedIdentifier': rel['Persistent_Identifier']['Identifier'],
                                    'relatedIdentifierType': rel['Persistent_Identifier']['Identifier_Scheme'],
                                    'relationType': rel['Relation_Type'].split(':')[0]})
            except KeyError:
                pass

    if "Related_Resource" in combi:
        for rel in combi['Related_Resource']:
            try:
                related_dps.append({'relatedIdentifier': rel['Persistent_Identifier']['Identifier'],
                                    'relatedIdentifierType': rel['Persistent_Identifier']['Identifier_Scheme'],
                                    'relationType': rel['Relation_Type'].split(':')[0]})
            except KeyError:
                pass

    return related_dps


def get_geo_locations(combi: dict) -> List:
    """Get list of geoLocation elements in datacite format containing the information of geo locations.

       There are two versions of this:
       1) Default schema - only textual representation of
       2) Geo schema including map (=bounding box or marker/point information) Including temporal and spatial descriptions
       Both are mutually exclusive.
       I.e. first test presence of 'geoLocation'. Then test presence of 'Covered_Geolocation_Place'

    :param combi: Combined JSON file that holds both user and system metadata

    :returns: list of dictionary elements with information of geo locations in DataCite format
    """

    geoLocations = []

    try:
        if 'GeoLocation' in combi:
            for geoloc in combi['GeoLocation']:
                geo_location = {}

                if 'Description_Spatial' in geoloc:
                    geo_location['geoLocationPlace'] = geoloc['Description_Spatial']

                if 'geoLocationBox' in geoloc:
                    lon0 = str(geoloc['geoLocationBox']['westBoundLongitude'])
                    lat0 = str(geoloc['geoLocationBox']['northBoundLatitude'])
                    lon1 = str(geoloc['geoLocationBox']['eastBoundLongitude'])
                    lat1 = str(geoloc['geoLocationBox']['southBoundLatitude'])

                    if lon0 == lon1 and lat0 == lat1:  # Dealing with a point.
                        geo_location['geoLocationPoint'] = {'pointLongitude': lon0,
                                                            'pointLatitude': lat0}
                    else:
                        geo_location['geoLocationBox'] = {'westBoundLongitude': lon0,
                                                          'eastBoundLongitude': lon1,
                                                          'southBoundLatitude': lat0,
                                                          'northBoundLatitude': lat1}

                geoLocations.append(geo_location)
    except KeyError:
        pass

    try:
        if 'Covered_Geolocation_Place' in combi:
            for location in combi['Covered_Geolocation_Place']:
                if location:
                    geoLocations.append({'geoLocationPlace': location})
    except KeyError:
        pass

    return geoLocations
