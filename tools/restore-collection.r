#!/bin/env irule -F
restoreCollection {

        if (*path == "") {
                writeLine("stdout", "\*path parameter is required (string)");
                succeed;
        }

        if (*timestamp == 0) {
                writeLine("stdout", "\*timestamp parameter is required (timestamp integer)");
                succeed;
        }

        # Make sure rodsadmin can read revisions and write to restore path.
        uuGetUserType(uuClientFullName, *userType);
        if (*userType == 'rodsadmin') {
                # Grant access to revisions.
                msiSetACL("recursive", "admin:own", uuClientFullName, "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION);
                msiSetACL("recursive", "inherit", uuClientFullName, "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION);

                # Grant write access to restore path.
                if (*restorePath != "") {
                       *writePath = *restorePath;
                } else {
                       *writePath = *path;
                }

                if (uuCollectionExists(*writePath)) {
                        msiSetACL("recursive", "admin:write", uuClientFullName, *writePath);
                } else {
                        uuChopPath(*writePath, *parent, *_);
                        while(*parent like regex "/[^/]/home/research-.*") {
                                if (uuCollectionExists(*parent)) {
                                        msiSetACL("recursive", "admin:write", *parent);
                                        break;
                                }
                                uuChopPath(*parent, *grandparent, *_);
                                *parent = *grandparent;
                        }
                }
        }

        # Retrieve all revisions before timestamp.
        iiRevisionListOfCollectionBeforeTimestamp(*path, *timestamp, *revisions);
        *iso8601 = uuiso8601(*timestamp);
        writeLine("stdout", "Restoring revisions of collection *path from before *iso8601.");
        writeLine("stdout", "Restoring to *writePath.");
        writeLine("stdout", "##############################");

        # Restore revisions in path.
        foreach(*revision in *revisions) {
                iirevisionwithpath(*revisionId, *originalPath) = *revision;
                if (*revisionId != "") {
                        foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE DATA_ID = *revisionId) {
                                *revPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
                        }
                        uuChopPath(*originalPath, *coll, *filename);

                        # Hanlde restore path.
                        if (*restorePath != "") {
                                *coll = *restorePath;

                                # Retrieve elemements.
                                *origPathElems = split(*originalPath, "/");
                                *pathElems = split(*path, "/");

                                # Compute the difference.
                                *diff = size(*origPathElems) - size(*pathElems) - 1;

                                # Add missing collections to collection path.
                                for(*i = 0; *i < *diff; *i = *i + 1) {
                                    *el = elem(*origPathElems, size(*pathElems) + *i)
                                    *coll = "*coll/*el"
                                }
                                *originalPath = "*coll/*filename";
                        }

                        # Create collection if it does not exists.
                        if (!uuCollectionExists(*coll)) {
                                msiCollCreate(*coll, 1, *status);
                        }
                        writeLine("stdout", "Restoring *revPath to *originalPath");
                        msiAddKeyValToMspStr("forceFlag", "", *options);
                        msiDataObjCopy(*revPath, *originalPath, *options, *msistatus);
                }
        }
}
input *path="", *timestamp=0, *restorePath=""
output ruleExecOut
