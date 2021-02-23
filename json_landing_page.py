# -*- coding: utf-8 -*-
"""Functions for transforming JSON to landingpage HTML."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import jinja2

from util import *


def json_landing_page_create_json_landing_page(callback, rodsZone, template_name, combiJsonPath, json_schema):
    """Get the landing page of published YoDa metadata as a string.

    :param callback:      Callback to rule Language
    :param rodsZone:      Zone name
    :param template_name: Name of landingpage template
    :param combiJsonPath: path to Yoda metadata JSON
    :param json_schema:   Dict holding entire contents of metadata.json for the category involved

    :return: Output HTML landing page
    """
    # Landing page creation is part of the publication process
    # Read user & system metadata from corresponding combi JSON file
    # (Python2) 'want_bytes=False': Do not encode embedded unicode strings as
    #                               UTF-8, as that will trip up jinja2.
    dictJsonData = jsonutil.read(callback, combiJsonPath, want_bytes=False)

    # Load the Jinja template.
    landingpage_template_path = '/' + rodsZone + '/yoda/templates/' + template_name
    template = data_object.read(callback, landingpage_template_path)

    # Enable autoescaping for all templates.
    # NOTE: autoescape is no longer an extension starting in jinja 2.9 (2017).
    Template = jinja2.Environment(autoescape=True,
                                  extensions=['jinja2.ext.autoescape']).from_string

    # Pre work input for render process.
    # When empty landing page, take a short cut
    if template_name == 'emptylandingpage.html.j2':
        persistent_identifier_datapackage = dictJsonData['System']['Persistent_Identifier_Datapackage']
        tm = Template(template)
        landing_page = tm.render(persistent_identifier_datapackage=persistent_identifier_datapackage)
        return landing_page

    # Gather all metadata.
    title = dictJsonData['Title']
    description = dictJsonData['Description']

    # Geo specific lab handling
    try:
        labids = dictJsonData['Lab']
        labs = []
        schema_labids = json_schema['definitions']['optionsLabs']['enum']
        schema_labnames = json_schema['definitions']['optionsLabs']['enumNames']
        for id in labids:
            index = schema_labids.index(id)
            labs.append(schema_labnames[index])
    except KeyError:
        labs = []

    # Geo specific additional lab handling
    try:
        additional_labs = dictJsonData['Additional_Lab']  # niet verplicht
    except KeyError:
        additional_labs = []

    try:
        disciplines = dictJsonData['Discipline']  # niet verplicht
    except KeyError:
        disciplines = []

    try:
        version = dictJsonData['Version']
    except KeyError:
        version = ''

    try:
        language = dictJsonData['Language']
    except KeyError:
        language = ''

    try:
        collected = dictJsonData['Collected']
    except KeyError:
        collected = {}

    try:
        covered_geolocation_place = dictJsonData['Covered_Geolocation_Place']
    except KeyError:
        covered_geolocation_place = {}

    try:
        covered_period = dictJsonData['Covered_Period']
    except KeyError:
        covered_period = []

    try:
        tags = dictJsonData['Tag']  # not mandatory
    except KeyError:
        tags = []

    try:
        apparatus = dictJsonData['Apparatus']
    except KeyError:
        apparatus = []

    try:
        main_setting = dictJsonData['Main_Setting']
    except KeyError:
        main_setting = []

    try:
        process_hazard = dictJsonData['Process_Hazard']
    except KeyError:
        process_hazard = []

    try:
        geological_structure = dictJsonData['Geological_Structure']
    except KeyError:
        geological_structure = []

    try:
        geomorphical_feature = dictJsonData['Geomorphical_Feature']
    except KeyError:
        geomorphical_feature = []

    try:
        material = dictJsonData['Material']
    except KeyError:
        material = []

    try:
        monitoring = dictJsonData['Monitoring']
    except KeyError:
        monitoring = []

    try:
        software = dictJsonData['Software']
    except KeyError:
        software = []

    try:
        measured_property = dictJsonData['Measured_Property']
    except KeyError:
        measured_property = []

    try:
        related_datapackages = dictJsonData['Related_Datapackage']  # not mandatory
    except KeyError:
        related_datapackages = []

    try:
        creators = dictJsonData['Creator']
    except KeyError:
        creators = []

    try:
        contributors = dictJsonData['Contributor']
    except KeyError:
        contributors = []

    try:
        contacts = dictJsonData['Contact']
    except KeyError:
        contacts = []

    try:
        funding_reference = dictJsonData['Funding_Reference']
    except KeyError:
        funding_reference = []

    license = dictJsonData['License']
    data_access_restriction = dictJsonData['Data_Access_Restriction']
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

    # Collection name  ILAB specific - part of default schemas
    try:
        collection_name = dictJsonData['Collection_Name']
    except KeyError:
        collection_name = ''

    tm = Template(template)
    landing_page = tm.render(
        title=title,
        description=description,
        labs=labs,
        additional_labs=additional_labs,
        disciplines=disciplines,
        version=version,
        language=language,
        tags=tags,
        apparatus=apparatus,
        main_setting=main_setting,
        process_hazard=process_hazard,
        geological_structure=geological_structure,
        geomorphical_feature=geomorphical_feature,
        material=material,
        monitoring=monitoring,
        software=software,
        measured_property=measured_property,
        creators=creators,
        contributors=contributors,
        contacts=contacts,
        publication_date=publication_date,
        data_access_restriction=data_access_restriction,
        license=license,
        license_uri=license_uri,
        open_access_link=open_access_link,
        funding_reference=funding_reference,
        data_classification=data_classification,
        collection_name=collection_name,
        last_modified_date=last_modified_date,
        related_datapackages=related_datapackages,
        persistent_identifier_datapackage=persistent_identifier_datapackage,
        geolocations=geolocations,
        covered_geolocation_place=covered_geolocation_place)

    return landing_page
