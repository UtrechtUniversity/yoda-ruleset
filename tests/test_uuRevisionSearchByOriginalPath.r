test_RevisionSearchByOriginalPath {
	if (*testPath == "") {
		*testPath = "/" ++ $rodsZoneClient ++ "/home/grp-test/revisioncreate/revisiontest.txt";
	}
	uuRevisionSearchByOriginalPath(*testPath, "", "", 10, 0, *result);
	writeLine("stdout", *result);
}

INPUT *testPath = ""
OUTPUT ruleExecOut
