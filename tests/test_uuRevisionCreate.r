testRevisionCreate {
	if (*testPath == "") {
		*testPath = "/" ++ $rodsZoneClient ++ "/home/grp-test/revisioncreate";
	}
	
	if (!uuCollectionExists(*testPath)) {
		*err = errorcode(msiCollCreate(*testPath, 0, *status));
		if (*err < 0) {
			writeLine("stdout", "Failed to create *testPath. errorcode=*err");
		} else {
			writeLine("stdout", "Created *testPath");
		}
	}
	
	*path = *testPath ++ "/revisiontest.txt";	
	*options = "";
	*err = errorcode(msiDataObjCreate(*path, *options, *fd));
        if (*err < 0) {
		writeLine("stdout", "Failed to create *path. errorcode=*err");
		msiAddKeyValToMspStr("objPath", *path, *options);
		msiAddKeyValToMspStr("openFlags", "O_WRONLYO_TRUNC", *options);
		msiDataObjOpen(*options, *fd);
	} else {
		writeLine("stdout", "Created *path");
	}


	*msg = "First line of revisions.txt"
	*len = strlen(*msg);	
	msiDataObjWrite(*fd, *msg, *len);
	msiDataObjClose(*fd,*status);

	uuRevisionCreate(*path, *id, *status);
	writeLine("stdout", "Status of uuRevisionCreate is *status");

	writeLine("stdout", "Calling uuRevisionList");
	uuRevisionList(*path, *revisions);

	uuKvpList2JSON(*revisions, *json_str, *size);
	writeLine("stdout", *json_str);

	writeLine("stdout", "Calling uuRevisionList2");

	uuRevisionList2(*path, "DATA_CREATE_TIME", "desc", 10, 0, *result);
	writeLine("stdout", *result);
}


INPUT *testPath=""
OUTPUT ruleExecOut
