test_RevisionSearchByOriginalPath {
	if (*searchstring == "") {
		*searchstring = "/" ++ $rodsZoneClient ++ "/home/grp-test/revisioncreate/revisiontest.txt";
	}
	uuRevisionSearchByOriginalPath(*searchstring, "", "", 10, 0, *result);
	writeLine("stdout", *result);
}

INPUT *searchstring = ""
OUTPUT ruleExecOut
