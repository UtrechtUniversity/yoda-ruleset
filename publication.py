# -*- coding: utf-8 -*-
"""Functions for publication."""

__copyright__ = 'Copyright (c) 2019-2024, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

from datetime import datetime

import genquery
from requests.exceptions import ReadTimeout

import datacite
import json_datacite
import json_landing_page
import meta
import provenance
import schema
import vault
from util import *

import re

__all__ = ['rule_process_publication',
           'rule_process_depublication',
           'rule_process_republication',
           'rule_update_publication',
           'rule_lift_embargos_on_data_access']


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
    config_keys = {}
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
            config_keys[attr2keys[attr]] = val
        except KeyError:
            continue

    # Any differences between
    for key in attr2keys:
        if key not in found_attrs and key not in optional_keys:
            log.write(ctx, 'Missing config key ' + key)

    return config_keys


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
    versionDOI = publication_state["versionDOI"]
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
    json_datacite.json_datacite_create_combi_metadata_json(ctx, metadataJsonPath, combiJsonPath, lastModifiedDateTime, versionDOI, publicationDate, openAccessLink, licenseUri)

    publication_state["combiJsonPath"] = combiJsonPath


def generate_system_json(ctx, publication_state):
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
    for key, value in publ_metadata.items():
        publication_state[key] = value

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
    for key in publication_state:
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
    if coll_status not in [str(constants.vault_package_state.PUBLISHED), str(constants.vault_package_state.PENDING_DEPUBLICATION), str(constants.vault_package_state.PENDING_REPUBLICATION)]:
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

        return my_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z')


def generate_preliminary_doi(ctx, publication_config, publication_state):
    """Generate a Preliminary DOI. Preliminary, because we check for collision later.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    dataCitePrefix = publication_config["dataCitePrefix"]
    yodaPrefix = publication_config["yodaPrefix"]

    randomId = datacite.generate_random_id(ctx, publication_config["randomIdLength"])

    publication_state["randomId"] = randomId
    publication_state["versionDOI"] = dataCitePrefix + "/" + yodaPrefix + "-" + randomId


def generate_base_doi(ctx, publication_config, publication_state):
    """Generate a base DOI.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    dataCitePrefix = publication_config["dataCitePrefix"]
    yodaPrefix = publication_config["yodaPrefix"]

    randomId = datacite.generate_random_id(ctx, publication_config["randomIdLength"])

    publication_state["baseRandomId"] = randomId
    publication_state["baseDOI"] = dataCitePrefix + "/" + yodaPrefix + "-" + randomId


def generate_datacite_json(ctx, publication_state):
    """Generate a DataCite compliant JSON based on yoda-metadata.json.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    """
    combiJsonPath = publication_state["combiJsonPath"]

    randomId = publication_state["randomId"]

    temp_coll, coll = pathutil.chop(combiJsonPath)
    datacite_json_path = temp_coll + "/" + randomId + "-dataCite.json"

    # Based on content of *combiJsonPath, get DataciteJson as string
    datacite_json = json_datacite.json_datacite_create_datacite_json(ctx, publication_state["landingPageUrl"], combiJsonPath)

    data_object.write(ctx, datacite_json_path, jsonutil.dump(datacite_json))

    publication_state["dataCiteJsonPath"] = datacite_json_path


def post_metadata_to_datacite(ctx, publication_state, doi, send_method, base_doi=False):
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
            httpCode = datacite.metadata_post(ctx, datacite_json)
        else:
            httpCode = datacite.metadata_put(ctx, doi, datacite_json)

        if (send_method == 'post' and httpCode == 201) or (send_method == 'put' and httpCode == 200):
            publication_state["dataCiteMetadataPosted"] = "yes"
        elif httpCode in [401, 403, 500, 503, 504]:
            # Unauthorized, Forbidden, Precondition failed, Internal Server Error
            log.write(ctx, "post_metadata_to_datacite: httpCode " + str(httpCode) + " received. Will be retried later")
            publication_state["status"] = "Retry"
        else:
            log.write(ctx, "post_metadata_to_datacite: httpCode " + str(httpCode) + " received. Unrecoverable error.")
            publication_state["status"] = "Unrecoverable"
    except ReadTimeout:
        # DataCite timeout.
        log.write(ctx, "post_metadata_to_datacite: timeout received. Will be retried later")
        publication_state["status"] = "Retry"


def post_draft_doi_to_datacite(ctx, publication_state):
    """Upload DOI to DataCite. This will register the DOI as a draft.
    This function is also a draft, and will have to be reworked!

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    """
    datacite_json_path = publication_state["dataCiteJsonPath"]
    datacite_json = data_object.read(ctx, datacite_json_path)

    try:
        # post the DOI only
        httpCode = datacite.metadata_post(ctx, {
            'data': {
                'type': 'dois',
                'attributes': {
                    'doi': datacite_json['data']['attributes']['doi']
                }
            }
        })

        if httpCode == 201:
            publication_state["dataCiteMetadataPosted"] = "no"
        elif httpCode in [401, 403, 500, 503, 504]:
            # Unauthorized, Forbidden, Precondition failed, Internal Server Error
            log.write(ctx, "post_draft_doi_to_datacite: httpCode " + str(httpCode) + " received. Will be retried later")
            publication_state["status"] = "Retry"
        else:
            log.write(ctx, "post_draft_doi_to_datacite: httpCode " + str(httpCode) + " received. Unrecoverable error.")
            publication_state["status"] = "Unrecoverable"
    except ReadTimeout:
        # DataCite timeout.
        log.write(ctx, "post_draft_doi_to_datacite: timeout received. Will be retried later")
        publication_state["status"] = "Retry"


def remove_metadata_from_datacite(ctx, publication_state, type_flag):
    """Remove metadata XML from DataCite.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    :param type_flag:          Determine whether it is base DOI or version DOI
    """
    import json
    payload = json.dumps({"data": {"attributes": {"event": "hide"}}})

    try:
        httpCode = datacite.metadata_put(ctx, publication_state[type_flag + "DOI"], payload)

        if httpCode == 200:
            publication_state["dataCiteMetadataPosted"] = "yes"
        elif httpCode in [401, 403, 412, 500, 503, 504]:
            # Unauthorized, Forbidden, Precondition failed, Internal Server Error
            log.write(ctx, "remove metadata from datacite: httpCode " + str(httpCode) + " received. Will be retried later")
            publication_state["status"] = "Retry"
        elif httpCode == 404:
            # Invalid DOI
            log.write(ctx, "remove metadata from datacite: 404 Not Found - Invalid DOI")
            publication_state["status"] = "Unrecoverable"
        else:
            log.write(ctx, "remove metadata from datacite: httpCode " + str(httpCode) + " received. Unrecoverable error.")
            publication_state["status"] = "Unrecoverable"
    except ReadTimeout:
        # DataCite timeout.
        log.write(ctx, "remove_metadata_from_datacite: timeout received. Will be retried later")
        publication_state["status"] = "Retry"


def mint_doi(ctx, publication_state, type_flag):
    """Announce the landing page URL for a DOI to dataCite. This will mint the DOI.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    :param type_flag:          Flag indicating DOI type ('version' or 'base')
    """
    import json
    payload = json.dumps({"data": {"attributes": {"url": publication_state["landingPageUrl"]}}})

    try:
        httpCode = datacite.metadata_put(ctx, publication_state[type_flag + "DOI"], payload)

        if httpCode == 200:  # 201:
            publication_state[type_flag + "DOIMinted"] = "yes"
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
    except ReadTimeout:
        # DataCite timeout.
        log.write(ctx, "mint_doi: timeout received. Will be retried later")
        publication_state["status"] = "Retry"


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

    # Get all DOI versions
    if "baseDOI" in publication_state:
        base_doi = publication_state["baseDOI"]
        versions = get_all_versions(ctx, vaultPackage, publication_state["baseDOI"])[0]
    else:
        base_doi = ''
        versions = []

    if publish == "publish":
        template_name = 'landingpage.html.j2'
    else:
        template_name = 'emptylandingpage.html.j2'

    landing_page_html = json_landing_page.json_landing_page_create_json_landing_page(ctx, user.zone(ctx), template_name, combiJsonPath, json_schema, base_doi, versions)

    data_object.write(ctx, landing_page_path, landing_page_html)

    publication_state["landingPagePath"] = landing_page_path


def copy_landingpage_to_public_host(ctx, random_id, publication_config, publication_state):
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
        publication_state["status"] = "Retry"
        log.write(ctx, "copy_landingpage_to_public: " + error)


def copy_metadata_to_moai(ctx, random_id, publication_config, publication_state):
    """Copy the metadata json file to configured MOAI.

    :param ctx:                Combined type of a callback and rei struct
    :param random_id:          Random ID part of DOI used for MOAI metadata file
    :param publication_config: Dict with publication configuration
    :param publication_state:  Dict with state of the publication process
    """
    publicHost = publication_config["publicHost"]
    yodaInstance = publication_config["yodaInstance"]
    yodaPrefix = publication_config["yodaPrefix"]
    # randomId = publication_state["randomId"]  ##### in case of base? ###### revert to original
    combiJsonPath = publication_state["combiJsonPath"]

    argv = publicHost + " inbox /var/www/moai/metadata/" + yodaInstance + "/" + yodaPrefix + "/" + random_id + ".json"
    copy_result = ctx.iiGenericSecureCopy(argv, combiJsonPath, '')
    error = copy_result['arguments'][2]
    if int(error) >= 0:
        publication_state["oaiUploaded"] = "yes"
    else:
        publication_state["status"] = "Retry"
        log.write(ctx, "copy_metadata_to_public: " + error)


def set_access_restrictions(ctx, vault_package, publication_state):
    """Set access restriction for vault package.

    This function is called when (re)publishing a vault package.
    The embargo date of a package is essential determining access.
    If current date < embargo end date, then set end date in `ord_lift_embargo_date`
    to be picked up by lift embargo cronjob.

    :param ctx:                Combined type of a callback and rei struct
    :param vault_package:      Path to the package in the vault
    :param publication_state:  Dict with state of the publication process

    :returns: None
    """
    # Embargo handling
    combiJsonPath = publication_state["combiJsonPath"]
    dictJsonData = jsonutil.read(ctx, combiJsonPath, want_bytes=False)

    # Remove empty objects to prevent empty fields on landingpage.
    dictJsonData = misc.remove_empty_objects(dictJsonData)

    active_embargo = False

    # Check whether lift_embargo_date is present already
    iter = genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + vault_package + "' AND META_COLL_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + "lift_embargo_date'",
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
    except Exception as e:
        log.write(ctx, "set_access_restrictions for {} failed: {}".format(vault_package, str(e)))
        publication_state["status"] = "Unrecoverable"
        return

    # We cannot set "null" as value in a kvp as this will crash msi_json_objops if we ever perform a uuKvp2JSON on it.
    if access_level == "null":
        publication_state["anonymousAccess"] = "no"
    else:
        publication_state["anonymousAccess"] = "yes"


def check_doi_availability(ctx, publication_state, type_flag):
    """Request DOI to check on availability. We want a 404 as return code.

    :param ctx:                Combined type of a callback and rei struct
    :param publication_state:  Dict with state of the publication process
    :param type_flag:          Flag indicating DOI type ('version' or 'base')
    """
    doi = publication_state[type_flag + "DOI"]

    try:
        http_code = datacite.metadata_get(ctx, doi)

        if http_code == 404:
            publication_state[type_flag + "DOIAvailable"] = "yes"
        elif http_code in [401, 403, 500, 503, 504]:
            # request failed, worth a retry
            publication_state["status"] = "Retry"
        elif http_code in [200, 204]:
            # DOI already in use
            publication_state[type_flag + "DOIAvailable"] = "no"
            publication_state["status"] = "Retry"
    except ReadTimeout:
        # DataCite timeout.
        log.write(ctx, "check_doi_availability: timeout received. Will be retried later")
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
    verbose = "verboseMode" in publication_config
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
        # Get previous publication state
        previous_vault_package = publication_state["previous_version"]
        previous_publication_state = get_publication_state(ctx, previous_vault_package)

        if "baseDOI" in previous_publication_state:
            # Set the link to previous publication state
            publication_state["baseDOI"] = previous_publication_state["baseDOI"]
            publication_state["baseDOIMinted"] = previous_publication_state["baseDOIMinted"]
            publication_state["baseRandomId"] = previous_publication_state["baseRandomId"]

        # Create base DOI if it does not exist in the previous publication state.
        elif "baseDOI" not in previous_publication_state:
            log.write(ctx, "Creating base DOI for the vault package <{}>".format(vault_package))
            try:
                generate_base_doi(ctx, publication_config, publication_state)
                check_doi_availability(ctx, publication_state, 'base')
                publication_state["baseDOIMinted"] = 'no'
                # Set the link to previous publication state
                previous_publication_state["baseDOI"] = publication_state["baseDOI"]
                previous_publication_state["baseRandomId"] = publication_state["baseRandomId"]
            except Exception as e:
                log.write(ctx, "Error while checking version DOI availability: " + str(e))
                publication_state["status"] = "Retry"

            save_publication_state(ctx, previous_vault_package, previous_publication_state)
            save_publication_state(ctx, vault_package, publication_state)

            if status == "Retry":
                if verbose:
                    log.write(ctx, "Error status for creating base DOI: " + status)
                return status

    # Publication date
    if "publicationDate" not in publication_state:
        if verbose:
            log.write(ctx, "Setting publication date.")
        publication_state["publicationDate"] = get_publication_date(ctx, vault_package)

    # DOI handling
    if "versionDOI" not in publication_state:
        if verbose:
            log.write(ctx, "Generating preliminary DOI.")
        generate_preliminary_doi(ctx, publication_config, publication_state)

        save_publication_state(ctx, vault_package, publication_state)

    elif "versionDOIAvailable" in publication_state:
        if publication_state["versionDOIAvailable"] == "no":
            if verbose:
                log.write(ctx, "Version DOI available: no")
                log.write(ctx, "Generating preliminary DOI.")
            generate_preliminary_doi(ctx, publication_config, publication_state)

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
        except Exception as e:
            log.write(ctx, "Exception while generating combi JSON: " + str(e))
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
        except Exception as e:
            log.write(ctx, "Exception while generating Datacite JSON: " + str(e))
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            log.write(ctx, "Error status after generating Datacite JSON: " + publication_state["status"])
            return publication_state["status"]

    # Check if DOI is in use
    if "versionDOIAvailable" not in publication_state:
        if verbose:
            log.write(ctx, "Checking whether version DOI is available.")

        try:
            check_doi_availability(ctx, publication_state, 'version')
        except Exception as e:
            log.write(ctx, "Error while checking DOI availability: " + str(e))
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            log.write(ctx, "Error status after checking version DOI availability: " + publication_state["status"])
            return publication_state["status"]

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
        except Exception as e:
            log.write(ctx, "Exception while sending metadata to Datacite: " + str(e))
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            log.write(ctx, "Error status after sending metadata to Datacite: " + publication_state["status"])
            return publication_state["status"]

    # Create landing page
    if "landingPagePath" not in publication_state:
        if verbose:
            log.write(ctx, "Creating landing page.")
        # Create landing page
        try:
            generate_landing_page(ctx, publication_state, "publish")
        except Exception as e:
            log.write(ctx, "Error while creating landing page: " + str(e))
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Unrecoverable":
            log.write(ctx, "Error status after creating landing page: " + publication_state["status"])
            return publication_state["status"]

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

        if publication_state["status"] == "Retry":
            log.write(ctx, "Error status after uploading landing page:" + publication_state["status"])
            return publication_state["status"]

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

        if publication_state["status"] == "Retry":
            log.write(ctx, "Error status after uploading to MOAI: " + publication_state["status"])
            return publication_state["status"]

    # Set access restriction for vault package.
    if "anonymousAccess" not in publication_state:
        if verbose:
            log.write(ctx, "Setting vault access restrictions.")
        set_access_restrictions(ctx, vault_package, publication_state)
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            log.write(ctx, "Error status after setting vault access restrictions." + publication_state["status"])
            return publication_state["status"]

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
            if verbose:
                log.write(ctx, "Updating previous version landing page.")
            previous_versions = get_all_versions(ctx, publication_state["previous_version"], publication_state["baseDOI"])[1]
            for item in previous_versions[1:]:
                update_publication(ctx, item[1], update_datacite=False, update_landingpage=True, update_moai=False)
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

    # Check if verbose mode is enabled
    verbose = "verboseMode" in publication_config
    if verbose:
        log.write(ctx, "Running process_depublication in verbose mode.")

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
        if verbose:
            log.write(ctx, "Generating combi JSON.")
        try:
            generate_system_json(ctx, publication_state)
        except Exception as e:
            log.write(ctx, "Exception while trying to generate system JSON during depublication: " + str(e))
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Hide metadata from DataCite
    if "dataCiteMetadataPosted" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading metadata to Datacite.")
        try:
            remove_metadata_from_datacite(ctx, publication_state, 'version')
            if update_base_doi:
                remove_metadata_from_datacite(ctx, publication_state, 'base')
        except Exception as e:
            log.write(ctx, "Exception while trying to remove metadata from Datacite during depublication: " + str(e))
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Create landing page
    if "landingPagePath" not in publication_state:
        if verbose:
            log.write(ctx, "Creating landing page.")
        # Create landing page
        try:
            generate_landing_page(ctx, publication_state, "depublish")
        except Exception as e:
            log.write(ctx, "Exception while generating landing page during depublication: " + str(e))
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Unrecoverable":
            return publication_state["status"]

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

        if publication_state["status"] == "Retry":
            return publication_state["status"]

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

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Set access restriction for vault package.
    if "anonymousAccess" not in publication_state:
        if verbose:
            log.write(ctx, "Setting vault access restrictions.")
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

    # Check if verbose mode is enabled
    verbose = "verboseMode" in publication_config
    if verbose:
        log.write(ctx, "Running process_republication in verbose mode.")

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
        except Exception as e:
            log.write(ctx, "Exception while generating combi JSON during republication: " + str(e))
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Generate DataCite JSON
    if "dataCiteJsonPath" not in publication_state:
        if verbose:
            log.write(ctx, "Generating Datacite JSON.")
        try:
            generate_datacite_json(ctx, publication_state)
        except Exception as e:
            log.write(ctx, "Exception while generating DataCite JSON for republication: " + str(e))
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Send DataCite JSON to metadata end point
    if "dataCiteMetadataPosted" not in publication_state:
        if verbose:
            log.write(ctx, "Uploading metadata to Datacite.")
        try:
            post_metadata_to_datacite(ctx, publication_state, publication_state['versionDOI'], 'put')

            if update_base_doi:
                post_metadata_to_datacite(ctx, publication_state, publication_state['baseDOI'], 'put', base_doi=True)
        except Exception as e:
            log.write(ctx, "Exception while posting metadata to Datacite during republication: " + str(e))
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Create landing page
    if "landingPagePath" not in publication_state:
        if verbose:
            log.write(ctx, "Creating landing page.")
        # Create landing page
        try:
            generate_landing_page(ctx, publication_state, "publish")
        except Exception as e:
            log.write(ctx, "Exception while creating landing page during republication: " + str(e))
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Unrecoverable":
            return publication_state["status"]

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

        if publication_state["status"] == "Retry":
            return publication_state["status"]

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

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Set access restriction for vault package.
    if "anonymousAccess" not in publication_state:
        if verbose:
            log.write(ctx, "Setting vault access restrictions.")
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

    log.write(ctx, "[UPDATE PUBLICATIONS] Start for {}".format(vault_package))
    collections = genquery.row_iterator(
        "COLL_NAME",
        "COLL_NAME like '%%/home/vault-%%' "
        "AND META_COLL_ATTR_NAME = '{}vault_status' "
        "AND META_COLL_ATTR_VALUE = '{}'".format(constants.UUORGMETADATAPREFIX, str(constants.vault_package_state.PUBLISHED)),
        genquery.AS_LIST,
        ctx
    )

    packages_found = False
    for collection in collections:
        coll_name = collection[0]
        if ((vault_package == '*' and re.match(r'/[^/]+/home/vault-.*', coll_name)) or (vault_package != '*' and re.match(r'/[^/]+/home/vault-.*', coll_name) and coll_name == vault_package)):
            packages_found = True
            output = update_publication(ctx, coll_name, update_datacite == 'Yes', update_landingpage == 'Yes', update_moai == 'Yes')
            log.write(ctx, coll_name + ': ', output)
     
    if not packages_found:
        log.write(ctx, "[UPDATE PUBLICATIONS] No packages found for {}".format(vault_package))
    else:
        log.write(ctx, "[UPDATE PUBLICATIONS] Finished for {}".format(vault_package))


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

    def _check_return_if_publication_status(return_statuses, location):
        # Used to check whether we need to return early because of an
        # unexpected publication status, and log a message for troubleshooting
        # purposes.
        if publication_state["status"] in return_statuses:
            log.write("update_publication: returned with error status from location '{}' (status: '{}')".format(location, publication_state["status"]))
            return True
        else:
            return False

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

    # Check if verbose mode is enabled
    verbose = "verboseMode" in publication_config
    if verbose:
        log.write(ctx, "Running update_publication in verbose mode.")

    # Publication must be finished.
    if status != "OK":
        log.write(ctx, "update_publication: Not processing vault package, because initial status is " + status)
        return status

    update_base_doi = False
    if "baseDOI" in publication_state:
        if verbose:
            log.write(ctx, "In branch for updating base DOI")
        if "previous_version" in publication_state and "next_version" not in publication_state:
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
    except Exception as e:
        log.write(ctx, "Exception while generating combi JSON after metadata update: " + str(e))
        publication_state["status"] = "Unrecoverable"

    save_publication_state(ctx, vault_package, publication_state)

    if _check_return_if_publication_status(["Unrecoverable", "Retry"], "before update DataCite"):
        return publication_state["status"]

    if update_datacite:
        # Generate DataCite JSON
        log.write(ctx, 'Update datacite for package {}'.format(vault_package))
        try:
            generate_datacite_json(ctx, publication_state)
        except Exception as e:
            log.write(ctx, "Exception while generating DataCite JSON after metadata update: " + str(e))
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if _check_return_if_publication_status(["Unrecoverable", "Retry"], "before send DataCite"):
            return publication_state["status"]

        # Send DataCite JSON to metadata end point
        if verbose:
            log.write(ctx, "Uploading metadata to Datacite.")
        try:
            post_metadata_to_datacite(ctx, publication_state, publication_state["versionDOI"], 'put')
            if update_base_doi:
                post_metadata_to_datacite(ctx, publication_state, publication_state["baseDOI"], 'put', base_doi=True)
        except Exception as e:
            log.write(ctx, "Exception while posting metadata to Datacite after metadata update: " + str(e))
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if _check_return_if_publication_status(["Unrecoverable", "Retry"], "before update landing page"):
            return publication_state["status"]

    if update_landingpage:
        # Create landing page
        log.write(ctx, 'Update landing page for package {}'.format(vault_package))
        try:
            generate_landing_page(ctx, publication_state, "publish")
        except Exception as e:
            log.write(ctx, "Exception while updating landing page after metadata update: " + str(e))
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if _check_return_if_publication_status(["Unrecoverable"], "before upload landing page"):
            return publication_state["status"]

        # Use secure copy to push landing page to the public host
        random_id = publication_state["randomId"]
        if verbose:
            log.write(ctx, "Uploading landing page.")
        copy_landingpage_to_public_host(ctx, random_id, publication_config, publication_state)
        if update_base_doi:
            base_random_id = publication_state["baseRandomId"]
            copy_landingpage_to_public_host(ctx, base_random_id, publication_config, publication_state)
        save_publication_state(ctx, vault_package, publication_state)

        if _check_return_if_publication_status(["Retry"], "before update MOAI"):
            return publication_state["status"]

    if update_moai:
        # Use secure copy to push combi JSON to MOAI server
        log.write(ctx, 'Update MOAI for package {}'.format(vault_package))
        random_id = publication_state["randomId"]
        copy_metadata_to_moai(ctx, random_id, publication_config, publication_state)
        if update_base_doi:
            base_random_id = publication_state["baseRandomId"]
            copy_metadata_to_moai(ctx, base_random_id, publication_config, publication_state)
        save_publication_state(ctx, vault_package, publication_state)

        if _check_return_if_publication_status(["Retry"], "before publication OK"):
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


def get_all_versions(ctx, path, doi):
    """Get all the version DOI of published data package in a vault.

    :param ctx:  Combined type of a callback and rei struct
    :param path: Path of the published data package
    :param doi:  Base DOI of the selected publication

    :return: Dict of related version DOIs
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
rule_process_publication = rule.make(inputs=range(1), outputs=range(1, 3))(process_publication)


"""Rule interface for processing depublication of a vault package."""
rule_process_depublication = rule.make(inputs=range(1), outputs=range(1, 3))(process_depublication)


"""Rule interface for processing republication of a vault package."""
rule_process_republication = rule.make(inputs=range(1), outputs=range(1, 3))(process_republication)


@rule.make()
def rule_lift_embargos_on_data_access(ctx):
    """Find vault packages that have a data access embargo that can be lifted as the embargo expires.

    If lift_embargo_date <= now, update publication.

    :param ctx:  Combined type of a callback and rei struct

    :returns: Status of lifting the embargo indications
    """
    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    zone = user.zone(ctx)

    # Find all packages that have embargo date for data access that must be lifted
    iter = genquery.row_iterator(
        "COLL_NAME, META_COLL_ATTR_VALUE",
        "COLL_NAME like  '" + "/{}/home/vault-%".format(zone) + "'"
        " AND META_COLL_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'lift_embargo_date' + "'"
        " AND META_COLL_ATTR_VALUE <= '{}'".format(datetime.now().strftime('%Y-%m-%d')),
        genquery.AS_LIST, ctx
    )
    for row in iter:
        vault_package = row[0]

        log.write(ctx, "Lift embargo for vault package: " + vault_package)
        set_update_publication_state(ctx, vault_package)
        process_publication(ctx, vault_package)

    return 'OK'
