# -*- coding: utf-8 -*-
"""Functions for publication."""

__copyright__ = 'Copyright (c) 2019-2022, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

import json
from datetime import datetime

import genquery

import datacite
import json_datacite41
import json_landing_page
import meta
import provenance
import schema
import vault
from util import *

__all__ = ['rule_process_publication',
           'rule_process_depublication',
           'rule_process_republication',
           'rule_update_publication']


def get_publication_config(ctx):
    """Get all publication config keys and their values and report any missing keys."""
    zone = user.zone(ctx)
    system_coll = "/" + zone + constants.UUSYSTEMCOLLECTION

    attr2keys = {"public_host": "publicHost",
                 "public_vhost": "publicVHost",
                 "moai_host": "moaiHost",
                 "yoda_prefix": "yodaPrefix",
                 "datacite_prefix": "dataCitePrefix",
                 "random_id_length": "randomIdLength",
                 "yoda_instance": "yodaInstance",
                 "davrods_vhost": "davrodsVHost",
                 "davrods_anonymous_vhost": "davrodsAnonymousVHost",
                 "publication_verbose_mode": "verboseMode"}
    optional_keys = ["publication_verbose_mode"]
    configKeys = {}
    found_attrs = []

    prefix_length = len(constants.UUORGMETADATAPREFIX)
    iter = genquery.row_iterator(
        "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + system_coll + "' AND  META_COLL_ATTR_NAME like '" + constants.UUORGMETADATAPREFIX + "%'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        # Strip prefix From attribute names
        attr = row[0][prefix_length:]
        val = row[1]

        try:
            found_attrs.append(attr)
            configKeys[attr2keys[attr]] = val
        except KeyError:
            continue

    # Any differences between
    for key in attr2keys:
        if key not in found_attrs and key not in optional_keys:
            log.write(ctx, 'Missing config key ' + key)

    return configKeys


def generate_combi_json(ctx, publication_config, publication_state):
    """Join system metadata with the user metadata in yoda-metadata.json.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    temp_coll = "/" + user.zone(ctx) + constants.IIPUBLICATIONCOLLECTION
    davrodsAnonymousVHost = publication_config["davrodsAnonymousVHost"]

    vaultPackage = publication_state["vaultPackage"]
    randomId = publication_state["randomId"]
    combiJsonPath = temp_coll + "/" + randomId + "-combi.json"

    yodaDOI = publication_state["yodaDOI"]
    lastModifiedDateTime = publication_state["lastModifiedDateTime"]
    publicationDate = publication_state["publicationDate"]

    openAccessLink = ''
    if publication_state["accessRestriction"].startswith("Open"):
        split_string = '/home/'
        subPath = vaultPackage[len(split_string) + vaultPackage.find(split_string):]

        openAccessLink = 'https://' + davrodsAnonymousVHost + "/" + subPath

    licenseUri = ""
    if "licenseUri" in publication_state:
        licenseUri = publication_state["licenseUri"]

    # metadataJsonPath contains latest json
    metadataJsonPath = meta.get_latest_vault_metadata_path(ctx, vaultPackage)

    # Combine content of current *metadataJsonPath with system info and creates a new file in *combiJsonPath:
    json_datacite41.json_datacite41_create_combi_metadata_json(ctx, metadataJsonPath, combiJsonPath, lastModifiedDateTime, yodaDOI, publicationDate, openAccessLink, licenseUri)

    publication_state["combiJsonPath"] = combiJsonPath


def generate_system_json(ctx, publication_state):
    """Overwrite combi metadata json with system-only metadata.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    """
    temp_coll = "/" + user.zone(ctx) + constants.IIPUBLICATIONCOLLECTION

    randomId = publication_state["randomId"]
    system_json_path = temp_coll + "/" + randomId + "-combi.json"

    system_json_data = {
        "System": {
            "Last_Modified_Date": publication_state["lastModifiedDateTime"],
            "Persistent_Identifier_Datapackage": {
                "Identifier_Scheme": "DOI",
                "Identifier": publication_state["yodaDOI"],
            },
            "Publication_Date": publication_state["publicationDate"]
        }
    }

    data_object.write(ctx, system_json_path, jsonutil.dump(system_json_data))
    publication_state["combiJsonPath"] = system_json_path


def get_publication_state(ctx, vault_package):
    """The publication state is kept as metadata on the vault package.

    :param ctx:           Combined type of a callback and rei struct
    :param vault_package: Path to the package in the vault

    :returns: Dict with state of the publication process
    """
    publication_state = {
        "status": "Unknown",
        "accessRestriction": "Closed"
    }

    publ_metadata = get_collection_metadata(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'publication_')

    # Take over all actual values as saved earlier.
    for key in publ_metadata.keys():
        publication_state[key] = publ_metadata[key]

    # Handle access restriction.
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME like '%Data_Access_Restriction' AND COLL_NAME = '" + vault_package + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        publication_state["accessRestriction"] = row[0]

    # Handle license.
    license = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME like '%License' AND COLL_NAME = '" + vault_package + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        license = row[0]

    if license != "":
        publication_state["license"] = license
        license_uri = ""
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "META_COLL_ATTR_NAME like '" + constants.UUORGMETADATAPREFIX + "license_uri" + "' AND COLL_NAME = '" + vault_package + "'",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            license_uri = row[0]

        if license_uri != "":
            publication_state["licenseUri"] = license_uri

    publication_state["vaultPackage"] = vault_package
    return publication_state


def save_publication_state(ctx, vault_package, publication_state):
    """Save the publication state key-value-pairs to AVU's on the vault package.

    :param ctx:               Combined type of a callback and rei struct
    :param vault_package:     Path to the package in the vault
    :param publication_state: Dict with state of the publication process
    """
    ctx.msi_rmw_avu("-C", vault_package, constants.UUORGMETADATAPREFIX + 'publication_%', "%", "%")
    for key in publication_state.keys():
        if publication_state[key] != "":
            avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'publication_' + key, publication_state[key])


def set_update_publication_state(ctx, vault_package):
    """Routine to set publication state of vault package pending to update.

    :param ctx:           Combined type of a callback and rei struct
    :param vault_package: Path to the package in the vault

    :returns: String with state of publication state update
    """
    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    coll_status = vault.get_coll_vault_status(ctx, vault_package).value
    if coll_status not in [str(constants.vault_package_state.PUBLISHED),
                           str(constants.vault_package_state.PENDING_DEPUBLICATION),
                           str(constants.vault_package_state.PENDING_REPUBLICATION)]:
        return "NotAllowed"

    publication_state = get_publication_state(ctx, vault_package)
    if publication_state["status"] != "OK":
        return "PublicationNotOK"

    # Set publication status
    publication_state["status"] = "Unknown"

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


def get_publication_date(ctx, vault_package):
    """Determine the time of publication as a datetime with UTC offset.

    First try action_log. Then icat-time.

    :param ctx:           Combined type of a callback and rei struct
    :param vault_package: Path to the package in the vault

    :return: Publication date in ISO8601 format
    """
    iter = genquery.row_iterator(
        "order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + vault_package + "' AND META_COLL_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'action_log' + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # row contains json encoded [str(int(time.time())), action, actor]
        log_item_list = jsonutil.parse(row[1])
        if log_item_list[1] == "published":
            publication_timestamp = datetime.fromtimestamp(int(log_item_list[0]))

            # ISO8601-fy
            return publication_timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f%z')

    # ISO8601-fy
    my_date = datetime.now()
    return my_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z')


def get_last_modified_datetime(ctx, vault_package):
    """Determine the time of last modification as a datetime with UTC offset.

    :param ctx:           Combined type of a callback and rei struct
    :param vault_package: Path to the package in the vault

    :return: Last modified date in ISO8601 format
    """
    iter = genquery.row_iterator(
        "order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + vault_package + "' AND META_COLL_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'action_log' + "'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        log_item_list = jsonutil.parse(row[1])
        my_date = datetime.fromtimestamp(int(log_item_list[0]))

        # ISO8601-fy
        return my_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z')


def generate_preliminary_DOI(ctx, publication_config, publication_state):
    """Generate a Preliminary DOI. Preliminary, because we check for collision later.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    dataCitePrefix = publication_config["dataCitePrefix"]
    yodaPrefix = publication_config["yodaPrefix"]

    randomId = datacite.generate_random_id(ctx, publication_config["randomIdLength"])

    publication_state["randomId"] = randomId
    publication_state["yodaDOI"] = dataCitePrefix + "/" + yodaPrefix + "-" + randomId


def generate_preliminary_next_version_DOI(ctx, publication_config, publication_state):
    """Generate a Preliminary next version DOI. Preliminary, because we check for collision later.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """

    dataCitePrefix = publication_config["dataCitePrefix"]
    yodaPrefix = publication_config["yodaPrefix"]

    # Retrieve random ID part of DOI.
    if "randomId" not in publication_state:
        doi = vault.get_doi(ctx, publication_state["previous_version"])
        randomId = doi.split("-").pop()
    else:
        randomId = publication_state["randomId"]

    # Generate next version of random ID part of DOI.
    if len(randomId.split(".")) == 2:
        randomId, version = randomId.split(".")
        version = str(int(version[1:]) + 1)
        randomId = "{}.v{}".format(randomId, version)
    else:
        randomId = "{}.v1".format(randomId)

    publication_state["randomId"] = randomId
    publication_state["yodaDOI"] = dataCitePrefix + "/" + yodaPrefix + "-" + randomId


def generate_datacite_json(ctx, publication_state):
    """Generate a DataCite compliant JSON based up yoda-metadata.json.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    """
    combiJsonPath = publication_state["combiJsonPath"]

    randomId = publication_state["randomId"]

    temp_coll, coll = pathutil.chop(combiJsonPath)
    datacite_json_path = temp_coll + "/" + randomId + "-dataCite.json"

    # Based on content of *combiJsonPath, get DataciteJson as string
    datacite_json = json_datacite41.json_datacite41_create_datacite_json(ctx, publication_state["landingPageUrl"], combiJsonPath)

    data_object.write(ctx, datacite_json_path, jsonutil.dump(datacite_json))

    publication_state["dataCiteJsonPath"] = datacite_json_path


def upload_metadata_to_datacite(ctx, publication_state, yoda_doi=None, hide=False):
    """Upload DataCite JSON to DataCite.

    This will register the DOI when posting, without minting it.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    :param yoda_doi:           DOI of data package in Yoda
    :param hide:               Boolean indicating if metadata should hidden on DataCite
    """
    # Give metadata attribute hide if it should be hidden on DataCite.
    if hide:
        datacite_json = json.dumps({"data": {"attributes": {"event": "hide"}}})
    else:
        datacite_json_path = publication_state["dataCiteJsonPath"]
        datacite_json = data_object.read(ctx, datacite_json_path)

    # If Yoda DOI is already minted, put instead of post to DataCite.
    send_method = 'post'
    if yoda_doi is not None:
        send_method = 'put'

    if send_method == 'post':
        httpCode = datacite.metadata_post(ctx, datacite_json)
    else:
        httpCode = datacite.metadata_put(ctx, yoda_doi, datacite_json)

    if (send_method == 'post' and httpCode == 201) or (send_method == 'put' and httpCode == 200):
        publication_state["dataCiteMetadataPosted"] = "yes"
    elif httpCode in [401, 403, 412, 500, 503, 504]:
        # Unauthorized, Forbidden, Precondition failed, Internal Server Error
        log.write(ctx, "upload_metadata_to_datacite: httpCode " + str(httpCode) + " received. Will be retried later")
        publication_state["status"] = "Retry"
    elif httpCode == 404:
        # Invalid DOI
        log.write(ctx, "upload_metadata_to_datacite: 404 Not Found - Invalid DOI")
        publication_state["status"] = "Unrecoverable"
    else:
        log.write(ctx, "upload_metadata_to_datacite: httpCode " + str(httpCode) + " received. Unrecoverable error.")
        publication_state["status"] = "Unrecoverable"


def mint_doi(ctx, yoda_doi, publication_state):
    """Announce the landing page URL for a DOI to dataCite. This will mint the DOI.

    :param ctx:                Combined type of a callback and rei struct
    :param yoda_doi:           DOI of data package in Yoda
    :param publication_state:  Dict with state of the publication process
    """
    payload = json.dumps({"data": {"attributes": {"url": publication_state["landingPageUrl"]}}})

    httpCode = datacite.metadata_put(ctx, yoda_doi, payload)

    if httpCode == 200:  # 201:
        publication_state["DOIMinted"] = "yes"
    elif httpCode in [401, 403, 412, 500, 503, 504]:
        # Unauthorized, Forbidden, Precondition failed, Internal Server Error
        log.write(ctx, "mint_doi: httpCode " + str(httpCode) + " received. Could be retried later")
        publication_state["status"] = "Retry"
    elif httpCode == 400:
        log.write(ctx, "mint_doi: 400 Bad Request - request body must be exactly two lines: DOI and URL; wrong domain, wrong prefix")
        publication_state["status"] = "Unrecoverable"
    else:
        log.write(ctx, "mint_doi: httpCode " + str(httpCode) + " received. Unrecoverable error.")
        publication_state["status"] = "Unrecoverable"


def generate_landing_page_url(ctx, publication_config, publication_state):
    """Generate a URL for the landing page.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    publicVHost = publication_config["publicVHost"]
    yodaInstance = publication_config["yodaInstance"]
    yodaPrefix = publication_config["yodaPrefix"]
    randomId = publication_state["randomId"]
    publicPath = yodaInstance + "/" + yodaPrefix + "/" + randomId + ".html"
    landingPageUrl = "https://" + publicVHost + "/" + publicPath

    publication_state["landingPageUrl"] = landingPageUrl


def generate_landing_page(ctx, publication_state, publish):
    """Generate a dataCite compliant XML based up yoda-metadata.json.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    :param publish:            Publication or depublication
    """
    combiJsonPath = publication_state["combiJsonPath"]
    randomId = publication_state["randomId"]
    vaultPackage = publication_state["vaultPackage"]

    json_schema = schema.get_active_schema(ctx, vaultPackage)
    temp_coll, coll = pathutil.chop(combiJsonPath)
    landing_page_path = temp_coll + "/" + randomId + ".html"

    if publish == "publish":
        template_name = 'landingpage.html.j2'
    else:
        template_name = 'emptylandingpage.html.j2'

    landing_page_html = json_landing_page.json_landing_page_create_json_landing_page(ctx, user.zone(ctx), template_name, combiJsonPath, json_schema)

    data_object.write(ctx, landing_page_path, landing_page_html)

    publication_state["landingPagePath"] = landing_page_path


def copy_landingpage_to_public_host(ctx, random_id, publication_config, publication_state):
    """Copy the resulting landing page to configured public host.

    :param ctx:                Combined type of a callback and rei struct
    :param random_id:          Random ID part of data package DOI
    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    publicHost = publication_config["publicHost"]
    landingPagePath = publication_state["landingPagePath"]
    yodaInstance = publication_config["yodaInstance"]
    yodaPrefix = publication_config["yodaPrefix"]
    publicPath = yodaInstance + "/" + yodaPrefix + "/" + random_id + ".html"

    argv = publicHost + " inbox /var/www/landingpages/" + publicPath

    error = 0
    ctx.iiGenericSecureCopy(argv, landingPagePath, error)
    if error >= 0:
        publication_state["landingPageUploaded"] = "yes"
    else:
        publication_state["status"] = "Retry"
        log.write(ctx, "copy_landingpage_to_public: " + str(error))


def copy_metadata_to_moai(ctx, random_id, publication_config, publication_state):
    """Copy the metadata json file to configured MOAI.

    :param ctx:                Combined type of a callback and rei struct
    :param random_id:          Random ID part of data package DOI
    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    publicHost = publication_config["publicHost"]
    yodaInstance = publication_config["yodaInstance"]
    yodaPrefix = publication_config["yodaPrefix"]
    combiJsonPath = publication_state["combiJsonPath"]

    argv = publicHost + " inbox /var/www/moai/metadata/" + yodaInstance + "/" + yodaPrefix + "/" + random_id + ".json"
    error = 0
    ctx.iiGenericSecureCopy(argv, combiJsonPath, error)
    if error >= 0:
        publication_state["oaiUploaded"] = "yes"
    else:
        publication_state["status"] = "Retry"
        log.write(ctx, "copy_metadata_to_public: " + error)


def set_access_restrictions(ctx, vault_package, publication_state):
    """Set access restriction for vault package.

    :param ctx:                Combined type of a callback and rei struct
    :param vault_package:      Path to the package in the vault
    :param publication_state:  Dict with state of the publication process

    :returns: None
    """
    access_restriction = publication_state["accessRestriction"]
    access_level = "null"

    if access_restriction.startswith('Open'):
        access_level = "read"

    try:
        msi.set_acl(ctx, "recursive", access_level, "anonymous", vault_package)
    except msi.Error:
        publication_state["status"] = "Unrecoverable"
        return

    # We cannot set "null" as value in a kvp as this will crash msi_json_objops if we ever perform a uuKvp2JSON on it.
    if access_level == "null":
        publication_state["anonymousAccess"] = "no"
    else:
        publication_state["anonymousAccess"] = "yes"


def check_doi_availability(ctx, publication_state):
    """Request DOI to check on availibity. We want a 404 as return code.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    """
    yodaDOI = publication_state["yodaDOI"]

    httpCode = datacite.metadata_get(ctx, yodaDOI)

    if httpCode == 404:
        publication_state["DOIAvailable"] = "yes"
    elif httpCode in [401, 403, 500, 503, 504]:
        # request failed, worth a retry
        publication_state["status"] = "Retry"
    elif httpCode in [200, 204]:
        # DOI already in use
        publication_state["DOIAvailable"] = "no"
        publication_state["status"] = "Retry"


def process_publication(ctx, vault_package):
    """Handling of publication of vault_package.

    :param ctx:             Combined type of a callback and rei struct
    :param vault_package:   Path to the package in the vault

    :return: "OK" if all went ok
    """

    publication_state = {}

    log.write(ctx, "Process publication of vault package <{}>".format(vault_package))

    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    vault_status = vault.get_coll_vault_status(ctx, vault_package).value

    if vault_status not in [str(constants.vault_package_state.PUBLISHED), str(constants.vault_package_state.APPROVED_FOR_PUBLICATION)]:
        return "InvalidPackageStatusForPublication" + ": " + vault_status

    # get publication configuration
    publication_config = get_publication_config(ctx)

    # get state of all related to the publication
    publication_state = get_publication_state(ctx, vault_package)
    status = publication_state['status']

    # Check if verbose mode is enabled
    verbose = True if "verboseMode" in publication_config else False
    if verbose:
        log.write(ctx, "Running process_publication in verbose mode.")

    # Publication status check and handling
    if verbose:
        log.write(ctx, "Initial publication status is: " + publication_state['status'])
    if status in ["Unrecoverable", "Processing"]:
        return "publication status: " + status
    elif status in ["Unknown", "Retry"]:
        status = "Processing"
        publication_state['status'] = status

    # Set flag to update base DOI when this data package is the latest version.
    update_base_doi = False
    if "previous_version" in publication_state and "next_version" not in publication_state:
        if verbose:
            log.write(ctx, "In branch for updating base DOI")

        update_base_doi = True
        v1_exists = True

        # Check if version 1 of data package exists.
        previous_vault_package = publication_state["previous_version"]
        previous_publication_state = get_publication_state(ctx, previous_vault_package)
        random_id = previous_publication_state["randomId"]
        if len(random_id.split(".")) != 2:
            v1_exists = False

        # If no version 1 exists for this data package, create it.
        if not v1_exists:
            log.write(ctx, "Creating v1 publication of vault package <{}>".format(previous_vault_package))
            generate_preliminary_next_version_DOI(ctx, publication_config, previous_publication_state)
            previous_publication_state['DOIMinted'] = 'no'
            save_publication_state(ctx, previous_vault_package, previous_publication_state)
            set_update_publication_state(ctx, previous_vault_package)
            status = process_publication(ctx, previous_vault_package)
            if status in ["Unrecoverable", "Retry"]:
                if verbose:
                    log.write(ctx, "Error status for creating v1 package: " + status)
                return status

    # Publication date
    if "publicationDate" not in publication_state:
        if verbose:
            log.write(ctx, "Setting publication date.")
        publication_state["publicationDate"] = get_publication_date(ctx, vault_package)

    # DOI handling
    if "yodaDOI" not in publication_state:
        # If a previous version is set generate a versioned DOI.
        if "previous_version" in publication_state:
            if verbose:
                log.write(ctx, "Generating preliminary DOI for next version.")
            generate_preliminary_next_version_DOI(ctx, publication_config, publication_state)
        else:
            if verbose:
                log.write(ctx, "Generating preliminary DOI.")
            generate_preliminary_DOI(ctx, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)

    elif "DOIAvailable" in publication_state:
        if publication_state["DOIAvailable"] == "no":

            if verbose:
                log.write(ctx, "DOI available: no")

            # If a previous version is set generate a versioned DOI.
            if "previous_version" in publication_state:
                if verbose:
                    log.write(ctx, "Generating preliminary DOI for next version.")
                generate_preliminary_next_version_DOI(ctx, publication_config, publication_state)
            else:
                if verbose:
                    log.write(ctx, "Generating preliminary DOI.")
                generate_preliminary_DOI(ctx, publication_config, publication_state)

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
        except msi.Error:
            if verbose:
                log.write(ctx, "Exception while generating combi JSON.")
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            if verbose:
                log.write(ctx, "Error status after generating combi JSON.")
            return publication_state["status"]

    # Create Landing page URL
    if verbose:
        log.write(ctx, "Creating landing page.")
    generate_landing_page_url(ctx, publication_config, publication_state)

    # Generate DataCite JSON
    if "dataCiteJsonPath" not in publication_state:
        if verbose:
            log.write(ctx, "Generating Datacite JSON.")
        try:
            generate_datacite_json(ctx, publication_state)
        except msi.Error:
            if verbose:
                log.write(ctx, "Error while generating Datacite JSON.")
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            if verbose:
                log.write(ctx, "Error status after generating Datacite JSON.")
            return publication_state["status"]

    # Check if DOI is in use
    if "DOIAvailable" not in publication_state:
        if verbose:
            log.write(ctx, "Checking whether DOI is available.")

        try:
            check_doi_availability(ctx, publication_state)
        except msi.Error:
            if verbose:
                log.write(ctx, "Error while checking DOI availability.")
            publication_state["status"] = "Retry"

        if publication_state["status"] == "Retry":
            if verbose:
                log.write(ctx, "Error status after checking DOI availability.")
            return publication_state["status"]

    # Send DataCite JSON to metadata end point
    if "dataCiteMetadataPosted" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading metadata to Datacite.")
        try:
            # Determine wether DOI is already minted.
            yoda_doi = None
            try:
                if publication_state['DOIMinted'] == 'yes':
                    yoda_doi = publication_state['yodaDOI']
            except KeyError:
                pass

            upload_metadata_to_datacite(ctx, publication_state, yoda_doi)

            if update_base_doi:
                # Remove version from DOI.
                if verbose:
                    log.write(ctx, "Updating base DOI.")
                yoda_doi = publication_state['yodaDOI'].rsplit(".", 1)[0]
                upload_metadata_to_datacite(ctx, publication_state, yoda_doi)
        except msi.Error:
            if verbose:
                log.write(ctx, "Error while sending metadata to Datacite.")
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            if verbose:
                log.write(ctx, "Error status after sending metadata to Datacite.")
            return publication_state["status"]

    # Create landing page
    if "landingPagePath" not in publication_state:
        if verbose:
            log.write(ctx, "Creating landing page.")
        # Create landing page
        try:
            generate_landing_page(ctx, publication_state, "publish")
        except msi.Error:
            if verbose:
                log.write(ctx, "Error while sending metadata to Datacite.")
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Unrecoverable":
            if verbose:
                log.write(ctx, "Error status after creating landing page.")
            return publication_state["status"]

    # Use secure copy to push landing page to the public host
    if "landingPageUploaded" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading landing page.")
        random_id = publication_state["randomId"]
        copy_landingpage_to_public_host(ctx, random_id, publication_config, publication_state)

        if update_base_doi:
            # Remove version from DOI.
            if verbose:
                log.write(ctx, "Updating base DOI landing page.")
            random_id = random_id.rsplit(".", 1)[0]
            copy_landingpage_to_public_host(ctx, random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            if verbose:
                log.write(ctx, "Error status after uploading landing page.")
            return publication_state["status"]

    # Use secure copy to push combi JSON to MOAI server
    if "oaiUploaded" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading to MOAI.")
        random_id = publication_state["randomId"]
        copy_metadata_to_moai(ctx, random_id, publication_config, publication_state)

        if update_base_doi:
            # Remove version from DOI.
            if verbose:
                log.write(ctx, "Updating base DOI at MOAI.")
            random_id = random_id.rsplit(".", 1)[0]
            copy_metadata_to_moai(ctx, random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            if verbose:
                log.write(ctx, "Error status after uplaoding to MOAI.")
            return publication_state["status"]

    # Set access restriction for vault package.
    if "anonymousAccess" not in publication_state:
        if verbose:
            log.write(ctx, "Setting vault access restrictions.")
        set_access_restrictions(ctx, vault_package, publication_state)
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            if verbose:
                log.write(ctx, "Error status after setting vault access restrictions.")
            return publication_state["status"]

    # Mint DOI with landing page URL.
    if "DOIMinted" not in publication_state:
        if verbose:
            log.write(ctx, "Minting DOI.")
        mint_doi(ctx, publication_state['yodaDOI'], publication_state)

        if update_base_doi:
            if verbose:
                log.write(ctx, "Base DOI update.")
            # Remove version from DOI.
            yoda_doi = publication_state['yodaDOI'].rsplit(".", 1)[0]
            mint_doi(ctx, yoda_doi, publication_state)

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            if verbose:
                log.write(ctx, "Error status during minting DOI.")
            return publication_state["status"]

        # The publication was a success
        publication_state["status"] = "OK"
        save_publication_state(ctx, vault_package, publication_state)

        avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'vault_status', constants.vault_package_state.PUBLISHED)

        if "previous_version" in publication_state:
            if verbose:
                log.write(ctx, "Updating previous version AVU.")
            avu.set_on_coll(ctx, publication_state["previous_version"], constants.UUORGMETADATAPREFIX + 'publication_next_version', vault_package)
    else:
        # The publication was a success
        if verbose:
            log.write(ctx, "Publication successful.")
        publication_state["status"] = "OK"
        save_publication_state(ctx, vault_package, publication_state)
        provenance.log_action(ctx, "system", vault_package, "publication updated")

    log.write(ctx, "Finished publication of vault package <{}>".format(vault_package))
    return publication_state["status"]


def process_depublication(ctx, vault_package):
    status = "Unknown"

    log.write(ctx, "Process depublication of vault package <{}>".format(vault_package))

    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
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
    status = publication_state['status']

    if status == "OK":
        # reset on first call
        set_update_publication_state(ctx, vault_package)
        publication_state = get_publication_state(ctx, vault_package)
        status = publication_state['status']

    if status in ["Unrecoverable", "Processing"]:
        return status
    elif status in ["Unknown", "Retry"]:
        status = "Processing"
        publication_state['status'] = status

    # Set flag to update base DOI when this data package is the latest version.
    update_base_doi = False
    if "previous_version" in publication_state and "next_version" not in publication_state:
        update_base_doi = True

    # Determine last modification time. Always run, no matter if retry
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime(ctx, vault_package)

    # Generate Combi Json consisting of user and system metadata
    if "combiJsonPath" not in publication_state:
        try:
            generate_system_json(ctx, publication_state)
        except msi.Error:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Hide metadata from DataCite
    if "dataCiteMetadataPosted" not in publication_state:
        try:
            upload_metadata_to_datacite(ctx, publication_state, publication_state['yodaDOI'], hide=True)

            if update_base_doi:
                # Remove version from DOI.
                yoda_doi = publication_state['yodaDOI'].rsplit(".", 1)[0]
                upload_metadata_to_datacite(ctx, publication_state, yoda_doi, hide=True)
        except msi.Error:
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Create landing page
    if "landingPagePath" not in publication_state:
        # Create landing page
        try:
            generate_landing_page(ctx, publication_state, "depublish")
        except msi.Error:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Unrecoverable":
            return publication_state["status"]

    # Use secure copy to push landing page to the public host
    if "landingPageUploaded" not in publication_state:
        random_id = publication_state["randomId"]
        copy_landingpage_to_public_host(ctx, random_id, publication_config, publication_state)

        if update_base_doi:
            # Remove version from DOI.
            random_id = random_id.rsplit(".", 1)[0]
            copy_landingpage_to_public_host(ctx, random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Use secure copy to push combi JSON to MOAI server
    if "oaiUploaded" not in publication_state:
        random_id = publication_state["randomId"]
        copy_metadata_to_moai(ctx, random_id, publication_config, publication_state)

        if update_base_doi:
            # Remove version from DOI.
            random_id = random_id.rsplit(".", 1)[0]
            copy_metadata_to_moai(ctx, random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Set access restriction for vault package.
    if "anonymousAccess" not in publication_state:
        set_access_restrictions(ctx, vault_package, publication_state)
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # The depublication was a success
    avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'vault_status', constants.vault_package_state.DEPUBLISHED)
    publication_state["status"] = "OK"
    save_publication_state(ctx, vault_package, publication_state)
    log.write(ctx, "Finished depublication of vault package <{}>".format(vault_package))

    return publication_state["status"]


def process_republication(ctx, vault_package):
    """Routine to process a republication with sanity checks at every step."""
    publication_state = {}

    log.write(ctx, "Process republication of vault package <{}>".format(vault_package))

    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    vault_status = vault.get_coll_vault_status(ctx, vault_package).value

    if vault_status not in [str(constants.vault_package_state.PENDING_REPUBLICATION)]:
        return "InvalidPackageStatusForRePublication" + ": " + vault_status

    publication_config = get_publication_config(ctx)

    # get state of all related to the publication
    publication_state = get_publication_state(ctx, vault_package)
    status = publication_state['status']

    if status == "OK":
        # reset on first call
        set_update_publication_state(ctx, vault_package)
        publication_state = get_publication_state(ctx, vault_package)
        status = publication_state['status']

    if status in ["Unrecoverable", "Processing"]:
        return status
    elif status in ["Unknown", "Retry"]:
        status = "Processing"
        publication_state['status'] = status

    # Set flag to update base DOI when this data package is the latest version.
    update_base_doi = False
    if "previous_version" in publication_state and "next_version" not in publication_state:
        update_base_doi = True

    # Publication date
    if "publicationDate" not in publication_state:
        publication_state["publicationDate"] = get_publication_date(ctx, vault_package)

    # Determine last modification time. Always run, no matter if retry
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime(ctx, vault_package)

    # Generate Combi Json consisting of user and system metadata
    if "combiJsonPath" not in publication_state:
        try:
            generate_combi_json(ctx, publication_config, publication_state)
        except msi.Error:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Generate DataCite JSON
    if "dataCiteJsonPath" not in publication_state:
        try:
            generate_datacite_json(ctx, publication_state)
        except msi.Error:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Send DataCite JSON to metadata end point
    if "dataCiteMetadataPosted" not in publication_state:
        try:
            upload_metadata_to_datacite(ctx, publication_state, publication_state['yodaDOI'])

            if update_base_doi:
                # Remove version from DOI.
                yoda_doi = publication_state['yodaDOI'].rsplit(".", 1)[0]
                upload_metadata_to_datacite(ctx, publication_state, yoda_doi)
        except msi.Error:
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Create landing page
    if "landingPagePath" not in publication_state:
        # Create landing page
        try:
            generate_landing_page(ctx, publication_state, "publish")
        except msi.Error:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Unrecoverable":
            return publication_state["status"]

    # Use secure copy to push landing page to the public host
    if "landingPageUploaded" not in publication_state:
        random_id = publication_state["randomId"]
        copy_landingpage_to_public_host(ctx, random_id, publication_config, publication_state)

        if update_base_doi:
            # Remove version from DOI.
            random_id = random_id.rsplit(".", 1)[0]
            copy_landingpage_to_public_host(ctx, random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Use secure copy to push combi JSON to MOAI server
    if "oaiUploaded" not in publication_state:
        random_id = publication_state["randomId"]
        copy_metadata_to_moai(ctx, random_id, publication_config, publication_state)

        if update_base_doi:
            # Remove version from DOI.
            random_id = random_id.rsplit(".", 1)[0]
            copy_metadata_to_moai(ctx, random_id, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Set access restriction for vault package.
    if "anonymousAccess" not in publication_state:
        set_access_restrictions(ctx, vault_package, publication_state)
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # The publication was a success
    publication_state["status"] = "OK"
    save_publication_state(ctx, vault_package, publication_state)
    avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'vault_status', constants.vault_package_state.PUBLISHED)
    log.write(ctx, "Finished republication of vault package <{}>".format(vault_package))

    return publication_state["status"]


@rule.make(inputs=range(4), outputs=range(4, 6))
def rule_update_publication(ctx, vault_package, update_datacite, update_landingpage, update_moai):
    """Rule interface for updating the publication of a vault package.

    :param ctx:                Combined type of a callback and rei struct
    :param vault_package:      Path to the package in the vault
    :param update_datacite:    Flag that indicates updating DataCite
    :param update_landingpage: Flag that indicates updating landingpage
    :param update_moai:        Flag that indicates updating MOAI (OAI-PMH)

    :returns: "OK" if all went ok
    """
    return update_publication(ctx, vault_package, update_datacite == 'Yes', update_landingpage == 'Yes', update_moai == 'Yes')


def update_publication(ctx, vault_package, update_datacite=False, update_landingpage=False, update_moai=False):
    """Routine to update a publication with sanity checks at every step.

    :param ctx:                Combined type of a callback and rei struct
    :param vault_package:      Path to the package in the vault
    :param update_datacite:    Flag that indicates updating DataCite
    :param update_landingpage: Flag that indicates updating landingpage
    :param update_moai:        Flag that indicates updating MOAI (OAI-PMH)

    :returns: "OK" if all went ok
    """
    publication_state = {}

    log.write(ctx, "update_publication: Process vault package <{}> DataCite={} landingpage={} MOAI={}".format(vault_package, update_datacite, update_landingpage, update_moai))

    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    vault_status = vault.get_coll_vault_status(ctx, vault_package).value

    if vault_status not in [str(constants.vault_package_state.PUBLISHED), str(constants.vault_package_state.DEPUBLISHED)]:
        return "InvalidPackageStatus" + ": " + vault_status

    publication_config = get_publication_config(ctx)

    # Get state of all related to the publication.
    publication_state = get_publication_state(ctx, vault_package)
    status = publication_state['status']

    # Publication must be finsished.
    if status != "OK":
        return status

    # Publication date
    if "publicationDate" not in publication_state:
        publication_state["publicationDate"] = get_publication_date(ctx, vault_package)

    # Determine last modification time. Always run, no matter if retry
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime(ctx, vault_package)

    # Generate Combi Json consisting of user and system metadata
    try:
        generate_combi_json(ctx, publication_config, publication_state)
    except msi.Error:
        publication_state["status"] = "Unrecoverable"

    save_publication_state(ctx, vault_package, publication_state)

    if publication_state["status"] in ["Unrecoverable", "Retry"]:
        return publication_state["status"]

    if update_datacite:
        # Generate DataCite JSON
        log.write(ctx, 'Update datacite for package {}'.format(vault_package))
        try:
            generate_datacite_json(ctx, publication_state)
        except msi.Error:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

        # Send DataCite JSON to metadata end point
        try:
            upload_metadata_to_datacite(ctx, publication_state, publication_state['yodaDOI'])
        except msi.Error:
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    if update_landingpage:
        # Create landing page
        log.write(ctx, 'Update landingpage for package {}'.format(vault_package))
        try:
            generate_landing_page(ctx, publication_state, "publish")
        except msi.Error:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Unrecoverable":
            return publication_state["status"]

        # Use secure copy to push landing page to the public host
        random_id = publication_state["randomId"]
        copy_landingpage_to_public_host(ctx, random_id, publication_config, publication_state)
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    if update_moai:
        # Use secure copy to push combi JSON to MOAI server
        log.write(ctx, 'Update MOAI for package {}'.format(vault_package))
        random_id = publication_state["randomId"]
        copy_metadata_to_moai(ctx, random_id, publication_config, publication_state)
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Updating was a success
    publication_state["status"] = "OK"
    save_publication_state(ctx, vault_package, publication_state)

    return publication_state["status"]


def get_collection_metadata(ctx, coll, prefix):
    """Retrieve all collection metadata.

    :param ctx:    Combined type of a callback and rei struct
    :param coll:   Collection to retrieve metadata from
    :param prefix: Prefix of the requested metadata

    :return: Dict with all requested (prefixed) attributes and strip off prefix for the key names
    """
    coll_metadata = {}
    iter = genquery.row_iterator(
        "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + coll + "' AND META_COLL_ATTR_NAME like '" + prefix + "%'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        coll_metadata[row[0][len(prefix):]] = row[1]

    return coll_metadata


"""Rule interface for processing publication of a vault package."""
rule_process_publication = rule.make(inputs=range(1), outputs=range(1, 3))(process_publication)


"""Rule interface for processing depublication of a vault package."""
rule_process_depublication = rule.make(inputs=range(1), outputs=range(1, 3))(process_depublication)


"""Rule interface for processing republication of a vault package."""
rule_process_republication = rule.make(inputs=range(1), outputs=range(1, 3))(process_republication)
