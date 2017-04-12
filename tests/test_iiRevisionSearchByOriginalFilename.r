test_iiRevisionSearchByOriginalPath {
	iiRevisionSearchByOriginalFilename(*searchstring, "", "", 100, 0, *result);
	writeLine("stdout", *result);
}

INPUT *searchstring = "test"
OUTPUT ruleExecOut
