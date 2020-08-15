# -*- coding: utf-8 -*-
"""Functions to publish dat0t and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

epic.py 


def get_publication_state(ctx, vault_package):
def save_publication_state(ctx, vault_package):

def set_update_publication_state(ctx, vault_package, status): # zet specifiek de publicatie status

def get_publication_date(ctx,):
def generate_preliminary_DOI(ctx, ):
def get_last_modified_datetime(ctx):

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
        save_publication_state(ctx, vault_package)
    elif "DOIAvailable" in publication_state:
        if publication_state["DOIAvailable"] == "no"
            generate_preliminary_DOI(ctx, )
            publication_state["combiJsonPath"] = ""
            publication_state["dataCiteXmlPath"] = ""
            save_publication_state(ctx, vault_package)

    # Determine last modification time. Always run, no matter if retry
    publication_state["lastModifiedDateTime"] = get_last_modified_datetime()

    # Generate Combi Json consisting of user and system metadata
    if "combiJsonPath" not in publication_state: 

        if not iiGenerateCombiJson(*publicationConfig, *publicationState))
        
            publication_state["status"] = "Unrecoverable"
               
        save_publication_state(ctx, vault_package)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Generate DataCite XML
    if "dataCiteXmlPath" not in publication_state:
        if not iiGenerateDataCiteXml(*publicationConfig, *publicationState))
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package)

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
        save_publication_state(ctx, vault_package)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Create landing page
    if "landingPagePath" not in publication_state:
        # Create landing page
        if not iiGenerateLandingPage(*publicationConfig, *publicationState, "publish"):
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package)

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

        save_publication_state(ctx, vault_package)

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
               
        save_publication_state(ctx, vault_package)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]

    # Remove metadata from DataCite
    if "dataCiteMetadataPosted" not in publication_state:
        if not iiRemoveMetadataFromDataCite(*publicationConfig, *publicationState):
            publication_state["status"] = "Retry"
        save_publication_state(ctx, vault_package)

        if publication_state["status"] in ["Unrecoverable", "Retry"]:
            return publication_state["status"]


    # Create landing page
    if "landingPagePath" not in publication_state:
        # Create landing page
        if not iiGenerateLandingPage(*publicationConfig, *publicationState, "depublish"):
            publication_state["status"] = "Unrecoverable"

        save_publication_state(ctx, vault_package)

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

    return publication_state["status"]
