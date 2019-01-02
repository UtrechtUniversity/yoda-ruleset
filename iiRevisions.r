# \file      iiRevisions.r
# \brief     Revision management. Each new file or file modification creates
#            a timestamped backup file in the revision store.
# \author    Paul Frederiks
# \copyright Copyright (c) 2017, Utrecht University. All rights reserved.
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
# \param[in] maxsize			Maximum file size of original
# \param[in] filterlist			A list with like expressions to blacklist
#
uuResourceModifiedPostRevision(*resource, *rodsZone, *logicalPath, *maxSize, *filterlist) {
	if (*logicalPath like "/" ++ *rodsZone ++ "/home/" ++ IIGROUPPREFIX ++ "*") {
		uuChopPath(*logicalPath, *parent, *basename);

		*ignore = false;
		foreach(*filter in *filterlist) {
			if (*basename like *filter) {
				writeLine("serverLog", "uuResourceModifiedPostRevision: Ignore *basename for revision store. Filter *filter matches");
				*ignore = true;
				break;
			}
		}

		if (*ignore) {
			succeed;
		}

		iiRevisionCreateAsynchronously(*resource, *logicalPath, *maxSize);
	}
}

# \brief  Asynchronous call to iiRevisionCreate.
#         Schedule the creation of a revision as a delayed to avoid a slow down
#         of the main process.
#
# \param[in] resource   The resource where the original is written to
# \param[in] path	The path of the added or modified file.
# \param[in] maxSize    The maximum file size of original
#
iiRevisionCreateAsynchronously(*resource, *path, *maxSize) {
	delay("<PLUSET>1s</PLUSET>") {
		iiRevisionCreate(*resource, *path, *maxSize, *id);
		if (*id != "") {
			writeLine("serverLog", "iiRevisionCreate: Revision created for *path ID=*id");
		}
	}
}

# \brief Create a revision of a dataobject in a revision folder.
#
# \param[in] resource		resource to retreive original from
# \param[in] path		path of data object to create a revision for
# \param[in] maxSize		max size of files in bytes
# \param[out] id		object id of revision
#
iiRevisionCreate(*resource, *path, *maxSize, *id) {
	*id = "";
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
		# generate a timestamp in iso8601 format to append to the filename of the revised file.
		msiGetIcatTime(*timestamp, "icat");
		*iso8601 = uuiso8601(*timestamp);
		*revFileName = *basename ++ "_" ++ *iso8601 ++ *dataOwner;
		*revColl = *revisionStore ++ "/" ++ *collId;
		if (!uuCollectionExists(*revColl)) {
		    msiCollCreate(*revColl, 1, *msistatus);
		}
		*revPath = *revColl ++ "/" ++ *revFileName;
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


# \brief Remove a revision from the revision store.
#        Called by revision-cleanup.r cronjob.
#
# \param[in] revisionId       DATA_ID of the revision to remove
#
iiRevisionRemove(*revisionId) {
	*isfound = false;
	*revisionStore =  "/$rodsZoneClient" ++ UUREVISIONCOLLECTION;
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE DATA_ID = "*revisionId" AND COLL_NAME like "*revisionStore/%") {
		if (!*isfound) {
			*isfound = true;
			*objPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		} else {
			writeLine("serverLog", "iiRevisionRemove: *revisionId returned multiple results");
			break;
		}
	}
	if (*isfound) {
		*args = "";
		msiAddKeyValToMspStr("objPath", *objPath, *args);
		msiAddKeyValToMspStr("forceFlag", "", *args);
		*err = errorcode(msiDataObjUnlink(*args, *status));
		if (*err < 0) {
			writeLine("serverLog", "iiRevisionRemove: Failed with errorcode: *err");
		} else {
			writeLine("serverLog", "iiRevisionRemove('*revisionId'): Removed *objPath from revision store");
		}
	} else {
		writeLine("serverLog", "iiRevisionRemove('*revisionId'): Revision ID not found or permission denied.");
	}
}


# \brief Copy a revision from the revision store into a research area.
#        Called by frontoffice when user restores a revision.
#
# \param[in] revisionId         id of revision data object
# \param[in] target             target collection to write in
# \param[in] overwrite          {restore_no_overwrite, restore_overwrite, restore_next_to}
#				With "restore_no_overwrite" the front end tries to copy the selected revision in *target
#				If the file already exist the user needs to decide what to do.
#				Function exits with corresponding status so front end can take action
#				Options for user are:
#				- "restore_overwrite" -> overwrite the file
#				- "restore_next_to" -> revision is places next to the file it conficted with by adding
# \param[in] newFileName	Name as entered by user when chosing option 'restore_next_to'
# \param[out] status            status of the process
# \param[out] statusInfo	Contextual info regarding status
#
iiRevisionRestore(*revisionId, *target, *overwrite, *newFileName, *status, *statusInfo) {
      #| writeLine("stdout", "Restore a revision");
        *status = "Unknown error";
        *isfound = false;
        *executeRestoration = false;
	*statusInfo = '';

	*vaultArea = "/" ++ $rodsZoneClient ++ "/home/" ++ IIVAULTPREFIX;
	*length = strlen(*vaultArea);

	if (substr(*target,0,*length) == *vaultArea) {
		#writeLine('serverLog', 'IS VAULT');
		*status = "VaultNotAllowed";
	        succeed;
	}

        *lockFound = false;
	iiGetLocks(*target, *locks);
	if (size(*locks) > 0) {
		foreach(*rootCollection in *locks) {
			if (strlen(*rootCollection) <= strlen(*target)) {
				*lockFound = true;
			}
		}
	}

        if (*lockFound) {
 	  	*status = 'TargetPathLocked'; # Path to be used is locked. Therefore, placement of revision is not allowed.
 		succeed;
	}

        foreach(*rev in SELECT DATA_NAME, COLL_NAME WHERE DATA_ID = *revisionId) {
                if (!*isfound) {
                        *isfound = true;
                        *revName = *rev.DATA_NAME; # revision name is suffixed with a timestamp for uniqueness
                        *revCollName = *rev.COLL_NAME;
                        *src = *revCollName ++ "/" ++ *revName;
                        writeLine("serverLog", "iiRevisionRestore: Source is *src");
			break;
                }
        }

        if (!*isfound) {
                writeLine("serverLog", "iiRevisionRestore: Could not find revision *revisionId");
                *status = "RevisionNotFound";
                succeed;
        }

        # Get MetaData
        msiString2KeyValPair("", *kvp);
        uuObjectMetadataKvp(*revisionId, UUORGMETADATAPREFIX, *kvp);

        if (!uuCollectionExists(*target)) {
                writeLine("serverLog", "iiRevisionRestore: Cannot find target collection *target");
                *status = "TargetPathDoesNotExist";
                succeed;
        }


        if (*overwrite == "restore_no_overwrite") {
                ## Check for presence of file in target directory
                ## If not present, it can be restored. Otherwise user must decide
                *existsTargetFile = false;

                # Get original name for check whether file exists
                msiGetValByKey(*kvp, UUORGMETADATAPREFIX ++ "original_data_name", *oriDataName);

                foreach (*row in SELECT DATA_NAME WHERE COLL_NAME = *target AND DATA_NAME = *oriDataName ) {
                        *existsTargetFile = true;
                        break;
                }

		# Check if directory with same name as target file exists.
                *existsTargetFileAsFolder = false;
                *targetPath = *target ++ "/" ++ *oriDataName;
                foreach (*row in SELECT COLL_NAME WHERE COLL_NAME = *targetPath){
                        *existsTargetFileAsFolder = true;
                        break;
                }

                if(*existsTargetFile) {
                        # User decision required
                        writeLine("serverLog", "File exists already");
                        *status = "FileExists";
                        succeed;
                }
                if(*existsTargetFileAsFolder) {
                        # User decision required
                        writeLine("serverLog", "File exists as folder");
                        *status = "FileExistsAsFolder";
                        succeed;
                }
                else { ## Revision can be restored directly - no user interference required
                        msiAddKeyValToMspStr("forceFlag", "", *options);
                        *dst = *target ++ "/" ++ *oriDataName;

                        *executeRestoration = true;
                }
        }
        else {
                if (*overwrite == "restore_overwrite") {
                        msiGetValByKey(*kvp, UUORGMETADATAPREFIX ++ "original_data_name", *oriDataName);
                        msiAddKeyValToMspStr("forceFlag", "", *options);
                        *dst = *target ++ "/" ++ *oriDataName;
                        *executeRestoration = true;

                } else if (*overwrite == "restore_next_to") {
                        # New file name is entered by user and can be a duplicate again. So check first.
                        *newFileNameExists = false;
                        foreach (*row in SELECT DATA_NAME WHERE COLL_NAME = *target AND DATA_NAME = *newFileName ){
                                *newFileNameExists = true;
                                break;
                        }

                        if (!*newFileNameExists) {
                                *dst = *target ++ "/" ++ *newFileName;
                        }
                        else {
                                *status = "FileExistsEnteredByUser";
                                succeed;
                        }

                        # Check if new destination is an existing folder.
                        *newFileNameExistsAsCollection = false;
                        foreach (*row in SELECT COLL_NAME WHERE COLL_NAME = *dst){
                                *newFileNameExistsAsCollection = true;
                                break;
                        }

                        if (!*newFileNameExistsAsCollection) {
                                *executeRestoration = true;
                        }
                        else {
                                *status = "FileEnteredByUserExistsAsFolder";
                                succeed;
                        }
                }
                else {
                        *statusInfo = "Illegal overwrite flag *overwrite";
			writeLine("serverLog", "iiRevisionRestore: *statusInfo");
                        *status = "Unrecoverable";
			succeed;
                }
        }

        # Actual restoration - perhaps check for locking one more time here? just before the actual copy action?
        if (*executeRestoration) {
                msiAddKeyValToMspStr("verifyChksum", "", *options);
                writeLine("serverLog", "iiRevisionRestore: *src => *dst [*options]");
                *err = errormsg(msiDataObjCopy("*src", "*dst", *options, *msistatus), *errmsg);
                if (*err < 0) {
			if (*err==-818000) {
				*status = "PermissionDenied";
				succeed;
			}
			*statusInfo = "Restoration failed with error *err: *errmsg";
                        writeLine("serverLog", "iiRevisionRestore: *statusInfo");
                        *status = "Unrecoverable";
                } else {
                        *status = "Success";
                }
        }
}


# \brief List revisions of path.
#
# \param[in]  path     Path of original file
# \param[out] result   List in JSON format with all revisions of the original path
#
iiRevisionList(*path, *result) {
	*revisions = list();
	*startpath = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION;
	*originalPathKey =  UUORGMETADATAPREFIX ++ 'original_path';
	*isFound = false;
	foreach(*row in SELECT DATA_ID, COLL_NAME, order(DATA_NAME)
		        WHERE META_DATA_ATTR_NAME = *originalPathKey
		   	AND META_DATA_ATTR_VALUE = *path
			AND COLL_NAME like '*startpath/%') {
		msiString2KeyValPair("", *kvp);
		*isFound = true;
		*id = *row.DATA_ID;
		#DEBUG writeLine("serverLog", "iiRevisionList: DataID: *id");
		*kvp.id = *id;
		*kvp.revisionPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		foreach(*meta in SELECT META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE WHERE DATA_ID = *id) {
			*name = *meta.META_DATA_ATTR_NAME;
			*val = *meta.META_DATA_ATTR_VALUE;
			#DEBUG writeLine("serverLog","iiRevisionList: metadata: *name - *val");
			msiAddKeyVal(*kvp, *name, *val);
		}

		*revisions = cons(*kvp, *revisions);
	}

	uuKvpList2JSON(*revisions, *result, *size);
}

# \brief Calculate the unix timestamp for the end of the current day (Same as start of next day).
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

# \datatype iirevisioncandidate    Represents a revision with a timestamp with an double for the timestamp and a string for the DATA_ID.
#                                  A removed candidate is represented with an empty data constructor
data iirevisioncandidate =
	| iirevisioncandidate : double * string -> iirevisioncandidate
	| iirevisionremoved : iirevisioncandidate

# \function iirevisionisremoved   Check if a revisioncandidate is removed by matching it with its constructor
iirevisionisremoved(*r) =
	match *r with
		| iirevisionremoved => true
		| iirevisioncandidate(*i, *s) => false

# \datatype iibucket   Represents a time bucket where a number of revisions should be kept with three integers
#                      The first integer represents a time offset
#                      The second integer represents the number of revisions that can stay in the bucket
#                      The third integer represents the starting index when revisions need to remove. 0 is the newest, -1 the oldest
#                      revision after the current original (which should always be kept) , 1 the revision after that, etc.
data iibucket =
	| iibucket : integer * integer * integer -> iibucket


# iRODS timestamps are in seconds since epoch (1970-01-01 00:00 UTC). Express minutes, hours, days and weeks in seconds
iiminutes(*m) = *m * 60
iihours(*h) = *h * iiminutes(60)
iidays(*d) = *d * iihours(24)
iiweeks(*w) = *w * iidays(7)

# \brief Return a list of time buckets to determine revisions to keep.
#
# \param[in] case  Select a bucketlist based on a string
# \return    lst   A bucket list
#
iiRevisionBucketList(*case) {
	if (*case == "A") {
		# keep one revision per time bucket
		*lst = list(
			 iibucket(iihours(6),  1, 1),
			 iibucket(iihours(12), 1, 0),
			 iibucket(iihours(18), 1, 0),
			 iibucket(iidays(1),   1, 0),
			 iibucket(iidays(2),   1, 0),
			 iibucket(iidays(3),   1, 0),
			 iibucket(iidays(4),   1, 0),
			 iibucket(iidays(5),   1, 0),
			 iibucket(iidays(6),   1, 0),
			 iibucket(iiweeks(1),  1, 0),
			 iibucket(iiweeks(2),  1, 0),
			 iibucket(iiweeks(3),  1, 0),
			 iibucket(iiweeks(4),  1, 0),
			 iibucket(iiweeks(8),  1, 0),
			 iibucket(iiweeks(12), 1, 0),
			 iibucket(iiweeks(16), 1, 0)
		);
	} else if (*case == "Simple") {
		*lst = list(iibucket(iiweeks(16), 16, 4));
	} else {
		# Case B and default
		# By keeping two revisions per time bucket, the oldest and the newest, the spread over time
		*lst = list(
			 iibucket(iihours(12), 2, 0),
			 iibucket(iidays(1),   2, 1),
			 iibucket(iidays(3),   2, 1),
			 iibucket(iidays(5),   2, 1),
			 iibucket(iiweeks(1),  2, 1),
			 iibucket(iiweeks(3),  2, 1),
			 iibucket(iiweeks(8),  2, 1),
			 iibucket(iiweeks(16), 2, 1)
		);
	}
	*lst;
}


# \brief Determine which revisions should be removed and which to remove based on a bucketlist.
#
# \param[in]  path             full path of original
# \param[in]  endOfCalendarDay Unix timestamp of the end of the calendar day you want regard as startpoint of the time buckets
# \param[in]  bucketlist       list of iibuckets consisting of an offset, size and start index
# \param[out] keep             list of revisions to keep
# \param[out] remove           list of revisions to remove
#
iiRevisionStrategy(*path, *endOfCalendarDay, *bucketlist, *keep, *remove) {
	if (*endOfCalendarDay == 0) {
		iiRevisionCalculateEndOfCalendarDay(*endOfCalendarDay);
	}
	iiRevisionCandidates(*path, *revisions);
	iiRevisionStrategyImplementation(*revisions, *endOfCalendarDay, *bucketlist, *keep, *remove);
}

# \brief Return list of revisioncandidates of a path.
#
# \param[in]  path       path of original
# \param[out] revisions  list of revisioncandidates
#
iiRevisionCandidates(*path, *revisions) {

	*revisions = list();
	*originalPathKey = UUORGMETADATAPREFIX ++ "original_path";
	*revisionStore = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION;

	foreach(*row in SELECT DATA_ID, order(DATA_NAME) WHERE META_DATA_ATTR_NAME = *originalPathKey
		                                         AND META_DATA_ATTR_VALUE = *path
							 AND COLL_NAME like "*revisionStore%") {
		*id = *row.DATA_ID;
		uuObjectMetadataKvp(*id, UUORGMETADATAPREFIX, *mdkvp);
		msiGetValByKey(*mdkvp, UUORGMETADATAPREFIX ++ "original_modify_time", *modifyTime);
		*revisions = cons(iirevisioncandidate(double(*modifyTime), *id), *revisions);
	}
}

# \brief Algorithm to find all removal candidates.
#
# \param[in] revisions     	list of iirevisioncandidates
# \param[in] endOfCalendarDay   Unix timestamp of the end of the calendar day you want regard as startpoint of the time buckets
# \param[in]  bucketlist        list of iibuckets consisting of an offset, size and start index
# \param[out] keep             list of revisions to keep
# \param[out] remove           list of revisions to remove
#
iiRevisionStrategyImplementation(*revisions, *endOfCalendarDay, *bucketlist, *keep, *remove) {
	*keep = list();
	*remove = list();

	# If no revisions are found, no revisions need to be removed
	if (size(*revisions) < 1) {
		#DEBUG writeLine("serverLog", "iiRevisionStrategyImplementation: Nothing to do, no revisions found for *path");
		succeed;
	}

	# Always keep the newest revision as it is the same as the original and becomes the "undo" after a change is made
	*keep = cons(hd(*revisions), *keep);
	*revisions = tl(*revisions);

	# Put the remaining revisions in buckets
	foreach(*bucket in *bucketlist) {
		if (size(*revisions) < 0) {
			break;
		}
		# Use a pseudo constructor on the bucket to put each integer in the proper variable
		iibucket(*offset, *sizeOfBucket, *startIdx) = *bucket;
		#DEBUG	writeLine("stdout", "Bucket: offset[*offset] sizeOfBucket[*sizeOfBucket] startIdx[*startIdx]");
		*startTime = *endOfCalendarDay - *offset;
		# each revision newer than the startTime of the bucket is a candidate to keep or remove in that bucket
		*candidates = list();
		*n = size(*revisions);
		for(*i = 0;*i < *n; *i = *i + 1) {
			*revision = hd(*revisions);
			# use pseudo data constructor iirevisioncandidate to initialize timeDouble and id.
			iirevisioncandidate(*timeDouble, *id) = *revision;
			#DEBUG writeLine("stdout", "*timeDouble: *id");
			if (*timeDouble > *startTime) {
				#DEBUG writeLine("stdout", "*timeDouble > *offset");
				*candidates = cons(*revision, *candidates);
				*revisions = tl(*revisions);
			} else {
				#DEBUG writeLine("stdout", "break;");
				break;
			}
		}

		# Determine if the size of the bucket is exceeded.
		*sizeOfCandidates = size(*candidates);
		*nToRemove = *sizeOfCandidates - *sizeOfBucket;
		if (*nToRemove > 0) {
			# Start marking revisions for removal from the startIdx until the max size of the bucket is reached.
			if (*startIdx < 0) {
				# If startIdx is negative go oldest to newest.
				for(*idx = *sizeOfCandidates + *startIdx; *idx > (*sizeOfCandidates + *startIdx - *nToRemove); *idx = *idx - 1) {
					*toRemove = elem(*candidates, *idx);
					*remove = cons(*toRemove, *remove);
					*candidates = setelem(*candidates, *idx, iirevisionremoved);
				}
			} else {
				# If startIdx is zero or higher go newest to oldest.
				for(*idx = *startIdx;*idx < (*nToRemove + *startIdx); *idx = *idx + 1) {
					*toRemove = elem(*candidates, *idx);
					*remove = cons(*toRemove, *remove);
					*candidates = setelem(*candidates, *idx, iirevisionremoved);
				}
			}
		}

		foreach(*toKeep in *candidates) {
			# Every candidate not marked for removal is added to the keep list
			if(!iirevisionisremoved(*toKeep)) {
				*keep = cons(*toKeep, *keep);
			}
		}
	}

	# All remaining revisions are older than the oldest bucket.
	foreach(*revision in *revisions) {
		*remove = cons(*revision, *remove);
	}
}

# \brief This search function is currently not used by the frontend as it also returns every file
#         with the search string one of the folders in its path.
#         Could still be useful in development and testing.
#
# \param[in] searchString	String to search for in the filesystem
# \param[in] orderby		Column to sort on, Defaults to COLL_NAME
# \param[in] ascdesc		"asc" for ascending order and "desc" for descending order
# \param[in] limit		Maximum number of results returned
# \param[in] offset		Offset in result set before returning results
# \param[out] result		List of results in JSON format
#
iiRevisionSearchByOriginalPath(*searchstring, *orderby, *ascdesc, *limit, *offset, *result) {
	# Generic exception handling intialisation for possible later purposes
        *status = 'Success';
        *statusInfo = '';

	*fields = list("META_DATA_ATTR_VALUE", "COUNT(DATA_ID)", "DATA_NAME");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_path"),
			   uumakelikecondition("META_DATA_ATTR_VALUE", *searchstring));
	*startpath = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION;
	*conditions = cons(uumakestartswithcondition("COLL_NAME", *startpath), *conditions);

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList, *status, *statusInfo);

	*result_lst = list();
	foreach(*kvp in tl(*kvpList)) {
		msiString2KeyValPair("", *res);
		*res.originalPath = *kvp.META_DATA_ATTR_VALUE;
		*res.numberOfRevisions = *kvp.DATA_ID;
		*result_lst = cons(*res, *result_lst);
	}

	*result_lst = cons(hd(*kvpList), uuListReverse(*result_lst));
	uuKvpList2JSON(*result_lst, *json_str, *size);
	*result = *json_str;
}

# \brief Used by frontend to search for revisions. Hence presence of *status and *statusInfo.
#
# \param[in] searchString	String to search for in the filesystem
# \param[in] orderby		Column to sort on, Defaults to COLL_NAME
# \param[in] ascdesc		"asc" for ascending order and "desc" for descending order
# \param[in] limit		Maximum number of results returned
# \param[in] offset		Offset in result set before returning results
# \param[out] result		List of results in JSON format
# \param[out] status            Status code: 'Success' of all ok
# \param[out] statusInfo        Extra information if something went wrong
#
iiRevisionSearchByOriginalFilename(*searchstring, *orderby, *ascdesc, *limit, *offset, *result, *status, *statusInfo) {
	*status = 'Success';
	*statusInfo = '';

	*originalDataNameKey = UUORGMETADATAPREFIX ++ "original_data_name";
	*fields = list("COLL_NAME", "META_DATA_ATTR_VALUE");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", *originalDataNameKey),
        		   uumakelikecondition("META_DATA_ATTR_VALUE", *searchstring));
	*startpath = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION;
	*conditions = cons(uumakestartswithcondition("COLL_NAME", *startpath), *conditions);

	uuPaginatedUpperQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList, *status, *statusInfo);
 	if (*status!='Success') {
        	succeed;
        }

	*result_lst = list();
	foreach(*kvp in tl(*kvpList)) {
		msiString2KeyValPair("", *res);
		*originalDataName = *kvp.META_DATA_ATTR_VALUE;
		*res.originalDataName = *originalDataName;
		*revisionColl = *kvp.COLL_NAME;
		*originalPathKey = UUORGMETADATAPREFIX ++ "original_path";
		*revCount = 0;
		*isFound = false;
		foreach(*row in SELECT DATA_ID WHERE COLL_NAME = *revisionColl
					       AND META_DATA_ATTR_NAME = *originalDataNameKey
					       AND META_DATA_ATTR_VALUE = *originalDataName
		       ) {
			*revId = *row.DATA_ID;
			*revCount = *revCount + 1;
			uuObjectMetadataKvp(*revId, UUORGMETADATAPREFIX ++ "original", *mdkvp);
			msiGetValByKey(*mdkvp, UUORGMETADATAPREFIX ++ "original_modify_time", *revModifyTime);
			if (!*isFound) {
				*isFound = true;
				msiGetValByKey(*mdkvp, UUORGMETADATAPREFIX ++ "original_path", *originalPath);
				msiGetValByKey(*mdkvp, UUORGMETADATAPREFIX ++ "original_coll_name", *originalCollName);
				*latestRevModifiedTime = double(*revModifyTime);
				*oldestRevModifiedTime = double(*revModifyTime);
			} else {
				*latestRevModifiedTime = max(*latestRevModifiedTime, double(*revModifyTime));
				*oldestRevModifiedTime = min(*oldestRevModifiedTime, double(*revModifyTime));
			}
		}
		*res.numberOfRevisions = str(*revCount);
		*res.originalPath = *originalPath;
		*res.originalCollName = *originalCollName;
		*res.latestRevisionModifiedTime = str(*latestRevModifiedTime);
		*res.oldestRevisionModifiedTime = str(*oldestRevModifiedTime);
		*res.collectionExists = 'false';
		if ( uuCollectionExists(*originalCollName)) {
			*res.collectionExists = 'true';
		}

		*result_lst = cons(*res, *result_lst);
	}

	*result_lst = cons(hd(*kvpList), uuListReverse(*result_lst));
	uuKvpList2JSON(*result_lst, *json_str, *size);
	*result = *json_str;
}

# \brief Not used by the frontend, but is still useful when debugging
#        the revision system and to detect renames as the Id stays the same after file renames.
#
iiRevisionSearchByOriginalId(*searchid, *orderby, *ascdesc, *limit, *offset, *result) {
        # Generic exception handling intialisation for possible later purposes
        *status = 'Success';
        *statusInfo = '';

	*fields = list("COLL_NAME", "DATA_NAME", "DATA_ID", "DATA_CREATE_TIME", "DATA_MODIFY_TIME", "DATA_CHECKSUM", "DATA_SIZE");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_id"));
        *conditions = cons(uucondition("META_DATA_ATTR_VALUE", "=", *searchid), *conditions);
	*startpath = "/" ++ $rodsZoneClient ++ "/revisions";
	*conditions = cons(uumakestartswithcondition("COLL_PARENT_NAME", *startpath), *conditions);

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList, *status, *statusInfo);

	foreach(*kvp in tl(*kvpList)) {
		*id = *kvp.DATA_ID;
		uuObjectMetadataKvp(*id, UUORGMETADATAPREFIX, *kvp);
	}

	*kvpList = cons(hd(*kvpList), uuListReverse(tl(*kvpList)));

	uuKvpList2JSON(*kvpList, *json_str, *size);
	*result = *json_str;
}


# \datatype iirevisionwithpath
# combination of revisionId and original path of the revised file
data iirevisionwithpath =
	| iirevisionwithpath : string * string -> iirevisionwithpath

# \brief iiRevisionListOfCollectionBeforeTimestamp
#
# \param[in] collName	   name of collection
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

# \brief iiRevisionLastBefore
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
