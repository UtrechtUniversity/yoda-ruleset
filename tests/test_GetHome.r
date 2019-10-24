testGetHome {
	*home = "/" ++ $rodsZoneClient ++ "/" ++ $userNameClient;
	writeLine("stdout", *home);
	foreach(*row in SELECT COLL_NAME, COLL_ID WHERE COLL_PARENT_NAME = *home) {
		writeLine("stdout", *row);
	}
}

INPUT null
OUTPUT ruleExecOut
