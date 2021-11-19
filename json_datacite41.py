# -*- coding: utf-8 -*-
"""Functions for transforming JSON to DataCite 4.1 XML."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import xml.etree.cElementTree as ET

from util import *

__all__ = ['rule_json_datacite41_create_combi_metadata_json',
           'rule_json_datacite41_create_datacite_json']


@rule.make()
def rule_json_datacite41_create_combi_metadata_json(ctx,
                                                    metadataJsonPath,
                                                    combiJsonPath,
                                                    lastModifiedDateTime,
                                                    yodaDOI,
                                                    publicationDate,
                                                    openAccessLink,
                                                    licenseUri):
    """Frontend function to add system info to yoda-metadata in json format.


    :param ctx:                  Combined type of a callback and rei struct
    :param metadataJsonPath:     Path to the most recent vault yoda-metadata.json in the corresponding vault
    :param combiJsonPath:        Path to where the combined info will be placed so it can be used for DataciteXml & landingpage generation
                                 other are system info parameters
    :param lastModifiedDateTime: Last modification time of publication
    :param yodaDOI:              DOI of publication
    :param publicationDate:      Date of publication
    :param openAccessLink:       Open access link to data of publication
    :param licenseUri:           URI to license of publication
    """
    json_datacite41_create_combi_metadata_json(ctx,
                                               metadataJsonPath,
                                               combiJsonPath,
                                               lastModifiedDateTime,
                                               yodaDOI,
                                               publicationDate,
                                               openAccessLink,
                                               licenseUri)
    """
    # get the data in the designated YoDa metadata.json and retrieve it as dict
    metaDict = jsonutil.read(ctx, metadataJsonPath)

    # add System info
    metaDict['System'] = {
        'Last_Modified_Date': lastModifiedDateTime,
        'Persistent_Identifier_Datapackage': {
            'Identifier_Scheme': 'DOI',
            'Identifier': yodaDOI
        },
        'Publication_Date': publicationDate,
        'Open_access_Link': openAccessLink,
        'License_URI': licenseUri
    }

    # Write combined data to file at location combiJsonPath
    jsonutil.write(ctx, combiJsonPath, metaDict)

    """


def json_datacite41_create_combi_metadata_json(ctx,
                                               metadataJsonPath,
                                               combiJsonPath,
                                               lastModifiedDateTime,
                                               yodaDOI,
                                               publicationDate,
                                               openAccessLink,
                                               licenseUri):
    """Frontend function to add system info to yoda-metadata in json format.

    :param ctx:                  Combined type of a callback and rei struct
    :param metadataJsonPath:     Path to the most recent vault yoda-metadata.json in the corresponding vault
    :param combiJsonPath:        Path to where the combined info will be placed so it can be used for DataciteXml & landingpage generation
                                 other are system info parameters
    :param lastModifiedDateTime: Last modification time of publication
    :param yodaDOI:              DOI of publication
    :param publicationDate:      Date of publication
    :param openAccessLink:       Open access link to data of publication
    :param licenseUri:           URI to license of publication
    """
    # get the data in the designated YoDa metadata.json and retrieve it as dict
    metaDict = jsonutil.read(ctx, metadataJsonPath)

    # add System info
    metaDict['System'] = {
        'Last_Modified_Date': lastModifiedDateTime,
        'Persistent_Identifier_Datapackage': {
            'Identifier_Scheme': 'DOI',
            'Identifier': yodaDOI
        },
        'Publication_Date': publicationDate,
        'Open_access_Link': openAccessLink,
        'License_URI': licenseUri
    }

    # Write combined data to file at location combiJsonPath
    jsonutil.write(ctx, combiJsonPath, metaDict)


@rule.make(inputs=[0], outputs=[1])
def rule_json_datacite41_create_datacite_json(ctx, combi_path):
    return json_datacite41_create_datacite_json(ctx, combi_path)


def json_datacite41_create_datacite_json(ctx, combi_path):
    """Based on content of combi json, get DataciteXml as string.

    :param ctx:        Combined type of a callback and rei struct
    :param combi_path: Path to the combined JSON file that holds both user and system metadata

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
            "relatedIdentifiers": get_related_datapackages(combi),
            "version": get_version(combi),
            "rightsList": get_rights_list(combi),
            "descriptions": get_descriptions(combi),
            "geoLocations": get_geo_locations(combi),
            "fundingReferences": get_funders(combi),
            "url": "https://schema.datacite.org/meta/kernel-4.0/index.html",
            "schemaVersion": "http://datacite.org/schema/kernel-4"
        }
    }
    return metadata

    """

      "doi": "10.5438/0012",
      ? "prefix": "10.5438",
      ? "suffix": "0012",
      "identifiers": [{
        "identifier": "https://doi.org/10.5438/0012",
        "identifierType": "DOI"
      }],
      "creators": getCreators(combi)[],
      "titles": getTitles(combi)[],
      "publisher": getPublisher(combi),
      # "container": {},
      "publicationYear": getPublicationYear(combi),
      "subjects": getSubjects(combi)[],
      "contributors": getContributors(combi)[],
      "dates": getDates(combi)[],
      "language": getLanguage(combi),
      "types": getResourceType(combi)?? {},
      "relatedIdentifiers": getRelatedDataPackage(combi) ??[],
      # "sizes": [],
      # "formats": [],
      "version": getVersion(combi),
      "rightsList": getRightsList(combi)[],
      "descriptions": getDescriptions(combi)[],
      "geoLocations": getGeoLocations(combi)[],
      "fundingReferences": getFunders(combi)[],
      # "xml": null,
      # "url":null,
      # "contentUrl": null,
      # "metadataVersion": 1,
      # "schemaVersion": "http://datacite.org/schema/kernel-4",
      # "source": null,
      # "isActive": true,
      # "state": "draft",
      # "reason": null,
      # "created": ### "2016-09-19T21:53:56.000Z",
      # "registered": null,
      # "updated": ### "2019-02-06T14:31:27.000Z"

    """


def get_DOI(combi):
    return combi['System']['Persistent_Identifier_Datapackage']['Identifier']


def get_identifiers(combi):
    return [{'identifier': combi['System']['Persistent_Identifier_Datapackage']['Identifier'],
             'identifierType': 'DOI'}]

 
def get_titles(combi):
    return [{'title': combi['Title'], 'language': 'en-us'}] # combi.get('Language', 'en')[0:2]}]  # taal moet langer 'en-us'


def get_descriptions(combi):
    return [{'description': combi['Description'], 'descriptionType': 'Abstract'}]


def get_publisher(combi):
    # FIXME (untouched from b057f496).
    return 'Utrecht University'


def get_publication_year(combi):
    return combi['System']['Publication_Date'][0:4]


def get_subjects(combi):
    """Get list in DataCite format containing:

       1) standard objects like tags/disciplne
       2) free items, for now specifically for GEO schemas

    :param combi: Combined JSON file that holds both user and system metadata

    :returns: list of subjects in DataCite format
    """

    subjects = []
    for discipline in combi.get('Discipline', []):
        subjects.append({'subjectScheme': 'OECD FOS 2007', 'subject': discipline})

    for tag in combi.get('Tag', []):
        subjects.append({'subject': tag, 'subjectScheme': 'Keyword'})

    # Geo schemas have some specific fields that need to be added as subject.
    # Sort of freely usable fields
    subject_fields = ['Main_Setting',
                      'Process_Hazard',
                      'Geological_Structure',
                      'Geomorphical_Feature',
                      'Material',
                      'Apparatus',
                      'Monitoring',
                      'Software',
                      'Measured_Property']

    # for each subject field that exists in the metadata...
    for field in subject_fields:
        for x in combi.get(field, []):
            subjects.append({'subject': x, 'subjectScheme': field})

    return subjects


def get_funders(combi):
    funders = []
    for funder in combi.get('Funding_Reference', []):
        funders.append({'fundingReference': {'funderName': funder['Funder_Name'], 
                                             'awardNumber': {'awardNumber': funder['Award_Number']}}})
    return funders


def get_creators(combi):
    """Return creator information in datacite format."""
    all_creators = []

    for creator in combi.get('Creator', []):
        affiliations = []
        for aff in creator.get('Affiliation', []):
            affiliations.append(aff)
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


def get_contributors(combi):
    """Get string in DataCite format containing contributors,
       including contact persons if these were added explicitly (GEO).

    :param combi: Combined JSON file that holds both user and system metadata

    :returns: XML element with contributors in DataCite format
    """
    all = []
    # 1) Contributor
    for person in combi.get('Contributor', []):
        affiliations = []
        for aff in person.get('Affiliation', []):
            affiliations.append(aff)
        name_ids = []
        for pid in person.get('Person_Identifier', []):
            if 'Name_Identifier' in pid and 'Name_Identifier_Scheme' in pid:
                name_ids.append({'nameIdentifier': pid['Name_Identifier'],
                                 'nameIdentifierScheme': pid['Name_Identifier_Scheme']})

        all.append({'contributorName': person['Name']['Family_Name'] + ', ' + person['Name']['Given_Name'],
                    'nameType': 'Personal',
                    # 'givenName': person['Name']['Given_Name'],
                    # 'familyName': person['Name']['Family_Name'],
                    'affiliation': affiliations,
                    'contributorType':  person['Contributor_Type'],
                    'nameIdentifiers': name_ids})

    # 2) Contactperson
    for person in combi.get('ContactPerson', []):
        affiliations = []
        for aff in person.get('Affiliation', []):
            affiliations.append(aff)
        name_ids = []
        for pid in person.get('Person_Identifier', []):
            if 'Name_Identifier' in pid and 'Name_Identifier_Scheme' in pid:
                name_ids.append({'nameIdentifier': pid['Name_Identifier'],
                                 'nameIdentifierScheme': pid['Name_Identifier_Scheme']})

        all.append({'name': person['Name']['Family_Name'] + ', ' + person['Name']['Given_Name'],
                    'nameType': 'Personal',
                    'givenName': person['Name']['Given_Name'],
                    'familyName': person['Name']['Family_Name'],
                    'affiliation': affiliations,
                    'contributorType': 'Contact',
                    'nameIdentifiers': name_ids})
    return all


def get_dates(combi):
    """ return list of dates in datacite format """

    dates = [{'date': combi.get('System', {}).get('Last_Modified_Date'), 'dateType': 'Updated'}, 
             {'date': combi.get('Embargo_End_Date'), 'dateType': 'Available'}]

    collected = combi.get('Collected')
    x = collected.get('Start_Date')
    y = collected.get('End_Date')
    if x is not None and y is not None:
        dates.append({'date': '{}/{}'.format(x, y), 'dateType': 'Collected'})

    return dates


def get_version(combi):
    """Get string in DataCite format containing version info."""
    return combi['Version']


# OK ?? moet 'Custom' hierbij???? waar komt dat vandaan??
def get_rights_list(combi):
    """Get list in DataCite format containing rights related information."""
    options = {'Open':       'info:eu-repo/semantics/openAccess',
               'Restricted': 'info:eu-repo/semantics/restrictedAccess',
               'Closed':     'info:eu-repo/semantics/closedAccess'}

    # {'rights': 'Custom'}
    return [{'rights': combi['Data_Access_Restriction'], 'rightsURI': options[combi['Data_Access_Restriction'].split()[0]]}]


def get_language(combi):
    """Get string in DataCite format containing language."""
    return 'en-us' # combi['Language'][0:2]


def get_resource_type(combi):
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

    return {"resourceTypeGeneral": descr, "resourceType": type}


def get_related_datapackages(combi):
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
    for rel in combi['Related_Datapackage']:
        related_dps.append({'relatedIdentifier': rel['Persistent_Identifier']['Identifier'],
                            'relatedIdentifierType': rel['Persistent_Identifier']['Identifier_Scheme'],
                            'relationType': rel['Relation_Type'].split(':')[0]})
    return related_dps


def get_geo_locations(combi):
    """Get list of geoLocation elements in datacite format containing the information of geo locations.

       There are two versions of this:
       1) Default schema - only textual representation of
       2) Geo schema including map (=bounding box or marker/point information) Inclunding temporal and spatial descriptions
       Both are mutually exclusive.
       I.e. first test presence of 'geoLocation'. Then test presence of 'Covered_Geolocation_Place'

    :param combi: Combined JSON file that holds both user and system metadata

    :returns: XML element with information of geo locations in DataCite format
    """

    geoLocations = []

    try:
        for geoloc in combi['GeoLocation']:
            spatial_description = geoloc['Description_Spatial']

            lon0 = str(geoloc['geoLocationBox']['westBoundLongitude'])
            lat0 = str(geoloc['geoLocationBox']['northBoundLatitude'])
            lon1 = str(geoloc['geoLocationBox']['eastBoundLongitude'])
            lat1 = str(geoloc['geoLocationBox']['southBoundLatitude'])

            geo_location = {}

            if spatial_description:
                geo_location['geoLocationPlace'] = spatial_description

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
        for location in combi['Covered_Geolocation_Place']:
            if location:
                geoLocations.append({'geoLocationPlace': location})
    except KeyError:
        return

    return geoLocations
