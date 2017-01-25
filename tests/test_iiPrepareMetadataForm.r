test_iiPrepareMetadataForm {
	foreach(*row in SELECT USER_GROUP_NAME, COLL_ACCESS_TYPE, COLL_ACCESS_NAME, COLL_ACCESS_USER_ID, COLL_ACCESS_COLL_ID WHERE COLL_NAME = *testPath) {
		writeLine("stdout", *row);
	}
}

input *testPath=""
output ruleExecOut
