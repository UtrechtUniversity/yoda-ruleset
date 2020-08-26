# -*- coding: utf-8 -*-
"""Functions to publish data and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'


from util import *
import epic
import datacite
import json_datacite41
import json_landing_page
import meta
import vault
import provenance
import mail

__all__ = ['rule_process_publication',
           'rule_process_depublication',
           'rule_process_republication']


"""
This is part of the transformation process. Perhaps in another script????
Used in published_xml_to_json.py -> iiCheckPublishedMetadataXmlForTransformationToJsonBatch()

# \brief Use secure copy to push publised json data object, that arose after transformation from xml->json, to MOAI area.
#
# \param[in] metadata_json     json metadata data object name to be copied to
# \param[in] origin_publication_path
# \param[in] publicHost
# \param[in] yodaInstance
# \param[in] yodaPrefix
#
iiCopyTransformedPublicationToMOAI(*metadata_json, *origin_publication_path, *publicHost, *yodaInstance, *yodaPrefix) {
        *argv = "*publicHost inbox /var/www/moai/metadata/*yodaInstance/*yodaPrefix/*metadata_json";
        *origin_json = '*origin_publication_path/*metadata_json';
        *err = errorcode(msiExecCmd("securecopy.sh", *argv, "", *origin_json, 1, *cmdExecOut));
        if (*err < 0) {
                msiGetStderrInExecCmdOut(*cmdExecOut, *stderr);
                msiGetStdoutInExecCmdOut(*cmdExecOut, *stdout);
                writeLine("serverLog", "iiCopyMetadataToMoai: errorcode *err");
                writeLine("serverLog", *stderr);
                writeLine("serverLog", *stdout);
        } else {
                #*publicationState.oaiUploaded = "yes";
                #DEBUG writeLine("serverLog", "iiCopyTransformedPublicationToMOAI: pushed *");
        }
}
"""


def generate_combi_json(ctx, publication_config, publication_state):
    """Join system metadata with the user metadata in yoda-metadata.json.

    :param publication_config: Dict with publication cnfiguration
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


def generate_system_json(ctx, publication_config, publication_state):
    """Overwrite combi metadata json with system-only metadata.

    :param publication_config: Dict with publication cnfiguration
    :param publication_state:  Dict with state of the publication process
    """
    temp_coll = "/" + user.zone(ctx) + constants.IIPUBLICATIONCOLLECTION

    vaultPackage = publication_state["vaultPackage"]
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


def get_publication_state(ctx, vault_package):
    """The publication state is kept as metadata on the vault package.

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
    """
    Save the publication state key-value-pairs to AVU's on the vault package.

    :param vault_package:        Path to the package in the vault
    :param publication_state:    Dict with state of the publication process
    """
    org_publication_state = get_publication_state(ctx, vault_package)

    for key in publication_state.keys():
        if publication_state[key] == "":
            if key in org_publication_state:
                # Delete key / val from the vault_package based upon origin data
                avu.rm_from_coll(ctx, vault_package, key, org_publication_state[key])
        else:
            avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'publication_' + key, publication_state[key])


def set_update_publication_state(ctx, vault_package):
    """Routine to set publication state of vault package pending to update.

    :param vault_package: Path to the package in the vault
    """
    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    coll_status = vault.get_coll_vault_status(ctx, vault_package).value
    if coll_status not in [str(constants.vault_package_state.PUBLISHED), str(constants.vault_package_state.PENDING_DEPUBLICATION), str(constants.vault_package_state.PENDING_REPUBLICATION)]:
        return "NotAllowed"

    # HDR - wordt hier helemaal niet gebruikt
    # get publication configuration
    config = epic.get_publication_config(ctx)

    publication_state = get_publication_state(ctx, vault_package)
    if publication_state["status"] != "OK":
        return "PublicationNotOK"

    # Set publication status
    publication_state["status"] = "Unknown"

    # Generate new XML's
    publication_state["combiJsonPath"] = ""
    publication_state["dataCiteXmlPath"] = ""

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

    :param vault_package: Path to the package in the vault

    :return: Publication date in ISO8601 format
    """
    from datetime import datetime

    iter = genquery.row_iterator(
        "order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + vault_package + "' AND META_COLL_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'action_log' + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # row contains json encoded [str(int(time.time())), action, actor]
        log_item_list = jsonutil.parse(row[1])
        if log_item_list[1] == "published":
            publication_timestamp = datetime.datetime.fromtimestamp(int(log_item_list[0]))

            # ISO8601-fy
            return publication_timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f%z')

    my_date = datetime.now()
    return my_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z')


def get_last_modified_datetime(ctx, vault_package):
    """Determine the time of last modification as a datetime with UTC offset.

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

        import datetime
        my_date = datetime.datetime.fromtimestamp(int(log_item_list[0]))

        return my_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z')


def generate_preliminary_DOI(ctx, publication_config, publication_state):
    """Generate a Preliminary DOI. Preliminary, because we check for collision later.

    :param publication_config: Dict with publication cnfiguration
    :param publication_state:  Dict with state of the publication process
    """
    dataCitePrefix = publication_config["dataCitePrefix"]
    yodaPrefix = publication_config["yodaPrefix"]

    randomId = datacite.generate_random_id(ctx, publication_config["randomIdLength"])

    publication_state["randomId"] = randomId
    publication_state["yodaDOI"] = dataCitePrefix + "/" + yodaPrefix + "-" + randomId


def generate_datacite_xml(ctx, publication_config, publication_state):
    """Generate a DataCite compliant XML based up yoda-metadata.json."""
    combiJsonPath = publication_state["combiJsonPath"]

    randomId = publication_state["randomId"]

    vaultPackage = publication_state["vaultPackage"]

    temp_coll, coll = pathutil.chop(combiJsonPath)
    datacite_xml_path = temp_coll + "/" + randomId + "-dataCite.xml"

    # Based on content of *combiJsonPath, get DataciteXml as string
    receiveDataciteXml = json_datacite41.json_datacite41_create_data_cite_xml_on_json(ctx, combiJsonPath)

    data_object.write(ctx, datacite_xml_path, receiveDataciteXml)

    publication_state["dataCiteXmlPath"] = datacite_xml_path


def post_metadata_to_datacite(ctx, publication_config, publication_state):
    """Upload DataCite XML to DataCite. This will register the DOI, without minting it.

    :param publication_config: Dict with publication cnfiguration
    :param publication_state:  Dict with state of the publication process
    """
    datacite_xml_path = publication_state["dataCiteXmlPath"]
    # len = int(publication_state["dataCiteXmlLen"]) # HDR - deze is niet meer nodig ??

    datacite_xml = data_object.read(ctx, datacite_xml_path)

    httpCode = datacite.register_doi_metadata(ctx, publication_state["yodaDOI"], datacite_xml)

    if httpCode == 201:
        publication_state["dataCiteMetadataPosted"] = "yes"
    elif httpCode in [401, 403, 500, 503, 504]:
        # Unauthorized, Forbidden, Precondition failed, Internal Server Error
        log.write(ctx, "post_metadata_to_datacite: httpCode " + str(httpCode) + " received. Will be retried later")
        publication_state["status"] = "Retry"
    else:
        log.write(ctx, "post_metadata_to_datacite: httpCode " + str(httpCode) + " received. Unrecoverable error.")
        publication_state["status"] = "Unrecoverable"


def remove_metadata_from_datacite(ctx, publication_config, publication_state):
    """Remove metadata XML from DataCite."""
    yodaDOI = publication_state["yodaDOI"]

    httpCode = datacite.delete_doi_metadata(ctx, yodaDOI)

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


def mint_doi(ctx, publication_config, publication_state):
    """Announce the landing page URL for a DOI to dataCite. This will mint the DOI.

    :param publication_config: Dict with publication cnfiguration
    :param publication_state:  Dict with state of the publication process
    """
    yodaDOI = publication_state["yodaDOI"]
    landingPageUrl = publication_state["landingPageUrl"]

    httpCode = datacite.register_doi_url(ctx, yodaDOI, landingPageUrl)

    if httpCode == 201:
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

    :param publication_config: Dict with publication cnfiguration
    :param publication_state:  Dict with state of the publication process

    :return: Landing page URL
    """
    vaultPackage = publication_state["vaultPackage"]
    yodaDOI = publication_state["yodaDOI"]
    publicVHost = publication_config["publicVHost"]
    yodaInstance = publication_config["yodaInstance"]
    yodaPrefix = publication_config["yodaPrefix"]
    randomId = publication_state["randomId"]
    publicPath = yodaInstance + "/" + yodaPrefix + "/" + randomId + ".html"
    landingPageUrl = "https://" + publicVHost + "/" + publicPath

    publication_state["landingPageUrl"] = landingPageUrl


def generate_landing_page(ctx, publication_config, publication_state, publish):
    """Generate a dataCite compliant XML based up yoda-metadata.json.

    :param publication_config: Dict with publication cnfiguration
    :param publication_state:  Dict with state of the publication process
    :param publish:            Publication or depublication
    """
    combiJsonPath = publication_state["combiJsonPath"]
    randomId = publication_state["randomId"]
    vaultPackage = publication_state["vaultPackage"]

    temp_coll, coll = pathutil.chop(combiJsonPath)
    landing_page_path = temp_coll + "/" + randomId + ".html"

    if publish == "publish":
        template_name = 'landingpage.html.j2'
    else:
        template_name = 'emptylandingpage.html.j2'

    landing_page_html = json_landing_page.json_landing_page_create_json_landing_page(ctx, user.zone(ctx), template_name, combiJsonPath)

    data_object.write(ctx, landing_page_path, landing_page_html)

    publication_state["landingPagePath"] = landing_page_path


def copy_landingpage_to_public_host(ctx, publication_config, publication_state):
    """Copy the resulting landing page to configured public host.

    :param publication_config: Dict with publication cnfiguration
    :param publication_state:  Dict with state of the publication process
    """
    publicHost = publication_config["publicHost"]
    landingPagePath = publication_state["landingPagePath"]
    yodaInstance = publication_config["yodaInstance"]
    yodaPrefix = publication_config["yodaPrefix"]
    randomId = publication_state["randomId"]
    publicPath = yodaInstance + "/" + yodaPrefix + "/" + randomId + ".html"

    argv = publicHost + " inbox /var/www/landingpages/" + publicPath

    error = 0
    ctx.iiGenericSecureCopy(argv, landingPagePath, error)
    if error >= 0:
        publication_state["landingPageUploaded"] = "yes"
    else:
        publication_state["status"] = "Retry"
        log.write(ctx, "copy_landingpage_to_public: " + str(error))


def copy_metadata_to_moai(ctx, publication_config, publication_state):
    """Copy the metadata json file to configured MOAI.

    :param publication_config: Dict with publication cnfiguration
    :param publication_state:  Dict with state of the publication process
    """
    publicHost = publication_config["publicHost"]
    yodaInstance = publication_config["yodaInstance"]
    yodaPrefix = publication_config["yodaPrefix"]
    randomId = publication_state["randomId"]
    combiJsonPath = publication_state["combiJsonPath"]

    argv = publicHost + " inbox /var/www/moai/metadata/" + yodaInstance + "/" + yodaPrefix + "/" + randomId + ".json"
    error = 0
    ctx.iiGenericSecureCopy(argv, combiJsonPath, error)
    if error >= 0:
        publication_state["oaiUploaded"] = "yes"
    else:
        publication_state["status"] = "Retry"
        log.write(ctx, "copy_metadata_to_public: " + error)


def set_access_restrictions(ctx, vault_package, publication_state):
    """Set access restriction for vault package.

    :param vault_package:      Path to the package in the vault
    :param publication_state:  Dict with state of the publication process
    """
    access_restriction = publication_state["accessRestriction"]
    access_level = "null"

    if access_restriction.startswith('Open'):
        access_level = "read"

        try:
            msi.set_acl(ctx, "recursive", access_level, "anonymous", vault_package)
        except msi.Error as e:
            publication_state["status"] = "Unrecoverable"
            return
    # We cannot set "null" as value in a kvp as this will crash msi_json_objops if we ever perform a uuKvp2JSON on it.
    if access_level == "null":
        publication_state["anonymousAccess"] = "no"
    else:
        publication_state["anonymousAccess"] = "yes"


def check_doi_availability(ctx, publication_config, publication_state):
    """Request DOI to check on availibity. We want a 404 as return code.

    :param publication_config: Dict with publication cnfiguration
    :param publication_state:  Dict with state of the publication process
    """
    yodaDOI = publication_state["yodaDOI"]

    httpCode = datacite.check_doi_availability(ctx, yodaDOI)

    if httpCode == 404:
        publication_state["DOIAvailable"] = "yes"
    elif httpCode in [401, 403, 500, 503, 504]:
        # request failed, worth a retry
        publication_state["status"] = "Retry"
    elif httpCode in [200, 204]:
        # DOI already in use
        publication_state["DOIAvailable"] = "no"
        publication_state["status"] = "Retry"


@rule.make(inputs=range(1), outputs=range(1, 3))
def rule_process_publication(ctx, vault_package):
    """Rule interface for processing vault status transition request.

    :param vault_package: Path to the package in the vault

    :return: "OK" if all went ok
    """
    return process_publication(ctx, vault_package)


def process_publication(ctx, vault_package):
    """Handling of publication of vault_package."""
    publication_state = {}

    log.write(ctx, "process_publication: Process vault package <{}>".format(vault_package))

    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    vault_status = vault.get_coll_vault_status(ctx, vault_package).value

    if vault_status not in [str(constants.vault_package_state.PUBLISHED), str(constants.vault_package_state.APPROVED_FOR_PUBLICATION)]:
        return "InvalidPackageStatusForPublication" + ": " + vault_status

    # get publication configuration
    publication_config = epic.get_publication_config(ctx)

    # get state of all related to the publication
    publication_state = get_publication_state(ctx, vault_package)
    status = publication_state['status']

    # Publication status check and handling
    if status in ["Unrecoverable"]:  # , "Processing"]: DEZE MOET ER WEER BIJ HDR!!!!
        return "publication status: " + status
    elif status in ["Unknown", "Retry"]:
        status = "Processing"
        publication_state['status'] = status

    # Publication date
    if "publicationDate" not in publication_state:
        publication_state["publicationDate"] = get_publication_date(ctx, vault_package)

    # DOI handling
    if "yodaDOI" not in publication_state:
        generate_preliminary_DOI(ctx, publication_config, publication_state)
        save_publication_state(ctx, vault_package, publication_state)
    elif "DOIAvailable" in publication_state:
        if publication_state["DOIAvailable"] == "no":
            generate_preliminary_DOI(ctx, publication_config, publication_state)
            publication_state["combiJsonPath"] = ""
            publication_state["dataCiteXmlPath"] = ""
            save_publication_state(ctx, vault_package, publication_state)

    # Determine last modification time. Always run, no matter if retry
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime(ctx, vault_package)

    # Generate Combi Json consisting of user and system metadata
    if "combiJsonPath" not in publication_state:
        try:
            generate_combi_json(ctx, publication_config, publication_state)
        except msi.Error as e:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Generate DataCite XML
    if "dataCiteXmlPath" not in publication_state:
        try:
            generate_datacite_xml(ctx, publication_config, publication_state)
        except msi.Error as e:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Check if DOI is in use
    if "DOIAvailable" not in publication_state:
        try:
            check_doi_availability(ctx, publication_config, publication_state)
        except msi.Error as e:
            publication_state["status"] = "Retry"

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Send DataCite XML to metadata end point
    if "dataCiteMetadataPosted" not in publication_state:
        try:
            post_metadata_to_datacite(ctx, publication_config, publication_state)
        except msi.Error as e:
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Create landing page
    if "landingPagePath" not in publication_state:
        # Create landing page
        try:
            generate_landing_page(ctx, publication_config, publication_state, "publish")
        except msi.Error as e:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Unrecoverable":
            return publication_state["status"]

    # Create Landing page URL
    generate_landing_page_url(ctx, publication_config, publication_state)

    # Use secure copy to push landing page to the public host
    if "landingPageUploaded" not in publication_state:
        copy_landingpage_to_public_host(ctx, publication_config, publication_state)
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Use secure copy to push combi XML to MOAI server
    if "oaiUploaded" not in publication_state:
        copy_metadata_to_moai(ctx, publication_config, publication_state)
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Set access restriction for vault package.
    if "anonymousAccess" not in publication_state:
        set_access_restrictions(ctx, vault_package, publication_state)
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Mint DOI with landing page URL.
    if "DOIMinted" not in publication_state:
        mint_doi(ctx, publication_config, publication_state)
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

        # The publication was a success
        publication_state["status"] = "OK"
        save_publication_state(ctx, vault_package, publication_state)

        avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'vault_status', constants.vault_package_state.PUBLISHED)

        # MAIL datamanager and researcher involved
        title = ""
        title_key = constants.UUUSERMETADATAPREFIX + "0_Title"
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "COLL_NAME = '" + vault_package + "' AND META_COLL_ATTR_NAME = '" + title_key + "'",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            title = row[0]

        datamanager = ""
        datamanager_key = constants.UUORGMETADATAPREFIX + "publication_approval_actor"
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "COLL_NAME = '" + vault_package + "' AND META_COLL_ATTR_NAME = '" + datamanager_key + "'",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            user_name_and_zone = row[0]
            datamanager = user.from_str(ctx, user_name_and_zone)[0]

        researcher_key = constants.UUORGMETADATAPREFIX + "publication_submission_actor"
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "COLL_NAME = '" + vault_package + "' AND META_COLL_ATTR_NAME = '" + researcher_key + "'",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            user_name_and_zone = row[0]
            researcher = user.from_str(ctx, user_name_and_zone)[0]

        doi = publication_state["yodaDOI"]

        sender = user.full_name(ctx)

        # Send datamanager publication notification.
        # HOe hier error af te vangen???
        mail.mail_new_package_published(ctx, datamanager, sender, title, doi)

        # Send researcher publication notification.
        mail.mail_your_package_published(ctx, researcher, sender, title, doi)
    else:
        # The publication was a success
        publication_state["status"] = "OK"
        save_publication_state(ctx, vault_package, publication_state)
        provenance.log_action(ctx, "system", vault_package, "publication updated")

        return publication_state["status"]


@rule.make(inputs=range(1), outputs=range(1, 3))
def rule_process_depublication(ctx, vault_package):
    """Rule interface for processing depublication of a vault package.

    :param vault_package: Path to the package in the vault

    :return: "OK" if all went ok
    """
    return process_depublication(ctx, vault_package)


def process_depublication(ctx, vault_package):
    status = "Unknown"

    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    vault_status = vault.get_coll_vault_status(ctx, vault_package).value
    if vault_status not in [str(constants.vault_package_state.PENDING_DEPUBLICATION)]:
        return "InvalidPackageStatusForPublication" + ": " + vault_status

    # get publication configuration
    publication_config = epic.get_publication_config(ctx)

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

    # Determine last modification time. Always run, no matter if retry
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime(ctx, vault_package)

    # Generate Combi Json consisting of user and system metadata
    if "combiJsonPath" not in publication_state:
        try:
            generate_system_json(ctx, publication_config, publication_state)
        except msi.Error as e:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Remove metadata from DataCite
    if "dataCiteMetadataPosted" not in publication_state:
        try:
            remove_metadata_from_datacite(ctx, publication_config, publication_state)
        except msi.Error as e:
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Create landing page
    if "landingPagePath" not in publication_state:
        # Create landing page
        try:
            generate_landing_page(ctx, publication_config, publication_state, "depublish")
        except msi.Error as e:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Unrecoverable":
            return publication_state["status"]

    # Use secure copy to push landing page to the public host
    if "landingPageUploaded" not in publication_state:
        copy_landingpage_to_public_host(ctx, publication_config, publication_state)
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Use secure copy to push combi XML to MOAI server
    if "oaiUploaded" not in publication_state:
        copy_metadata_to_moai(ctx, publication_config, publication_state)
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
    # rule_provenance_log_action("system", *vaultPackage, "publication updated") ?????

    return publication_state["status"]


@rule.make(inputs=range(1), outputs=range(1, 3))
def rule_process_republication(ctx, vault_package):
    """Rule interface for processing republication of a vault package.

    :param vault_package: Path to the package in the vault

    :return: "OK" if all went ok
    """
    return process_republication(ctx, vault_package)


def process_republication(ctx, vault_package):
    """Routine to process a republication with sanity checks at every step."""
    publication_state = {}

    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    vault_status = vault.get_coll_vault_status(ctx, vault_package).value
    if vault_status not in [str(constants.vault_package_state.PENDING_REPUBLICATION)]:
        return "InvalidPackageStatusForRePublication" + ": " + vault_status

    publication_config = epic.get_publication_config(ctx)

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

    # Publication date
    if "publicationDate" not in publication_state:
        publication_state["publicationDate"] = get_publication_date(ctx, vault_package)

    # Determine last modification time. Always run, no matter if retry
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime(ctx, vault_package)

    # Generate Combi Json consisting of user and system metadata
    if "combiJsonPath" not in publication_state:
        try:
            generate_combi_json(ctx, publication_config, publication_state)
        except msi.Error as e:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Generate DataCite XML
    if "dataCiteXmlPath" not in publication_state:
        try:
            generate_datacite_xml(ctx, publication_config, publication_state)
        except msi.Error as e:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Send DataCite XML to metadata end point
    if "dataCiteMetadataPosted" not in publication_state:
        try:
            post_metadata_to_datacite(ctx, publication_config, publication_state)
        except msi.Error as e:
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Create landing page
    if "landingPagePath" not in publication_state:
        # Create landing page
        try:
            generate_landing_page(ctx, publication_config, publication_state, "publish")
        except msi.Error as e:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Unrecoverable":
            return publication_state["status"]

    # Use secure copy to push landing page to the public host
    if "landingPageUploaded" not in publication_state:
        copy_landingpage_to_public_host(ctx, publication_config, publication_state)
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Use secure copy to push combi XML to MOAI server
    if "oaiUploaded" not in publication_state:
        copy_metadata_to_moai(ctx, publication_config, publication_state)
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

    return publication_state["status"]


def get_collection_metadata(ctx, coll, prefix):
    """Retrieve all collection metadata.

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
