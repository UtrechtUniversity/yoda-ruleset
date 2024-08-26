# -*- coding: utf-8 -*-
"""Functions for transforming JSON to landingpage HTML."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from datetime import datetime

import jinja2
from dateutil import parser

from util import *


def persistent_identifier_to_uri(identifier_scheme, identifier):
    """Transform a persistent identifier to URI.

    Supported identifier schemes are Handle, DOI, ORCID and URL.

    :param identifier_scheme: Schema of identifier to transform
    :param identifier:        Identifier to transform to URI

    :returns: URI of persistent identifier
    """
    # Identifier already is an URI.
    if identifier.lower().startswith("https://") or identifier.lower().startswith("http://"):
        return identifier

    # Create a URI from the identifier scheme and identifier.
    uri = ""
    if identifier_scheme == "DOI":
        uri = "https://doi.org/{}".format(identifier)
    elif identifier_scheme == "ORCID":
        uri = "https://orcid.org/{}".format(identifier)
    elif identifier_scheme == "Handle":
        uri = "https://hdl.handle.net/{}".format(identifier)
    elif identifier_scheme == "URL":
        uri = identifier
    else:
        uri = "#{}".format(identifier)

    return uri


def json_landing_page_create_json_landing_page(ctx, zone, template_name, combi_json_path, json_schema, base_doi, versions):
    """Get the landing page of published YoDa metadata as a string.

    :param ctx:             Combined type of a ctx and rei struct
    :param zone:            Zone name
    :param template_name:   Name of landingpage template
    :param combi_json_path: Path to combined metadata JSON file
    :param json_schema:     Dict holding entire contents of metadata.json for the category involved
    :param base_doi:        Base DOI of the publication
    :param versions:        Dict containing all the versions of the publication

    :return: Output HTML landing page
    """
    # Landing page creation is part of the publication process
    # Read user & system metadata from corresponding combi JSON file
    # (Python2) 'want_bytes=False': Do not encode embedded unicode strings as
    #                               UTF-8, as that will trip up jinja2.
    json_data = jsonutil.read(ctx, combi_json_path, want_bytes=False)

    # Remove empty objects to prevent empty fields on landingpage.
    json_data = misc.remove_empty_objects(json_data)

    # Load the Jinja template.
    landingpage_template_path = "/{}/yoda/templates/{}".format(zone, template_name)
    template = data_object.read(ctx, landingpage_template_path)

    # Enable autoescaping for all templates.
    # NOTE: autoescape is no longer an extension starting in jinja 2.9 (2017).
    Template = jinja2.Environment(autoescape=True, extensions=["jinja2.ext.autoescape"]).from_string

    # Pre work input for render process.
    # When empty landing page, take a short cut
    if template_name == "emptylandingpage.html.j2":
        persistent_identifier_datapackage = json_data["System"]["Persistent_Identifier_Datapackage"]
        tm = Template(template)
        landing_page = tm.render(persistent_identifier_datapackage=persistent_identifier_datapackage)
        return landing_page

    ############################################################################
    # Embargo
    ############################################################################
    no_active_embargo = True
    embargo_end_date = json_data.get("Embargo_End_Date", None)
    if embargo_end_date is not None and len(embargo_end_date):
        no_active_embargo = datetime.now().strftime("%Y-%m-%d") >= embargo_end_date

    ############################################################################
    # Core metadata
    ############################################################################
    title = json_data["Title"]
    description = json_data["Description"]
    creators = json_data.get("Creator", [])
    license = json_data["License"]
    data_access_restriction = json_data["Data_Access_Restriction"]
    data_classification = json_data["Data_Classification"]

    keywords = json_data.get("Tag", [])
    # From core-2 and default-3 Tag is renamed to Keyword
    keywords.extend(json_data.get("Keyword", []))

    try:
        disciplines = []
        discipline_ids = json_data["Discipline"]
        schema_disc_ids = json_schema["definitions"]["optionsDiscipline"]["enum"]
        schema_disc_names = json_schema["definitions"]["optionsDiscipline"]["enumNames"]
        for id in discipline_ids:
            index = schema_disc_ids.index(id)
            disciplines.append(schema_disc_names[index])
    except KeyError:
        disciplines = []

    try:
        datatype = ""
        datatype_id = json_data["Data_Type"]
        schema_dt_ids = json_schema["definitions"]["optionsDataType"]["enum"]
        schema_dt_names = json_schema["definitions"]["optionsDataType"]["enumNames"]
        index = schema_dt_ids.index(datatype_id)
        datatype = schema_dt_names[index]
    except KeyError:
        datatype = ""

    try:
        language = ""
        language_id = json_data["Language"]
        # Convert just the language schemas to unicode to handle when a language has non-ascii characters (like Volapük)
        schema_lang_ids = map(lambda x: x.decode("utf-8"), json_schema["definitions"]["optionsISO639-1"]["enum"])
        schema_lang_names = map(lambda x: x.decode("utf-8"), json_schema["definitions"]["optionsISO639-1"]["enumNames"])
        index = schema_lang_ids.index(language_id)
        # Language variable must be kept in unicode, otherwise landing page fails to build with a language with non-ascii characters
        language = schema_lang_names[index]
    except KeyError:
        language = ""

    ############################################################################
    # Default metadata
    ############################################################################
    version = json_data.get("Version", "")
    collection_name = json_data.get("Collection_Name", "")
    contributors = json_data.get("Contributor", [])
    funding_reference = json_data.get("Funding_Reference", [])
    covered_geolocation_place = json_data.get("Covered_Geolocation_Place", {})

    all_related_resources = json_data.get("Related_Datapackage", [])
    # From core-2 and default-3 Related_Datapackage is renamed to Related_Resource
    all_related_resources.extend(json_data.get("Related_Resource", []))

    ############################################################################
    # Geo specific metadata
    ############################################################################
    contacts = json_data.get("Contact", [])                # epos-msl-0, teclab-0, teclab-1, hptlab-0, hptlab-1
    labids = json_data.get("Lab", [])                      # epos-msl-0, teclab-0, teclab-1, hptlab-0, hptlab-1
    additional_labs = json_data.get("Additional_Lab", [])  # epos-msl-0, teclab-0, teclab-1, hptlab-0, hptlab-1
    geolocations = json_data.get("GeoLocation", {})        # dag-0, epos-msl-0, teclab-0, teclab-1, hptlab-0, hptlab-1

    # Convert lab identifiers to lab names.
    try:
        labs = []
        schema_labids = json_schema["definitions"]["optionsLabs"]["enum"]
        schema_labnames = json_schema["definitions"]["optionsLabs"]["enumNames"]
        for id in labids:
            index = schema_labids.index(id)
            labs.append(schema_labnames[index])
    except KeyError:
        labs = []

    # Geo specific keywords
    keywords.extend(json_data.get("Apparatus", []))                       # teclab-0, teclab-1, hptlab-0, hptlab-1
    keywords.extend(json_data.get("Material", []))                        # teclab-0, teclab-1, hptlab-0, hptlab-1
    keywords.extend(json_data.get("Measured_Property", []))               # teclab-0, teclab-1, hptlab-0, hptlab-1
    keywords.extend(json_data.get("Monitoring", []))                      # teclab-0, teclab-1, hptlab-0
    keywords.extend(json_data.get("Main_Setting", []))                    # teclab-0, teclab-1
    keywords.extend(json_data.get("Process_Hazard", []))                  # teclab-0, teclab-1
    keywords.extend(json_data.get("Geological_Structure", []))            # teclab-0, teclab-1
    keywords.extend(json_data.get("Software", []))                        # teclab-0, teclab-1
    keywords.extend(json_data.get("Geomorphological_Feature", []))        # teclab-1
    keywords.extend(json_data.get("Pore_Fluid", []))                      # hptlab-1
    keywords.extend(json_data.get("Ancillary_Equipment", []))             # hptlab-1
    keywords.extend(json_data.get("Inferred_Deformation_Behaviour", []))  # hptlab-1

    ############################################################################
    # System metadata
    ############################################################################
    persistent_identifier_datapackage = json_data["System"]["Persistent_Identifier_Datapackage"]
    open_access_link = json_data["System"].get("Open_access_Link", "")
    license_uri = json_data["System"].get("License_URI", "")

    # Format last modified and publication date.
    # Python 3: https://docs.python.org/3/library/datetime.html#datetime.date.fromisoformat
    # last_modified_date = date.fromisoformat(json_data['System']['Last_Modified_Date'])
    last_modified_date = parser.parse(json_data["System"]["Last_Modified_Date"])
    last_modified_date = last_modified_date.strftime("%Y-%m-%d %H:%M:%S%z")
    # Python 3: https://docs.python.org/3/library/datetime.html#datetime.date.fromisoformat
    # publication_date = date.fromisoformat(json_data['System']['Publication_Date'])
    publication_date = parser.parse(json_data["System"]["Publication_Date"])
    publication_date = publication_date.strftime("%Y-%m-%d %H:%M:%S%z")

    tm = Template(template)
    # Add custom function to transform a persistent identifier to URI.
    tm.globals["persistent_identifier_to_uri"] = persistent_identifier_to_uri

    # Render landingpage template.
    return tm.render(
        title=title,
        description=description,
        datatype=datatype,
        labs=labs,
        additional_labs=additional_labs,
        disciplines=disciplines,
        version=version,
        language=language,
        keywords=keywords,
        creators=creators,
        contributors=contributors,
        contacts=contacts,
        publication_date=publication_date,
        embargo_end_date=embargo_end_date,
        no_active_embargo=no_active_embargo,
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
        versions=versions,
    )
