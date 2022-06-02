# -*- coding: utf-8 -*-
"""Functions for transforming JSON to landingpage HTML."""

__copyright__ = 'Copyright (c) 2019, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import jinja2

from util import *

def orcid():
    """ example of presentation of orcid - not used at the moment """

    return ('<a href="https://orcid.org/0000-0001-5727-2427">'
            '<img alt="ORCID logo" src="https://info.orcid.org/wp-content/uploads/2019/11/orcid_16x16.png" width="16" height="16" />'
            'https://orcid.org/0000-0001-2345-6789'
            '</a>')

def orcid_schema_id_to_identifier(identifier):
    """ in case of ORCID -> return only the id part of, what could be, a complete uri that is passed as identifier """

    if identifier.startswith('https://orcid.org'):
        return identifier.split('/')[-1]  # final part contains the actual id
    return identifier


def schema_id_to_uri(schema_id, identifier):
    """
    DAG:
    Creator / Contributor => ORCID not at the moment.
    Related Data Package => URL, Handle en DOI

    DEFAULT:
    Namen tbv Creator/Contributor

        "ORCID",
        "DAI", URI-fied a DAI looks like this: info:eu-repo/dai/nl/123456785
        "Author identifier (Scopus)", https://www.scopus.com/authid/detail.uri?authorId=
        "ResearcherID (Web of Science)", https://www.researcherid.com/rid/$1
        "ISNI", http://isni.org/isni/000000012146438X

    Related datapackage:
        "ARK",  https://nl.wikipedia.org/wiki/Archival_Resource_Key
        "arXiv",
        "bibcode",
        "DOI",
        "EAN13",
        "EISSN",
        "Handle",
        "ISBN",
        "ISSN",
        "ISTC",
        "LISSN",
        "LSID",
        "PMID",
        "PURL",
        "UPC",
        "URL",
        "URN"
    """
    # if not identifier:
    #    return 'NO IDENTIFIER'

    if identifier.upper().startswith('HTTPS://'):
        return identifier

    # Create a hyperlink from the raw schema information
    domain = ''
    id = ''
    if schema_id == 'DOI':
        domain = 'https://doi.org/'  # ff checken of identifier niet begint met /
        id = identifier
    elif schema_id == 'ORCID':
        domain = 'https://orcid.org/'
        id = identifier
    elif schema_id == 'Handle':
        domain = 'https://hdl.handle.net/'
        id = identifier
    elif schema_id == 'URL':
        domain = identifier
        id = ''
    else:
        domain = 'https://' + schema_id + '.org/' 
        id = identifier

    return domain + id


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
        schema_lang_ids = json_schema['definitions']['optionsLanguage']['enum']
        schema_lang_names = json_schema['definitions']['optionsLanguage']['enumNames']
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
    all_taggebles = (tags + apparatus + main_setting + process_hazard + geological_structure
                     + geomorphical_feature + material + monitoring + software + measured_property
                     + pore_fluid + ancillary_equipment + inferred_deformation_behaviour)

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
    # tm.globals['custom_function'] = custom_function
    tm.globals['schema_id_to_uri'] = schema_id_to_uri
    tm.globals['orcid_schema_id_to_identifier'] = orcid_schema_id_to_identifier
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
        related_datapackages=related_datapackages,
        persistent_identifier_datapackage=persistent_identifier_datapackage,
        geolocations=geolocations,
        covered_geolocation_place=covered_geolocation_place)

    return landing_page
