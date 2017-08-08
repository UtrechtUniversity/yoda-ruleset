test_uuRevisionRemove_all {
	if (*testPath == "") {
		failmsg(-1, "To remove all revisions of a original path provide a *testPath");
	} else {
		foreach(*row in SELECT DATA_ID, DATA_NAME, COLL_NAME WHERE META_DATA_ATTR_NAME = "org_original_path"  AND META_DATA_ATTR_VALUE = *testPath) {
			*id = *row.DATA_ID;
			*coll = *row.COLL_NAME;
			*name = *row.DATA_NAME;
			writeLine("stdout", "uuRevisionRemove: Removing *coll/*name");
			iiRevisionRemove(*id);
		}
	}

}

INPUT *testPath = ""
OUTPUT ruleExecOut
