# -*- coding: utf-8 -*-
"""Functions for transforming JSON to DataCite 4.1 XML."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import xml.etree.cElementTree as ET

from util import *

__all__ = ['rule_json_datacite41_create_combi_metadata_json',
           'rule_json_datacite41_create_data_cite_xml_on_json']


def El(tag, *children, **attrs):
    """Construct an XML element with the given attributes and children.

    If a string is given as the only child, it is used as a textual element body instead.

    :param tag:       Tag of XML element to construct
    :param *children: Children of XML element to construct
    :param **attrs:   Attributes of XML element to construct

    :returns: XML element
    """
    if type(tag) is str:
        tag = tag.decode('utf-8')

    el = ET.Element(tag, attrs)

    if len(children) == 1 and type(children[0]) in [str, unicode]:
        text = children[0]
        if type(text) is str:
            text = text.decode('utf-8')
        el.text = text
    else:
        el.extend(children)

    return el


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
def rule_json_datacite41_create_data_cite_xml_on_json(ctx, combi_path):
    return json_datacite41_create_data_cite_xml_on_json(ctx, combi_path)


def json_datacite41_create_data_cite_xml_on_json(ctx, combi_path):
    """Based on content of combi json, get DataciteXml as string.

    :param ctx:        Combined type of a callback and rei struct
    :param combi_path: Path to the combined JSON file that holds both user and system metadata

    :returns: string -- Holds Datacite formatted metadata of Yoda
    """

    combi = jsonutil.read(ctx, combi_path)

    ET.register_namespace('', 'http://datacite.org/schema/kernel-4')
    ET.register_namespace('yoda', 'https://yoda.uu.nl/schemas/default')

    # Build datacite XML
    e = ET.fromstring(getHeader() + '</resource>')

    for f in [getDOI,
              getTitles,
              getDescriptions,
              getPublisher,
              getPublicationYear,
              getSubjects,
              getCreators,
              getContributors,
              getDates,
              getVersion,
              getRightsList,
              getLanguage,
              getResourceType,
              getRelatedDataPackage,
              getGeoLocations,
              getFunders]:
        try:
            x = f(combi)
        except KeyError:
            # Ignore absent fields.
            continue
        except IndexError:
            # Ignore absent fields.
            continue

        if isinstance(x, str):
            if len(x):
                e.append(ET.fromstring(unicode(x)))
        elif x is not None:
            e.append(x)

    return ET.tostring(e, encoding='UTF-8')


def getHeader():
    # TODO: all that is present before the yoda data  !! Hier moet de ID nog in
    return '''<?xml version="1.0" encoding="UTF-8"?><resource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://datacite.org/schema/kernel-4" xmlns:yoda="https://yoda.uu.nl/schemas/default" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd">'''

    # Note: xmlns:yoda is currently unused and pruned automatically.
    #       Also, the url is invalid.


def getDOI(combi):
    return El('identifier', combi['System']['Persistent_Identifier_Datapackage']['Identifier'],
              identifierType='DOI')


def getTitles(combi):
    return El('titles',
              El('title', combi['Title'],
                 **{'xml:lang': combi.get('Language', 'en')[0:2]}))


def getDescriptions(combi):
    return El('descriptions',
              El('description', combi['Description'],
                  descriptionType='Abstract'))


def getPublisher(combi):
    # FIXME (untouched from b057f496).
    return '<publisher>Utrecht University</publisher>'  # Hardcoded like in former XSLT


def getPublicationYear(combi):
    return El('publicationYear', combi['System']['Publication_Date'][0:4])


def getSubjects(combi):
    """Get string in DataCite format containing:

       1) standard objects like tags/disciplne
       2) free items, for now specifically for GEO schemas

    :param combi: Combined JSON file that holds both user and system metadata

    :returns: XML element with subjects in DataCite format
    """

    subjects = []  # :: [(scheme, value)]

    subjects += [('OECD FOS 2007', x) for x in combi.get('Discipline', [])]
    subjects += [('Keyword', x) for x in combi.get('Tag', [])]

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
        subjects += [(field, x) for x in combi.get(field, [])]

    # Create elements, prune empty / null values.
    subjects = [El('subject', value, subjectScheme=scheme)
                for scheme, value in subjects
                if type(value) in (str, unicode) and len(value)]

    if subjects:
        return El('subjects', *subjects)


def getFunders(combi):
    return El('fundingReferences',
              *[El('fundingReference',
                   El('funderName',  funder['Funder_Name']),
                   El('awardNumber', funder['Award_Number']))
                for funder in combi.get('Funding_Reference', [])])


def getCreators(combi):
    """Get string in DataCite format containing creator information."""
    creators = [El('creator',
                   El('creatorName', '{}, {}'.format(creator['Name']['Family_Name'], creator['Name']['Given_Name'])),
                   *[El('nameIdentifier', pid['Name_Identifier'], nameIdentifierScheme=pid['Name_Identifier_Scheme'])
                       for pid in creator.get('Person_Identifier', [])
                       if 'Name_Identifier' in pid and 'Name_Identifier_Scheme' in pid]
                   + [El('affiliation', x) for x in creator.get('Affiliation', [])])
                for creator in combi.get('Creator', [])]

    if creators:
        return El('creators', *creators)


def getContributors(combi):
    """Get string in DataCite format containing contributors,
       including contact persons if these were added explicitly (GEO).

    :param combi: Combined JSON file that holds both user and system metadata

    :returns: XML element with contributors in DataCite format
    """
    contribs = [El('contributor',
                   El('contributorName', '{}, {}'.format(person['Name']['Family_Name'], person['Name']['Given_Name'])),
                   *[El('nameIdentifier', pid['Name_Identifier'], nameIdentifierScheme=pid['Name_Identifier_Scheme'])
                       for pid in person.get('Person_Identifier', [])
                       if 'Name_Identifier' in pid and 'Name_Identifier_Scheme' in pid]
                   + [El('affiliation', x) for x in person.get('Affiliation', [])],
                   contributorType=('ContactPerson' if typ == 'Contact' else person['Contributor_Type']))

                # Contact is a special case introduced for Geo - Contributor type = 'contactPerson'
                for typ in ['Contributor', 'Contact']
                for person in combi.get(typ, [])]

    if contribs:
        return El('contributors', *contribs)


def getDates(combi):

    def get_span(d):
        x = d.get('Start_Date')
        y = d.get('End_Date')
        if x is not None and y is not None:
            return '{}/{}'.format(x, y)

    dates = [El('date', dat, dateType=typ)
             for typ, dat in [('Updated',   combi.get('System', {}).get('Last_Modified_Date')),
                              ('Available', combi.get('Embargo_End_Date')),
                              ('Collected', get_span(combi.get('Collected', {})))]
             if dat is not None]

    if dates:
        return El('dates', *dates)


def getVersion(combi):
    """Get string in DataCite format containing version info."""
    return El('version', combi['Version'])


def getRightsList(combi):
    """Get string in DataCite format containing rights related information."""
    options = {'Open':       'info:eu-repo/semantics/openAccess',
               'Restricted': 'info:eu-repo/semantics/restrictedAccess',
               'Closed':     'info:eu-repo/semantics/closedAccess'}

    return El('rightsList', El('rights',
                               rightsURI=options[combi['Data_Access_Restriction'].split()[0]]))


def getLanguage(combi):
    """Get string in DataCite format containing language."""
    return El('language', combi['Language'][0:2])


def getResourceType(combi):
    """Get string in DataCite format containing Resource type and default handling."""
    typs = {'Dataset':   'Research Data',
            'DataPaper': 'Method Description',
            'Software':  'Computer code'}

    typ = combi.get('Data_Type', 'Text')
    if typ not in typs:
        typ = 'Text'

    descr = {'Dataset': 'Research Data',
             'DataPaper': 'Method Description',
             'Software': 'Computer code'}\
        .get(typ, 'Other Document')

    return El('resourceType', descr, resourceTypeGeneral=typ)


def getRelatedDataPackage(combi):
    """Get string in DataCite format containing related datapackages."""
    related = [El('relatedIdentifier',    rel['Persistent_Identifier']['Identifier'],
                  relatedIdentifierType=rel['Persistent_Identifier']['Identifier_Scheme'],
                  relationType=rel['Relation_Type'].split(':')[0])
               for rel in combi['Related_Datapackage']]
    if related:
        return El('relatedIdentifiers', *related)


def getGeoLocations(combi):
    """Get string in datacite format containing the information of geo locations.

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
            temp_description_start = geoloc['Description_Temporal']['Start_Date']
            temp_description_end = geoloc['Description_Temporal']['End_Date']
            spatial_description = geoloc['Description_Spatial']

            lon0 = str(geoloc['geoLocationBox']['westBoundLongitude'])
            lat0 = str(geoloc['geoLocationBox']['northBoundLatitude'])
            lon1 = str(geoloc['geoLocationBox']['eastBoundLongitude'])
            lat1 = str(geoloc['geoLocationBox']['southBoundLatitude'])

            geoPlace = None
            geoPoint = None
            geoBox   = None

            if spatial_description:
                geoPlace = El('geoLocationPlace', spatial_description)

            if lon0 == lon1 and lat0 == lat1:  # Dealing with a point.
                geoPoint  = El('geoLocationPoint',
                               El('pointLongitude', lon0),
                               El('pointLatitude', lat0))
            else:
                geoBox = El('geoLocationBox',
                            El('westBoundLongitude', lon0),
                            El('eastBoundLongitude', lon1),
                            El('southBoundLatitude', lat0),
                            El('northBoundLatitude', lat1))

            # Put it all together as one geoLocation elemenmt
            geoLocations += [El('geoLocation', *[x for x in [geoPlace, geoPoint, geoBox] if x])]

        if len(geoLocations):
            return El('geoLocations', *geoLocations)

    except KeyError:
        pass

    try:
        locationList = combi['Covered_Geolocation_Place']
        for location in locationList:
            if location:
                geoLocations += [El('geoLocation', El('geoLocationPlace', location))]
    except KeyError:
        return

    if len(geoLocations):
        return El('geoLocations', *geoLocations)
