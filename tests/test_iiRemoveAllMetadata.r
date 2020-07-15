test_iiRemoveAllMetadata {

	if (*testPath == "") {
		*testPath = "/$rodsZoneClient/home/research-test/meta";
	}

	rule_meta_remove(*testPath);

}

input *testPath=""
output ruleExecOut
