test_iiRemoveAllMetadata {

	if (*testPath == "") {
		*testPath = "/$rodsZoneClient/home/research-test/meta";
	}

	iiRemoveAllMetadata(*testPath);

}

input *testPath=""
output ruleExecOut
