test_RevisionSearchByOriginalPath {
	if (*testPath == "") {
		*testPath = "/" ++ $rodsZoneClient ++ "/home/grp-test/revisioncreate/revisiontest.txt";
	}
	uuRevisionSearchByOriginalPath(*testPath, "DATA_CREATE_TIME", "desc", 10, 0, *result);
	writeLine("stdout", *result);
}

INPUT *testPath = ""
OUTPUT ruleExecOut
