# -*- coding: utf-8 -*-
"""Functions to publish dat0t and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

epic.py 
datacite.py


"""
notes:
constants.vault_package_state.SUBMITTED_FOR_PUBLICATION
'org_publication_lastModifiedDateTime'"

    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "COLL_NAME = '%s' AND META_COLL_ATTR_NAME = 'org_publication_lastModifiedDateTime'" % (coll),
        genquery.AS_LIST, callback
    )

    for row in iter:


"""

def get_publication_state(ctx, vault_package):
    """
        The publication state is kept as metadata on the vaultPackage.

        vault_package               path to the package in the vault
        returns publication_state   key-value-pair containing the state
    """
    publication_state = {"status":"Unknown",
                         "accessRestriction":"Closed"
    }
    publ_metadata = get_collection_metadata(ctx, vault_package, UUORGMETADATAPREFIX + 'publication_')

    # take over all actual values as saved earlier
    for key in publ_metadata.keys():
        publication_state[key] = publ_metadata[key]

    # Handle access restriction
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME like '%Data_Access_Restriction' AND COLL_NAME = '" + vault_package + "'"
        genquery.AS_LIST, callback
    )
    for row in iter:
        publication_state["accessRestriction"] = row[0]

    # Handle license
    license = ""
    iter = genquery.row_iterator(
        "META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME like '%License' AND COLL_NAME = '" + vault_package + "'"
        genquery.AS_LIST, callback
    )
    for row in iter:
        license = row[0]

    if license != "":
        publication_state["license"] = license
        license_uri = ""
        iter = genquery.row_iterator(
            "META_COLL_ATTR_VALUE",
            "META_COLL_ATTR_NAME like '" + constants.UUORGMETADATAPREFIX + "license_uri" + "' AND COLL_NAME = '" + vault_package + "'"
            genquery.AS_LIST, callback
        )
        for row in iter:
            license_uri = row[0]

        if license_uri != "":
            publication_state["licenseUri" = license_uri

    publication_state['vaultPackage'] = vault_package
    return publication_state


def save_publication_state(ctx, vault_package, publication_state):
    """
    Save the publicationState key-value-pair to AVU's on the vaultPackage.

    param vault_package        path to the package in the vault
    param publication_state    dict containing all key/values regarding publication 

    """

    for key in publication_state.keys():
        publication_state[key] = publ_metadata[key]
        avu.set_on_coll(ctx, vault_package, UUORGMETADATAPREFIX + 'publication_' + key, publication_state[key])


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
    if coll_status not in [constants.vault_package_state.PUBLISHED, constants.vault_package_state.DEPUBLICATION,constants.vault_package_state.REPUBLICATION]:
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
    return my_date.strftime('%Y-%m-%dT%H:%M:%S.%f%z'))
#         if(*publicationState.publicationDate == "" ) {
#            msiGetIcatTime(*now, "unix");
#            *publicationDate = uuiso8601date(*now);

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

#	# iso8601 compliant datetime with UTC offset
#	*lastModifiedDateTime = timestrf(datetime(int(*lastModifiedTimestamp)), "%Y-%m-%dT%H:%M:%S%z");
#	*publicationState.lastModifiedDateTime = *lastModifiedDateTime;


def generate_preliminary_DOI(ctx, publication_config): 
    """
    Generate a Preliminary DOI. Preliminary, because we check for collision later.

    param publication_config      Configuration is passed as key-value-pairs throughout publication process
    
    """

    dataCitePrefix = publicationConfig.dataCitePrefix;
    yodaPrefix = publicationConfig.yodaPrefix;

    datacite.rule_generate_random_id(ctx, publication_config["randomIdLength"])

	# Genereate random ID for DOI.
	*randomId = "";
	rule_generate_random_id(*length, *randomId);

	*yodaDOI = "*dataCitePrefix/*yodaPrefix-*randomId";
	*publicationState.randomId = *randomId;
	*publicationState.yodaDOI = *yodaDOI;


##########################
def generate_datacite_xml(ctx, publication_config, publication_state)
# \brief Generate a dataCite compliant XML based up yoda-metadata.json
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is passed around as key-value-pairs
#
    combiJsonPath = publication_state["combiJsonPath"]

    randomId = publication_state["randomId"]

    vaultPackage = publication_state["vaultPackage"]
#####
#        uuChopPath(*combiJsonPath, *tempColl, *_);

    temp_coll, coll = pathutil.chop(combiJsonPath)
    datacite_xml_path = temp_coll + "/" + randomId + "-dataCite.xml";

    ## WAAR ZIJN DEZE ZAKEN VOOR NODIG
        *pathElems = split(*vaultPackage, "/");
        *rodsZone = elem(*pathElems, 0);
        *vaultGroup = elem(*pathElems, 2);
        uuGetBaseGroup(*vaultGroup, *baseGroup);
        uuGroupGetCategory(*baseGroup, *category, *subcategory);

    # Based on content of *combiJsonPath, get DataciteXml as string
    receiveDataciteXml = rule_json_datacite41_create_data_cite_xml_on_json(combiJsonPath)

#        msiDataObjCreate(*dataCiteXmlPath, "forceFlag=", *fd);
#        msiDataObjWrite(*fd, *receiveDataciteXml, *len);                       # Get length back
#        msiDataObjClose(*fd, *status);

    data_object.write(ctx, datacite_xml_path, receiveDataciteXml)   

 
    publication_state["dataCiteXmlPath"] = datacite_xml_path 
    publication_state["dataCiteXmlLen"] = str(len)   ###J NIET MEER NODIG!!??
        #DEBUG writeLine("serverLog", "iiGenerateDataCiteXml: Generated *dataCiteXmlPath");
}



########################
def post_metadata_to_datacite(ctx, publication_config, publication_state):
# \brief Upload dataCite XML to dataCite. This will register the DOI, without minting it.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs

    dataCiteXmlPath = publication_state["dataCiteXmlPath"]
    len = int(publication_state["dataCiteXmlLen"]) # HDR - deze is niet meer nodig ??
    
    datacite_xml = data_object.read(callback, datacite_xml_path)

    httpCode = rule_register_doi_metadata(publication_state["yodaDOI"], datacite_xml);

    if httpCode == "201":
        publication_state["dataCiteMetadataPosted"] = "yes"
    elif httpCode in ["401", "403", "500", "503", 504]:
        # Unauthorized, Forbidden, Precondition failed, Internal Server Error
         log.write(ctx, "post_metadata_to_datacite: httpCode " + httpCode + " received. Will be retried later")
        publication_state["status"] = "Retry"
    else:
        log.write(ctx, "post_metadata_to_datacite: httpCode " + httpCode + " received. Unrecoverable error.")
        publication_state["status"] = "Unrecoverable"

#############################
def remove_metadata_from_datacite(ctx, publication_config, publication_state):
# \brief Remove metadata XML from DataCite.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
    yodaDOI = publication_state["yodaDOI"]

    httpCode = rule_delete_doi_metadata(ctx, yodaDOI);

    if httpCode == "200":
        publication_state["dataCiteMetadataPosted"] = "yes"
    elif httpCode in ["401", "403", "412", "500", "503", 504]:
        # Unauthorized, Forbidden, Precondition failed, Internal Server Error
         log.write(ctx, "remove metadata from datacite: httpCode " + httpCode + " received. Will be retried later")
        publication_state["status"] = "Retry"
    elif httpCode == "404":
        # Invalid DOI
        log.write(ctx, "remove metadata from datacite: 404 Not Found - Invalid DOI")
        publication_state["status"] = "Unrecoverable"
    else:
        log.write(ctx, "remove metadata from datacite: httpCode " + httpCode + " received. Unrecoverable error.")
        publication_state["status"] = "Unrecoverable"


###############################
def mint_doi(ctx, publication_config, publication_state):
    """
    Announce the landing page URL for a DOI to dataCite. This will mint the DOI.

    publication_config      Configuration is passed as key-value-pairs throughout publication process
    publication_state       The state of the publication process is also kept in a key-value-pairs
    returns status of publication ???
    """
    yodaDOI = publication_state["yodaDOI"]
    landingPageUrl = publication_state["landingPageUrl"]

    httpCode = rule_register_doi_url(ctx, yodaDOI, landingPageUrl)

    if httpCode == "201":
        publication_state["DOIMinted"] = "yes"
    elif httpCode in ["401", "403", "412", "500", "503", 504]:
        # Unauthorized, Forbidden, Precondition failed, Internal Server Error
         log.write(ctx, "mint_doi: httpCode " + httpCode + " received. Could be retried later")
        publication_state["status"] = "Retry"
    elif httpCode == "400":
        log.write(ctx, "mint_doi: 400 Bad Request - request body must be exactly two lines: DOI and URL; wrong domain, wrong prefix")
        publication_state["status"] = "Unrecoverable" 
    else:
        log.write(ctx, "mint_doi: httpCode " + httpCode + " received. Unrecoverable error.")
        publication_state["status"] = "Unrecoverable"


###############################
def generate_landing_page_url(ctx, publication_config, publication_state)
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
    landingPageUrl = "https://" + publicVHost + "/" + publicPath"
    
    return landingPageUrl



###############################
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





###############################
def process_publication(ctx, vault_package):
    publication_state = {}

    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    current_coll_status = get_coll_vault_status(ctx, coll).value
    return "NotAllowed"

    # get publication configuration
    config = epic.get_publication_config(ctx)
    return "Retry"

    # get state of all related to the publication
    publication_state = get_publication_state(ctx, vault_package) 
    status = publication_state['status']

    if status in ["Unrecoverable", "Processing"]:
        return ""
    elif status in ["Unknown", "Retry"]:
        status = "Processing"
        publication_state['status'] = status

    if "publicationDate" not in publication_state:
        publication_state["publicationDate"] = get_publication_date(ctx)

    if "yodaDOI" not in publication_state:
        generate_preliminary_DOI(ctx, )
        save_publication_state(ctx, vault_package, publication_state)
    elif "DOIAvailable" in publication_state:
        if publication_state["DOIAvailable"] == "no"
            generate_preliminary_DOI(ctx, )
            publication_state["combiJsonPath"] = ""
            publication_state["dataCiteXmlPath"] = ""
            save_publication_state(ctx, vault_package, publication_state)

    # Determine last modification time. Always run, no matter if retry
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime(ctx)

    # Generate Combi Json consisting of user and system metadata
    if "combiJsonPath" not in publication_state: 

        if not iiGenerateCombiJson(*publicationConfig, *publicationState))
        
            publication_state["status"] = "Unrecoverable"
               
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Generate DataCite XML
    if "dataCiteXmlPath" not in publication_state:
        if not iiGenerateDataCiteXml(*publicationConfig, *publicationState))
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Check if DOI is in use
    if "DOIAvailable" not in publication_state:
        if not iiCheckDOIAvailability(*publicationConfig, *publicationState):
            publication_state["status"] = "Retry"
        # WAAROM HIER GEEN SAVE VAN STATE???

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Send DataCite XML to metadata end point
    if "dataCiteMetadataPosted" not in publication_state:
        if not iiPostMetadataToDataCite(*publicationConfig, *publicationState):
            publication_state["status"] = "Retry"
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Create landing page
    if "landingPagePath" not in publication_state:
        # Create landing page
        if not iiGenerateLandingPage(*publicationConfig, *publicationState, "publish"):
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Unrecoverable":
            return publication_state["status"]



    # Create Landing page URL
        #DEBUG writeLine("serverLog", "iiProcessPublication: starting iiGenerateLandingPageUrl");
    iiGenerateLandingPageUrl(*publicationConfig, *publicationState);



    # Use secure copy to push landing page to the public host
    if "landingPageUploaded" not in publication_state:

        if not iiCopyLandingPage2PublicHost(*publicationConfig, *publicationState):
             publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Use secure copy to push combi XML to MOAI server
    if "oaiUploaded" not in publication_state:
        if not iiCopyMetadataToMOAI(*publicationConfig, *publicationState):
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Set access restriction for vault package.
    if "anonymousAccess" not in publication_state:

        if not iiSetAccessRestriction(*vaultPackage, *publicationState):
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Mint DOI with landing page URL.
    if "DOIMinted" not in publication_state:
        if not iiMintDOI(*publicationConfig, *publicationState):
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

        # The publication was a success
        publication_state["status"] = "OK"
        save_publication_state(ctx, vault_package, publication_state)

        avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'vault_status', constants.vault_package_state.PUBLISHED)


        # Send datamanager publication notification.
        
        # Send researcher publication notification.

            """


                        msiString2KeyValPair(UUORGMETADATAPREFIX ++ "vault_status=" ++ PUBLISHED, *vaultStatusKvp);
                        msiSetKeyValuePairsToObj(*vaultStatusKvp, *vaultPackage, "-C");

                        # Retrieve package title for notifications.
                        *title = "";
                        *titleKey = UUUSERMETADATAPREFIX ++ "0_Title";
                        foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *vaultPackage AND META_COLL_ATTR_NAME = *titleKey) {
                                *title = *row.META_COLL_ATTR_VALUE;
                                break;
                        }

                        # Send datamanager publication notification.
                        *datamanager = "";
                        *actorKey = UUORGMETADATAPREFIX ++ "publication_approval_actor";
                        foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *vaultPackage AND META_COLL_ATTR_NAME = *actorKey) {
                                *userNameAndZone = *row.META_COLL_ATTR_VALUE;
                                uuGetUserAndZone(*userNameAndZone, *datamanager, *zone);
                                break;
                        }

                        *mailStatus = "";
                        *message = "";
                        rule_mail_new_package_published(*datamanager, uuClientFullName, *title, *publicationState.yodaDOI, *mailStatus, *message);
                        if (int(*mailStatus) != 0) {
                            writeLine("serverLog", "iiProcessPublication: Datamanager notification failed: *message");
                        }

                        # Send researcher publication notification.
                        *researcher = "";
                        *actorKey = UUORGMETADATAPREFIX ++ "publication_submission_actor";
                        foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = *vaultPackage AND META_COLL_ATTR_NAME = *actorKey) {
                                *userNameAndZone = *row.META_COLL_ATTR_VALUE;
                                uuGetUserAndZone(*userNameAndZone, *researcher, *zone);
                                break;
                        }

                        *mailStatus = "";
                        *message = "";
                        rule_mail_your_package_published(*researcher, uuClientFullName, *title, *publicationState.yodaDOI, *mailStatus, *message);
                        if (int(*mailStatus) != 0) {
                            writeLine("serverLog", "iiProcessPublication: Researcher notification failed: *message");
                        }

             """

    else:
        # The publication was a success
        publication_state["status"] = "OK"
        save_publication_state(ctx, vault_package, publication_state)
        rule_provenance_log_action("system", *vaultPackage, "publication updated")
        
        return publication_state["status"]


# returns status
def process_depublication(ctx, vault_package):
    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    current_coll_status = get_coll_vault_status(ctx, coll).value
    if current_coll_status is not PENDING_DEPUBLICATION:
        return "NotAllowed"

    # get publication configuration
    config = epic.get_publication_config(ctx)
    return "Retry"

    # get state of all related to the publication
    publication_state = get_publication_state(ctx, vault_package)
    status = publication_state['status']

    # Reset state on first call
    if status == "OK":
        set_update_publication_state(ctx, vault_package, status)
        publication_state = get_publication_state(ctx, vault_package)
        publication_state["accessRestriction"] = "Closed"

    if publication_state["status"] in ["Unrecoverable", "Processing"]:
        return ""
    elif publication_state["status"] in ["Unknown", "Retry"]:
        status = "Processing"
        publication_state = status

    # Determine last modification time. Always run, no matter if retry
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime()


    # Generate Combi Json consisting of user and system metadata
    if "combiJsonPath" not in publication_state: 

        if not iiGenerateSystemJson(*publicationConfig, *publicationState)) 
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


    # Create landing page
    if "landingPagePath" not in publication_state:
        # Create landing page
        if not iiGenerateLandingPage(*publicationConfig, *publicationState, "depublish"):
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Unrecoverable":
            return publication_state["status"]


    # Use secure copy to push landing page to the public host
    if "landingPageUploaded" not in publication_state:

        if not iiCopyLandingPage2PublicHost(*publicationConfig, *publicationState):
             publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Use secure copy to push combi XML to MOAI server
    if "oaiUploaded" not in publication_state:
        if not iiCopyMetadataToMOAI(*publicationConfig, *publicationState):
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # Set access restriction for vault package.
    if "anonymousAccess" not in publication_state:

        if not iiSetAccessRestriction(*vaultPackage, *publicationState):
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]


        # The depublication was a success
        avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'vault_status', constants.vault_package_state.DEPUBLISHED)
        publication_state["status"] = "OK"
        save_publication_state(ctx, vault_package, publication_state)
        # rule_provenance_log_action("system", *vaultPackage, "publication updated") ?????
       
        ctx.writeLine("serverLog", "iiProcessDepublication: All steps for depublication completed") 
        return publication_state["status"]




"""
# \brief Routine to process a republication with sanity checks at every step.
#
# \param[in] vaultPackage       path to package in the vault to publish
# \param[out] status		status of the publication
#

def process_republication(ctx, vault_package):
    publication_state = {}

    # check permissions - rodsadmin only
    if user.user_type(ctx) != 'rodsadmin':
        log.write(ctx, "User is no rodsadmin")
        return 'Insufficient permissions - should only be called by rodsadmin'

    # check current status, perhaps transitioned already
    current_coll_status = get_coll_vault_status(ctx, coll).value
    return "NotAllowed"

    # get publication configuration
    config = epic.get_publication_config(ctx)
    return "Retry"

    # get state of all related to the publication
    publication_state = get_publication_state(ctx, vault_package) 
    status = publication_state['status']

    if status in ["Unrecoverable", "Processing"]:
        return ""
    elif status in ["Unknown", "Retry"]:
        status = "Processing"
        publication_state['status'] = status

    if "publicationDate" not in publication_state:
        publication_state["publicationDate"] = get_publication_date(ctx)

    # Determine last modification time. Always run, no matter if retry
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime()

    # Generate Combi Json consisting of user and system metadata
    if "combiJsonPath" not in publication_state: 

        if not iiGenerateCombiJson(*publicationConfig, *publicationState))
        
            publication_state["status"] = "Unrecoverable"
               
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Generate DataCite XML
    if "dataCiteXmlPath" not in publication_state:
        if not iiGenerateDataCiteXml(*publicationConfig, *publicationState))
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Send DataCite XML to metadata end point
    if "dataCiteMetadataPosted" not in publication_state:
        if not iiPostMetadataToDataCite(*publicationConfig, *publicationState):
            publication_state["status"] = "Retry"
        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]


    # Create landing page
    if "landingPagePath" not in publication_state:
        # Create landing page
        if not iiGenerateLandingPage(*publicationConfig, *publicationState, "publish"):
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Unrecoverable":
            return publication_state["status"]


    # Use secure copy to push landing page to the public host
    if "landingPageUploaded" not in publication_state:

        if not iiCopyLandingPage2PublicHost(*publicationConfig, *publicationState):
             publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]


    # Use secure copy to push combi XML to MOAI server
    if "oaiUploaded" not in publication_state:
        if not iiCopyMetadataToMOAI(*publicationConfig, *publicationState):
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]



    # Set access restriction for vault package.
    if "anonymousAccess" not in publication_state:
        if not iiSetAccessRestriction(*vaultPackage, *publicationState):
            publication_state["status"] = "Retry"

        save_publication_state(ctx, vault_package, publication_state)

        if publication_state["status"] == "Retry":
            return publication_state["status"]

    # The publication was a success
    publication_state["status"] = "OK"
    save_publication_state(ctx, vault_package, publication_state)
    avu.set_on_coll(ctx, vault_package, constants.UUORGMETADATAPREFIX + 'vault_status', constants.vault_package_state.PUBLISHED)

    ireturn publication_state["status"]



def get_collection_metadata(coll, prefix):
"""
    return a dict with all requested (prefixed) attributes and strip off prefix for the key names.
    example key: org_publication_lastModifiedDateTime    

"""
    coll_metadata = {}
    iter = genquery.row_iterator(
        "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "COLL_NAME = '" + coll + "' AND META_COLL_ATTR_NAME like '" + prefix + "%'",
        genquery.AS_LIST, callback
    )

    for row in iter:
        coll_metadata[row[0]] = row[1][len(prefix):]

    return coll_metadata
