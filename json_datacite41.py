# -*- coding: utf-8 -*-
"""Functions for transforming JSON to DataCite 4.1 XML."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from util import *

__all__ = ['rule_uu_json_datacite41_create_combi_metadata_json',
           'rule_uu_json_datacite41_create_data_cite_xml_on_json']


def rule_uu_json_datacite41_create_combi_metadata_json(rule_args, callback, rei):
    """Frontend function to add system info to yoda-metadata in json format.

    :param metadataJsonPath: Path to the most recent vault yoda-metadata.json in the corresponding vault
    :param combiJsonPath: Path to where the combined info will be placed so it can be used for DataciteXml & landingpage generation
                          other are system info parameters
    """
    metadataJsonPath, combiJsonPath, lastModifiedDateTime, yodaDOI, publicationDate, openAccessLink, licenseUri = rule_args[0:7]

    # get the data in the designated YoDa metadata.json and retrieve it as dict
    metaDict = jsonutil.read(callback, metadataJsonPath)

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
    jsonutil.write(callback, combiJsonPath, metaDict)


def rule_uu_json_datacite41_create_data_cite_xml_on_json(rule_args, callback, rei):
    """Based on content of *combiJsonPath, get DataciteXml as string.

    :param combiJsonPath: path to the combined Json file that holds both User and System metadata

    :returns: string -- Holds Datacite formatted metadata of Yoda
    """
    combiJsonPath, receiveDataciteXml = rule_args[0:2]

    # Get dict containing the wanted metadata
    dict = jsonutil.read(callback, combiJsonPath)

    # Build datacite XML as string
    xmlString = getHeader()

    # Build datacite XML as string
    xmlString += getDOI(dict)

    xmlString += getTitles(dict)
    xmlString += getDescriptions(dict)
    xmlString += getPublisher(dict)
    xmlString += getPublicationYear(dict)
    xmlString += getSubjects(dict)

    xmlString += getCreators(dict)
    xmlString += getContributors(dict)
    xmlString += getDates(dict)
    xmlString += getVersion(dict)
    xmlString += getRightsList(dict)
    xmlString += getLanguage(dict)
    xmlString += getResourceType(dict)
    xmlString += getRelatedDataPackage(dict)

    xmlString += getGeoLocations(dict)
    xmlString += getFunders(dict)

    # Close the XML.
    xmlString += '</resource>'

    rule_args[1] = xmlString


def getHeader():
    # TODO: all that is present before the yoda data  !! Hier moet de ID nog in
    return '''<?xml version="1.0" encoding="UTF-8"?><resource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://datacite.org/schema/kernel-4" xmlns:yoda="https://yoda.uu.nl/schemas/default" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd">'''


def getDOI(dict):
    try:
        doi = dict['System']['Persistent_Identifier_Datapackage']['Identifier']
        return '<identifier identifierType="DOI">' + doi + '</identifier>'
    except KeyError:
        pass
    return ''


def getTitles(dict):
    try:
        language = dict['Language'][0:2]
        title = dict['Title']
        return '<titles><title xml:lang="' + language + '">' + title + '</title></titles>'
    except KeyError:
        pass

    return ''


def getDescriptions(dict):
    try:
        description = dict['Description']
        return '<descriptions><description descriptionType="Abstract">' + description + '</description></descriptions>'
    except KeyError:
        pass

    return ''


def getPublisher(dict):
    return '<publisher>Utrecht University</publisher>'  # Hardcoded like in former XSLT


def getPublicationYear(dict):
    try:
        publicationYear = dict['System']['Publication_Date'][0:4]
        return '<publicationYear>' + publicationYear + '</publicationYear>'
    except KeyError:
        pass
    return ''


def getSubjects(dict):
    """Get string in DataCite format containing:

       1) standard objects like tags/disciplne
       2) free items, for now specifically for GEO schemas
    """
    subjectDisciplines = ''
    subjectTags = ''
    subjectFree = ''

    try:
        for disc in dict['Discipline']:
            if disc:
                subjectDisciplines += '<subject subjectScheme="OECD FOS 2007">' + disc + '</subject>'
    except (KeyError, TypeError):
        pass

    try:
        for tag in dict['Tag']:
            if tag:
                subjectTags += '<subject subjectScheme="Keyword">' + tag + '</subject>'
    except KeyError:
        pass

    # Geo schemas have some specific fields that need to be added as subject.
    # Sort of freely usable fields
    subject_fields = ["Main_Setting",
                      "Process_Hazard",
                      "Geological_Structure",
                      "Geomorphical_Feature",
                      "Material",
                      "Apparatus",
                      "Monitoring",
                      "Software",
                      "Measured_Property"]

    for field in subject_fields:
        try:
            for value in dict[field]:
                if value:
                    subjectFree += '<subject subjectScheme="' + field + '">' + value + '</subject>'
        except KeyError:
            continue  # Try next field in the list.

    if subjectDisciplines or subjectTags or subjectFree:
        return '<subjects>' + subjectDisciplines + subjectTags + subjectFree + '</subjects>'

    return ''


def getFunders(dict):
    fundingRefs = ''
    try:
        for funder in dict['Funding_Reference']:
            fundingRefs += '<fundingReference><funderName>' + funder['Funder_Name'] + '</funderName><awardNumber>' + funder['Award_Number'] + '</awardNumber></fundingReference>'
        return '<fundingReferences>' + fundingRefs + '</fundingReferences>'

    except KeyError:
        pass

    return ''


def getCreators(dict):
    """Get string in DataCite format containing creator information."""
    creators = ''
    try:
        for creator in dict['Creator']:
            creators += '<creator>'
            creators += '<creatorName>' + creator['Name']['First_Name'] + ' ' + creator['Name']['Last_Name'] + '</creatorName>'

            # Possibly multiple person identifiers
            nameIdentifiers = ''
            try:
                for dictId in creator['Person_Identifier']:
                    nameIdentifiers += '<nameIdentifier nameIdentifierScheme="' + dictId['Name_Identifier_Scheme'] + '">' + dictId['Name_Identifier'] + '</nameIdentifier>'
            except KeyError:
                pass

            # Possibly multiple affiliations
            affiliations = ''
            try:
                for aff in creator['Affiliation']:
                    affiliations += '<affiliation>' + aff + '</affiliation>'
            except KeyError:
                pass

            creators += nameIdentifiers
            creators += affiliations
            creators += '</creator>'

        if creators:
            return '<creators>' + creators + '</creators>'
    except KeyError:
        pass

    return ''


def getContributors(dict):
    """Get string in datacite format containing contributors,
       including contact persons if these were added explicitely (GEO).
    """
    contributors = ''

    try:
        for yoda_contributor in ['Contributor', 'Contact']:  # Contact is a special case introduced for Geo - Contributor type = 'contactPerson'
            for contributor in dict[yoda_contributor]:
                if yoda_contributor == 'Contact':
                    contributors += '<contributor contributorType="ContactPerson">'
                else:
                    contributors += '<contributor contributorType="' + contributor['Contributor_Type'] + '">'

                contributors += '<contributorName>' + contributor['Name']['First_Name'] + ' ' + contributor['Name']['Last_Name'] + '</contributorName>'

                # Possibly multiple person identifiers
                nameIdentifiers = ''
                try:
                    for dictId in contributor['Person_Identifier']:
                        nameIdentifiers += '<nameIdentifier nameIdentifierScheme="' + dictId['Name_Identifier_Scheme'] + '">' + dictId['Name_Identifier'] + '</nameIdentifier>'
                except KeyError:
                    pass

                # Possibly multiple affiliations
                affiliations = ''
                try:
                    for aff in contributor['Affiliation']:
                        affiliations += '<affiliation>' + aff + '</affiliation>'
                except KeyError:
                    pass

                contributors += nameIdentifiers
                contributors += affiliations
                contributors += '</contributor>'

    except KeyError:
        pass

    if contributors:
        return '<contributors>' + contributors + '</contributors>'
    return ''


# /brief Get string in datacite format containing all date information
def getDates(dict):
    try:
        dates = ''
        dateModified = dict['System']['Last_Modified_Date']
        dates += '<date dateType="Updated">' + dateModified + '</date>'
    except KeyError:
        pass

    try:
        dateEmbargoEnd = dict['Embargo_End_Date']
        dates += '<date dateType="Available">' + dateEmbargoEnd + '</date>'
    except KeyError:
        pass

    try:
        dateCollectStart = dict['Collected']['Start_Date']
        dateCollectEnd = dict['Collected']['End_Date']

        dates += '<date dateType="Collected">' + dateCollectStart + '/' + dateCollectEnd + '</date>'
    except KeyError:
        pass

    if dates:
        return '<dates>' + dates + '</dates>'

    return ''


def getVersion(dict):
    """Get string in DataCite format containing version info."""
    try:
        version = dict['Version']
        return '<version>' + version + '</version>'
    except KeyError:
        return ''


def getRightsList(dict):
    """Get string in DataCite format containing rights related information."""
    try:
        # licenseURI = dict['System']['License_URI']
        # rights = '<rights rightsURI="' + licenseURI + '"></rights>'
        rights = ''

        accessRestriction = dict['Data_Access_Restriction']

        accessOptions = {'Open': 'info:eu-repo/semantics/openAccess', 'Restricted': 'info:eu-repo/semantics/restrictedAccess', 'Closed': 'info:eu-repo/semantics/closedAccess'}

        rightsURI = ''
        for option, uri in accessOptions.items():
            if accessRestriction.startswith(option):
                rightsURI = uri
                break
        rights += '<rights rightsURI="' + rightsURI + '"></rights>'
        if rights:
            return '<rightsList>' + rights + '</rightsList>'

    except KeyError:
        pass

    return ''


def getLanguage(dict):
    """Get string in DataCite format containing language."""
    try:
        language = dict['Language'][0:2]
        return '<language>' + language + '</language>'
    except KeyError:
        pass
    return ''


def getResourceType(dict):
    """Get string in DataCite format containing Resource type and default handling."""
    yodaResourceToDatacite = {'Dataset': 'Research Data', 'DataPaper': 'Method Description', 'Software': 'Computer code'}

    try:
        resourceType = dict['Data_Type']
        dataciteDescr = yodaResourceToDatacite[resourceType]
    except KeyError:
        resourceType = 'Text'
        dataciteDescr = 'Other Document'  # Default value

    return '<resourceType resourceTypeGeneral="' + resourceType + '">' + dataciteDescr + '</resourceType>'


def getRelatedDataPackage(dict):
    """Get string in DataCite format containing related datapackages."""
    relatedIdentifiers = ''

    try:
        for relPackage in dict['Related_Datapackage']:
            relType = relPackage['Relation_Type'].split(':')[0]
            # title = relPackage['Title']
            persistentSchema = relPackage['Persistent_Identifier']['Identifier_Scheme']
            persistentID = relPackage['Persistent_Identifier']['Identifier']
            relatedIdentifiers += '<relatedIdentifier relatedIdentifierType="' + persistentSchema + '" relationType="' + relType + '">' + persistentID + '</relatedIdentifier>'

        if relatedIdentifiers:
            return '<relatedIdentifiers>' + relatedIdentifiers + '</relatedIdentifiers>'
        return ''
    except KeyError:
        return ''


def getGeoLocations(dict):
    """Get string in datacite format containing the information of geo locations.

       There are two versions of this:
       1) Default schema - only textual representation of
       2) Geo schema including map (=bounding box or marker/point information) Inclunding temporal and spatial descriptions
       Both are mutually exclusive.
       I.e. first test presence of 'geoLocation'. Then test presence of 'Covered_Geolocation_Place'
    """
    geoLocations = ''

    try:
        for geoloc in dict['GeoLocation']:
            temp_description_start = geoloc['Description_Temporal']['Start_Date']
            temp_description_end = geoloc['Description_Temporal']['End_Date']
            spatial_description = geoloc['Description_Spatial']

            lon0 = str(geoloc['geoLocationBox']['westBoundLongitude'])
            lat0 = str(geoloc['geoLocationBox']['northBoundLatitude'])
            lon1 = str(geoloc['geoLocationBox']['eastBoundLongitude'])
            lat1 = str(geoloc['geoLocationBox']['southBoundLatitude'])

            geoPlace = ''
            geoPoint = ''
            geoBox = ''

            if spatial_description:
                geoPlace = '<geoLocationPlace>' + spatial_description + '</geoLocationPlace>'

            if lon0 == lon1 and lat0 == lat1:  # Dealing with a point.
                pointLong = '<pointLongitude>' + lon0 + '</pointLongitude>'
                pointLat = '<pointLatitude>' + lat0 + '</pointLatitude>'
                geoPoint = '<geoLocationPoint>' + pointLong + pointLat + ' </geoLocationPoint>'
            else:
                wbLon = '<westBoundLongitude>' + lon0 + '</westBoundLongitude>'
                ebLon = '<eastBoundLongitude>' + lon1 + '</eastBoundLongitude>'
                sbLat = '<southBoundLatitude>' + lat0 + '</southBoundLatitude>'
                nbLat = '<northBoundLatitude>' + lat1 + '</northBoundLatitude>'

                geoBox = '<geoLocationBox>' + wbLon + ebLon + sbLat + nbLat + '</geoLocationBox>'

        # Put it all together as one geoLocation elemenmt
            geoLocations = geoLocations + '<geoLocation>' + geoPlace + geoPoint + geoBox + '</geoLocation>'

        if len(geoLocations):
            return '<geoLocations>' + geoLocations + '</geoLocations>'

    except KeyError:
        pass

    try:
        locationList = dict['Covered_Geolocation_Place']
        for location in locationList:
            if location:
                geoLocations += '<geoLocation><geoLocationPlace>' + location + '</geoLocationPlace></geoLocation>'
    except KeyError:
        return ''

    if len(geoLocations):
        return '<geoLocations>' + geoLocations + '</geoLocations>'
    return ''
