test_RevisionSearchByOriginalPath {
	uuRevisionSearchByOriginalFilename(*searchstring, "", "", 10, 0, *result);
	writeLine("stdout", *result);
}

INPUT *searchstring = "test"
OUTPUT ruleExecOut
