# -*- coding: utf-8 -*-
"""Functions to publish dat0t and manage permissions of vault packages."""

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
    """
    Join system metadata with the user metadata in yoda-metadata.json.

    publication_config      Configuration is passed as key-value-pairs throughout publication process
    publication_state       The state of the publication process is also kept in a key-value-pairs
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
    """
    Overwrite combi metadata json with system-only metadata.

    publication_config  Configuration is passed as key-value-pairs throughout publication process
    publication_state   The state of the publication process is also kept in a key-value-pairs
    """

    temp_coll = "/" + user.zone(ctx) + constants.IIPUBLICATIONCOLLECTION

    vaultPackage = publication_state["vaultPackage"]
    randomId = publication_state["randomId"]
    system_json_path = temp_coll + "/" + randomId + "-combi.json"

    system_json_data = {"System": 
        {"Last_Modified_Date": publication_state["lastModifiedDateTime"],
         "Persistent_Identifier_Datapackage": 
             {
                "Identifier_Scheme": "DOI",
                "Identifier": publication_state["yodaDOI"],
             },
         "Publication_Date": publication_state["publicationDate"]
        }
    }

    data_object.write(ctx, system_json_path, jsonutil.dump(system_json_data))


def get_publication_state(ctx, vault_package):
    """
        The publication state is kept as metadata on the vaultPackage.

        vault_package               path to the package in the vault

        returns publication_state   key-value-pair containing the state
    """
    publication_state = {"status": "Unknown",
                         "accessRestriction": "Closed"
                        }
    publ_metadata = get_collection_metadata(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'publication_')
    log.write(ctx, publ_metadata)

    # take over all actual values as saved earlier
    for key in publ_metadata.keys():
        publication_state[key] = publ_metadata[key]

    # Handle access restriction
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME like '%Data_Access_Restriction' AND COLL_NAME = '" + vault_package + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        publication_state["accessRestriction"] = row[0]

    # Handle license
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
    Save the publicationState key-value-pair to AVU's on the vaultPackage.

    param vault_package        path to the package in the vault
    param publication_state    dict containing all key/values regarding publication
    """
    for key in publication_state.keys():
        # publication_state[key] = publ_metadata[key]
        avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'publication_' + key, publication_state[key])


def set_update_publication_state(ctx, vault_package, status):
    """
    Routine to set publication state of vault package pending to update.

    vaultPackage   path to package in the vault to update
    returns status         status of the publication state update
    """
    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    coll_status = get_coll_vault_status(ctx, coll).value
    if coll_status not in [str(constants.vault_package_state.PUBLISHED), str(constants.vault_package_state.DEPUBLICATION), str(constants.vault_package_state.REPUBLICATION)]:
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
    if not save_publication_state(ctx, vault_package, publication_state):
        return "UnknownError"


def get_publication_date(ctx, vault_package):
    """
    Determine the time of publication as a datetime with UTC offset.
    First try action_log. Then icat-time

    param[in] vault_package
    return publicationdate in iso8601 format
    """
    from datetime import datetime
    my_date = datetime.now()
    return my_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z')

    iter = genquery.row_iterator(
        "order_desc(META_COLL_ATTR_VALUE)",
        "COLL_NAME = '" + vault_package + "' AND META_COLL_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'action_log' + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        # row contains json encoded [str(int(time.time())), action, actor]
        log_item_list = jsonutil.parse(row[0])
        if log_item_list[1] == "published":
            publication_timestamp = log_item_list[0]

            # HIer nog ISO8601 van maken!!
            return publicationDateTime
    # HdR not netjes!!!!
    from datetime import datetime
    my_date = datetime.now()
    return my_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z')


def get_last_modified_datetime(ctx, vault_package):
    """
    Determine the time of last modification as a datetime with UTC offset.
    param[in] vault_package
    returns last modification datetime in iso8601 format
    """
    iter = genquery.row_iterator(
        "order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + vault_package + "' AND META_COLL_ATTR_NAME = '" + constants.UUORGMETADATAPREFIX + 'action_log' + "'",
        genquery.AS_LIST, ctx
    )
    for row in iter:
        log_item_list = jsonutil.parse(row[1])
        log.write(ctx, log_item_list)

        import datetime
        my_date = datetime.datetime.fromtimestamp(int(log_item_list[0]))
        return my_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z')

        # return log_item_list[0]


def generate_preliminary_DOI(ctx, publication_config, publication_state):
    """
    Generate a Preliminary DOI. Preliminary, because we check for collision later.

    param publication_config      Configuration is passed as key-value-pairs throughout publication process
    param publication_state
    """
    dataCitePrefix = publication_config["dataCitePrefix"]
    yodaPrefix = publication_config["yodaPrefix"]

    randomId = datacite.generate_random_id(ctx, publication_config["randomIdLength"])

    publication_state["randomId"] = randomId
    publication_state["yodaDOI"] = dataCitePrefix + "/" + yodaPrefix + "-" + randomId


def generate_datacite_xml(ctx, publication_config, publication_state):
    """ Generate a dataCite compliant XML based up yoda-metadata.json """
    combiJsonPath = publication_state["combiJsonPath"]

    randomId = publication_state["randomId"]

    vaultPackage = publication_state["vaultPackage"]

    temp_coll, coll = pathutil.chop(combiJsonPath)
    datacite_xml_path = temp_coll + "/" + randomId + "-dataCite.xml"

    # Based on content of *combiJsonPath, get DataciteXml as string
    receiveDataciteXml = json_datacite41_create_data_cite_xml_on_json(ctx, combiJsonPath)

    data_object.write(ctx, datacite_xml_path, receiveDataciteXml)

    publication_state["dataCiteXmlPath"] = datacite_xml_path
    # publication_state["dataCiteXmlLen"] = str(len)   ###J NIET MEER NODIG!!??


def post_metadata_to_datacite(ctx, publication_config, publication_state):
    """ Upload dataCite XML to dataCite. This will register the DOI, without minting it.

    \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
    \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
    """

    datacite_xml_path = publication_state["dataCiteXmlPath"]
    # len = int(publication_state["dataCiteXmlLen"]) # HDR - deze is niet meer nodig ??

    datacite_xml = data_object.read(ctx, datacite_xml_path)
    log.write(ctx, datacite_xml)

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
    """ Remove metadata XML from DataCite. """

    yodaDOI = publication_state["yodaDOI"]

    httpCode = datacite.delete_doi_metadata(ctx, yodaDOI)

    if httpCode == 200:
        publication_state["dataCiteMetadataPosted"] = "yes"
    elif httpCode in [401, 403, 412, 500, 503, 504]:
        # Unauthorized, Forbidden, Precondition failed, Internal Server Error
        log.write(ctx, "remove metadata from datacite: httpCode " + str(httpCode) + " received. Will be retried later")        publication_state["status"] = "Retry"
    elif httpCode == 404:
        # Invalid DOI
        log.write(ctx, "remove metadata from datacite: 404 Not Found - Invalid DOI")
        publication_state["status"] = "Unrecoverable"
    else:
        log.write(ctx, "remove metadata from datacite: httpCode " + str(httpCode) + " received. Unrecoverable error.")
        publication_state["status"] = "Unrecoverable"


def mint_doi(ctx, publication_config, publication_state):
    """
    Announce the landing page URL for a DOI to dataCite. This will mint the DOI.

    publication_config      Configuration is passed as key-value-pairs throughout publication process
    publication_state       The state of the publication process is also kept in a key-value-pairs
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
    """
    Generate a URL for the landing page.

    param[in] publication_config      Configuration is passed as key-value-pairs throughout publication process
    param[in,out] publication_state   The state of the publication process is also kept in a key-value-pairs

    returns landing page url
    """
    vaultPackage = publication_state["vaultPackage"]
    yodaDOI = publication_state["yodaDOI"]
    publicVHost = publication_config["publicVHost"]
    yodaInstance = publication_config["yodaInstance"]
    yodaPrefix = publication_config["yodaPrefix"]
    randomId = publication_state["randomId"]
    publicPath = yodaInstance + "/" + yodaPrefix + "/" + randomId + ".html"
    landingPageUrl = "https://" + publicVHost + "/" + publicPath

    return landingPageUrl


def generate_landing_page(ctx, publication_config, publication_state, publish):
    """
    Generate a dataCite compliant XML based up yoda-metadata.json
    publication_config      Configuration is passed as key-value-pairs throughout publication process
    publication_state       The state of the publication process is passed around as key-value-pairs
    publish                 publication or depublication
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

    # landing_page_html = rule_json_landing_page_create_json_landing_page(user.zone(ctx), template_name, combiJsonPath)
    landing_page_html = json_landing_page.json_landing_page_create_json_landing_page(ctx, user.zone(ctx), template_name, combiJsonPath)

    log.write(ctx, landing_page_html)

    data_object.write(ctx, landing_page_path, landing_page_html)

    publication_state["landingPagePath"] = landing_page_path


def generate_datacite_xml(ctx, publication_config, publication_state):
    """ Generate a dataCite compliant XML based up yoda-metadata.json """

    combiJsonPath = publication_state["combiJsonPath"]

    randomId = publication_state["randomId"]

    vaultPackage = publication_state["vaultPackage"]

    temp_coll, coll = pathutil.chop(combiJsonPath)
    datacite_xml_path = temp_coll + "/" + randomId + "-dataCite.xml"

    # Based on content of *combiJsonPath, get DataciteXml as string
    receiveDataciteXml = json_datacite41.json_datacite41_create_data_cite_xml_on_json(ctx, combiJsonPath)

    data_object.write(ctx, datacite_xml_path, receiveDataciteXml)

    publication_state["dataCiteXmlPath"] = datacite_xml_path


def copy_landingpage_to_public_host(ctx, publication_config, publication_state):
    """
    Copy the resulting landing page to configured public host
    publication_config   Current configuration
    publication_state    Current publication state
    """
    publicHost = publication_config["publicHost"]
    landingPagePath = publication_state["landingPagePath"]
    yodaInstance = publication_config["yodaInstance"]
    yodaPrefix = publication_config["yodaPrefix"]
    randomId = publication_state["randomId"]
    publicPath = yodaInstance + "/" + yodaPrefix + "/" + randomId + ".html"

    argv = publicHost + " " + inbox + " /var/www/landingpages/" + publicPath
    error = ""
    error_message = ""
    ctx.iiGenericSecureCopy(argv, landingPagePath, error, error_message)
    if error == "":
        publication_state["landingPageUploaded"] = "yes"
    else:
        publication_state["status"] = "Retry"
        log.write(ctx, "copy_landingpage_to_public: " + error)
        log.write(ctx, "copy_landingpage_to_public: " + error_message


def copy_metadata_to_moai(ctx, publication_config, publication_state):
    """
    Copy the metadata json file to configured moai
    publication_config   Current configuration
    publication_state    Current publication state
    """
    publicHost = publication_config["publicHost"]
    yodaInstance = publication_config["yodaInstance"]
    yodaPrefix = publication_config["yodaPrefix"]
    randomId =  publication_state["randomId"]
    combiJsonPath = publication_state["combiJsonPath"]

    argv = publicHost + " " + inbox + " /var/www/moai/metadata/" + yodaInstance + "/" + yodaPrefix + "/" + randomId + ".json"
    error = ""
    error_message = ""
    ctx.iiGenericSecureCopy(argv, combiJsonPath, error, error_message)
    if error == "":
        publication_state["oaiUploaded"] = "yes"
    else:
        publication_state["status"] = "Retry"
        log.write(ctx, "copy_metadata_to_public: " + error)
        log.write(ctx, "copy_metadata_to_public: " + error_message)


def set_access_restrictions(ctx, vault_package, publication_state):
    """
    Set access restriction for vault package.

    vaultPackage       Path to the package in the vault
    publicationState   The state of the publication process is also kept in a key-value-pairs
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
    """
    Request DOI to check on availibity. We want a 404 as return code.

    publicationConfig      Configuration is passed as key-value-pairs throughout publication process
    publicationState       The state of the publication process is also kept in a key-value-pair
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
    """ rule interface for processing vault status transition request

    param[in]  vault package

    return [status, statusInfo] "Success" if went ok

    """
    log.write(ctx, "vault_package")
    # return 'Success VPackage=' + vault_package

    return process_publication(ctx, vault_package)


def process_publication(ctx, vault_package):
    publication_state = {}

    log.write(ctx, "PUBLICATION OF " + vault_package)

    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    vault_status = vault.get_coll_vault_status(ctx, vault_package).value
    log.write(ctx, "CURRENT COLL STATUS: " + vault_status)

    if vault_status not in [str(constants.vault_package_state.PUBLISHED), str(constants.vault_package_state.APPROVED_FOR_PUBLICATION)]:
        return "InvalidPackageStatusForPublication" + ": " + vault_status

    # get publication configuration
    publication_config = epic.get_publication_config(ctx)
    log.write(ctx, publication_config)

    # get state of all related to the publication
    publication_state = get_publication_state(ctx, vault_package)
    status = publication_state['status']

    log.write(ctx, status)

    log.write(ctx, "SO FAR, SO GOOD")
    #return "SO FAR, SO GOOD"

    # Publication status check and handling
    if status in ["Unrecoverable"]:  # , "Processing"]: DEZE MOET ER WEER BIJ HDR
        return "publication status: " + status
    elif status in ["Unknown", "Retry"]:
        status = "Processing"
        publication_state['status'] = status # Deze wordt pas bewaard wanneer specifieke keys niet bestaan verderop.

    # Publication date
    if "publicationDate" not in publication_state:
        publication_state["publicationDate"] = get_publication_date(ctx, vault_package)

    log.write(ctx, "SO FAR, SO GOOD2")
#    return "SO FAR, SO GOOD2 " + publication_state["publicationDate"]

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

    log.write(ctx, "SO FAR, SO GOOD3")
    log.write(ctx, publication_state)
#    return "SO FAR, SO GOOD3 " + publication_state["yodaDOI"]

    # Determine last modification time. Always run, no matter if retry
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime(ctx, vault_package)

    log.write(ctx, "SO FAR, SO GOOD4")
    log.write(ctx, publication_state)
    # return "SO FAR, SO GOOD4 " + publication_state["lastModifiedDateTime"]

    # Generate Combi Json consisting of user and system metadata
    if "combiJsonPath" not in publication_state:
        try:
            generate_combi_json(ctx, publication_config, publication_state)
        except msi.Error as e:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    log.write(ctx, "SO FAR, SO GOOD5")
    log.write(ctx, publication_state)
#    return "SO FAR, SO GOOD5 "

    # Generate DataCite XML
    if "dataCiteXmlPath" not in publication_state:
        try:
            generate_datacite_xml(ctx, publication_config, publication_state)
        except msi.Error as e:
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    log.write(ctx, "SO FAR, SO GOOD6")
    log.write(ctx, publication_state)
#    return "SO FAR, SO GOOD6 "

    # Check if DOI is in use
    if "DOIAvailable" not in publication_state:
        try:
            check_doi_availability(ctx, publication_config, publication_state)
        except msi.Error as e:
            publication_state["status"] = "Retry"

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    log.write(ctx, "SO FAR, SO GOOD7")
    log.write(ctx, publication_state)
#    return "SO FAR, SO GOOD7 "

    # Send DataCite XML to metadata end point
    if "dataCiteMetadataPosted" not in publication_state:
        try:
            post_metadata_to_datacite(ctx, publication_config, publication_state)
        except msi.Error as e:
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    log.write(ctx, "SO FAR, SO GOOD8")
    log.write(ctx, publication_state)
    # return "SO FAR, SO GOOD8 "

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

    log.write(ctx, "SO FAR, SO GOOD9")
    log.write(ctx, publication_state)
    return "SO FAR, SO GOOD9"

    # Create Landing page URL
        #DEBUG writeLine("serverLog", "iiProcessPublication: starting iiGenerateLandingPageUrl");
    generate_landing_page_url(ctx, publication_config, publication_state)

    log.write(ctx, "SO FAR, SO GOOD10")
    log.write(ctx, publication_state)
    return "SO FAR, SO GOOD10"

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
        title_key = UUUSERMETADATAPREFIX ++ "0_Title"
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "COLL_NAME = '" + vault_package + "' AND META_COLL_ATTR_NAME = '" + title_key + "'",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            title = row[0]

        datamanager = ""
        datamanager_key = UUORGMETADATAPREFIX ++ "publication_approval_actor"
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "COLL_NAME = '" + vault_package + "' AND META_COLL_ATTR_NAME = '" + datamanager_key + "'",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            user_name_and_zone = row[0]
            datamanager = user.user_and_zone(user_name_and_zone)[0]

        researcher_key = UUORGMETADATAPREFIX ++ "publication_submission_actor"
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "COLL_NAME = '" + vault_package + "' AND META_COLL_ATTR_NAME = '" + datamanager_key + "'",
            genquery.AS_LIST, ctx
        )
        for row in iter:
            user_name_and_zone = row[0]
            researcher = user.user_and_zone(user_name_and_zone)[0]

        doi = publication_state["yodaDOI"]

        sender = user.full_name(ctx)

        # Send datamanager publication notification.
        # HOe hier error af te vangen???
        mail.mail_new_package_published(ctx, datamanager, sender, title, doi)
        # Datamanager notification failed: *message

        # Send researcher publication notification.
        mail.mail_your_package_published(ctx, researcher, sender, title, doi)
        # "iiProcessPublication: Researcher notification failed: *message"
    else:
        # The publication was a success
        publication_state["status"] = "OK"
        save_publication_state(ctx, vault_package, publication_state)
        provenance.log_action("system", vault_package, "publication updated")

        return publication_state["status"]


@rule.make(inputs=range(1), outputs=range(1, 3))
def rule_process_depublication(ctx, vault_package):
    """ rule interface for processing vault status transition request

    param[in]  vault package

    return [status, statusInfo] "Success" if went ok

    """
    log.write(ctx, "vault_package")
    # return 'Success VPackage=' + vault_package

    return process_depublication(ctx, vault_package)


def process_depublication(ctx, vault_package):
    status = "Unknown"

    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    current_coll_status = get_coll_vault_status(ctx, coll).value
    if current_coll_status is not PENDING_DEPUBLICATION:
        return "NotAllowed"

    # check current status, perhaps transitioned already
    vault_status = vault.get_coll_vault_status(ctx, vault_package).value
    log.write(ctx, "CURRENT COLL STATUS: " + vault_status)

    if vault_status not in [str(constants.vault_package_state.PENDING_DEPUBLICATION)]:
        return "InvalidPackageStatusForPublication" + ": " + vault_status

    # get publication configuration
    publication_config = epic.get_publication_config(ctx)
    log.write(ctx, publication_config)

    # get state of all related to the publication
    publication_state = get_publication_state(ctx, vault_package)
    status = publication_state['status']

    if status == "OK":
        # reset on first call
        set_update_publication_state(ctx, vault_package)
        publication_state = get_publication_state(ctx, vault_package)
        status = publication_state['status']

    if status in ["Unrecoverable", "Processing"]:
        return ""
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
        if not iiRemoveMetadataFromDataCite(*publicationConfig, *publicationState):
            publication_state["status"] = "Retry"
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
    """ rule interface for processing vault status transition request

    param[in]  vault package

    return [status, statusInfo] "Success" if went ok

    """
    log.write(ctx, "vault_package")
    # return 'Success VPackage=' + vault_package

    return process_republication(ctx, vault_package)


def process_republication(ctx, vault_package):
    """ Routine to process a republication with sanity checks at every step. """

    publication_state = {}

    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    vault_status = vault.get_coll_vault_status(ctx, vault_package).value
    log.write(ctx, "CURRENT COLL STATUS: " + vault_status)

    if vault_status not in [str(constants.vault_package_state.PENDING_REPUBLICATION)]:
        return "InvalidPackageStatusForREPublication" + ": " + vault_status

# HDR DIT NOG GOED MAKEN publication_config
    # get publication configuration
#    config = epic.get_publication_config(ctx)
#    return "Retry"

    publication_config = epic.get_publication_config(ctx)

    # get state of all related to the publication
    publication_state = get_publication_state(ctx, vault_package)
    status = publication_state['status']
    log.write(ctx, status)

    if status == "OK":
        # reset on first call
        set_update_publication_state(ctx, vault_package)
        publication_state = get_publication_state(ctx, vault_package)
        status = publication_state['status']

    if status in ["Unrecoverable", "Processing"]:
        return ""
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
    """
    return a dict with all requested (prefixed) attributes and strip off prefix for the key names.
    example key: org_publication_lastModifiedDateTime

    """
    coll_metadata = {}
    iter = genquery.row_iterator(
        "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + coll + "' AND META_COLL_ATTR_NAME like '" + prefix + "%'",
        genquery.AS_LIST, ctx
    )

    for row in iter:
        log.write(ctx, row[0][len(prefix):] + "=>" + row[1])
        coll_metadata[row[0][len(prefix):]] = row[1]

    return coll_metadata
