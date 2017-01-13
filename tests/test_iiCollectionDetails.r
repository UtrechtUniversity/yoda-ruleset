testiiCollectionDetails {
	if (*testPath == "") {
		*testPath = "/" ++ $rodsZoneClient ++ "/home";
	}
	iiCollectionDetails(*testPath, *result);
	writeLine("stdout", *result);
}

input *testPath=""
output ruleExecOut
