"""Functions for transforming JSON to landingpage HTML."""

__copyright__ = 'Copyright (c) 2019-2025, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
from datetime import datetime

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
        uri = f"https://doi.org/{identifier}"
    elif identifier_scheme == "ORCID":
        uri = f"https://orcid.org/{identifier}"
    elif identifier_scheme == "Handle":
        uri = f"https://hdl.handle.net/{identifier}"
    elif identifier_scheme == "URL":
        uri = identifier
    else:
        uri = f"#{identifier}"

    return uri


def _schema_org_organization(name: str, identifier: str = "") -> dict:
    """Convert an affiliation to a schema.org Organization.

    :param name:       Name of the organization
    :param identifier: A ROR URI ID

    :returns: Organization in schema.org format
    """
    organization: dict = {"@type": "Organization", "name": name}

    if identifier.startswith("https://") or identifier.startswith("http://"):
        organization["@id"] = identifier
        # sameAs is what Google asked for, derived from a Google example:
        # https://developers.google.com/search/docs/appearance/structured-data/dataset#example
        organization["sameAs"] = identifier

    return organization


def _schema_org_affiliations(affiliations: list) -> list[dict]:
    """Convert multiple affiliations to a list of schema.org Organizations.

    :param affiliations: List of organization affiliations

    :returns: List of Organizations in schema.org format
    """
    organizations = []

    # Different schemas use different ways to store affiliations
    for affiliation in affiliations:
        # Example below is for default-3, etc.
        if isinstance(affiliation, dict):
            name = affiliation.get("Affiliation_Name", "")
            if name:
                organizations.append(_schema_org_organization(str(name), affiliation.get("Affiliation_Identifier", "")))

        # Example below is for core-0, etc.
        elif isinstance(affiliation, str) and affiliation:
            organizations.append(_schema_org_organization(affiliation))

    return organizations


def _schema_org_person(person: dict) -> dict:
    """Convert a creator to a schema.org @type person.

    :param person: Creator in Yoda's metadata format

    :returns: Person in schema.org format
    """
    name = person.get("Name", {})
    if isinstance(name, str):
        full_name = name
    else:
        full_name = " ".join(filter(None, [name.get("Given_Name", ""), name.get("Family_Name", "")]))

    person_schema_org: dict = {
        "@type": "Person",
        "name": full_name,
    }

    uris = []
    for person_identifier in person.get("Person_Identifier", []):
        uri = persistent_identifier_to_uri(person_identifier.get("Name_Identifier_Scheme", ""),
                                           person_identifier.get("Name_Identifier", ""))
        if (uri.startswith("https://") or uri.startswith("http://")) and uri not in uris:
            uris.append(uri)

    if uris:
        # @id takes exactly one IRI https://www.w3.org/TR/json-ld11/#node-identifiers
        person_schema_org["@id"] = uris[0]
        person_schema_org["sameAs"] = uris

    affiliations = person.get("Affiliation", [])
    if isinstance(affiliations, str):
        affiliations = [affiliations]

    organizations = _schema_org_affiliations(affiliations)
    if organizations:
        person_schema_org["affiliation"] = organizations

    return person_schema_org


def _schema_org_keywords(keywords: list) -> list:
    """Get the keywords of a data package as a list of plain strings.

    :param keywords: Keywords of the data package, as collected for the template

    :returns: List of keywords
    """
    all_keywords = []

    # Schema.org expects plain text as keywords.
    # Special case about TreeKeyword: only the subject is used.
    for keyword in keywords:
        if isinstance(keyword, dict):
            all_keywords.append(keyword.get("subject", ""))

    return list(dict.fromkeys(keyword for keyword in all_keywords if keyword))


def _schema_org_date(date: str) -> str:
    """Convert timestamp to a date.

    :param date: Date/timestamp

    :returns: Date as YYYY-MM-DD, empty when there is no usable date
    """
    try:
        return parser.parse(date).strftime("%Y-%m-%d")
    except Exception:
        return ""


def _schema_org_temporal_coverage(json_data: dict) -> str:
    """Convert the collection period of a data package to temporal coverage.

    :param json_data: Combined metadata JSON of the data package

    :returns: Collection period as an ISO 8601 coverage
    """
    collected = json_data.get("Collected", {})
    start_date = _schema_org_date(collected.get("Start_Date", ""))
    end_date = _schema_org_date(collected.get("End_Date", ""))

    if not (start_date and end_date):
        return ""

    return f"{start_date}/{end_date}"


def create_schema_org_json_ld(json_data: dict,
                              doi_uri: str,
                              keywords: list,
                              publisher: str,
                              landing_page_url: str,
                              download_url: str) -> str:
    """Create the schema.org JSON-LD metadata block.

    The block is an entry point for crawlers such as the Google dataset crawler (primary
    consumer). The metadata fields are chosen based on the landingpage source file,
    what Google required/recommended, and the DataCite JSON-LD reference:
    https://developers.google.com/search/docs/appearance/structured-data/dataset
    https://schema.org/Dataset
    https://support.datacite.org/docs/datacite-content-resolver

    In principle, the minimum block has the Google required fields correctly
    converted. Other recommended properties are converted as much as possible.
    However, some out-of-date schemas have different ways of storing metadata fields,
    and to prevent errors from missing the whole block, this function will discard
    problematic keys only.

    :param json_data:        Combined metadata JSON of the data package
    :param doi_uri:          URI of the DOI of the data package
    :param keywords:         Keywords of the data package
    :param publisher:        Name of the publishing organization
    :param landing_page_url: Public URL of this landing page
    :param download_url:     URL to retrieve the data, empty unless it is openly available

    :returns: schema.org Dataset as a JSON string
    """
    # Google requires name and description.
    # Any key after @ is not our metadata key.
    json_ld: dict = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": json_data["Title"],
        "description": json_data["Description"],
    }

    # @id as identifier.
    if doi_uri:
        json_ld["@id"] = doi_uri
        json_ld["identifier"] = doi_uri

    if landing_page_url:
        json_ld["url"] = landing_page_url

    # Only if the data is publicly available.
    if download_url:
        # contentUrl is a Google required property of a DataDownload.
        json_ld["distribution"] = [{"@type": "DataDownload", "contentUrl": download_url}]
        json_ld["isAccessibleForFree"] = True

    # A license URI is used, not a name, because schema.org/license expects a URL or
    # CreativeWork, and Google asks for a URL pointing to a specific license version.
    # https://schema.org/license
    # Custom has no URI, it is the collection's Open_access_Link, in this case, the key is ignored,
    # which is safe, also Google only recommends it.
    if json_data.get("License", "") != "Custom":
        license_uri = json_data["System"].get("License_URI", "")
        if license_uri:
            json_ld["license"] = license_uri

    # Name is mandatory in the metadata form, so an empty one means the
    # metadata is broken, which is left out of the JSON-LD block.
    creators = []
    for creator in json_data.get("Creator", []):
        person = _schema_org_person(creator)
        if person.get("name"):
            creators.append(person)
    if creators:
        json_ld["creator"] = creators

    all_keywords = _schema_org_keywords(keywords)
    if all_keywords:
        json_ld["keywords"] = all_keywords

    # Version value is a string
    version = json_data.get("Version", "")
    if version:
        json_ld["version"] = version

    temporal_coverage = _schema_org_temporal_coverage(json_data)
    if temporal_coverage:
        json_ld["temporalCoverage"] = temporal_coverage

    date_published = _schema_org_date(json_data["System"].get("Publication_Date", ""))
    if date_published:
        json_ld["datePublished"] = date_published

    # Development env: "Yoda development team"
    # Production env: "Utrecht University"
    if publisher:
        json_ld["publisher"] = {"@type": "Organization", "name": publisher}

    # Extract the abbr., e.g., extract "en" from "en - English".
    language = json_data.get("Language", "").split("-")[0].strip()
    if language:
        json_ld["inLanguage"] = language

    # JSON escape.
    return (json.dumps(json_ld, indent=2)
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026"))


def json_landing_page_create_json_landing_page(ctx: rule.Context,
                                               zone: str,
                                               template_name: str,
                                               combi_json_path: str,
                                               json_schema: dict,
                                               random_id: str,
                                               base_doi: str,
                                               versions: dict,
                                               is_deaccession_complete: bool,
                                               is_archived: bool,
                                               landing_page_url: str) -> str:
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
    :param landing_page_url:            Public URL of this landing page

    :return: Output HTML landing page
    """
    import jinja2

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
    contacts = json_data.get("Contact", [])                # epos-msl-0, epos-msl-1, teclab-0, teclab-1, hptlab-0, hptlab-1
    labids = json_data.get("Lab", [])                      # epos-msl-0, epos-msl-1, teclab-0, teclab-1, hptlab-0, hptlab-1
    additional_labs = json_data.get("Additional_Lab", [])  # epos-msl-0, teclab-0, teclab-1, hptlab-0, hptlab-1
    geolocations = json_data.get("GeoLocation", {})        # dag-0, epos-msl-0, epos-msl-1, teclab-0, teclab-1, hptlab-0, hptlab-1

    # Convert lab identifiers to lab names.
    try:
        labs = []
        for lab in labids:
            if isinstance(lab, str):
                schema_labids = json_schema["definitions"]["optionsLabs"]["enum"]
                schema_labnames = json_schema["definitions"]["optionsLabs"]["enumNames"]
                idx = schema_labids.index(lab)
                labs.append(schema_labnames[idx])
            elif isinstance(lab, dict):
                lab_name = lab.get("name")
                labs.append(lab_name)
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

    # Whether the data can be downloaded in the JSON-LD block
    # Conditions are derived from the landingpage template, which activates the download button.
    is_openly_available = no_active_embargo and data_access_restriction.startswith("Open") and not is_deaccession_complete

    for field in ("Creator", "Language", "Keyword", "Tag", "TreeKeyword", "Collected", "Version"):
        if field in json_schema.get("required", []) and not json_data.get(field):
            log.write(ctx, f"Landing page {random_id}: mandatory metadata '{field}' is missing, "
                           "so it is omitted of the schema.org JSON-LD block")

    # Create schema.org JSON-LD block.
    try:
        schema_org_json_ld = create_schema_org_json_ld(
            json_data,
            persistent_identifier_to_uri(persistent_identifier_datapackage["Identifier_Scheme"],
                                         persistent_identifier_datapackage["Identifier"]),
            keywords,
            config.datacite_publisher,
            landing_page_url,
            open_access_link if is_openly_available else "")
    except Exception as e:
        log.write(ctx, f"Could not create schema.org JSON-LD metadata: {e}")
        schema_org_json_ld = ""

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
        schema_org_json_ld=schema_org_json_ld,
        geolocations=geolocations,
        covered_geolocation_place=covered_geolocation_place,
        random_id=random_id,
        base_doi=base_doi,
        versions=versions,
        is_deaccession_complete=is_deaccession_complete,
        is_archived=is_archived,
        matomo_counter_enabled=config.matomo_counter_enabled,
        matomo_tracking_enabled=config.matomo_tracking_enabled,
        matomo_server_fqdn=config.matomo_server_fqdn,
        matomo_site_id=config.matomo_site_id,
    )
