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
	
	*path = *testPath ++ "/revisiontest2.txt";	
	# *options = "";
	# *err = errorcode(msiDataObjCreate(*path, *options, *fd));
        # if (*err == -312000) {
	# 	writeLine("stdout", "*path already exists. Opening for write");
	# 	msiAddKeyValToMspStr("objPath", *path, *options);
	# 	msiAddKeyValToMspStr("openFlags", "O_WRONLY", *options);
	# 	msiDataObjOpen(*options, *fd);
	# 	msiDataObjLseek(*fd, 0, "SEEK_END", *status);
	# } else if (*err < 0) {
	# 	writeLine("stdout", "Failed to create *path. errorcode=*err");
	# } else {
	# 	writeLine("stdout", "Created *path");
	# }

	msiGetIcatTime(*datetime, "human");
	#msiGetFormattedSystemTime(*datetime, "human", "%%A %%Y-%%m-%%d %%H:%%M:%%S %%Z");
	# *msg = "Line added at *datetime\n";
	# *len = strlen(*msg);
	# msiDataObjWrite(*fd, *msg, *len);
	# msiDataObjClose(*fd,*status);

	# *err = errorcode(uuRevisionCreate(*path, *id));
	# writeLine("stdout", "uuRevisionCreate: errorcode=*err");

	#writeLine("stdout", "Calling uuRevisionList");
	#uuRevisionList(*path, *revisions);

	#uuKvpList2JSON(*revisions, *json_str, *size);
	#writeLine("stdout", *json_str);

	#writeLine("stdout", "Calling uuRevisionSearchByName");

	#uuRevisionSearchByName(*path, "DATA_CREATE_TIME", "desc", 10, 0, *result);
	#writeLine("stdout", *result);
}


INPUT *testPath=""
OUTPUT ruleExecOut
