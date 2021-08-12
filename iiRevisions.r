# \file      iiRevisions.r
# \brief     Revision management. Each new file or file modification creates
#            a timestamped backup file in the revision store.
# \author    Paul Frederiks
# \copyright Copyright (c) 2017-2021, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# \brief Create revisions on file modifications.
#
#        This policy should trigger whenever a new file is added or modified
#	 in the workspace of a Research team. This should be done asynchronously.
#	 Triggered from instance specific rulesets.
#
# \param[in] resource			The resource where the original is written to
# \param[in] rodsZone			Zone where the original can be found
# \param[in] logicalPath		path of the original
#
uuResourceModifiedPostRevision(*resource, *rodsZone, *logicalPath) {
	if (*logicalPath like "/" ++ *rodsZone ++ "/home/" ++ IIGROUPPREFIX ++ "*") {
		uuChopPath(*logicalPath, *parent, *basename);

		*ignore = false;
		foreach(*filter in UUBLOCKLIST) {
			if (*basename like *filter) {
				writeLine("serverLog", "uuResourceModifiedPostRevision: Ignore *basename for revision store. Filter *filter matches");
				*ignore = true;
				break;
			}
		}

		if (*ignore) {
			succeed;
		}

		iiRevisionCreateAsynchronously(*resource, *logicalPath, UUMAXREVISIONSIZE);
	}
}

# \brief  Asynchronous call to iiRevisionCreate via scheduled job.
#
# \param[in] resource   The resource where the original is written to
# \param[in] path       The path of the added or modified file.
# \param[in] maxSize    The maximum file size of original
#
iiRevisionCreateAsynchronously(*resource, *path, *maxSize) {
    # Mark data object for revision creation by setting 'org_revision_scheduled' metadata.
    # Give rods 'own' access so that they can set&remove the AVU.
    errorcode(msiSetACL("default", "own", "rods#$rodsZoneClient", *path));

    msiString2KeyValPair("", *kv);
    msiAddKeyVal(*kv, UUORGMETADATAPREFIX ++ "revision_scheduled", "*resource");
    msiSetKeyValuePairsToObj(*kv, *path, "-d");
    #writeLine("serverLog", "uuRevisionCreateAsynchronously: Revision creation scheduled for *path");
}

# Scheduled revision creation batch job.
#
# Creates revisions for all data objects marked with 'org_revision_scheduled' metadata.
#
# XXX: This function cannot be ported to Python in 4.2.7:
#      msiDataObjCopy causes a deadlock for files of size
#      maximum_size_for_single_buffer_in_megabytes (32) or larger due to an iRODS PREP bug.
#      https://github.com/irods/irods_rule_engine_plugin_python/issues/54
#
# \param[in] verbose           whether to log verbose messages for troubleshooting (1: yes, 0: no)
uuRevisionBatch(*verbose) {
    *stopped = 0;
    foreach (*row in SELECT DATA_ID
                     WHERE  COLL_NAME = "/$rodsZoneClient/yoda/flags" AND DATA_NAME = "stop_revisions") {
        *stopped = 1;
    }

    if (*stopped) {
        writeLine("serverLog", "Batch revision job is stopped");
    } else {
        writeLine("serverLog", "Batch revision job started");
        *count        = 0;
        *countOk      = 0;
        *countIgnored = 0;
        *printVerbose = bool(*verbose);

        *attr      = UUORGMETADATAPREFIX ++ "revision_scheduled";
        *errorattr = UUORGMETADATAPREFIX ++ "revision_failed";
        foreach (*row in SELECT COLL_NAME, DATA_NAME, DATA_SIZE, META_DATA_ATTR_VALUE
                         WHERE  META_DATA_ATTR_NAME = '*attr') {
            *count = *count + 1;

            # Stop scheduled revision if stop flag is set.
            foreach (*row in SELECT DATA_ID
                             WHERE  COLL_NAME = "/$rodsZoneClient/yoda/flags" AND DATA_NAME = "stop_revisions") {
                writeLine("serverLog", "Batch revision job is stopped");
                break;
            }

            # Perform scheduled revision creation for one data object.
            *path  = *row."COLL_NAME" ++ "/" ++ *row."DATA_NAME";
            *resc  = *row."META_DATA_ATTR_VALUE";
            *size  = *row."DATA_SIZE";

            if (*printVerbose) {
                writeLine("serverLog", "Batch revision: creating revision for *path on resc *resc");
            }

            *revstatus = errorcode(iiRevisionCreate(*resc, *path, UUMAXREVISIONSIZE, *verbose, *id));

            *kv.*attr = *resc;

            # Remove revision_scheduled flag no matter if it succeeded or not.
            # rods should have been given own access via policy to allow AVU
            # changes.

            if (*printVerbose) {
                writeLine("serverLog", "Batch revision: removing AVU for *path");
            }

            *rmstatus = errorcode(msiRemoveKeyValuePairsFromObj(*kv, *path, "-d"));
            if (*rmstatus != 0) {
                # The object's ACLs may have changed.
                # Force the ACL and try one more time.
                errorcode(msiSudoObjAclSet("", "own", uuClientFullName, *path, ""));
                *rmstatus = errorcode(msiRemoveKeyValuePairsFromObj(*kv, *path, "-d"));

                if (*rmstatus != 0) {
                    writeLine("serverLog", "revision error: Scheduled revision creation of <*path>: could not remove schedule flag (*rmstatus)");
                }
            }

            if (*revstatus == 0) {
                if (*id != "") {
                    writeLine("serverLog", "iiRevisionCreate: Revision created for *path ID=*id");
                    *countOk = *countOk + 1;
                } else {
                    *countIgnored = *countIgnored + 1;
                }

                # Revision creation OK. Remove any existing error indication attribute.
                *c = *row."COLL_NAME";
                *d = *row."DATA_NAME";
                foreach (*x in SELECT DATA_NAME
                               WHERE  COLL_NAME            = '*c'
                                 AND  DATA_NAME            = '*d'
                                 AND  META_DATA_ATTR_NAME  = '*errorattr'
                                 AND  META_DATA_ATTR_VALUE = 'true') {

                    # Only try to remove it if we know for sure it exists,
                    # otherwise we get useless errors in the log.
                    *errorkv.*errorattr = "true";
                    errorcode(msiRemoveKeyValuePairsFromObj(*errorkv, *path, "-d"));
                    break;
                }
            } else {
                # Set error attribute

                writeLine("serverLog", "revision error: Scheduled revision creation of <*path> failed (*revstatus)");
                *errorkv.*errorattr = "true";
                errorcode(msiSetKeyValuePairsToObj(*errorkv, *path, "-d"));
            }
        }

        writeLine("serverLog", "Batch revision job finished. " ++ str(*countOk+*countIgnored) ++ "/*count successfully processed, of which *countOk resulted in new revisions");
    }
}

# \brief Create a revision of a dataobject in a revision folder.  ## BLIJFT ##
#
# \param[in] resource		resource to retrieve original from
# \param[in] path		path of data object to create a revision for
# \param[in] maxSize		max size of files in bytes
# \param[in] verbose		whether to print messages for troubleshooting to log (1: yes, 0: no)
# \param[out] id		object id of revision
#
iiRevisionCreate(*resource, *path, *maxSize, *verbose, *id) {
    *id = "";
    *printVerbose = bool(*verbose);
    uuChopPath(*path, *parent, *basename);
    *objectId = 0;
    *found = false;
    foreach(*row in SELECT DATA_ID, DATA_MODIFY_TIME, DATA_OWNER_NAME, DATA_SIZE, COLL_ID, DATA_RESC_HIER
            WHERE DATA_NAME = *basename AND COLL_NAME = *parent AND DATA_RESC_HIER like '*resource%') {
        if (!*found) {
            *found = true;
            *dataId = *row.DATA_ID;
            *modifyTime = *row.DATA_MODIFY_TIME;
            *dataSize = *row.DATA_SIZE;
            *collId = *row.COLL_ID;
            *dataOwner = *row.DATA_OWNER_NAME;
        }
    }

    if (!*found) {
        writeLine("serverLog", "iiRevisionCreate: DataObject was not found or path was collection");
        succeed;
    }


    if (double(*dataSize)>*maxSize) {
        writeLine("serverLog", "iiRevisionCreate: Files larger than *maxSize bytes cannot store revisions");
        succeed;
    }


    foreach(*row in SELECT USER_NAME, USER_ZONE WHERE DATA_ID = *dataId AND USER_TYPE = "rodsgroup" AND DATA_ACCESS_NAME = "own") {
        *groupName = *row.USER_NAME;
        *userZone = *row.USER_ZONE;
    }

    # All revisions are stored in a group with the same name as the research group in a system collection
    # When this collection is missing, no revisions will be created. When the group manager is used to
    # create new research groups, the revision collection will be created as well.
    *revisionStore = "/*userZone" ++ UUREVISIONCOLLECTION ++ "/*groupName";

    *revisionStoreExists = false;
    foreach(*row in SELECT COLL_ID WHERE COLL_NAME = *revisionStore) {
        *revisionStoreExists = true;
    }

    if (*revisionStoreExists) {
        # Exists: Revisions are enabled.

        # Allow rodsadmin to create subcollections.
        errorcode(msiSetACL("default", "admin:own", "rods#$rodsZoneClient", *revisionStore));

        # generate a timestamp in iso8601 format to append to the filename of the revised file.
        msiGetIcatTime(*timestamp, "icat");
        *iso8601 = uuiso8601(*timestamp);
        *revFileName = *basename ++ "_" ++ *iso8601 ++ *dataOwner;
        *revColl = *revisionStore ++ "/" ++ *collId;

        if (uuCollectionExists(*revColl)) {
            # Rods may not have own access yet.
            errorcode(msiSetACL("default", "admin:own", "rods#$rodsZoneClient", *revColl));
        } else {
            msiCollCreate(*revColl, 1, *msistatus);
            # Inheritance is enabled - ACLs are already good.
            # (rods and the research group both have own)
        }

        *revPath = *revColl ++ "/" ++ *revFileName;

        if ( *printVerbose ) {
            writeLine("serverLog", "iiRevisionCreate: creating revision *path -> *revPath" );
        }

        *err = errorcode(msiDataObjCopy(*path, *revPath, "verifyChksum=", *msistatus));
        if (*err < 0) {
            if (*err == -312000) {
                # When a file is modified multiple times in a second, only the first modification can be stored as the revision name with timestamp will be the same
                # iRODS returns timestamps in seconds only.
                # -312000 OVERWRITE_WITHOUT_FORCE_FLAG
                writeLine("serverLog", "iiRevisionCreate: *revPath already exists. This means that *basename was changed multiple times within the same second.");
                succeed;
            } else if (*err == -814000) {
                # -814000 CAT_UNKNOWN_COLLECTION
                writeLine("serverLog", "iiRevisionCreate: Could not access or create *revColl. Please check permissions");
                succeed;
            } else {
                writeLine("serverLog", "iiRevisionCreate: failed for *path with errorCode *err");
                succeed;
            }
        } else {
            foreach(*row in SELECT DATA_ID WHERE DATA_NAME = *revFileName AND COLL_NAME = *revColl) {
                *id = *row.DATA_ID;
            }

            # Add original metadata to revision data object.
            msiString2KeyValPair("", *revkv);
            msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_path", *path);
            msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_coll_name", *parent);
            msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_data_name", *basename);
            msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_data_owner_name", *dataOwner);
            msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_data_id", *dataId);
            msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_coll_id", *collId);
            msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_modify_time", *modifyTime);
            msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_group_name", *groupName);
            msiAddKeyVal(*revkv, UUORGMETADATAPREFIX ++ "original_filesize", *dataSize);

            msiAssociateKeyValuePairsToObj(*revkv, *revPath, "-d");
        }
    } else {
        writeLine("serverLog", "iiRevisionCreate: *revisionStore does not exists or is inaccessible for current client.");
        succeed;
    }
}


# \brief Calculate the unix timestamp for the end of the current day (Same as start of next day).   ## KAN WEG ##
#
# param[out] endOfCalendarDay		Timestamp of the end of the current day
#
iiRevisionCalculateEndOfCalendarDay(*endOfCalendarDay) {
		msiGetIcatTime(*timestamp, "unix"); # Get current Timestamp
		*bdY = timestrf(datetime(double(*timestamp)), "%b %d %Y"); # Generate string of current date (e.g. Jan 14 1982).

		*endofcalendarday_dt = datetime(*bdY ++ " 23:59:59"); # Append the last second of the day and convert to datetime
		*endofcalendarday_str = timestrf(*endofcalendarday_dt, "%s"); # Generate string of unix timestamp of the last second of the day
		*endOfCalendarDay =  double(*endofcalendarday_str) + 1.0; # Convert to double and add 1 second to get 00:00 of the next day
}

# Deze moet blijven
# \datatype iirevisioncandidate    Represents a revision with a timestamp with an double for the timestamp and a string for the DATA_ID.
#                                  A removed candidate is represented with an empty data constructor
data iirevisioncandidate =
	| iirevisioncandidate : double * string -> iirevisioncandidate
	| iirevisionremoved : iirevisioncandidate


# \brief iiRevisionListOfCollectionBeforeTimestamp   ## BLIJFT ##
#
# \param[in] collName      name of collection
# \param[in] timestamp     only revisions created before this timestamp will be returned
# \param[out] revisions    list of revisions
#
iiRevisionListOfCollectionBeforeTimestamp(*collName, *timestamp, *revisions) {
        *revisions = list();
        *originalPathKey = UUORGMETADATAPREFIX ++ "original_path";
        foreach(*row in SELECT META_DATA_ATTR_VALUE WHERE META_DATA_ATTR_NAME = *originalPathKey AND META_DATA_ATTR_VALUE LIKE '*collName/%') {
                *originalPath = *row.META_DATA_ATTR_VALUE;
                iiRevisionLastBefore(*originalPath, *timestamp, *revisionId);
                if (*revisionId != "") {
                        *revisions = cons(iirevisionwithpath(*revisionId, *originalPath), *revisions);
                }
        }
}

# \brief iiRevisionLastBefore   ## BLIJFT ##
#
# \param[in] path        original path
# \param[in] timestamp   the first revision before this timestamp will be returned
# \param[out] revisionId  ID of revision
#
iiRevisionLastBefore(*path, *timestamp, *revisionId) {
        *revisionId = "";
        iiRevisionCandidates(*path, *candidates);
        foreach(*candidate in *candidates) {
                iirevisioncandidate(*timeDouble, *candidateId) = *candidate;
                if (*timeDouble < *timestamp) {
                        *revisionId = *candidateId;
                        break;
                }
        }
}
