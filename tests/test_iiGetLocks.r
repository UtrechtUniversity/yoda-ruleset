test_iiGetLocks {
	if (*testPath == "") {
		*testPath = "/$rodsZoneClient/home/$userNameClient";
	}
	iiGetLocks(*testPath, *locks, *locked);
	if (*locked) {
		writeLine("stdout", "Locks found on *testPath: *locks");
	} else {
		writeLine("stdout", "No locks found on *testPath: *locks");
	}
	
}

input *testPath=""
output ruleExecOut
