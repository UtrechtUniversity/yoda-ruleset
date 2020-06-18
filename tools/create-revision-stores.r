#!/usr/bin/irule -F
createRevisionStores {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	foreach (*row in SELECT USER_NAME WHERE USER_TYPE = 'rodsgroup' AND USER_NAME like 'research-%') {
		*groupName = *row.USER_NAME;

		*revisionStore = "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION ++ "/" ++ *groupName;
		if (!uuCollectionExists(*revisionStore)) {
			writeLine("stdout", "Creating *revisionStore");
			msiCollCreate(*revisionStore, 1, *status);
			msiSetACL("recursive", "own", *groupName, *revisionStore);

			*previousPath = "";
			*groupColl = "/$rodsZoneClient/home/*groupName"
			writeLine("stdout", "Scanning *groupColl for data objects to create initial revisions");

			# rodsadmin needs at least read access to research group to copy data
			# unfortunately msiCheckAccess does not check for group membership, but it won't be a problem
			# when we add a user level ACL.
			msiCheckAccess(*groupColl, "read object", *readPermission);

			if (*readPermission == 0) {
				writeLine("stdout", "Granting read access to *groupColl");
				msiSetACL("recursive", "admin:read", uuClientFullName, *groupColl);
			}

			*count = 0;
			# First process the main collection
			foreach(*row in SELECT COLL_NAME, DATA_NAME, DATA_RESC_NAME where COLL_NAME = *groupColl) {
				*collName = *row.COLL_NAME;
				*dataName = *row.DATA_NAME;
				*resource = *row.DATA_RESC_NAME;
				*path = "*collName/*dataName";

				*skip = false;

				foreach(*filter in UUBLOCKLIST) {
					if (*dataName like *filter) {
						writeLine("stdout", "Ignore *path for revision store. Filter *filter matches");
						*skip = true;
						break;
					}
				}

				if (*path == *previousPath) {
					# Skip replicas
					*skip = true;
				}

				if (!*skip) {
					# We need read access on the original object
					# unfortunately msiCheckAccess does not check for group membership, but it won't be a problem
					# when we add a user level ACL.
					msiCheckAccess(*path, "read object", *objectReadPermission);
					if (*objectReadPermission == 0) {
						writeLine("stdout", "Granting read access to *path");
						msiSetACL("default", "admin:read", uuClientFullName, *path);
					}

					iiRevisionCreate(*resource, *path, UUMAXREVISIONSIZE, *id);
					if (*id != "") {
				        	writeLine("serverLog", "Revision created for *path with id: *id");
					}

					if (*objectReadPermission == 0) {
						writeLine("stdout", "Revoking read access to *path");
						msiSetACL("default", "admin:null", uuClientFullName, *path);
					}

					*previousPath = *path;
					*count = *count + 1;
				}
			}
			# Then process the rest of the tree
			foreach(*row in SELECT COLL_NAME, DATA_NAME, DATA_RESC_NAME where COLL_NAME like "*groupColl/%") {
				*collName = *row.COLL_NAME;
				*dataName = *row.DATA_NAME;
				*resource = *row.DATA_RESC_NAME;
				*path = "*collName/*dataName";

				*skip = false;

				foreach(*filter in UUBLOCKLIST) {
					if (*dataName like *filter) {
						writeLine("stdout", "Ignore *path for revision store. Filter *filter matches");
						*skip = true;
					}
				}

				if (*path == *previousPath) {
					# Skip replicas
					*skip = true;
				}

				if (!*skip) {
					msiCheckAccess(*path, "read object", *objectReadPermission);
					if (*objectReadPermission == 0) {
						writeLine("stdout", "Granting read access to *path");
						msiSetACL("default", "admin:read", uuClientFullName, *path);
					}

					iiRevisionCreate(*resource, *path, UUMAXREVISIONSIZE, *id);
					if (*id != "") {
				        	writeLine("serverLog", "Revision created for *path with id: *id");
					}

					if (*objectReadPermission == 0) {
						writeLine("stdout", "Revoking read access to *path");
						msiSetACL("default", "admin:null", uuClientFullName, *path);
					}

					*previousPath = *path;
					*count = *count + 1;
				}
			}

			writeLine("stdout", "*count revisions created");

			# Remove the temporary read ACL
			if (*readPermission == 0) {
				writeLine("stdout", "Revoking read access to *groupColl");
				msiSetACL("recursive", "admin:null", uuClientFullName, *groupColl);
			}




		}

	}
}

input null
output ruleExecOut
