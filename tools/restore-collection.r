#!/bin/env irule -F
restoreCollection {
	
	if (*path == "") {
		writeLine("stdout", "\*path parameter is required");
		succeed;
	}

	if (*timestamp == 0) {
		writeLine("stdout", "\*timestamp parameter is required");
		succeed;
	}

	uuGetUserType(uuClientFullName, *userType);
	if (*userType == 'rodsadmin') {
		writeLine("stdout", "Ensure rodsadmin has permission to write to *path");
		msiSetACL("recursive", "admin:own", uuClientFullName, "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION);
		msiSetACL("recursive", "inherit", uuClientFullName, "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION);
		if (uuCollectionExists(*path)) {
			msiSetACL("recursive", "admin:write", uuClientFullName, *path);
		} else {
			uuChopPath(*path, *parent, *_);
			while(*parent like regex "/[^/]/home/research-") {
				if (uuCollectionExists(*parent)) {
					msiSetACL("recursive", "admin:write", *parent);
					break;
				}
				uuChopPath(*parent, *grandparent, *_);
				*parent = *grandparent;
			}
		}
			
	}


	
	iiRevisionListOfCollectionBeforeTimestamp(*path, *timestamp, *revisions); 
	foreach(*revision in *revisions) {
		uurevisionwithpath(*revisionId, *originalPath) = *revision;
		if (*revisionId != "") {
			foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE DATA_ID = *revisionId) {
				*revPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
			}
			uuChopPath(*originalPath, *coll, *filename);
			if (!uuCollectionExists(*coll)) {
				msiCollCreate(*coll, 1, *status);
			}
			writeLine("stdout", "Restoring *revPath to *originalPath");
			msiAddKeyValToMspStr("forceFlag", "", *options);
			msiDataObjCopy(*revPath, *originalPath, *options, *msistatus);
		}
			
	}

}

input *path="", *timestamp=0
output ruleExecOut
