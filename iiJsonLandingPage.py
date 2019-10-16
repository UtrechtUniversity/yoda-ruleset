# \file      iiJsonLandingPage.py
# \brief     Functions for transforming JSON to landingpage HTML.
# \author    Harm de Raaff
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.
from jinja2 import Template
import os
from json import loads
from collections import OrderedDict


# \brief Read yoda-metadata.json from vault and return as (ordered!) dict
#
# \param[in] rods_zone
# \param[in] category    name of category the metadata belongs to
#
# \return dict hodling the category JSONSchema
def getJinjaLandingPageTemplate(callback, path):
    coll_name, data_name = os.path.split(path)
    data_size = getDataObjSize(callback, coll_name, data_name)

    # Open landing page template.
    ret_val = callback.msiDataObjOpen('objPath=' + path, 0)
    fileHandle = ret_val['arguments'][1]

    # Read data
    ret_val = callback.msiDataObjRead(fileHandle, data_size, irods_types.BytesBuf())

    # Close metadata XML.
    callback.msiDataObjClose(fileHandle, 0)

    read_buf = ret_val['arguments'][2]
    return ''.join(read_buf.buf)


# \brief Get yodametadata Json and return as (ordered!) dict
#
# \param[in] yoda_json_path
#
# \return dict hodling the content of yoda-metadata.json
#
def getMetadaJsonDict(callback, yoda_json_path):
    coll_name, data_name = os.path.split(yoda_json_path)

    data_size = getDataObjSize(callback, coll_name, data_name)

    # Open JSON file
    ret_val = callback.msiDataObjOpen('objPath=' + yoda_json_path, 0)
    fileHandle = ret_val['arguments'][1]

    # Read JSON
    ret_val = callback.msiDataObjRead(fileHandle, data_size, irods_types.BytesBuf())

    # Close JSON
    callback.msiDataObjClose(fileHandle, 0)

    # Parse JSON into dict.
    read_buf = ret_val['arguments'][2]
    jsonText = ''.join(read_buf.buf)

    # Use the hook to keep ordering of elements as in metadata.json
    return json.loads(jsonText, object_pairs_hook=OrderedDict)


#####################################################
## Create a landing page
#####################################################
#
# \brief Get the landing page of published YoDa metadata as a string
#
# \param[in] rodsZone
# \param[in] vaultMetadataJsonPath - Path to vault package
# \param[out] string representation of the landingpage
#
# \return string with html cont
def iiCreateJsonLandingPage(rule_args, callback, rei):

    rodsZone, template_name, combiJsonPath, receiveLandingPage = rule_args[0:4]

    # Landing page creation is part of the publication proces
    # Read user & system metadata from corresponding combiJson file
    dictJsonData = getMetadaJsonDict(callback, combiJsonPath)

    # load the ninja file as text
    landingpage_template_path = '/' + rodsZone + '/yoda/templates/' + template_name
    callback.writeString("serverLog", landingpage_template_path)
    template = getJinjaLandingPageTemplate(callback, landingpage_template_path)

    # pre work input for render process.
    # When empty landing page, take a short cut
    if template_name == 'emptylandingpage.html':
        persistent_identifier_datapackage = dictJsonData['System']['Persistent_Identifier_Datapackage']
        tm = Template(template)
        landing_page = tm.render(persistent_identifier_datapackage=persistent_identifier_datapackage)

        callback.writeString("serverLog", landing_page)
        rule_args[3] = landing_page
        return

    # Gather all metadata
    title = dictJsonData['Title']
    description = dictJsonData['Description']
    disciplines = dictJsonData['Discipline']
    version = dictJsonData['Version']
    language = dictJsonData['Language']
    collected = dictJsonData['Collected']

    try:
        covered_geolocation_place = dictJsonData['Covered_Geolocation_Place']
    except KeyError:
        covered_geolocation_place = {}

    try:
        covered_period = dictJsonData['Covered_Period']
    except KeyError:
        covered_period = []

    tags = dictJsonData['Tag']
    related_datapackages = dictJsonData['Related_Datapackage']

    creators = dictJsonData['Creator']
    contributors = dictJsonData['Contributor']
    license  = dictJsonData['License']
    data_access_restriction = dictJsonData['Data_Access_Restriction']

    funding_reference = dictJsonData['Funding_Reference']
    data_classification = dictJsonData['Data_Classification']

    last_modified_date = dictJsonData['System']['Last_Modified_Date']
    persistent_identifier_datapackage = dictJsonData['System']['Persistent_Identifier_Datapackage']
    publication_date = dictJsonData['System']['Publication_Date']
    open_access_link = dictJsonData['System']['Open_access_Link']
    license_uri = dictJsonData['System']['License_URI']

    try:
        geolocations = dictJsonData['GeoLocation']
    except KeyError:
        geolocations = {}
        pass

    collection_name = 'collection-name'

    tm = Template(template)
    landing_page = tm.render(title=title, description=description, disciplines=disciplines, version=version, language=language, tags=tags, creators=creators, contributors=contributors, publication_date=publication_date,
                data_access_restriction=data_access_restriction, license=license, license_uri=license_uri, open_access_link=open_access_link, funding_reference=funding_reference,
                data_classification=data_classification, collection_name=collection_name, last_modified_date=last_modified_date, related_datapackages=related_datapackages,
                persistent_identifier_datapackage=persistent_identifier_datapackage, geolocations=geolocations)

    callback.writeString("serverLog", landing_page)

    rule_args[3] = landing_page
