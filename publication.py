"""Functions for publication."""

__copyright__ = 'Copyright (c) 2019-2026, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
import re
import urllib.parse
from datetime import datetime
from traceback import format_exc
from typing import List, Tuple

import genquery
from requests.exceptions import ReadTimeout
from tstrings import t

import datacite
import json_datacite
import json_landing_page
import meta
import provenance
import research
import schema
import vault
import vault_deaccession
from publication_utils import (
    generate_base_doi,
    generate_landing_page_url,
    generate_preliminary_doi,
    is_latest_version,
    should_abort,
    should_process,
    should_return_early
)
from util import *

__all__ = ['rule_process_publication',
           'rule_process_depublication',
           'rule_process_republication',
           'rule_update_publication',
           'rule_add_base_doi',
           'rule_lift_embargos_on_data_access']


def get_publication_config(ctx: rule.Context) -> dict[str, str]:
    """Get all publication config keys and their values and report any missing keys."""
    zone = user.zone(ctx)
    system_coll = f"/{zone}{constants.UUSYSTEMCOLLECTION}"

    attr_mapping = {
        "public_host": "publicHost",
        "public_vhost": "publicVHost",
        "moai_host": "moaiHost",
        "yoda_prefix": "yodaPrefix",
        "datacite_prefix": "dataCitePrefix",
        "random_id_length": "randomIdLength",
        "yoda_instance": "yodaInstance",
        "davrods_vhost": "davrodsVHost",
        "davrods_anonymous_vhost": "davrodsAnonymousVHost",
        "publication_verbose_mode": "verboseMode"
    }
    optional_keys = {"publication_verbose_mode"}

    config_keys = {}
    found_attrs = set()
    prefix_length = len(constants.UUORGMETADATAPREFIX)

    iter = genquery.row_iterator(
        "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        f"COLL_NAME = '{system_coll}' AND  META_COLL_ATTR_NAME like '{constants.UUORGMETADATAPREFIX}%'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        attr = row[0][prefix_length:]  # Strip prefix from attributes.
        val = row[1]

        if attr in attr_mapping:
            found_attrs.add(attr)
            config_keys[attr_mapping[attr]] = val
        else:
            log.write(ctx, f'Unknown config attribute: {attr}')

    # Report missing required keys.
    missing = set(attr_mapping.keys()) - found_attrs - optional_keys
    for key in missing:
        log.write(ctx, f'Missing config key: {key}')

    return config_keys


def generate_combi_json(ctx: rule.Context, publication_config: dict, publication_state: dict) -> None:
    """Join system metadata with the user metadata in yoda-metadata.json.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process

    :raises Exception: When latest metadata is not found
    """
    davrods_anonymous_vhost = publication_config["davrodsAnonymousVHost"]
    vault_package = publication_state["vaultPackage"]
    random_id = publication_state["randomId"]
    combi_json_path = f"/{user.zone(ctx)}{constants.IIPUBLICATIONCOLLECTION}/{random_id}-combi.json"
    version_doi = publication_state["versionDOI"]
    last_modified_date = publication_state["lastModifiedDateTime"]
    publication_date = publication_state["publicationDate"]

    # Build open access link if applicable.
    open_access_link = ""
    if publication_state["accessRestriction"].startswith("Open"):
        subpath = vault_package.split('/home/', 1)[1]
        open_access_link = urllib.parse.quote(
            f"https://{davrods_anonymous_vhost}/{subpath}",
            safe=":/="
        )

    # Get license URI if present.
    license_uri = publication_state.get("licenseUri", "")

    # Retrieve and validate metadata.
    metadata_json_path = meta.get_latest_vault_metadata_path(ctx, vault_package)
    if metadata_json_path is None:
        raise Exception("Latest vault metadata not found")

    metadata = jsonutil.read(ctx, metadata_json_path)

    # Add system metadata.
    metadata['System'] = {
        'Last_Modified_Date': last_modified_date,
        'Persistent_Identifier_Datapackage': {
            'Identifier_Scheme': 'DOI',
            'Identifier': version_doi
        },
        'Publication_Date': publication_date,
        'Open_access_Link': open_access_link,
        'License_URI': license_uri
    }

    deaccession_date = vault_deaccession.get_deaccession_date(ctx, vault_package)
    if deaccession_date:
        metadata['System']['Withdrawn_Date'] = deaccession_date.strftime('%Y-%m-%dT%H:%M:%S%z')

    # Write combined metadata to file.
    jsonutil.write(ctx, combi_json_path, metadata)
    publication_state["combiJsonPath"] = combi_json_path


def generate_system_json(ctx: rule.Context, publication_state: dict) -> None:
    """Overwrite combi metadata json with system-only metadata.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    """
    temp_coll = "/" + user.zone(ctx) + constants.IIPUBLICATIONCOLLECTION

    randomId = publication_state["randomId"]
    system_json_path = temp_coll + "/" + randomId + "-combi.json"

    doi = publication_state["versionDOI"]

    system_json_data = {
        "System": {
            "Last_Modified_Date": publication_state["lastModifiedDateTime"],
            "Persistent_Identifier_Datapackage": {
                "Identifier_Scheme": "DOI",
                "Identifier": doi,
            },
            "Publication_Date": publication_state["publicationDate"]
        }
    }

    data_object.write(ctx, system_json_path, jsonutil.dump(system_json_data))
    publication_state["combiJsonPath"] = system_json_path


def get_publication_state(ctx: rule.Context, vault_package: str) -> dict:
    """The publication state is kept as metadata on the vault package.

    :param ctx:           Combined type of a callback and rei struct
    :param vault_package: Path to the package in the vault

    :returns: Dict with state of the publication process
    """
    publication_state = {
        "status": constants.publication_status.UNKNOWN,
        "accessRestriction": "Closed"
    }

    publ_metadata = get_collection_metadata(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'publication_')

    # Take over all actual values as saved earlier.
    for key, value in publ_metadata.items():
        publication_state[key] = value

    # Handle access restriction.
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        t("META_COLL_ATTR_NAME like '%Data_Access_Restriction' AND COLL_NAME = '{vault_package}'"),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        publication_state["accessRestriction"] = row[0]

    # Handle license.
    license = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        t("META_COLL_ATTR_NAME like '%License' AND COLL_NAME = '{vault_package}'"),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        license = row[0]

    if license != "":
        publication_state["license"] = license
        license_uri = ""
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            t("META_COLL_ATTR_NAME like '{constants.UUORGMETADATAPREFIX}license_uri' AND COLL_NAME = '{vault_package}'"),
            genquery.AS_LIST, ctx
        )
        for row in iter:
            license_uri = row[0]

        if license_uri != "":
            publication_state["licenseUri"] = license_uri

    publication_state["vaultPackage"] = vault_package
    return publication_state


def save_publication_state(ctx: rule.Context, vault_package: str, publication_state: dict) -> None:
    """Save the publication state key-value-pairs to AVU's on the vault package.

    :param ctx:               Combined type of a callback and rei struct
    :param vault_package:     Path to the package in the vault
    :param publication_state: Dict with state of the publication process
    """
    avu.rmw_from_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'publication_%', "%", "%")
    for key in publication_state:
        if publication_state[key] != "":
            avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'publication_' + key, str(publication_state[key]))


def set_update_publication_state(ctx: rule.Context, vault_package: str) -> str:
    """Routine to set publication state of vault package pending to update.

    :param ctx:           Combined type of a callback and rei struct
    :param vault_package: Path to the package in the vault

    :returns: String with state of publication state update
    """
    # check permissions - rodsadmin only
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    coll_status = vault.get_coll_vault_status(ctx, vault_package).value
    if coll_status not in [str(constants.vault_package_state.PUBLISHED), str(constants.vault_package_state.PENDING_DEPUBLICATION), str(constants.vault_package_state.PENDING_REPUBLICATION)]:
        return "NotAllowed"

    publication_state = get_publication_state(ctx, vault_package)
    if publication_state["status"] != constants.publication_status.OK:
        return "PublicationNotOK"

    # Set publication status
    publication_state["status"] = constants.publication_status.UNKNOWN

    # Generate new JSONs
    publication_state["combiJsonPath"] = ""
    publication_state["dataCiteJsonPath"] = ""

    # Post metadata to DataCite
    publication_state["dataCiteMetadataPosted"] = ""

    # Generate new landingpage
    publication_state["landingPagePath"] = ""
    publication_state["landingPageUploaded"] = ""

    # Update OAI-PMH metadata
    publication_state["oaiUploaded"] = ""

    # Update anonymous access
    publication_state["anonymousAccess"] = ""

    # Save state
    save_publication_state(ctx, vault_package, publication_state)
    return ""


def get_publication_date(ctx: rule.Context, vault_package: str) -> str:
    """Determine the time of publication as a datetime with UTC offset.

    First try action_log. Then icat-time.

    :param ctx:           Combined type of a callback and rei struct
    :param vault_package: Path to the package in the vault

    :return: Publication date in ISO8601 format
    """
    iter = genquery.row_iterator(
        "order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE",
        t("COLL_NAME = '{vault_package}' AND META_COLL_ATTR_NAME = '{constants.UUORGMETADATAPREFIX}action_log'"),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # row contains json encoded [str(int(time.time())), action, actor]
        log_item_list = jsonutil.parse(row[1])
        if log_item_list[1] == "published":
            publication_timestamp = datetime.fromtimestamp(int(log_item_list[0]))

            # ISO8601-fy
            return publication_timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f%z')

    my_date = datetime.now()
    return my_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z')


def get_last_modified_datetime(ctx: rule.Context, vault_package: str) -> str:
    """Determine the time of last modification as a datetime with UTC offset.

    :param ctx:           Combined type of a callback and rei struct
    :param vault_package: Path to the package in the vault

    :return: Last modified date in ISO8601 format
    """
    iter = genquery.row_iterator(
        "order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE",
        t("COLL_NAME = '{vault_package}' AND META_COLL_ATTR_NAME = '{constants.UUORGMETADATAPREFIX}action_log'"),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        log_item_list = jsonutil.parse(row[1])
        my_date = datetime.fromtimestamp(int(log_item_list[0]))
        return my_date.strftime('%Y-%m-%dT%H:%M:%S%z')

    my_date = datetime.now()
    return my_date.strftime('%Y-%m-%dT%H:%M:%S%z')


def generate_datacite_json(ctx: rule.Context, publication_state: dict) -> None:
    """Generate a DataCite compliant JSON based on yoda-metadata.json.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    """
    combiJsonPath = publication_state["combiJsonPath"]

    randomId = publication_state["randomId"]

    temp_coll, coll = pathutil.chop(combiJsonPath)
    datacite_json_path = temp_coll + "/" + randomId + "-dataCite.json"

    # Based on content of *combiJsonPath, get DataciteJson as string
    datacite_json = json_datacite.create_datacite_json(ctx, publication_state["landingPageUrl"], combiJsonPath)

    data_object.write(ctx, datacite_json_path, jsonutil.dump(datacite_json))

    publication_state["dataCiteJsonPath"] = datacite_json_path


def post_metadata_to_datacite(ctx: rule.Context, publication_state: dict, doi: str, send_method: str, base_doi: bool = False) -> None:
    """Upload DataCite JSON to DataCite. This will register the DOI, without minting it.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    :param doi:                DataCite DOI to update metadata
    :param send_method:        http verb (either 'post' or 'put')
    :param base_doi:           Indicates if we are sending metadata for base DOI
    """
    datacite_json_path = publication_state["dataCiteJsonPath"]
    datacite_json = data_object.read(ctx, datacite_json_path)

    if base_doi:
        datacite_json = datacite_json.replace(publication_state['versionDOI'], doi)

    try:
        if send_method == 'post':
            response = datacite.metadata_post(datacite_json)
        else:
            response = datacite.metadata_put(doi, datacite_json)

        http_code = response.status_code

        if (send_method == 'post' and http_code == 201) or (send_method == 'put' and http_code == 200):
            publication_state["dataCiteMetadataPosted"] = "yes"
        elif http_code in [401, 403, 500, 503, 504]:
            # Unauthorized, Forbidden, Precondition failed, Internal Server Error
            log.write(ctx, f"post_metadata_to_datacite: HTTP code {http_code} received. Operation will be retried later. {datacite.get_errors(response.json())}")
            publication_state["status"] = constants.publication_status.RETRY
        else:
            log.write(ctx, f"post_metadata_to_datacite: HTTP code {http_code} received. Unrecoverable error. {datacite.get_errors(response.json())}")
            publication_state["status"] = constants.publication_status.UNRECOVERABLE
    except ReadTimeout:
        # DataCite timeout.
        log.write(ctx, "post_metadata_to_datacite: DataCite timeout received. Operation will be retried later.")
        publication_state["status"] = constants.publication_status.RETRY


def post_draft_doi_to_datacite(ctx: rule.Context, publication_state: dict) -> None:
    """Upload DOI to DataCite. This will register the DOI as a draft.
    This function is also a draft, and will have to be reworked!

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    """
    datacite_json_path = publication_state["dataCiteJsonPath"]
    datacite_json = data_object.read(ctx, datacite_json_path)

    try:
        # post the DOI only
        response = datacite.metadata_post({
            'data': {
                'type': 'dois',
                'attributes': {
                    'doi': datacite_json['data']['attributes']['doi']
                }
            }
        })

        http_code = response.status_code

        if http_code == 201:
            publication_state["dataCiteMetadataPosted"] = "no"
        elif http_code in [401, 403, 500, 503, 504]:
            # Unauthorized, Forbidden, Precondition failed, Internal Server Error
            log.write(ctx, f"post_draft_doi_to_datacite: HTTP code {http_code} received. Operation will be retried later. {datacite.get_errors(response.json())}")
            publication_state["status"] = constants.publication_status.RETRY
        else:
            log.write(ctx, f"post_draft_doi_to_datacite: HTTP code {http_code} received. Unrecoverable error. {datacite.get_errors(response.json())}")
            publication_state["status"] = constants.publication_status.UNRECOVERABLE
    except ReadTimeout:
        # DataCite timeout.
        log.write(ctx, "post_draft_doi_to_datacite: DataCite timeout received. Operation will be retried later.")
        publication_state["status"] = constants.publication_status.RETRY


def remove_metadata_from_datacite(ctx: rule.Context, publication_state: dict, type_flag: str) -> None:
    """Remove metadata XML from DataCite.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    :param type_flag:          Determine whether it is base DOI or version DOI
    """
    payload = json.dumps({"data": {"attributes": {"event": "hide"}}})

    try:
        response = datacite.metadata_put(publication_state[type_flag + "DOI"], payload)

        http_code = response.status_code

        if http_code == 200:
            publication_state["dataCiteMetadataPosted"] = "yes"
        elif http_code in [401, 403, 412, 500, 503, 504]:
            # Unauthorized, Forbidden, Precondition failed, Internal Server Error
            log.write(ctx, f"remove_metadata_from_datacite: HTTP code {http_code} received. Operation will be retried later. {datacite.get_errors(response.json())}")
            publication_state["status"] = constants.publication_status.RETRY
        elif http_code == 404:
            # Invalid DOI
            log.write(ctx, f"remove_metadata_from_datacite: HTTP code {http_code}. Invalid DOI. {datacite.get_errors(response.json())}")
            publication_state["status"] = constants.publication_status.UNRECOVERABLE
        else:
            log.write(ctx, f"remove_metadata_from datacite: HTTP code {http_code} received. Unrecoverable error. {datacite.get_errors(response.json())}")
            publication_state["status"] = constants.publication_status.UNRECOVERABLE
    except ReadTimeout:
        # DataCite timeout.
        log.write(ctx, "remove_metadata_from_datacite: DataCite timeout received. Operation will be retried later.")
        publication_state["status"] = constants.publication_status.RETRY


def mint_doi(ctx: rule.Context, publication_state: dict, type_flag: str) -> None:
    """Announce the landing page URL for a DOI to dataCite. This will mint the DOI.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    :param type_flag:          Flag indicating DOI type ('version' or 'base')
    """
    payload = json.dumps({"data": {"attributes": {"url": publication_state["landingPageUrl"]}}})

    try:
        response = datacite.metadata_put(publication_state[type_flag + "DOI"], payload)

        http_code = response.status_code

        if http_code == 200:  # 201:
            publication_state[type_flag + "DOIMinted"] = "yes"
        elif http_code in [401, 403, 412, 500, 503, 504]:
            # Unauthorized, Forbidden, Precondition failed, Internal Server Error
            log.write(ctx, f"mint_doi: HTTP code {http_code} received. Operation could be retried later. {datacite.get_errors(response.json())}")
            publication_state["status"] = constants.publication_status.RETRY
        elif http_code == 400:
            log.write(ctx, f"mint_doi: HTTP code {http_code} received. Request body must be exactly two lines: DOI and URL; wrong domain, wrong prefix. {datacite.get_errors(response.json())}")
            publication_state["status"] = constants.publication_status.UNRECOVERABLE
        else:
            log.write(ctx, f"mint_doi: HTTP code {http_code} received. Unrecoverable error. {datacite.get_errors(response.json())}")
            publication_state["status"] = constants.publication_status.UNRECOVERABLE
    except ReadTimeout:
        # DataCite timeout.
        log.write(ctx, "mint_doi: DataCite timeout received. Operation will be retried later.")
        publication_state["status"] = constants.publication_status.RETRY


def generate_landing_page(ctx: rule.Context, publication_state: dict, publish: str) -> None:
    """Generate landingpage based upon yoda-metadata.json metadata and system metadata.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    :param publish:            "publish" for publication or "depublish" for depublication
    """
    combi_json_path = publication_state["combiJsonPath"]
    random_id = publication_state["randomId"]
    vault_package = publication_state["vaultPackage"]

    json_schema = schema.get_active_schema(ctx, vault_package)
    temp_coll, coll = pathutil.chop(combi_json_path)
    landing_page_path = temp_coll + "/" + random_id + ".html"

    # Check vault archive state.
    is_archived = False
    if config.enable_data_package_archive:
        import vault_archive  # noqa: F406
        is_archived = vault_archive.vault_archival_status(ctx, coll) == "archived"

    # Check vault deaccession state.
    deaccession_status = vault_deaccession.vault_deaccession_status(ctx, vault_package)
    is_deaccession_complete = constants.vault_deaccession_state(deaccession_status) == constants.vault_deaccession_state.DEACCESSION_COMPLETE

    # Get DOI and versions.
    base_doi = publication_state.get("baseDOI", "")
    versions = get_all_versions(ctx, vault_package, base_doi)[0] if base_doi else []

    # Select template based on publish state.
    template_name = "landingpage.html.j2" if publish == "publish" else "emptylandingpage.html.j2"

    # Generate and write landing page.
    landing_page_html = json_landing_page.json_landing_page_create_json_landing_page(
        ctx,
        user.zone(ctx),
        template_name,
        combi_json_path,
        json_schema,
        random_id,
        base_doi,
        versions,
        is_deaccession_complete,
        is_archived,
    )

    data_object.write(ctx, landing_page_path, landing_page_html)
    publication_state["landingPagePath"] = landing_page_path


def copy_landingpage_to_public_host(ctx: rule.Context, random_id: str, publication_config: dict, publication_state: dict) -> None:
    """Copy the resulting landing page to configured public host.

    :param ctx:                Combined type of a callback and rei struct
    :param random_id:          Random ID part of DOI used for landingpage file
    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    publicHost = publication_config["publicHost"]
    landingPagePath = publication_state["landingPagePath"]
    yodaInstance = publication_config["yodaInstance"]
    yodaPrefix = publication_config["yodaPrefix"]
    publicPath = yodaInstance + "/" + yodaPrefix + "/" + random_id + ".html"

    argv = publicHost + " inbox /var/www/landingpages/" + publicPath

    copy_result = ctx.iiGenericSecureCopy(argv, landingPagePath, '')
    error = copy_result['arguments'][2]
    if int(error) >= 0:
        publication_state["landingPageUploaded"] = "yes"
    else:
        publication_state["status"] = constants.publication_status.RETRY
        log.write(ctx, "copy_landingpage_to_public_host: " + error)


def copy_metadata_to_moai(ctx: rule.Context, random_id: str, publication_config: dict, publication_state: dict) -> None:
    """Copy the metadata json file to configured MOAI.

    :param ctx:                Combined type of a callback and rei struct
    :param random_id:          Random ID part of DOI used for MOAI metadata file
    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    public_host = publication_config["publicHost"]
    yoda_instance = publication_config["yodaInstance"]
    yoda_prefix = publication_config["yodaPrefix"]
    combi_json_path = publication_state["combiJsonPath"]

    remote_destination = f"inbox /var/www/moai/metadata/{yoda_instance}/{yoda_prefix}/{random_id}.json"
    remote_path = f"{public_host} {remote_destination}"

    copy_result = ctx.iiGenericSecureCopy(remote_path, combi_json_path, '')
    error_code = int(copy_result['arguments'][2])

    if error_code >= 0:
        publication_state["oaiUploaded"] = "yes"
    else:
        publication_state["status"] = constants.publication_status.RETRY
        log.write(ctx, f"copy_metadata_to_moai: {error_code}")


def generate_manifest(ctx: rule.Context, publication_state: dict) -> None:
    """Generate a manifest of data package.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    """
    temp_coll = "/" + user.zone(ctx) + constants.IIPUBLICATIONCOLLECTION

    vault_package = publication_state["vaultPackage"]
    random_id = publication_state["randomId"]
    manifest_path = temp_coll + "/" + random_id + "-manifest.json"

    # Only retrieve manifest for open access vault packages.
    if publication_state["accessRestriction"].startswith("Open"):
        manifest = research.research_manifest(ctx, vault_package, empty_colls=True)['manifest']
    else:
        manifest = []
    data_object.write(ctx, manifest_path, json.dumps(manifest))

    publication_state["manifestPath"] = manifest_path


def copy_manifest_to_public_host(ctx: rule.Context, random_id: str, publication_config: dict, publication_state: dict) -> None:
    """Copy the manifest JSON to configured public host.

    :param ctx:                Combined type of a callback and rei struct
    :param random_id:          Random ID part of DOI used for landingpage file
    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    publicHost = publication_config["publicHost"]
    manifest_path = publication_state["manifestPath"]
    yodaInstance = publication_config["yodaInstance"]
    yodaPrefix = publication_config["yodaPrefix"]
    publicPath = yodaInstance + "/" + yodaPrefix + "/" + random_id + "-manifest.json"

    argv = publicHost + " inbox /var/www/landingpages/" + publicPath

    copy_result = ctx.iiGenericSecureCopy(argv, manifest_path, '')
    error = copy_result['arguments'][2]
    if int(error) >= 0:
        publication_state["manifestUploaded"] = "yes"
    else:
        publication_state["status"] = constants.publication_status.RETRY
        log.write(ctx, "copy_manifest_to_public_host: " + error)


def set_access_restrictions(ctx: rule.Context, vault_package: str, publication_state: dict) -> None:
    """Set access restriction for vault package.

    This function is called when (re)publishing a vault package.
    The embargo date of a package is essential determining access.
    If current date < embargo end date, then set end date in `org_lift_embargo_date`
    to be picked up by lift embargo cronjob.

    :param ctx:                Combined type of a callback and rei struct
    :param vault_package:      Path to the package in the vault
    :param publication_state:  Dict with state of the publication process
    """
    # Embargo handling
    combiJsonPath = publication_state["combiJsonPath"]
    dictJsonData = jsonutil.read(ctx, combiJsonPath)

    # Remove empty objects to prevent empty fields on landingpage.
    dictJsonData = misc.remove_empty_objects(dictJsonData)

    active_embargo = False

    # Check whether lift_embargo_date is present already
    iter = genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        t("COLL_NAME = '{vault_package}' AND META_COLL_ATTR_NAME = '{constants.UUORGMETADATAPREFIX}lift_embargo_date'"),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # Just get rid of the previous lift_embargo_date.
        # Will be introduced again if required in below code but will keep the code more focused whether lift_date must be introduced or not.
        avu.rm_from_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'lift_embargo_date', row[1])

    # Datapackage under embargo?
    embargo_end_date = dictJsonData.get('Embargo_End_Date', None)
    if embargo_end_date is not None and len(embargo_end_date):
        # String comparison is possible as both are in same string format YYYY-MM-DD
        active_embargo = (datetime.now().strftime('%Y-%m-%d') < embargo_end_date)

    access_restriction = publication_state["accessRestriction"]

    # Lift embargo handling is only interesting when package has open access.
    if access_restriction.startswith('Open'):
        if active_embargo:
            # datapackage data is under embargo.
            # Add indication to metadata on vault_package so cronjob can pick it up and sets acls when embargo date is passed in the FUTURE
            avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'lift_embargo_date', embargo_end_date)

    # Now handle the data access taking possible embargo into account
    access_level = "null"
    # Only without an active embargo date AND open access is it allowed to read data!
    if access_restriction.startswith('Open') and not active_embargo:
        access_level = "read"

    try:
        msi.set_acl(ctx, "recursive", access_level, "anonymous", vault_package)
    except Exception:
        log.write(ctx, f"set_access_restrictions for {vault_package} failed: {format_exc()}")
        publication_state["status"] = constants.publication_status.UNRECOVERABLE
        return

    # Revoke anonymous access on original data if data package is deaccessioned
    deaccession_status = vault_deaccession.vault_deaccession_status(ctx, vault_package)
    if constants.vault_deaccession_state(deaccession_status) == constants.vault_deaccession_state.DEACCESSION_COMPLETE:
        try:
            msi.set_acl(ctx, "recursive", "admin:null", "anonymous", f"{vault_package}/original")
        except Exception:
            log.write(ctx, f"set_access_restrictions for {vault_package}/original failed: {format_exc()}")
            publication_state["status"] = constants.publication_status.UNRECOVERABLE
            return

    # We cannot set "null" as value in a kvp as this will crash msi_json_objops if we ever perform a uuKvp2JSON on it.
    if access_level == "null":
        publication_state["anonymousAccess"] = "no"
    else:
        publication_state["anonymousAccess"] = "yes"


def check_doi_availability(ctx: rule.Context, publication_state: dict, type_flag: str) -> None:
    """Request DOI to check on availability. We want a 404 as return code.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    :param type_flag:          Flag indicating DOI type ('version' or 'base')
    """
    doi = publication_state[type_flag + "DOI"]

    try:
        response = datacite.metadata_get(doi)

        http_code = response.status_code

        if http_code == 404:
            publication_state[type_flag + "DOIAvailable"] = "yes"
        elif http_code in [401, 403, 500, 503, 504]:
            # request failed, worth a retry
            publication_state["status"] = constants.publication_status.RETRY
        elif http_code in [200, 204]:
            # DOI already in use
            publication_state[type_flag + "DOIAvailable"] = "no"
            publication_state["status"] = constants.publication_status.RETRY
    except ReadTimeout:
        # DataCite timeout.
        log.write(ctx, "check_doi_availability: DataCite timeout received. Operation will be retried later.")
        publication_state["status"] = constants.publication_status.RETRY


def process_publication(ctx: rule.Context, vault_package: str) -> str:
    """Handling of publication of a vault data package.

    Each version gets its own version DOI and a base DOI that is then inherited
    by all subsequent versions.

    :param ctx:             Combined type of a callback and rei struct
    :param vault_package:   Path to the package in the vault

    :return: "OK" if all went ok
    """
    log.write(ctx, f"Process publication of vault package <{vault_package}>")

    # Check permissions, rodsadmin only.
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # Check current status, perhaps data package transitioned already.
    vault_status = vault.get_coll_vault_status(ctx, vault_package).value
    if vault_status not in [str(constants.vault_package_state.PUBLISHED), str(constants.vault_package_state.APPROVED_FOR_PUBLICATION)]:
        return "InvalidPackageStatusForPublication" + ": " + vault_status

    # Get publication configuration.
    publication_config = get_publication_config(ctx)

    # Get state of all related to the publication.
    publication_state = get_publication_state(ctx, vault_package)

    # Check if verbose mode is enabled.
    verbose = "verboseMode" in publication_config
    if verbose:
        log.write(ctx, "Running process_publication in verbose mode.")

    # Publication status check and handling
    if verbose:
        log.write(ctx, "Initial publication status is: " + str(publication_state['status']))

    if should_return_early(publication_state['status']):
        return str(publication_state['status'])
    elif should_process(publication_state['status']):
        publication_state['status'] = constants.publication_status.PROCESSING

    # Get previous publication state if exists.
    previous_publication_state = {}
    if 'previous_version' in publication_state:
        previous_vault_package = publication_state["previous_version"]
        previous_publication_state = get_publication_state(ctx, previous_vault_package)

    update_base_doi = False
    # Set flag to update base DOI when this data package is the latest version.
    if is_latest_version(publication_state):
        update_base_doi = True

    # Create base DOI if it does not exist in the previous publication state.
    if 'previous_version' not in publication_state and "baseDOI" not in publication_state:
        log.write(ctx, f"Creating base DOI for the vault package <{vault_package}>")
        try:
            generate_base_doi(publication_config, publication_state)
            check_doi_availability(ctx, publication_state, 'base')
            publication_state["baseDOIMinted"] = 'no'
            update_base_doi = True
        except Exception:
            log.write(ctx, "Error while checking base DOI availability: " + format_exc())
            publication_state["status"] = constants.publication_status.RETRY

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            if verbose:
                log.write(ctx, "Error status for creating base DOI: " + str(publication_state['status']))
            return str(publication_state['status'])

    if update_base_doi:
        if verbose:
            log.write(ctx, "In branch for updating base DOI")

        if "baseDOI" in previous_publication_state:
            # Set the link to previous publication state
            publication_state["baseDOI"] = previous_publication_state["baseDOI"]
            publication_state["baseDOIMinted"] = previous_publication_state["baseDOIMinted"]
            publication_state["baseRandomId"] = previous_publication_state["baseRandomId"]

    # Publication date
    if "publicationDate" not in publication_state:
        if verbose:
            log.write(ctx, "Setting publication date.")
        publication_state["publicationDate"] = get_publication_date(ctx, vault_package)

    # DOI handling
    if "versionDOI" not in publication_state:
        if verbose:
            log.write(ctx, "Generating preliminary DOI.")
        generate_preliminary_doi(publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)

    elif "versionDOIAvailable" in publication_state:
        if publication_state["versionDOIAvailable"] == "no":
            if verbose:
                log.write(ctx, "Version DOI available: no")
                log.write(ctx, "Generating preliminary DOI.")
            generate_preliminary_doi(publication_config, publication_state)

            publication_state["combiJsonPath"] = ""
            publication_state["dataCiteJsonPath"] = ""
            save_publication_state(ctx, vault_package, publication_state)

    # Determine last modification time. Always run, no matter if retry
    if verbose:
        log.write(ctx, "Updating modification date.")
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime(ctx, vault_package)

    # Generate Combi Json consisting of user and system metadata
    if "combiJsonPath" not in publication_state:
        if verbose:
            log.write(ctx, "Generating combi JSON.")

        try:
            generate_combi_json(ctx, publication_config, publication_state)
        except Exception:
            log.write(ctx, "Exception while generating combi JSON: " + format_exc())
            publication_state["status"] = constants.publication_status.UNRECOVERABLE

        save_publication_state(ctx, vault_package, publication_state)

        if should_abort(publication_state["status"]):
            if verbose:
                log.write(ctx, "Error status after generating combi JSON.")
            return str(publication_state["status"])

    # Create Landing page URL
    if verbose:
        log.write(ctx, "Creating landing page.")
    generate_landing_page_url(publication_config, publication_state)

    # Generate DataCite JSON
    if "dataCiteJsonPath" not in publication_state:
        if verbose:
            log.write(ctx, "Generating Datacite JSON.")
        try:
            generate_datacite_json(ctx, publication_state)
        except Exception:
            log.write(ctx, "Exception while generating Datacite JSON: " + format_exc())
            publication_state["status"] = constants.publication_status.UNRECOVERABLE

        save_publication_state(ctx, vault_package, publication_state)

        if should_abort(publication_state["status"]):
            log.write(ctx, "Error status after generating Datacite JSON: " + str(publication_state["status"]))
            return str(publication_state["status"])

    # Check if DOI is in use
    if "versionDOIAvailable" not in publication_state:
        if verbose:
            log.write(ctx, "Checking whether version DOI is available.")

        try:
            check_doi_availability(ctx, publication_state, 'version')
        except Exception:
            log.write(ctx, "Error while checking DOI availability: " + format_exc())
            publication_state["status"] = constants.publication_status.RETRY

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, "Error status after checking version DOI availability: " + str(publication_state["status"]))
            return str(publication_state["status"])

    # Determine whether an update ('put') or create ('post') message has to be sent to datacite
    datacite_action = 'post'
    if publication_state.get('versionDOIMinted') == 'yes':
        datacite_action = 'put'

    # Send DataCite JSON to metadata end point
    if "dataCiteMetadataPosted" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading metadata to Datacite.")
        try:
            version_doi = publication_state['versionDOI']
            post_metadata_to_datacite(ctx, publication_state, version_doi, datacite_action)

            if update_base_doi:
                base_doi = None
                datacite_action = 'post'
                if publication_state.get('baseDOIMinted') == 'yes':
                    datacite_action = 'put'
                if verbose:
                    log.write(ctx, "Updating base DOI.")
                base_doi = publication_state['baseDOI']
                post_metadata_to_datacite(ctx, publication_state, base_doi, datacite_action, base_doi=True)
        except Exception:
            log.write(ctx, "Exception while sending metadata to Datacite: " + format_exc())
            publication_state["status"] = constants.publication_status.RETRY

        save_publication_state(ctx, vault_package, publication_state)

        if should_abort(publication_state["status"]):
            log.write(ctx, "Error status after sending metadata to Datacite: " + str(publication_state["status"]))
            return str(publication_state["status"])

    # Create landing page
    if "landingPagePath" not in publication_state:
        if verbose:
            log.write(ctx, "Creating landing page.")
        # Create landing page
        try:
            generate_landing_page(ctx, publication_state, "publish")
        except Exception:
            log.write(ctx, "Error while creating landing page: " + format_exc())
            publication_state["status"] = constants.publication_status.UNRECOVERABLE

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, "Error status after creating landing page: " + str(publication_state["status"]))
            return str(publication_state["status"])

    # Use secure copy to push landing page to the public host
    if "landingPageUploaded" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading landing page.")
        random_id = publication_state["randomId"]
        copy_landingpage_to_public_host(ctx, random_id, publication_config, publication_state)

        if update_base_doi:
            base_random_id = publication_state["baseRandomId"]
            if verbose:
                log.write(ctx, "Updating base DOI landing page.")
            copy_landingpage_to_public_host(ctx, base_random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, "Error status after uploading landing page:" + str(publication_state["status"]))
            return str(publication_state["status"])

    # Create manifest JSON.
    if "manifestPath" not in publication_state:
        if verbose:
            log.write(ctx, "Creating manifest JSON.")
        # Create landing page
        try:
            generate_manifest(ctx, publication_state)
        except Exception:
            log.write(ctx, "Error while creating manifest JSON: " + format_exc())
            publication_state["status"] = constants.publication_status.UNRECOVERABLE

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, "Error status after creating manifest JSON: " + str(publication_state["status"]))
            return str(publication_state["status"])

    # Use secure copy to push manifest JSON to the public host.
    if "manifestUploaded" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading manifest JSON.")
        random_id = publication_state["randomId"]
        copy_manifest_to_public_host(ctx, random_id, publication_config, publication_state)

        if update_base_doi:
            base_random_id = publication_state["baseRandomId"]
            if verbose:
                log.write(ctx, "Updating base DOI manifest JSON.")
            copy_manifest_to_public_host(ctx, base_random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, "Error status after uploading manifest JSON:" + str(publication_state["status"]))
            return str(publication_state["status"])

    # Use secure copy to push combi JSON to MOAI server
    if "oaiUploaded" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading to MOAI.")
        random_id = publication_state["randomId"]
        copy_metadata_to_moai(ctx, random_id, publication_config, publication_state)

        if update_base_doi:
            base_random_id = publication_state["baseRandomId"]
            if verbose:
                log.write(ctx, "Updating base DOI at MOAI.")
            copy_metadata_to_moai(ctx, base_random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, "Error status after uploading to MOAI: " + str(publication_state["status"]))
            return str(publication_state["status"])

    # Set access restriction for vault package.
    if "anonymousAccess" not in publication_state:
        if verbose:
            log.write(ctx, "Setting vault access restrictions.")
        set_access_restrictions(ctx, vault_package, publication_state)

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, "Error status after setting vault access restrictions." + str(publication_state["status"]))
            return str(publication_state["status"])

    # Mint DOI with landing page URL.
    if "versionDOIMinted" not in publication_state:
        if verbose:
            log.write(ctx, "Minting DOI.")
        mint_doi(ctx, publication_state, 'version')

        if update_base_doi:
            if verbose:
                log.write(ctx, "Base DOI update.")
            base_doi = publication_state['baseDOI']
            mint_doi(ctx, publication_state, 'base')
            if 'previous_version' in publication_state:
                previous_publication_state['baseDOIMinted'] = publication_state['baseDOIMinted']
                save_publication_state(ctx, previous_vault_package, previous_publication_state)

        save_publication_state(ctx, vault_package, publication_state)

        if should_abort(publication_state["status"]):
            if verbose:
                log.write(ctx, "Error status during minting DOI.")
            return str(publication_state["status"])

        # The publication was a success
        publication_state["status"] = constants.publication_status.OK
        save_publication_state(ctx, vault_package, publication_state)

        avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'vault_status', constants.vault_package_state.PUBLISHED.value)
        if "previous_version" in publication_state:
            if verbose:
                log.write(ctx, "Updating previous version AVU.")
            avu.set_on_coll(ctx, publication_state["previous_version"], constants.UUORGMETADATAPREFIX + 'publication_next_version', vault_package)
            if verbose:
                log.write(ctx, "Updating previous version landing page.")
            previous_versions = get_all_versions(ctx, publication_state["previous_version"], publication_state["baseDOI"])[1]
            for item in previous_versions[1:]:
                update_publication(ctx, item[1], update_datacite=False, update_landingpage=True, update_moai=False)
    else:
        # The publication was a success
        if verbose:
            log.write(ctx, "Publication successful.")
        publication_state["status"] = constants.publication_status.OK
        save_publication_state(ctx, vault_package, publication_state)
        provenance.log_action(ctx, "system", vault_package, "publication updated")

    log.write(ctx, f"Finished publication of vault package <{vault_package}>")
    return str(publication_state["status"])


def process_depublication(ctx: rule.Context, vault_package: str) -> str:
    """Handling of depublication of a vault data package.

    :param ctx:             Combined type of a callback and rei struct
    :param vault_package:   Path to the package in the vault

    :return: "OK" if all went ok
    """
    log.write(ctx, f"Process depublication of vault package <{vault_package}>")

    # check permissions - rodsadmin only
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    vault_status = vault.get_coll_vault_status(ctx, vault_package).value
    if vault_status not in [str(constants.vault_package_state.PENDING_DEPUBLICATION)]:
        return "InvalidPackageStatusForPublication" + ": " + vault_status

    # get publication configuration
    publication_config = get_publication_config(ctx)

    # get state of all related to the publication
    publication_state = get_publication_state(ctx, vault_package)

    # Check if verbose mode is enabled
    verbose = "verboseMode" in publication_config
    if verbose:
        log.write(ctx, "Running process_depublication in verbose mode.")

    if publication_state['status'] == constants.publication_status.OK:
        # reset on first call
        set_update_publication_state(ctx, vault_package)
        publication_state = get_publication_state(ctx, vault_package)

    if should_return_early(publication_state['status']):
        return str(publication_state['status'])
    elif should_process(publication_state['status']):
        publication_state['status'] = constants.publication_status.PROCESSING

    # Set flag to update base DOI when this data package is the latest version.
    update_base_doi = False
    if is_latest_version(publication_state):
        update_base_doi = True

    # Determine last modification time. Always run, no matter if retry
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime(ctx, vault_package)

    # Generate Combi Json consisting of user and system metadata
    if "combiJsonPath" not in publication_state:
        if verbose:
            log.write(ctx, "Generating combi JSON.")
        try:
            generate_system_json(ctx, publication_state)
        except Exception:
            log.write(ctx, "Exception while trying to generate system JSON during depublication: " + format_exc())
            publication_state["status"] = constants.publication_status.UNRECOVERABLE

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            return str(publication_state["status"])

    # Hide metadata from DataCite
    if "dataCiteMetadataPosted" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading metadata to Datacite.")
        try:
            remove_metadata_from_datacite(ctx, publication_state, 'version')
            if update_base_doi:
                remove_metadata_from_datacite(ctx, publication_state, 'base')
        except Exception:
            log.write(ctx, "Exception while trying to remove metadata from Datacite during depublication: " + format_exc())
            publication_state["status"] = constants.publication_status.RETRY

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            return str(publication_state["status"])

    # Create landing page
    if "landingPagePath" not in publication_state:
        if verbose:
            log.write(ctx, "Creating landing page.")
        # Create landing page
        try:
            generate_landing_page(ctx, publication_state, "depublish")
        except Exception:
            log.write(ctx, "Exception while generating landing page during depublication: " + format_exc())
            publication_state["status"] = constants.publication_status.UNRECOVERABLE

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            return str(publication_state["status"])

    # Use secure copy to push landing page to the public host
    if "landingPageUploaded" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading landing page.")
        random_id = publication_state["randomId"]
        copy_landingpage_to_public_host(ctx, random_id, publication_config, publication_state)

        if update_base_doi:
            base_random_id = publication_state["baseRandomId"]
            copy_landingpage_to_public_host(ctx, base_random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            return str(publication_state["status"])

    # Use secure copy to push combi JSON to MOAI server
    if "oaiUploaded" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading to MOAI.")
        random_id = publication_state["randomId"]
        copy_metadata_to_moai(ctx, random_id, publication_config, publication_state)

        if update_base_doi:
            base_random_id = publication_state["baseRandomId"]
            copy_metadata_to_moai(ctx, base_random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            return str(publication_state["status"])

    # Set access restriction for vault package.
    if "anonymousAccess" not in publication_state:
        if verbose:
            log.write(ctx, "Setting vault access restrictions.")
        set_access_restrictions(ctx, vault_package, publication_state)

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            return str(publication_state["status"])

    # The depublication was a success
    avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'vault_status', constants.vault_package_state.DEPUBLISHED.value)
    publication_state["status"] = constants.publication_status.OK
    save_publication_state(ctx, vault_package, publication_state)
    log.write(ctx, f"Finished depublication of vault package <{vault_package}>")

    return str(publication_state["status"])


def process_republication(ctx: rule.Context, vault_package: str) -> str:
    """Handling of republication of a vault data package.

    :param ctx:             Combined type of a callback and rei struct
    :param vault_package:   Path to the package in the vault

    :return: "OK" if all went ok
    """
    log.write(ctx, f"Process republication of vault package <{vault_package}>")

    # check permissions - rodsadmin only
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    vault_status = vault.get_coll_vault_status(ctx, vault_package).value

    if vault_status not in [str(constants.vault_package_state.PENDING_REPUBLICATION)]:
        return "InvalidPackageStatusForRePublication" + ": " + vault_status

    publication_config = get_publication_config(ctx)

    # get state of all related to the publication
    publication_state = get_publication_state(ctx, vault_package)

    # Check if verbose mode is enabled
    verbose = "verboseMode" in publication_config
    if verbose:
        log.write(ctx, "Running process_republication in verbose mode.")

    if publication_state['status'] == constants.publication_status.OK:
        # reset on first call
        set_update_publication_state(ctx, vault_package)
        publication_state = get_publication_state(ctx, vault_package)

    if should_return_early(publication_state['status']):
        return str(publication_state['status'])
    elif should_process(publication_state['status']):
        publication_state['status'] = constants.publication_status.PROCESSING

    # Set flag to update base DOI when this data package is the latest version.
    update_base_doi = False
    if is_latest_version(publication_state):
        if verbose:
            log.write(ctx, "In branch for updating base DOI")
        update_base_doi = True

    # Publication date
    if "publicationDate" not in publication_state:
        publication_state["publicationDate"] = get_publication_date(ctx, vault_package)

    # Determine last modification time. Always run, no matter if retry
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime(ctx, vault_package)

    # Generate Combi Json consisting of user and system metadata
    if "combiJsonPath" not in publication_state:
        if verbose:
            log.write(ctx, "Generating combi JSON.")
        try:
            generate_combi_json(ctx, publication_config, publication_state)
        except Exception:
            log.write(ctx, "Exception while generating combi JSON during republication: " + format_exc())
            publication_state["status"] = constants.publication_status.UNRECOVERABLE

        save_publication_state(ctx, vault_package, publication_state)

        if should_abort(publication_state["status"]):
            return str(publication_state["status"])

    # Generate DataCite JSON
    if "dataCiteJsonPath" not in publication_state:
        if verbose:
            log.write(ctx, "Generating Datacite JSON.")
        try:
            generate_datacite_json(ctx, publication_state)
        except Exception:
            log.write(ctx, "Exception while generating DataCite JSON for republication: " + format_exc())
            publication_state["status"] = constants.publication_status.UNRECOVERABLE

        save_publication_state(ctx, vault_package, publication_state)

        if should_abort(publication_state["status"]):
            return str(publication_state["status"])

    # Send DataCite JSON to metadata end point
    if "dataCiteMetadataPosted" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading metadata to Datacite.")
        try:
            post_metadata_to_datacite(ctx, publication_state, publication_state['versionDOI'], 'put')

            if update_base_doi:
                post_metadata_to_datacite(ctx, publication_state, publication_state['baseDOI'], 'put', base_doi=True)
        except Exception:
            log.write(ctx, "Exception while posting metadata to Datacite during republication: " + format_exc())
            publication_state["status"] = constants.publication_status.RETRY

        save_publication_state(ctx, vault_package, publication_state)

        if should_abort(publication_state["status"]):
            return str(publication_state["status"])

    # Create landing page
    if "landingPagePath" not in publication_state:
        if verbose:
            log.write(ctx, "Creating landing page.")
        # Create landing page
        try:
            generate_landing_page(ctx, publication_state, "publish")
        except Exception:
            log.write(ctx, "Exception while creating landing page during republication: " + format_exc())
            publication_state["status"] = constants.publication_status.UNRECOVERABLE

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            return str(publication_state["status"])

    # Use secure copy to push landing page to the public host
    if "landingPageUploaded" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading landing page.")
        random_id = publication_state["randomId"]
        copy_landingpage_to_public_host(ctx, random_id, publication_config, publication_state)

        if update_base_doi:
            base_random_id = publication_state["baseRandomId"]
            copy_landingpage_to_public_host(ctx, base_random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            return str(publication_state["status"])

    # Create manifest JSON.
    if "manifestPath" not in publication_state:
        if verbose:
            log.write(ctx, "Creating manifest JSON.")
        # Create landing page
        try:
            generate_manifest(ctx, publication_state)
        except Exception:
            log.write(ctx, "Error while creating manifest JSON: " + format_exc())
            publication_state["status"] = constants.publication_status.UNRECOVERABLE

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, "Error status after creating manifest JSON: " + str(publication_state["status"]))
            return str(publication_state["status"])

    # Use secure copy to push manifest JSON to the public host.
    if "manifestUploaded" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading manifest JSON.")
        random_id = publication_state["randomId"]
        copy_manifest_to_public_host(ctx, random_id, publication_config, publication_state)

        if update_base_doi:
            base_random_id = publication_state["baseRandomId"]
            if verbose:
                log.write(ctx, "Updating base DOI manifest JSON.")
            copy_manifest_to_public_host(ctx, base_random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, "Error status after uploading manifest JSON:" + str(publication_state["status"]))
            return str(publication_state["status"])

    # Use secure copy to push combi JSON to MOAI server
    if "oaiUploaded" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading to MOAI.")
        random_id = publication_state["randomId"]
        copy_metadata_to_moai(ctx, random_id, publication_config, publication_state)

        if update_base_doi:
            base_random_id = publication_state["baseRandomId"]
            copy_metadata_to_moai(ctx, base_random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            return str(publication_state["status"])

    # Set access restriction for vault package.
    if "anonymousAccess" not in publication_state:
        if verbose:
            log.write(ctx, "Setting vault access restrictions.")
        set_access_restrictions(ctx, vault_package, publication_state)

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            return str(publication_state["status"])

    # The publication was a success
    publication_state["status"] = constants.publication_status.OK
    save_publication_state(ctx, vault_package, publication_state)
    avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'vault_status', constants.vault_package_state.PUBLISHED.value)
    log.write(ctx, f"Finished republication of vault package <{vault_package}>")

    return str(publication_state["status"])


@rule.make(inputs=[0, 1, 2, 3])
def rule_update_publication(ctx: rule.Context,
                            vault_package: str,
                            update_datacite: str,
                            update_landingpage: str,
                            update_moai: str) -> None:
    """Rule interface for updating the publication of a vault package.

    :param ctx:                Combined type of a callback and rei struct
    :param vault_package:      Path to the package in the vault
    :param update_datacite:    Flag that indicates updating DataCite
    :param update_landingpage: Flag that indicates updating landingpage
    :param update_moai:        Flag that indicates updating MOAI (OAI-PMH)
    """
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "User is no rodsadmin", True)
        return

    log.write(ctx, f"[UPDATE PUBLICATIONS] Start for {vault_package}", True)
    collections = genquery.row_iterator(
        "COLL_NAME",
        "COLL_NAME like '%%/home/vault-%%' "
        f"AND META_COLL_ATTR_NAME = '{constants.UUORGMETADATAPREFIX}vault_status' "
        f"AND META_COLL_ATTR_VALUE in ('{str(constants.vault_package_state.PUBLISHED)}', '{str(constants.vault_package_state.DEPUBLISHED)}')",
        genquery.AS_LIST,
        ctx
    )

    packages_found = False
    for collection in collections:
        coll_name = collection[0]
        if ((vault_package == '*' and re.match(r'/[^/]+/home/vault-.*', coll_name)) or (vault_package != '*' and re.match(r'/[^/]+/home/vault-.*', coll_name) and coll_name == vault_package)):
            packages_found = True
            output = update_publication(ctx, coll_name, update_datacite == 'Yes', update_landingpage == 'Yes', update_moai == 'Yes')
            log.write(ctx, coll_name + ': ' + output, True)

    if not packages_found:
        log.write(ctx, f"[UPDATE PUBLICATIONS] No packages found for {vault_package}", True)
    else:
        log.write(ctx, f"[UPDATE PUBLICATIONS] Finished for {vault_package}", True)


def update_publication(ctx: rule.Context,
                       vault_package: str,
                       update_datacite: bool = False,
                       update_landingpage: bool = False,
                       update_moai: bool = False) -> str:
    """Routine to update a publication with sanity checks at every step.

    :param ctx:                Combined type of a callback and rei struct
    :param vault_package:      Path to the package in the vault
    :param update_datacite:    Flag that indicates updating DataCite
    :param update_landingpage: Flag that indicates updating landingpage
    :param update_moai:        Flag that indicates updating MOAI (OAI-PMH)

    :returns: "OK" if all went ok
    """
    log.write(ctx, f"update_publication: Process vault package <{vault_package}> DataCite={update_datacite} landingpage={update_landingpage} MOAI={update_moai}")

    # check permissions - rodsadmin only
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    vault_status = vault.get_coll_vault_status(ctx, vault_package).value

    if vault_status not in [str(constants.vault_package_state.PUBLISHED), str(constants.vault_package_state.DEPUBLISHED)]:
        return "InvalidPackageStatus" + ": " + vault_status

    publication_config = get_publication_config(ctx)

    # Get state of all related to the publication.
    publication_state = get_publication_state(ctx, vault_package)

    # Check if verbose mode is enabled
    verbose = "verboseMode" in publication_config
    if verbose:
        log.write(ctx, "Running update_publication in verbose mode.")

    # Publication must be finished.
    if publication_state['status'] != constants.publication_status.OK:
        log.write(ctx, "update_publication: Not processing vault package, because initial status is " + str(publication_state['status']))
        return str(publication_state['status'])

    # Abort if data packages has a known unsupported metadata schema
    try:
        metadata_schema = vault.get_current_metadata_schema_data_package(ctx, vault_package)
    except ValueError as e:
        log.write(ctx, "update_publication: Not processing vault package, because its metadata schema cannot be determined: " + str(e))
        publication_state["status"] = constants.publication_status.UNRECOVERABLE

    save_publication_state(ctx, vault_package, publication_state)
    if should_abort(publication_state["status"]):
        log.write(ctx, f"update_publication: returned with error status after retrieving metadata schema (status: '{publication_state['status']}')")
        return str(publication_state["status"])

    if metadata_schema is None:
        log.write(ctx, "update_publication: Not processing vault package, because it has no metadata schema.")
        publication_state["status"] = constants.publication_status.UNRECOVERABLE
    elif schema_utils.is_unsupported_schema(metadata_schema):
        log.write(ctx,
                  f"update_publication: Not processing vault package, because it has an unsupported metadata schema: {metadata_schema}")
        publication_state["status"] = constants.publication_status.UNRECOVERABLE

    save_publication_state(ctx, vault_package, publication_state)
    if should_abort(publication_state["status"]):
        log.write(ctx, f"update_publication: returned with error status after checking metadata schema (status: '{publication_state['status']}')")
        return str(publication_state["status"])

    update_base_doi = False
    if "baseDOI" in publication_state:
        if verbose:
            log.write(ctx, "In branch for updating base DOI")
        if is_latest_version(publication_state):
            update_base_doi = True

    # Publication date
    if "publicationDate" not in publication_state:
        publication_state["publicationDate"] = get_publication_date(ctx, vault_package)

    # Determine last modification time. Always run, no matter if retry
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime(ctx, vault_package)

    # Generate Combi Json consisting of user and system metadata
    if verbose:
        log.write(ctx, "Generating combi JSON.")
    try:
        generate_combi_json(ctx, publication_config, publication_state)
    except Exception:
        log.write(ctx, "Exception while generating combi JSON after metadata update: " + format_exc())
        publication_state["status"] = constants.publication_status.UNRECOVERABLE

    save_publication_state(ctx, vault_package, publication_state)
    if should_abort(publication_state["status"]):
        log.write(ctx, f"update_publication: returned with error status before update DataCite (status: '{publication_state['status']}')")
        return str(publication_state["status"])

    if update_datacite:
        # Generate DataCite JSON
        log.write(ctx, f'Update datacite for package {vault_package}')
        try:
            generate_datacite_json(ctx, publication_state)
        except Exception:
            log.write(ctx, "Exception while generating DataCite JSON after metadata update: " + format_exc())
            publication_state["status"] = constants.publication_status.UNRECOVERABLE

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, f"update_publication: returned with error status before send DataCite (status: '{publication_state['status']}')")
            return str(publication_state["status"])

        # Send DataCite JSON to metadata end point
        if verbose:
            log.write(ctx, "Uploading metadata to Datacite.")
        try:
            post_metadata_to_datacite(ctx, publication_state, publication_state["versionDOI"], 'put')
            if update_base_doi:
                post_metadata_to_datacite(ctx, publication_state, publication_state["baseDOI"], 'put', base_doi=True)
        except Exception:
            log.write(ctx, "Exception while posting metadata to Datacite after metadata update: " + format_exc())
            publication_state["status"] = constants.publication_status.RETRY

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, f"update_publication: returned with error status before update landing page (status: '{publication_state['status']}')")
            return str(publication_state["status"])

    if update_landingpage:
        # Create landing page
        log.write(ctx, f'Update landing page for package {vault_package}')
        try:
            generate_landing_page(ctx, publication_state, "publish")
        except Exception:
            log.write(ctx, "Exception while updating landing page after metadata update: " + format_exc())
            publication_state["status"] = constants.publication_status.UNRECOVERABLE

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, f"update_publication: returned with error status before upload landing page (status: '{publication_state['status']}')")
            return str(publication_state["status"])

        # Use secure copy to push landing page to the public host
        random_id = publication_state["randomId"]
        if verbose:
            log.write(ctx, "Uploading landing page.")
        copy_landingpage_to_public_host(ctx, random_id, publication_config, publication_state)
        if update_base_doi:
            base_random_id = publication_state["baseRandomId"]
            copy_landingpage_to_public_host(ctx, base_random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, f"update_publication: returned with error status before update manifest (status: '{publication_state['status']}')")
            return str(publication_state["status"])

        try:
            generate_manifest(ctx, publication_state)
        except Exception:
            log.write(ctx, "Error while creating manifest JSON: " + format_exc())
            publication_state["status"] = constants.publication_status.UNRECOVERABLE

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, f"update_publication: returned with error status before upload manifest (status: '{publication_state['status']}')")
            return str(publication_state["status"])

        # Use secure copy to push manifest JSON to the public host.
        random_id = publication_state["randomId"]
        if verbose:
            log.write(ctx, "Uploading manifest JSON.")
        copy_manifest_to_public_host(ctx, random_id, publication_config, publication_state)
        if update_base_doi:
            base_random_id = publication_state["baseRandomId"]
            copy_manifest_to_public_host(ctx, base_random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, f"update_publication: returned with error status before update MOAI (status: '{publication_state['status']}')")
            return str(publication_state["status"])

    if update_moai:
        # Use secure copy to push combi JSON to MOAI server
        log.write(ctx, f'Update MOAI for package {vault_package}')
        random_id = publication_state["randomId"]
        copy_metadata_to_moai(ctx, random_id, publication_config, publication_state)
        if update_base_doi:
            base_random_id = publication_state["baseRandomId"]
            copy_metadata_to_moai(ctx, base_random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)
        if should_abort(publication_state["status"]):
            log.write(ctx, f"update_publication: returned with error status before publication OK (status: '{publication_state['status']}')")
            return str(publication_state["status"])

    # Updating was a success
    publication_state["status"] = constants.publication_status.OK
    save_publication_state(ctx, vault_package, publication_state)

    return str(publication_state["status"])


@rule.make(inputs=[0])
def rule_add_base_doi(ctx: rule.Context, vault_package: str) -> None:
    """Rule interface for adding the base DOI to a vault package.

    Can be removed after release of v2.2.

    :param ctx:           Combined type of a callback and rei struct
    :param vault_package: Path to the package in the vault
    """
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "User is no rodsadmin", True)
        return

    log.write(ctx, f"[ADD BASE DOI] Start for {vault_package}", True)
    collections = genquery.row_iterator(
        "COLL_NAME",
        "COLL_NAME like '%%/home/vault-%%' "
        f"AND META_COLL_ATTR_NAME = '{constants.UUORGMETADATAPREFIX}vault_status' "
        f"AND META_COLL_ATTR_VALUE in ('{str(constants.vault_package_state.PUBLISHED)}', '{str(constants.vault_package_state.DEPUBLISHED)}')",
        genquery.AS_LIST,
        ctx
    )

    packages_found = False
    for collection in collections:
        coll_name = collection[0]
        if ((vault_package == '*' and re.match(r'/[^/]+/home/vault-.*', coll_name)) or (vault_package != '*' and re.match(r'/[^/]+/home/vault-.*', coll_name) and coll_name == vault_package)):
            packages_found = True
            output = add_base_doi(ctx, coll_name)
            log.write(ctx, f"{coll_name}: {output}", True)

    if not packages_found:
        log.write(ctx, f"[ADD BASE DOI] No packages found for {vault_package}", True)
    else:
        log.write(ctx, f"[ADD BASE DOI] Finished for {vault_package}", True)


def add_base_doi(ctx: rule.Context, vault_package: str) -> str:
    """Routine to add a base DOI to a publication if it is missing.

    Can be removed after release of v2.2.

    :param ctx:           Combined type of a callback and rei struct
    :param vault_package: Path to the package in the vault

    :returns: "OK" if all went ok
    """
    log.write(ctx, f"add_base_doi: Check base doi for vault package <{vault_package}>")

    # Check permissions, rodsadmin only.
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # Check current status, perhaps data package transitioned already.
    vault_publication_status = vault.get_coll_vault_status(ctx, vault_package).value
    if vault_publication_status not in [str(constants.vault_package_state.PUBLISHED),
                                        str(constants.vault_package_state.DEPUBLISHED)]:
        return "InvalidVaultPublicationStatus" + ": " + vault_publication_status

    # Check vault deaccession state.
    vault_deaccession_status = vault_deaccession.vault_deaccession_status(ctx, vault_package)
    if vault_deaccession_status in [str(constants.vault_deaccession_state.DEACCESSION_REQUESTED),
                                    str(constants.vault_deaccession_state.DEACCESSION_APPROVED),
                                    str(constants.vault_deaccession_state.DEACCESSION_COMPLETE)]:
        return "InvalidVaultDeaccessionStatus" + ": " + vault_deaccession_status

    publication_config = get_publication_config(ctx)
    publication_state = get_publication_state(ctx, vault_package)

    # Create base DOI if it does not exist in the previous publication state.
    if 'previous_version' not in publication_state and "baseDOI" not in publication_state:
        log.write(ctx, f"add_base_doi: Create base DOI for vault package <{vault_package}>")
        try:
            generate_base_doi(publication_config, publication_state)
            check_doi_availability(ctx, publication_state, 'base')
            publication_state["baseDOIMinted"] = 'no'
        except Exception:
            log.write(ctx, "add_base_doi: Error while checking base DOI availability: " + format_exc())
            publication_state["status"] = constants.publication_status.RETRY

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] != constants.publication_status.OK:
            log.write(ctx, "add_base_doi: Error status for creating base DOI: " + str(publication_state["status"]))
            return str(publication_state["status"])

        try:
            datacite_action = 'post'
            if publication_state.get('baseDOIMinted') == 'yes':
                datacite_action = 'put'
            post_metadata_to_datacite(ctx, publication_state, publication_state['baseDOI'], datacite_action, base_doi=True)
        except Exception:
            log.write(ctx, "add_base_doi: Exception while sending metadata to Datacite: " + format_exc())
            publication_state["status"] = constants.publication_status.RETRY

        save_publication_state(ctx, vault_package, publication_state)
        if publication_state["status"] != constants.publication_status.OK:
            log.write(ctx, "add_base_doi: Error status for sending metadata to Datacite: " + str(publication_state["status"]))
            return str(publication_state["status"])

        try:
            log.write(ctx, f"add_base_doi: Mint Base DOI for vault package <{vault_package}>")
            mint_doi(ctx, publication_state, 'base')
        except Exception:
            log.write(ctx, "add_base_doi: Exception while minting base DOI: " + format_exc())
            publication_state["status"] = constants.publication_status.RETRY

        save_publication_state(ctx, vault_package, publication_state)
        if publication_state["status"] != constants.publication_status.OK:
            log.write(ctx, "add_base_doi: Error status for minting base DOI: " + str(publication_state["status"]))
            return str(publication_state["status"])

    log.write(ctx, f"add_base_doi: Processed vault package <{vault_package}>")
    return str(constants.publication_status.OK)


def get_collection_metadata(ctx: rule.Context, coll: str, prefix: str) -> dict:
    """Retrieve all collection metadata.

    :param ctx:    Combined type of a callback and rei struct
    :param coll:   Collection to retrieve metadata from
    :param prefix: Prefix of the requested metadata

    :return: Dict with all requested (prefixed) attributes and strip off prefix for the key names
    """
    coll_metadata = {}
    iter = genquery.row_iterator(
        "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        t("COLL_NAME = '{coll}' AND META_COLL_ATTR_NAME like '{prefix}%'"),
        genquery.AS_LIST, ctx
    )

    for row in iter:
        coll_metadata[row[0][len(prefix):]] = row[1]

    return coll_metadata


def get_all_versions(ctx: rule.Context, path: str, doi: str) -> Tuple[List, List]:
    """Get all the version DOI of published data package in a vault.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path of the published data package
    :param doi:  Base DOI of the selected publication

    :return: Tuple with version DOIS and previous version DOIs
    """
    coll_parent_name = path.rsplit('/', 1)[0]

    org_publ_info, data_packages, grouped_base_dois = vault.get_all_doi_versions(ctx, coll_parent_name)

    # Sort by publication date
    sorted_publ = [sorted(x, key=lambda x: datetime.strptime(x[1], "%Y-%m-%dT%H:%M:%S.%f"), reverse=True) for x in grouped_base_dois]

    sorted_publ = [element for innerList in sorted_publ for element in innerList]

    # Convert the date into two formats for display and tooltip (Jan 1, 1990 and 1990-01-01 00:00:00)
    sorted_publ = [[x[0], datetime.strptime(x[1], "%Y-%m-%dT%H:%M:%S.%f").strftime("%b %d, %Y"), x[2],
                    datetime.strptime(x[1], "%Y-%m-%dT%H:%M:%S.%f").strftime('%Y-%m-%d %H:%M:%S%z'), x[3]] for x in sorted_publ]

    all_versions = []
    all_previous_versions = []

    for item in sorted_publ:
        if item[0] == doi:
            all_versions.append([item[1], item[2], item[3]])
            all_previous_versions.append([item[2], item[4]])

    return all_versions, all_previous_versions


"""Rule interface for processing publication of a vault package."""
rule_process_publication = rule.make(inputs=[0], outputs=[1, 2])(process_publication)


"""Rule interface for processing depublication of a vault package."""
rule_process_depublication = rule.make(inputs=[0], outputs=[1, 2])(process_depublication)


"""Rule interface for processing republication of a vault package."""
rule_process_republication = rule.make(inputs=[0], outputs=[1, 2])(process_republication)


@rule.make()
def rule_lift_embargos_on_data_access(ctx: rule.Context) -> str:
    """Find vault packages that have a data access embargo that can be lifted as the embargo expires.

    If lift_embargo_date <= now, update publication.

    :param ctx:  Combined type of a callback and rei struct

    :returns: Status of lifting the embargo indications
    """
    # check permissions - rodsadmin only
    if not user.is_rodsadmin(ctx):
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    zone = user.zone(ctx)

    # Find all packages that have embargo date for data access that must be lifted
    iter = genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        f"COLL_NAME like '/{zone}/home/vault-%'"
        " AND META_COLL_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'lift_embargo_date' + "'"
        f" AND META_COLL_ATTR_VALUE <= '{datetime.now().strftime('%Y-%m-%d')}'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        vault_package = row[0]

        log.write(ctx, "Lift embargo for vault package: " + vault_package)
        set_update_publication_state(ctx, vault_package)
        process_publication(ctx, vault_package)

    return str(constants.publication_status.OK)
