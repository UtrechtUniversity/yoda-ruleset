# -*- coding: utf-8 -*-
"""Functions for transforming JSON to landingpage HTML."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from jinja2 import Template
import os
from json import loads
from collections import OrderedDict


def iiCreateJsonLandingPage(rule_args, callback, rei):
    """Get the landing page of published YoDa metadata as a string.

       Arguments:
       rodsZone           -- Zone name
       template_name      -- name of landingpage template
       combiJsonPath      -- path to Yoda metadata JSON
       receiveLandingPage -- output HTML landing page
    """
    rodsZone, template_name, combiJsonPath, receiveLandingPage = rule_args[0:4]

    # Landing page creation is part of the publication proces
    # Read user & system metadata from corresponding combi JSON file
    dictJsonData = jsonutil.read(callback, combiJsonPath)

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
    license = dictJsonData['License']
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

    # FIXME: ?
    collection_name = 'collection-name'

    tm = Template(template)
    landing_page = tm.render(
        title=title, description=description,
        disciplines=disciplines, version=version,
        language=language, tags=tags, creators=creators,
        contributors=contributors, publication_date=publication_date,
        data_access_restriction=data_access_restriction,
        license=license, license_uri=license_uri,
        open_access_link=open_access_link, funding_reference=funding_reference,
        data_classification=data_classification, collection_name=collection_name,
        last_modified_date=last_modified_date,
        related_datapackages=related_datapackages,
        persistent_identifier_datapackage=persistent_identifier_datapackage,
        geolocations=geolocations)

    rule_args[3] = landing_page
