test_iiPrepareMetadataForm {
	iiPrepareMetadataForm(*testPath, *result);
	writeLine("stdout", *result);
}

input *testPath=""
output ruleExecOut
