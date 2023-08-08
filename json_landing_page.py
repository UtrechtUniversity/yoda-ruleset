# -*- coding: utf-8 -*-
"""Functions for transforming JSON to landingpage HTML."""

__copyright__ = 'Copyright (c) 2019-2023, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import jinja2
from dateutil import parser

from util import *


def persistent_identifier_to_uri(identifier_scheme, identifier):
    """
    Transform a persistent identifier to URI.

    Supported identifier schemes are Handle, DOI, ORCID and URL.

    :param identifier_scheme: Schema of identifier to transform
    :param identifier:        Identifier to transform to URI

    :returns: URI of persistent identifier
    """
    # Identifier already is an URI.
    if identifier.lower().startswith('https://') or identifier.lower().startswith('http://'):
        return identifier

    # Create a URI from the identifier scheme and identifier.
    uri = ""
    if identifier_scheme == 'DOI':
        uri = "https://doi.org/{}".format(identifier)
    elif identifier_scheme == 'ORCID':
        uri = "https://orcid.org/{}".format(identifier)
    elif identifier_scheme == 'Handle':
        uri = "https://hdl.handle.net/{}".format(identifier)
    elif identifier_scheme == 'URL':
        uri = identifier
    else:
        uri = "#{}".format(identifier)

    return uri


def json_landing_page_create_json_landing_page(callback, rodsZone, template_name, combiJsonPath, json_schema, baseDOI, versions):
    """Get the landing page of published YoDa metadata as a string.

    :param callback:      Callback to rule Language
    :param rodsZone:      Zone name
    :param template_name: Name of landingpage template
    :param combiJsonPath: path to Yoda metadata JSON
    :param json_schema:   Dict holding entire contents of metadata.json for the category involved
    :param baseDOI:       Base DOI of the publication
    :param versions:      Dict containing all the versions of the publication

    :return: Output HTML landing page
    """
    # Landing page creation is part of the publication process
    # Read user & system metadata from corresponding combi JSON file
    # (Python2) 'want_bytes=False': Do not encode embedded unicode strings as
    #                               UTF-8, as that will trip up jinja2.
    dictJsonData = jsonutil.read(callback, combiJsonPath, want_bytes=False)

    # Remove empty lists, empty dicts, or None elements
    # to prevent empty fields on landingpage.
    dictJsonData = jsonutil.remove_empty(dictJsonData)

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
        discipline_ids = dictJsonData['Discipline']
        disciplines = []
        schema_disc_ids = json_schema['definitions']['optionsDiscipline']['enum']
        schema_disc_names = json_schema['definitions']['optionsDiscipline']['enumNames']
        for id in discipline_ids:
            index = schema_disc_ids.index(id)
            disciplines.append(schema_disc_names[index])
    except KeyError:
        disciplines = []

    try:
        version = dictJsonData['Version']
    except KeyError:
        version = ''

    try:
        language = ''
        language_id = dictJsonData['Language']
        schema_lang_ids = json_schema['definitions']['optionsISO639-1']['enum']
        schema_lang_names = json_schema['definitions']['optionsISO639-1']['enumNames']
        index = schema_lang_ids.index(language_id)
        language = schema_lang_names[index]
    except KeyError:
        language = ''

    try:
        datatype = ''
        datatype_id = dictJsonData['Data_Type']
        schema_dt_ids = json_schema['definitions']['optionsDataType']['enum']
        schema_dt_names = json_schema['definitions']['optionsDataType']['enumNames']
        index = schema_dt_ids.index(datatype_id)
        datatype = schema_dt_names[index]
    except KeyError:
        datatype = ''

    try:
        covered_geolocation_place = dictJsonData['Covered_Geolocation_Place']
    except KeyError:
        covered_geolocation_place = {}

    try:
        tags = dictJsonData['Tag']  # not mandatory
    except KeyError:
        tags = []

    try:
        keywords = dictJsonData['Keyword']  # not mandatory
    except KeyError:
        keywords = []

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
        geomorphical_feature = dictJsonData['Geomorphological_Feature']
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

    # geo hptlab specific
    try:
        pore_fluid = dictJsonData['Pore_Fluid']
    except KeyError:
        pore_fluid = []

    try:
        ancillary_equipment = dictJsonData['Ancillary_Equipment']
    except KeyError:
        ancillary_equipment = []

    try:
        inferred_deformation_behaviour = dictJsonData['Inferred_Deformation_Behaviour']
    except KeyError:
        inferred_deformation_behaviour = []

    # Route all domain specific keywords to tag area of landingpage
    all_taggebles = (tags + keywords + apparatus + main_setting + process_hazard + geological_structure
                     + geomorphical_feature + material + monitoring + software + measured_property
                     + pore_fluid + ancillary_equipment + inferred_deformation_behaviour)

    # from core-2 and default-3 'Datapackage' is renamed to 'Resource'
    try:
        related_resources = dictJsonData['Related_Resource']  # not mandatory
    except KeyError:
        related_resources = []

    # Resources backward compatibility with older schema definitions
    try:
        related_datapackages = dictJsonData['Related_Datapackage']  # not mandatory
    except KeyError:
        related_datapackages = []

    # Presence of rel_resources and rel_datapackage is mutually exclusive.
    all_related_resources = related_resources + related_datapackages

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
    persistent_identifier_datapackage = dictJsonData['System']['Persistent_Identifier_Datapackage']
    open_access_link = dictJsonData['System']['Open_access_Link']
    license_uri = dictJsonData['System']['License_URI']

    # Format last modified date.
    # Python 3: https://docs.python.org/3/library/datetime.html#datetime.date.fromisoformat
    # last_modified_date = date.fromisoformat(dictJsonData['System']['Last_Modified_Date'])
    last_modified_date = parser.parse(dictJsonData['System']['Last_Modified_Date'])
    last_modified_date = last_modified_date.strftime('%Y-%m-%d %H:%M:%S%z')

    # Format publication date.
    # Python 3: https://docs.python.org/3/library/datetime.html#datetime.date.fromisoformat
    # publication_date = date.fromisoformat(dictJsonData['System']['Publication_Date'])
    publication_date = parser.parse(dictJsonData['System']['Publication_Date'])
    publication_date = publication_date.strftime('%Y-%m-%d %H:%M:%S%z')

    try:
        geolocations = dictJsonData['GeoLocation']
    except KeyError:
        geolocations = {}

    # Collection name  ILAB specific - part of default schemas
    try:
        collection_name = dictJsonData['Collection_Name']
    except KeyError:
        collection_name = ''

    try:
        base_doi = baseDOI
    except KeyError:
        base_doi = ''

    try:
        all_versions = versions
    except KeyError:
        all_versions = []

    tm = Template(template)
    # tm.globals['custom_function'] = custom_function
    tm.globals['persistent_identifier_to_uri'] = persistent_identifier_to_uri
    landing_page = tm.render(
        title=title,
        description=description,
        datatype=datatype,
        labs=labs,
        additional_labs=additional_labs,
        disciplines=disciplines,
        version=version,
        language=language,
        tags=all_taggebles,
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
        related_resources=all_related_resources,
        persistent_identifier_datapackage=persistent_identifier_datapackage,
        geolocations=geolocations,
        covered_geolocation_place=covered_geolocation_place,
        base_doi=base_doi,
        all_versions=all_versions)

    return landing_page
