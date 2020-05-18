# -*- coding: utf-8 -*-
"""Functions for transforming JSON to landingpage HTML."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from jinja2 import Template
from util import *

__all__ = ['rule_uu_json_landing_page_create_json_landing_page']


def rule_uu_json_landing_page_create_json_landing_page(rule_args, callback, rei):
    """Get the landing page of published YoDa metadata as a string.

    :param rodsZone: Zone name
    :param template_name: Name of landingpage template
    :param combiJsonPath: path to Yoda metadata JSON
    :param receiveLandingPage: output HTML landing page
    """
    rodsZone, template_name, combiJsonPath, receiveLandingPage = rule_args[0:4]

    # Landing page creation is part of the publication process
    # Read user & system metadata from corresponding combi JSON file
    # (Python2) 'want_bytes=False': Do not encode embedded unicode strings as
    #                               UTF-8, as that will trip up jinja2.
    dictJsonData = jsonutil.read(callback, combiJsonPath, want_bytes=False)

    # Load the Jinja template.
    landingpage_template_path = '/' + rodsZone + '/yoda/templates/' + template_name
    template = data_object.read(callback, landingpage_template_path)

    # Pre work input for render process.
    # When empty landing page, take a short cut
    if template_name == 'emptylandingpage.html.j2':
        persistent_identifier_datapackage = dictJsonData['System']['Persistent_Identifier_Datapackage']
        tm = Template(template)
        landing_page = tm.render(persistent_identifier_datapackage=persistent_identifier_datapackage)
        rule_args[3] = landing_page
        return

    # Gather all metadata.
    title = dictJsonData['Title']
    description = dictJsonData['Description']

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
        pass

    # Collection name  ILAB specific - part of default schemas
    try:
        collection_name = dictJsonData['Collection_Name']
    except KeyError:
        collection_name = ''

    tm = Template(template)
    landing_page = tm.render(
        title=title,
        description=description,
        disciplines=disciplines,
        version=version,
        language=language,
        tags=tags,
        creators=creators,
        contributors=contributors,
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

    rule_args[3] = landing_page
