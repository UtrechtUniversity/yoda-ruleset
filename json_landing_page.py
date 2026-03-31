"""Functions for transforming JSON to landingpage HTML."""

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from datetime import datetime
from typing import Dict

import jinja2
from dateutil import parser

from util import *


def persistent_identifier_to_uri(identifier_scheme: str, identifier: str) -> str:
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


def json_landing_page_create_json_landing_page(ctx: rule.Context,
                                               zone: str,
                                               template_name: str,
                                               combi_json_path: str,
                                               json_schema: Dict,
                                               random_id: str,
                                               base_doi: str,
                                               versions: Dict,
                                               is_deaccession_complete: bool,
                                               is_archived: bool) -> str:
    """Get the landing page of published Yoda metadata as a string.

    :param ctx:                         Combined type of a ctx and rei struct
    :param zone:                        Zone name
    :param template_name:               Name of landingpage template
    :param combi_json_path:             Path to combined metadata JSON file
    :param json_schema:                 Dict holding entire contents of metadata.json for the category involved
    :param random_id:                   Random ID of the publication
    :param base_doi:                    Base DOI of the publication
    :param versions:                    Dict containing all the versions of the publication
    :param is_deaccession_complete:     Whether the data package is deaccessioned
    :param is_archived:                 Whether the data package is archived

    :return: Output HTML landing page
    """
    # Read and clean metadata.
    json_data = jsonutil.read(ctx, combi_json_path)
    json_data = misc.remove_empty_objects(json_data)

    # Load and prepare Jinja template.
    landingpage_template_path = f"/{zone}/yoda/templates/{template_name}"
    template = data_object.read(ctx, landingpage_template_path)
    tm = jinja2.Environment(autoescape=True).from_string(template)

    # Handle empty landing page (depublication).
    if template_name == "emptylandingpage.html.j2":
        persistent_identifier_datapackage = json_data["System"]["Persistent_Identifier_Datapackage"]
        return tm.render(
            matomo_tracking_enabled=config.matomo_tracking_enabled,
            matomo_server_fqdn=config.matomo_server_fqdn,
            matomo_site_id=config.matomo_site_id,
            persistent_identifier_datapackage=persistent_identifier_datapackage)

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

    # Extract keywords from multiple sources.
    keywords = []
    for keyword in json_data.get("Tag", []):  # from core-2 and default-3 Tag is renamed to Keyword
        keywords.append({"subject": keyword, "subjectScheme": "Keyword"})

    if "TreeKeyword" in json_data:
        keywords.extend(json_data["TreeKeyword"])
    else:
        for keyword in json_data.get("Keyword", []):
            keywords.append({"subject": keyword, "subjectScheme": "Keyword"})

    # Extract discipline names from schema.
    try:
        disciplines = []
        discipline_ids = json_data.get("Discipline", [])
        if discipline_ids:
            schema_disc_ids = json_schema["definitions"]["optionsDiscipline"]["enum"]
            schema_disc_names = json_schema["definitions"]["optionsDiscipline"]["enumNames"]
            disciplines = [schema_disc_names[schema_disc_ids.index(id)] for id in discipline_ids]
    except (KeyError, ValueError, IndexError):
        disciplines = []

    # Extract data type name from schema.
    try:
        datatype = ""
        datatype_id = json_data.get("Data_Type")
        if datatype_id:
            schema_dt_ids = json_schema["definitions"]["optionsDataType"]["enum"]
            schema_dt_names = json_schema["definitions"]["optionsDataType"]["enumNames"]
            datatype = schema_dt_names[schema_dt_ids.index(datatype_id)]
    except (KeyError, ValueError, IndexError):
        datatype = ""

    # Extract language name from schema.
    try:
        language = ""
        language_id = json_data.get("Language")
        if language_id:
            schema_lang_ids = json_schema["definitions"]["optionsISO639-1"]["enum"]
            schema_lang_names = json_schema["definitions"]["optionsISO639-1"]["enumNames"]
            language = schema_lang_names[schema_lang_ids.index(language_id)]
    except (KeyError, ValueError, IndexError):
        language = ""

    ############################################################################
    # Default metadata
    ############################################################################
    version = json_data.get("Version", "")
    collection_name = json_data.get("Collection_Name", "")
    contributors = json_data.get("Contributor", [])
    funding_reference = json_data.get("Funding_Reference", [])
    covered_geolocation_place = json_data.get("Covered_Geolocation_Place", {})

    # Combine related resources from both old and new field names.
    all_related_resources = json_data.get("Related_Datapackage", [])
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
        if labids:
            schema_labids = json_schema["definitions"]["optionsLabs"]["enum"]
            schema_labnames = json_schema["definitions"]["optionsLabs"]["enumNames"]
            labs = [schema_labnames[schema_labids.index(id)] for id in labids]
    except (KeyError, ValueError, IndexError):
        labs = []

    # Geo specific keywords.
    geo_keyword_fields = [
        "Apparatus",                       # teclab-0, teclab-1, hptlab-0, hptlab-1
        "Material",                        # teclab-0, teclab-1, hptlab-0, hptlab-1
        "Measured_Property",               # teclab-0, teclab-1, hptlab-0, hptlab-1
        "Monitoring",                      # teclab-0, teclab-1, hptlab-0
        "Main_Setting",                    # teclab-0, teclab-1
        "Process_Hazard",                  # teclab-0, teclab-1
        "Geological_Structure",            # teclab-0, teclab-1
        "Software",                        # teclab-0, teclab-1
        "Geomorphological_Feature",        # teclab-1
        "Pore_Fluid",                      # hptlab-1
        "Ancillary_Equipment",             # hptlab-1
        "Inferred_Deformation_Behaviour",  # hptlab-1
    ]
    for field in geo_keyword_fields:
        keywords.extend(json_data.get(field, []))

    ############################################################################
    # System metadata
    ############################################################################
    persistent_identifier_datapackage = json_data["System"]["Persistent_Identifier_Datapackage"]
    open_access_link = json_data["System"].get("Open_access_Link", "")

    # Determine license URI.
    license_uri = ""
    if no_active_embargo and license == "Custom" and data_access_restriction.startswith("Open"):
        license_uri = open_access_link
    elif license != "Custom":
        license_uri = json_data["System"].get("License_URI", "")

    # Format last modified and publication date.
    last_modified_date_time = parser.parse(json_data["System"]["Last_Modified_Date"])
    last_modified_date = last_modified_date_time.strftime("%Y-%m-%d %H:%M:%S%z")
    publication_date_time = parser.parse(json_data["System"]["Publication_Date"])
    publication_date = publication_date_time.strftime("%Y-%m-%d %H:%M:%S%z")

    # Add custom template functions.
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
        random_id=random_id,
        base_doi=base_doi,
        versions=versions,
        is_deaccession_complete=is_deaccession_complete,
        is_archived=is_archived,
        matomo_tracking_enabled=config.matomo_tracking_enabled,
        matomo_server_fqdn=config.matomo_server_fqdn,
        matomo_site_id=config.matomo_site_id,
    )
