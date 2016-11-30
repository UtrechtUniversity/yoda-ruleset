testBrowseHome {
	*home = "/" ++ $rodsZoneClient ++ "/home/" ++ $userNameClient;
	writeLine("stdout", *home);
	iiBrowse(*home,"Collection","COLL_NAME", "asc", 100,0, *result);
	writeLine("stdout", *result);
}

INPUT null
OUTPUT ruleExecOut
