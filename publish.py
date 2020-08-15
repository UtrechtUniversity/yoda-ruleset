# -*- coding: utf-8 -*-
"""Functions to publish dat0t and manage permissions of vault packages."""

__copyright__ = 'Copyright (c) 2019-2020, Utrecht University'
__license__   = 'GPLv3, see LICENSE'

epic.py 


def get_publication_state(ctx, vault_package):
def save_publication_state(ctx, vault_package):
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




"""
outine to process a publication with sanity checks at every step.
#
# \param[in] vaultPackage       path to package in the vault to publish
# \param[out] status		status of the publication
#
iiProcessPublication(*vaultPackage, *status) {
	*status = "Unknown";

	# Check preconditions
	iiVaultStatus(*vaultPackage, *vaultStatus);
	if (*vaultStatus != APPROVED_FOR_PUBLICATION &&
	    *vaultStatus != PUBLISHED) {
		*status = "NotAllowed";
		succeed;
	}

	uuGetUserType(uuClientFullName, *userType);
	if (*userType != "rodsadmin") {
		*status = "NotAllowed" ;
		succeed;
	}

	# Load configuration
	*err = errorcode(iiGetPublicationConfig(*publicationConfig));
	if (*err < 0) {
		*status = "Retry";
		succeed;
	}

	# Load state
	iiGetPublicationState(*vaultPackage, *publicationState);
	*status = *publicationState.status;
	if (*status == "Unrecoverable" || *status == "Processing") {
		succeed;
	} else if (*status == "Unknown" || *status == "Retry") {
		*status = "Processing";
		*publicationState.status = "Processing";
	}

	if (!iiHasKey(*publicationState, "publicationDate")) {
        iiGetPublicationDate(*publicationState);
	}

	if (!iiHasKey(*publicationState, "yodaDOI")) {
		# Generate Yoda DOI
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiGeneratePreliminaryDOI");
		iiGeneratePreliminaryDOI(*publicationConfig, *publicationState);
		iiSavePublicationState(*vaultPackage, *publicationState);
	} else if (iiHasKey(*publicationState, "DOIAvailable")) {
		if  (*publicationState.DOIAvailable == "no") {
			#DEBUG writeLine("serverLog", "iiProcessPublication: DOI not available, starting iiGeneratePreliminaryDOI");
			iiGeneratePreliminaryDOI(*publicationConfig, *publicationState);
			# We need to generate new json and xml
			*publicationState.combiJsonPath = "";
			*publicationState.dataCiteXmlPath = "";
			iiSavePublicationState(*vaultPackage, *publicationState);
		}
	}

	# Determine last modification time. Always run, no matter if retry.
	iiGetLastModifiedDateTime(*publicationState);

	if (!iiHasKey(*publicationState, "combiJsonPath")) {
		# Generate Combi Json consisting of user and system metadata

		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiGenerateCombiJson");
		*err = errorcode(iiGenerateCombiJson(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationState.status = "Unrecoverable";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Unrecoverable" || *publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}

	if (!iiHasKey(*publicationState, "dataCiteXmlPath")) {
		# Generate DataCite XML
		*err = errorcode(iiGenerateDataCiteXml(*publicationConfig, *publicationState));
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiGenerateDataCiteXml");
		if (*err < 0) {
			*publicationState.status = "Unrecoverable";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Unrecoverable" || *publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}

	}

	if (!iiHasKey(*publicationState, "DOIAvailable")) {
		# Check if DOI is in use
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiCheckDOIAvailability");
		*err = errorcode(iiCheckDOIAvailability(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationState.status = "Retry";
		}
		if (*publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}

	if (!iiHasKey(*publicationState, "dataCiteMetadataPosted")) {
                # Send DataCite XML to metadata end point
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiPostMetadataToDataCite");
		*err = errorcode(iiPostMetadataToDataCite(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationState.status = "Retry";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Retry" || *publicationState.status == "Unrecoverable") {
			*status = *publicationState.status;
			succeed;
		}
	}

	# Create landing page
	if (!iiHasKey(*publicationState, "landingPagePath")) {
		*err = errorcode(iiGenerateLandingPage(*publicationConfig, *publicationState, "publish"));
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiGenerateLandingPage");
		if (*err < 0) {
			*publicationState.status = "Unrecoverable";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Unrecoverable") {
			*status = *publicationState.status;
			succeed;
		}
	}

	# Create Landing page URL
	#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiGenerateLandingPageUrl");
	iiGenerateLandingPageUrl(*publicationConfig, *publicationState);

	if(!iiHasKey(*publicationState, "landingPageUploaded")) {
		# Use secure copy to push landing page to the public host
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiCopyLandingPage2PublicHost");
		*err = errorcode(iiCopyLandingPage2PublicHost(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationState.status = "Retry";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}

	if(!iiHasKey(*publicationState, "oaiUploaded")) {
		# Use secure copy to push combi XML to MOAI server
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiCopyMetadataToMOAI");
		*err = errorcode(iiCopyMetadataToMOAI(*publicationConfig, *publicationState));
		if (*err < 0) {
			publicationState.status = "Retry";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}

	if (!iiHasKey(*publicationState, "anonymousAccess")) {
		# Set access restriction for vault package.
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiSetAccessRestriction");
		*err = errorcode(iiSetAccessRestriction(*vaultPackage, *publicationState));
		if (*err < 0) {
			publicationState.status = "Retry";
		}
		iiSavePublicationState(*vaultPackage, *publicationState);
		if (*publicationState.status == "Retry") {
			*status = *publicationState.status;
			succeed;
		}
	}

	if (!iiHasKey(*publicationState, "DOIMinted")) {
		# Mint DOI with landing page URL.
		#DEBUG writeLine("serverLog", "iiProcessPublication: starting iiMintDOI");
		*err = errorcode(iiMintDOI(*publicationConfig, *publicationState));
		if (*err < 0) {
			*publicationState.status = "Retry";
		}
		if (*publicationState.status == "Unrecoverable" || *publicationState.status == "Retry") {
			iiSavePublicationState(*vaultPackage, *publicationState);
			*status = *publicationState.status;
			succeed;

		} else {
			writeLine("serverLog", "iiProcessPublication: All steps for publication completed");
			# The publication was a success;
			*publicationState.status = "OK";
			iiSavePublicationState(*vaultPackage, *publicationState);
			*status = *publicationState.status;
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
		}
	} else {
	        writeLine("serverLog", "iiProcessPublication: All steps for publication completed");
	        # The publication was a success;
	        *publicationState.status = "OK";
	        iiSavePublicationState(*vaultPackage, *publicationState);
		*status = *publicationState.status;

		rule_provenance_log_action("system", *vaultPackage, "publication updated");
	}
}
"""
