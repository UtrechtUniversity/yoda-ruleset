# \file      iiPublish.r
# \brief     This file contains rules related to publishing a datapackage
#            for a research group.
# \author    Paul Frederiks
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2017-2020, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.


#\ Generic secure copy functionality
# \param[in] argv         argument string for secure copy like "*publicHost inbox /var/www/landingpages/*publicPath";
# \param[in] origin_path  local path of origin file
# \param[out] err         return the error to calling function
#
iiGenericSecureCopy(*argv, *origin_path, *err) {
        *err = errorcode(msiExecCmd("securecopy.sh", *argv, "", *origin_path, 1, *cmdExecOut));
        if (*err < 0) {
                msiGetStderrInExecCmdOut(*cmdExecOut, *stderr);
                msiGetStdoutInExecCmdOut(*cmdExecOut, *stdout);
                writeLine("serverLog", "iiGenericSecureCopy: errorcode *err");
                writeLine("serverLog", *stderr);
                writeLine("serverLog", *stdout);
        }
}


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


# \brief Determine the time of publication as a datetime with UTC offset.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
iiGetPublicationDate(*publicationState) {
        *actionLog = UUORGMETADATAPREFIX ++ "action_log";
        *vaultPackage = *publicationState.vaultPackage;
        *publicationState.publicationDate = "";

        foreach(*row in SELECT order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE
                                          WHERE META_COLL_ATTR_NAME = *actionLog
                                          AND COLL_NAME = *vaultPackage) {
            *logRecord = *row.META_COLL_ATTR_VALUE;
            *action = "";
            msi_json_arrayops(*logRecord, *action, "get", 1);
            if (*action == "published") {
                *publicationTimestamp = "";
                msi_json_arrayops(*logRecord, *publicationTimestamp, "get", 0);
                # iso8601 compliant datetime with UTC offset
                *publicationDateTime = timestrf(datetime(int(*publicationTimestamp)), "%Y-%m-%dT%H:%M:%S%z");
                *publicationState.publicationDate = uuiso8601date(*publicationDateTime);
                #DEBUG writeLine("serverLog", "iiGetPublicationDate: *publicationState.publicationDate");
                break;
            }
        }

        if(*publicationState.publicationDate == "" ) {
            msiGetIcatTime(*now, "unix");
            *publicationDate = uuiso8601date(*now);
            *publicationState.publicationDate = *publicationDate;
        }
}


# \brief Determine the time of last modification as a datetime with UTC offset.
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
iiGetLastModifiedDateTime(*publicationState) {
	*actionLog = UUORGMETADATAPREFIX ++ "action_log";
	*vaultPackage = *publicationState.vaultPackage;
	foreach(*row in SELECT order_desc(META_COLL_MODIFY_TIME), META_COLL_ATTR_VALUE
                                          WHERE META_COLL_ATTR_NAME = *actionLog
                                          AND COLL_NAME = *vaultPackage) {
		*logRecord = *row.META_COLL_ATTR_VALUE;
		break;
	}

	*lastModifiedTimestamp = "";
	msi_json_arrayops(*logRecord, *lastModifiedTimestamp, "get", 0);
	# iso8601 compliant datetime with UTC offset
	*lastModifiedDateTime = timestrf(datetime(int(*lastModifiedTimestamp)), "%Y-%m-%dT%H:%M:%S%z");
	*publicationState.lastModifiedDateTime = *lastModifiedDateTime;
	#DEBUG writeLine("serverLog", "iiGetLastModifiedDateTime: *lastModifiedDateTime");
}


# \brief Generate a Landing page from the combi JSON and the landingpage template
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
iiGenerateLandingPage(*publicationConfig, *publicationState, *publish)
{
        *combiJsonPath = *publicationState.combiJsonPath;
        *randomId = *publicationState.randomId;
        uuChopPath(*combiJsonPath, *tempColl, *_);

        *vaultPackage = *publicationState.vaultPackage;
        *pathElems = split(*vaultPackage, "/");
        *rodsZone = elem(*pathElems, 0);
        *vaultGroup = elem(*pathElems, 2);

        uuGetBaseGroup(*vaultGroup, *baseGroup);
        uuGroupGetCategory(*baseGroup, *category, *subcategory);
        if (*publish == "publish") {
            *template_name = 'landingpage.html.j2';
        } else {
            *template_name = 'emptylandingpage.html.j2';
        }

        *receiveLandingPage = ''; ## initialize before handover to Python
        # Based on content of *combiJsonPath, get landingpage as string
        rule_json_landing_page_create_json_landing_page(*rodsZone, *template_name, *combiJsonPath, *receiveLandingPage);

        writeString('serverLog', *receiveLandingPage);

        *landingPagePath = "*tempColl/*randomId.html";
        msiDataObjCreate(*landingPagePath, "forceFlag=", *fd);
        msiDataObjWrite(*fd, *receiveLandingPage, *len);
        msiDataObjClose(*fd, *status);
        #DEBUG writeLine("serverLog", "landing page len=*len");
        *publicationState.landingPageLen = str(*len);
        *publicationState.landingPagePath = *landingPagePath;
        #DEBUG writeLine("serverLog", "iiGenerateLandingPage: Generated *landingPagePath");
}


# \brief iiCopyLandingPage2PublicHost
#
# \param[in] publicationConfig      Configuration is passed as key-value-pairs throughout publication process
# \param[in,out] publicationState   The state of the publication process is also kept in a key-value-pairs
#
iiCopyLandingPage2PublicHost(*publicationConfig, *publicationState) {
	*publicHost = *publicationConfig.publicHost;
	*landingPagePath = *publicationState.landingPagePath;
	*yodaInstance = *publicationConfig.yodaInstance;
	*yodaPrefix = *publicationConfig.yodaPrefix;
	*randomId =  *publicationState.randomId;
	*publicPath = "*yodaInstance/*yodaPrefix/*randomId.html";
	*argv = "*publicHost inbox /var/www/landingpages/*publicPath";
	*err = errorcode(msiExecCmd("securecopy.sh", *argv, "", *landingPagePath, 1, *cmdExecOut));
	if (*err < 0) {
		*publicationState.status = "Retry";
		msiGetStderrInExecCmdOut(*cmdExecOut, *stderr);
		msiGetStdoutInExecCmdOut(*cmdExecOut, *stdout);
		writeLine("serverLog", "iiCopyLandingPage2PublicHost: errorcode *err");
		writeLine("serverLog", *stderr);
		writeLine("serverLog", *stdout);
	} else {
		*publicationState.landingPageUploaded = "yes";
		#DEBUG writeLine("serverLog", "iiCopyLandingPage2PublicHost: pushed *publicPath");
	}
}


# \brief Configuration is extracted from metadata on the UUSYSTEMCOLLECTION.
#
# \param[out] publicationConfig  a key-value-pair containing the configuration
#
iiGetPublicationConfig(*publicationConfig) {
	# Translation from camelCase config key to snake_case metadata attribute
	*configKeys = list(
		 "publicHost",
		 "publicVHost",
		 "moaiHost",
		 "yodaPrefix",
		 "dataCitePrefix",
		 "randomIdLength",
		 "yodaInstance",
		 "davrodsVHost",
		 "davrodsAnonymousVHost"
		 );
	*metadataAttributes = list(
		 "public_host",
		 "public_vhost",
		 "moai_host",
		 "yoda_prefix",
		 "datacite_prefix",
		 "random_id_length",
		 "yoda_instance",
		 "davrods_vhost",
		 "davrods_anonymous_vhost");

	*nKeys = size(*configKeys);
	*sysColl = "/" ++ $rodsZoneClient ++ UUSYSTEMCOLLECTION;

	#DEBUG writeLine("serverLog", "iiGetPublicationConfig: fetching publication configuration from *sysColl");
	iiCollectionMetadataKvpList(*sysColl, UUORGMETADATAPREFIX, true, *kvpList);

	# Add all metadata keys found to publicationConfig with the configKey as key.
	foreach(*kvp in *kvpList) {
		for(*idx = 0;*idx < *nKeys;*idx = *idx + 1) {
			if (*kvp.attrName == elem(*metadataAttributes, *idx)) {
				*configKey = elem(*configKeys, *idx);
				*publicationConfig."*configKey" = *kvp.attrValue;
				break;
			}
		}
	}

	# Check if all config keys are set;
	for(*idx = 0;*idx < *nKeys;*idx = *idx + 1) {
		*configKey = elem(*configKeys, *idx);
		*err = errorcode(*publicationConfig."*configKey");
		if (*err < 0) {
			*metadataAttribute = elem(*metadataAttributes, *idx);
			writeLine("serverLog", "iiGetPublicationConfig: *configKey missing; please set *metadataAttribute on *sysColl");
			fail;
		}
	}
	#DEBUG writeKeyValPairs("serverLog", *publicationConfig, "=");
}


# \brief The publication state is kept as metadata on the vaultPackage.
#
# \param[in] vaultPackage        path to the package in the vault
# \param[out] publicationState   key-value-pair containing the state
#
iiGetPublicationState(*vaultPackage, *publicationState) {
	# defaults
	msiString2KeyValPair("", *publicationState);
	*publicationState.status = "Unknown";
	*publicationState.accessRestriction = "Closed";

	iiCollectionMetadataKvpList(*vaultPackage, UUORGMETADATAPREFIX++"publication_", true, *kvpList);
	foreach(*kvp in *kvpList) {
		*key = *kvp.attrName;
		*val = *kvp.attrValue;
		*publicationState."*key" = *val;
	}

	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME like '%Data_Access_Restriction' AND COLL_NAME = *vaultPackage) {
		*publicationState.accessRestriction = *row.META_COLL_ATTR_VALUE;
	}

	*license = "";
	foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME like '%License' AND COLL_NAME = *vaultPackage) {
		*license = *row.META_COLL_ATTR_VALUE;
	}

	if (*license != "") {
		*publicationState.license = *license;
		*licenseAttrName = UUORGMETADATAPREFIX ++ "license_uri";
		*licenseUri = "";
		foreach(*row in SELECT META_COLL_ATTR_VALUE WHERE META_COLL_ATTR_NAME = *licenseAttrName AND COLL_NAME = *vaultPackage) {
			*licenseUri = *row.META_COLL_ATTR_VALUE;
		}

		if (*licenseUri != "") {
			*publicationState.licenseUri = *licenseUri;
		}
	}

	*publicationState.vaultPackage = *vaultPackage;
	#DEBUG writeKeyValPairs("serverLog", *publicationState, "=");
}


# \brief Save the publicationState key-value-pair to AVU's on the vaultPackage.
#
# \param[in] vaultPackage        path to the package in the vault
# \param[out] publicationState   key-value-pair containing the state
#
iiSavePublicationState(*vaultPackage, *publicationState) {
	msiString2KeyValPair("", *kvp);
	foreach(*key in *publicationState) {
		msiGetValByKey(*publicationState, *key, *val);
                if (*val == "") {
                        *val = "REMOVE_KEY";
                }
		*attrName = UUORGMETADATAPREFIX ++ "publication_" ++ *key;
		*kvp."*attrName" = *val;
	}
	msiSetKeyValuePairsToObj(*kvp, *vaultPackage, "-C");

	msiString2KeyValPair("", *kvp);
	foreach(*key in *publicationState) {
		msiGetValByKey(*publicationState, *key, *val);
                if (*val == "") {
                        *attrName = UUORGMETADATAPREFIX ++ "publication_" ++ *key;
                        *kvp."*attrName" = "REMOVE_KEY";
                }
	}
	msiRemoveKeyValuePairsFromObj(*kvp, *vaultPackage, "-C");
}


# Helper function with use outside this ruleset. Move to UU ruleset
iiHasKey(*kvp, *key) {
	*err = errorcode(*kvp."*key");
	if (*err == 0) {
		*result = true;
	} else {
		*result = false;
	}
	*result;
}


# \brief Routine to set publication state of vault package pending to update.
#
# \param[in]  vaultPackage   path to package in the vault to update
# \param[out] status         status of the publication state update
#
iiSetUpdatePublicationState(*vaultPackage, *status) {
	*status = "Unknown";

	# Check preconditions
	iiVaultStatus(*vaultPackage, *vaultStatus);
	if (*vaultStatus != PUBLISHED &&
	    *vaultStatus != PENDING_DEPUBLICATION &&
	    *vaultStatus != PENDING_REPUBLICATION) {
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
		*status = "UnkownError";
		succeed;
	}

	# Load state
	iiGetPublicationState(*vaultPackage, *publicationState);
	if (*publicationState.status != "OK") {
		*status = "PublicationNotOK";
		succeed;
	}

	# Set publication status
	*publicationState.status = "Unknown";

	# Generate new XML's
	*publicationState.combiJsonPath = "";
	*publicationState.dataCiteXmlPath = "";

	# Post metadata to DataCite
	*publicationState.dataCiteMetadataPosted = "";

	# Generate new landingpage
	*publicationState.landingPagePath = "";
	*publicationState.landingPageUploaded = "";

	# Update OAI-PMH metadata
	*publicationState.oaiUploaded = "";

	# Update anonymous access
	*publicationState.anonymousAccess = "";

	# Save state
	*err = errorcode(iiSavePublicationState(*vaultPackage, *publicationState));
	if (*err < 0) {
		*status = "UnkownError";
		succeed;
	}
}


# \brief Routine to update the landingpage of a published package.
#
# \param[in]  vaultPackage      path to package in the vault to publish
# \param[out] status		status of the publication
#
iiUpdateLandingpage(*vaultPackage, *status) {
	*status = "Unknown";

	# Check preconditions
	iiVaultStatus(*vaultPackage, *vaultStatus);
	if (*vaultStatus != PUBLISHED && *vaultStatus != DEPUBLISHED) {
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

	# Publication must be finsished.
	if (*publicationState.status != "OK") {
		*status = "NotAllowed";
		succeed;
	}

    if (!iiHasKey(*publicationState, "publicationDate")) {
        iiGetPublicationDate(*publicationState);
	}

	# Determine last modification time. Always run, no matter if retry.
	iiGetLastModifiedDateTime(*publicationState);

	# Generate Combi XML consisting of user and system metadata
	#DEBUG writeLine("serverLog", "iiUpdateLandingpage: starting iiGenerateCombiXml");
	*err = errorcode(iiGenerateCombiXml(*publicationConfig, *publicationState));
	if (*err < 0) {
		*status = "Unrecoverable";
		succeed;
	}

	# Create landing page
	#DEBUG writeLine("serverLog", "iiUpdateLandingpage: starting iiGenerateLandingPage");
	*err = errorcode(iiGenerateLandingPage(*publicationConfig, *publicationState, "publish"));
	if (*err < 0) {
		*status = "Unrecoverable";
		succeed;
	}

	# Use secure copy to push landing page to the public host
	#DEBUG writeLine("serverLog", "iiUpdateLandingpage: starting iiCopyLandingPage2PublicHost");
	*err = errorcode(iiCopyLandingPage2PublicHost(*publicationConfig, *publicationState));
	if (*err < 0) {
		*status = "Retry";
		succeed;
	}

	# The update was a success;
	writeLine("serverLog", "iiUpdateLandingpage: landingpage updated for *vaultPackage");
	*status = "OK";
}

iiCollectionMetadataKvpList(*path, *prefix, *strip, *lst) {
	*lst = list();
	foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE
		WHERE COLL_NAME = *path
		AND META_COLL_ATTR_NAME like '*prefix%') {
		msiString2KeyValPair("", *kvp);
		if (*strip) {
			*kvp.attrName = triml(*row.META_COLL_ATTR_NAME, *prefix);
		} else {
			*kvp.attrName = *row.META_COLL_ATTR_NAME;
		}
		*kvp.attrValue = *row.META_COLL_ATTR_VALUE;
		*lst = cons(*kvp, *lst);
	}
}
