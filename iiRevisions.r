# \file
# \brief     Revision management
# \author    Paul Frederiks
# \copyright Copyright (c) 2016, Utrecht university. All rights reserved
# \license   GPLv3, see LICENSE
#
#####################################################
#

# \brief uuResourceModifiedPostRevision 	Create revisions on file modifications
# \description				This policy should trigger whenever a new file is added or modified
#					in the workspace of a Research team. This should be done asynchronously
# \param[in,out] out	This is a required argument for Dynamic PEP's in the 4.1.x releases. It is unused.
uuResourceModifiedPostRevision(*resource, *rodsZone, *logicalPath, *maxSize, *filterlist) {
	if (*logicalPath like "/" ++ *rodsZone ++ "/home/" ++ IIGROUPPREFIX ++ "*") {
		uuChopPath(*logicalPath, *parent, *basename);
		
		foreach(*filter in *filterlist) {
			if (*basename like *filter) {
				writeLine("serverLog", "uuResourceModifiedPostRevision: Ignore *basename for revision store. Filter *filter matches");
				succeed;
			}
		}

		iiRevisionCreateAsynchronously(*resource, *logicalPath, *maxSize);
	}
}

# \brief iiRevisionCreateAsynchronously  Asynchronous call to iiRevisionCreate
# \param[in] path	The path of the added or modified file.
iiRevisionCreateAsynchronously(*resource, *path, *maxSize) {
	remote("localhost", "") {
		delay("<PLUSET>1s</PLUSET>") {
			iiRevisionCreate(*resource, *path, *maxSize, *id);
			writeLine("serverLog", "iiRevisionCreate: Revision created for *path ID=*id");
		}
	}
}

# \brief iiRevisionCreate create a revision of a dataobject in a revision folder
# \param[in] resource		resource to retreive original from
# \param[in] path		path of data object to create a revision for
# \param[in] maxSize		max size of files in bytes
# \param[out] id		object id of revision
iiRevisionCreate(*resource, *path, *maxSize, *id) {
	*id = "";
	uuChopPath(*path, *parent, *basename);
	*objectId = 0;
	*found = false;
	foreach(*row in SELECT DATA_ID, DATA_MODIFY_TIME, DATA_OWNER_NAME, DATA_SIZE, COLL_ID
	       		WHERE DATA_NAME = *basename AND COLL_NAME = *parent AND DATA_RESC_NAME = *resource) {
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


	if (int(*dataSize)>*maxSize) {
		writeLine("serverLog", "iiRevisionCreate: Files larger than *maxSize bytes cannot store revisions");
		succeed;
	}	


	foreach(*row in SELECT USER_NAME, USER_ZONE WHERE DATA_ID = *dataId AND USER_TYPE = "rodsgroup" AND DATA_ACCESS_NAME = "own") {
	       *groupName = *row.USER_NAME;
		*userZone = *row.USER_ZONE;
	}

	*revisionStore = "/*userZone" ++ UUREVISIONCOLLECTION ++ "/*groupName";

	foreach(*row in SELECT COUNT(COLL_ID) WHERE COLL_NAME = *revisionStore) {
	       	*revisionStoreExists = bool(int(*row.COLL_ID));
       	}

	if (*revisionStoreExists) {
		msiGetIcatTime(*timestamp, "icat");
		*iso8601 = timestrf(datetime(int(*timestamp)), "%Y%m%dT%H%M%S%z");
		*revFileName = *basename ++ "_" ++ *iso8601 ++ *dataOwner;
		*revColl = *revisionStore ++ "/" ++ *collId;
		*revPath = *revColl ++ "/" ++ *revFileName;
		*err = errorcode(msiDataObjCopy(*path, *revPath, "verifyChksum=", *msistatus));
		if (*err < 0) {
			if (*err == -312000) {
			# -312000 OVERWRITE_WITHOUT_FORCE_FLAG
				writeLine("serverLog", "iiRevisionCreate: *revPath already exists. This means that *basename was changed multiple times within the same second.");
				succceed;
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


# \brief iiRevisionRemove
# \param[in] revision_id
iiRevisionRemove(*revisionId) {
	*isfound = false;
	*revisionStore =  "/$rodsZoneClient" ++ UUREVISIONCOLLECTION;
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE DATA_ID = "*revisionId" AND COLL_NAME like "*revisionStore/%") {
		if (!*isfound) {
			*isfound = true;
			*objPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		} else {
			writeLine("serverLog", "iiRevisionRemove: *revisionId returned multiple results");
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


# \brief iiRevisionRestore
# \param[in] revision_id        id of revision data object
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
iiRevisionRestore(*revisionId, *target, *overwrite, *status, *statusInfo) {
      #| writeLine("stdout", "Restore a revision");
        *status = "Unknown error";
        *isfound = false;
        *executeRestoration = false;
	*statusInfo = '';

        foreach(*rev in SELECT DATA_NAME, COLL_NAME WHERE DATA_ID = *revisionId) {
                if (!*isfound) {
                        *isfound = true;
                        *revName = *rev.DATA_NAME; # revision name is suffixed with a timestamp for uniqueness
                        *revCollName = *rev.COLL_NAME;
                        *src = *revCollName ++ "/" ++ *revName;
                        writeLine("serverLog", "Source is: *src");
                }
        }

        if (!*isfound) {
                writeLine("serverLog", "uuRevisionRestore: Could not find revision *revisionId");
                *status = "RevisionNotFound";
                succeed;
        }

       # Get MetaData
        msiString2KeyValPair("", *kvp);
        uuObjectMetadataKvp(*revisionId, UUORGMETADATAPREFIX, *kvp);

        if (!uuCollectionExists(*target)) {
                writeLine("serverLog", "uuRevisionRestore: Cannot find target collection *target");
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
                if(*existsTargetFile) {
                        # User decision required
                        writeLine("serverLog", "File exists already");
                        *status = "FileExists";
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
                        #new file name is entered by user and can be a duplicate again. So check first.
			*newFileNameExists = false;
			foreach (*row in  SELECT DATA_NAME WHERE COLL_NAME = *target AND DATA_NAME = *newFileName ){
				*newFileNameExists = true;
				break;	
			}	
			
			if (!*newFileNameExists) {
				*dst = *target ++ "/" ++ *newFileName;
                        	*executeRestoration = true;
			}
			else {
				*status = "FileExistsEnteredByUser";
				succeed;
			}	
                }
                else {
                        *statusInfo = "Illegal overwrite flag *overwrite";
			writeLine("serverLog", "uuRevisionRestore: *statusInfo");
                        *status = "Unrecoverable";
			succeed;
                }
        }

        # Actual restoration
        if (*executeRestoration) {
                msiAddKeyValToMspStr("verifyChksum", "", *options);
                writeLine("serverLog", "uuRevisionRestore: *src => *dst [*options]");
                *err = errormsg(msiDataObjCopy("*src", "*dst", *options, *msistatus), *errmsg);
                if (*err < 0) {
			if (*err==-818000) {
				*status = "PermissionDenied";
				succeed;
			}                        
			*statusInfo = "Restoration failed with error *err: *errmsg";
                        writeLine("serverLog", "uuRevisionRestore: *statusInfo");
                        *status = "Unrecoverable";
                } else {
                        *status = "Success";
                }
        }
}


# \brief iiRevisionList list revisions of path
# \param[in]  path     Path of original file
# \param[out] result   List in JSON format with all revisions of the original path
iiRevisionList(*path, *result) {
	#| writeLine("stdout", "List revisions of path");
	*revisions = list();
	*startpath = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION;
	*originalPathKey =  UUORGMETADATAPREFIX ++ 'original_path';
	*isFound = false;
	foreach(*row in SELECT DATA_ID, COLL_NAME, order(DATA_NAME) 
		        WHERE META_DATA_ATTR_NAME = *originalPathKey
		   	AND META_DATA_ATTR_VALUE = *path
			AND COLL_NAME like '*startpath/%%') {
		msiString2KeyValPair("", *kvp);
		*isFound = true;
		*id = *row.DATA_ID;
		# writeLine("serverLog", "DataID: *id");
		*kvp.id = *id;
		*kvp.revisionPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		foreach(*meta in SELECT META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE WHERE DATA_ID = *id) {
			*name = *meta.META_DATA_ATTR_NAME;
			*val = *meta.META_DATA_ATTR_VALUE;
			# writeLine("serverLog","metada: *name - *val");
			msiAddKeyVal(*kvp, *name, *val);	
		}

		*revisions = cons(*kvp, *revisions);
	}
	
	uuKvpList2JSON(*revisions, *result, *size);	
}

# \brief iiRevisionCalculateEndOfCalendarDay    Calculate the unix timestamp for the end of the current day (Same as start of next day)
# param[out] endOfCalendarDay		Timestamp of the end of the current day
iiRevisionCalculateEndOfCalendarDay(*endOfCalendarDay) {
		msiGetIcatTime(*timestamp, "unix"); # Get current Timestamp
		*bdY = timestrf(datetime(int(*timestamp)), "%b %d %Y"); # Generate string of current date (e.g. Jan 14 1982).	
		
		*endofcalendarday_dt = datetime(*bdY ++ " 23:59:59"); # Append the last second of the day and convert to datetime
		*endofcalendarday_str = timestrf(*endofcalendarday_dt, "%s"); # Generate string of unix timestamp of the last second of the day
		*endOfCalendarDay =  int(*endofcalendarday_str) + 1; # Convert to integer and add 1 second to get 00:00 of the next day
}

# \datatype uurevisioncandidate    Represents a revision with a timestamp with an integer for the timestamp and a string for the DATA_ID.
#                                  A removed candidate is represented with an empty dataconstructor
data uurevisioncandidate = 
	| uurevisioncandidate : integer * string -> uurevisioncandidate
	| uurevisionremoved : uurevisioncandidate

# \function uurevisionisremoved   Check if a revisioncandidate is removed by matching it with its constructor
uurevisionisremoved(*r) =
	match *r with
		| uurevisionremoved => true
		| uurevisioncandidate(*i, *s) => false

# \datatype uubucket   Represents a time bucket where a number of revisions should be kept with three integers
#                      The first integer represents a time offset
#                      The second integer represents the number of revisions that can stay in the bucket
#                      The third integer represents the starting index when revisions need to remove. 0 is the newest, -1 the oldest
#                      revision after the current original (which should always be kept) , 1 the revision after that, etc.
data uubucket =
	| uubucket : integer * integer * integer -> uubucket


# iRODS timestamps are in seconds since epoch (1970-01-01 00:00 UTC). Express minutes, hours, days and weeks in seconds
uuminutes(*m) = *m * 60
uuhours(*h) = *h * uuminutes(60)
uudays(*d) = *d * uuhours(24)
uuweeks(*w) = *w * uudays(7) 

# \brief iiRevisionBucketList   Return a list of time buckets to determine revisions to keep
# \param[in] case    Select a bucketlist based on a string
# \returnvalue lst   A bucket list
iiRevisionBucketList(*case) {
	if (*case == "A") {
		*lst = list(
			 uubucket(uuhours(6),  1, 1),
			 uubucket(uuhours(12), 1, 0),
			 uubucket(uuhours(18), 1, 0),
			 uubucket(uudays(1),   1, 0),
			 uubucket(uudays(2),   1, 0),
			 uubucket(uudays(3),   1, 0),
			 uubucket(uudays(4),   1, 0),
			 uubucket(uudays(5),   1, 0),
			 uubucket(uudays(6),   1, 0),
			 uubucket(uuweeks(1),  1, 0),
			 uubucket(uuweeks(2),  1, 0),
			 uubucket(uuweeks(3),  1, 0),
			 uubucket(uuweeks(4),  1, 0),
			 uubucket(uuweeks(8),  1, 0),
			 uubucket(uuweeks(12), 1, 0),
			 uubucket(uuweeks(16), 1, 0)
		); 
	} else if (*case == "J")  {
		*lst = list(
                         uubucket(uuminutes(5),    1, 1),
                         uubucket(uuminutes(10),   1, 0),
                         uubucket(uuminutes(15),   1, 0),
                         uubucket(uuminutes(20),   1, 0),
                         uubucket(uuminutes(40),   1, 0),
                         uubucket(uuminutes(60),   1, 0),
                         uubucket(uuminutes(80),   1, 0),
                         uubucket(uuminutes(100),  1, 0),
                         uubucket(uuminutes(120),  1, 0),
                         uubucket(uuminutes(140),  1, 0),
                         uubucket(uuminutes(280),  1, 0),
                         uubucket(uuminutes(320),  1, 0),
                         uubucket(uuminutes(460),  1, 0),
                         uubucket(uuminutes(920),  1, 0),
                         uubucket(uuminutes(1380), 1, 0),
                         uubucket(uuminutes(1820), 1, 0)
                         );
	} else if (*case == "Simple") {
		*lst = list(uubucket(uuweeks(16), 16, 4));
	} else {
		# Case B and default
		*lst = list(
			 uubucket(uuhours(12), 2, 0),
			 uubucket(uudays(1),   2, 1),
			 uubucket(uudays(3),   2, 1),
			 uubucket(uudays(5),   2, 1),
			 uubucket(uuweeks(1),  2, 1),
			 uubucket(uuweeks(3),  2, 1),
			 uubucket(uuweeks(8),  2, 1),
			 uubucket(uuweeks(16), 2, 1)
		);
	}
	*lst;
}

# \brief iiRevisionStrategy    Determine which revisions should be removed and which to remove based on a bucketlist
# \param[in]  path              full path of original
# \param[in]  endOfCalendarDay  Unix timestamp of the end of the calendar day you want regard as startpoint of the time buckets
# \param[in]  bucketlist        list of uubuckets consisting of an offset, size and start index
# \param[out] keep             list of revisions to keep
# \param[out] remove           list of revisions to remove
iiRevisionStrategy(*path, *endOfCalendarDay, *bucketlist, *keep, *remove) {
	*keep = list();
	*remove = list();
	*revisions = list();
	*originalPathKey = UUORGMETADATAPREFIX ++ "original_path";
	*revisionStore = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION;
	foreach(*row in SELECT DATA_ID, order(DATA_NAME) WHERE META_DATA_ATTR_NAME = *originalPathKey
		                                         AND META_DATA_ATTR_VALUE = *path
							 AND COLL_NAME like "*revisionStore%") {
		*id = *row.DATA_ID;
		uuObjectMetadataKvp(*id, UUORGMETADATAPREFIX, *mdkvp);
		msiGetValByKey(*mdkvp, UUORGMETADATAPREFIX ++ "original_modify_time", *modifyTime);
		*revisions = cons(uurevisioncandidate(int(*modifyTime), *id), *revisions);
	}
	
	# If no revisions are found, no revisions need to be removed
	if (size(*revisions) < 1) {
		writeLine("serverLog", "iiRevisionStrategy: Nothing to do, no revisions found for *path");
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
		uubucket(*offset, *sizeOfBucket, *startIdx) = *bucket;
	#	writeLine("stdout", "Bucket: offset[*offset] sizeOfBucket[*sizeOfBucket] startIdx[*startIdx]");
		*startTime = *endOfCalendarDay - *offset; 
		# each revision newer than the startTime of the bucket is a candidate to keep or remove in that bucket
		*candidates = list();
		*n = size(*revisions);
		for(*i = 0;*i < *n; *i = *i + 1) {
			*revision = hd(*revisions);
			# use pseudo data constructor uurevisioncandidate to initialize timeInt and id.
			uurevisioncandidate(*timeInt, *id) = *revision;
	#		writeLine("stdout", "*timeInt: *id");
			if (*timeInt > *startTime) {
	#			writeLine("stdout", "*timeInt > *offset");
				*candidates = cons(*revision, *candidates);
				*revisions = tl(*revisions);
			} else {
	#			writeLine("stdout", "break;");
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
				for(*idx = *sizeOfCandidates + *startidx; *idx > (*sizeOfCandidates + *startIdx - *nToRemove); *idx = *idx - 1) {
					*toRemove = elem(*candidates, *idx);
					*remove = cons(*toRemove, *remove);
					*candidates = setelem(*candidates, *idx, uurevisionremoved);
				}
			} else {
				# If startIdx is zero or higher go newest to oldest.
				for(*idx = *startIdx;*idx < (*nToRemove + *startIdx); *idx = *idx + 1) {
					*toRemove = elem(*candidates, *idx);
					*remove = cons(*toRemove, *remove);
					*candidates = setelem(*candidates, *idx, uurevisionremoved);
				}
			}
		}

		foreach(*toKeep in *candidates) {	
			# Every candidate not marked for removal is added to the keep list
			if(!uurevisionisremoved(*toKeep)) {	
				*keep = cons(*toKeep, *keep);
			}
		}
	}	

	# All remaining revisions are older than the oldest bucket.
	foreach(*revision in *revisions) {
		*remove = cons(*revision, *remove);
	}
}

# \brief iiRevisionSearchByOriginalPath 
iiRevisionSearchByOriginalPath(*searchstring, *orderby, *ascdesc, *limit, *offset, *result) {
	*fields = list("META_DATA_ATTR_VALUE", "COUNT(DATA_ID)", "DATA_NAME");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_path"),
			   uumakelikecondition("META_DATA_ATTR_VALUE", *searchstring));
	*startpath = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION;
	*conditions = cons(uumakestartswithcondition("COLL_NAME", *startpath), *conditions);

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList);
	
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

# \brief iiRevisionSearchByOriginalFilename
iiRevisionSearchByOriginalFilename(*searchstring, *orderby, *ascdesc, *limit, *offset, *result) {
	*originalDataNameKey = UUORGMETADATAPREFIX ++ "original_data_name";
	*fields = list("COLL_NAME", "META_DATA_ATTR_VALUE");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", *originalDataNameKey),
        		   uumakelikecondition("META_DATA_ATTR_VALUE", *searchstring));	
	*startpath = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION;
	*conditions = cons(uumakestartswithcondition("COLL_NAME", *startpath), *conditions);

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList);
	
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
				*latestRevModifiedTime = int(*revModifyTime);
				*oldestRevModifiedTime = int(*revModifyTime);
			} else {
				*latestRevModifiedTime = max(*latestRevModifiedTime, int(*revModifyTime));
				*oldestRevModifiedTime = min(*oldestRevModifiedTime, int(*revModifyTime));
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

# \brief iiRevisionSearchByOriginalId
# Id stays the same after file renames.
iiRevisionSearchByOriginalId(*searchid, *orderby, *ascdesc, *limit, *offset, *result) {
	*fields = list("COLL_NAME", "DATA_NAME", "DATA_ID", "DATA_CREATE_TIME", "DATA_MODIFY_TIME", "DATA_CHECKSUM", "DATA_SIZE");
	*conditions = list(uucondition("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_id"));
        *conditions = cons(uucondition("META_DATA_ATTR_VALUE", "=", *searchid), *conditions);	
	*startpath = "/" ++ $rodsZoneClient ++ "/revisions";
	*conditions = cons(uumakestartswithcondition("COLL_PARENT_NAME", *startpath), *conditions);

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList);

	foreach(*kvp in tl(*kvpList)) {
		*id = *kvp.DATA_ID;
		uuObjectMetadataKvp(*id, UUORGMETADATAPREFIX, *kvp);
	}

	*kvpList = cons(hd(*kvpList), uuListReverse(tl(*kvpList)));
	
	uuKvpList2JSON(*kvpList, *json_str, *size);
	*result = *json_str;
}

