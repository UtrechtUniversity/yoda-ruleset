testiiCollectionDetails {
	if (*testPath == "") {
		*testPath = "/" ++ $rodsZoneClient ++ "/home";
	}
	iiCollectionDetails(*testPath, *result, *status, *statusInfo);
	writeLine("stdout", *result);
}

input *testPath=""
output ruleExecOut
