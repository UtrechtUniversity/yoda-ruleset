testCreateDatapackage {
	if (*testPath == "") {
		*testPath = "/" ++ $rodsZoneClient ++ "/home/grp-test/testCreateDatapackage";
	}
	uuChopPath(*testPath, *parent, *basename);

	if (!uuCollectionExists(*parent)) {
		failmsg(-317000, "*parent does not exist or is not a collection or is hidden from current user");
	}

	*err = errorcode(msiCollCreate(*testPath, 0, *status));
	if (*err < 0) {
		if (*err == -809000) {
			writeLine("stdout", "*testPath already exists. Reusing..");
		} else {
			writeLine("stdout", "Failed to create *testPath. errorcode=*err");
		}
	} else {
		writeLine("stdout", "Created *testPath");
	}

	iiCreateDatapackage(*testPath);
	writeLine("stdout", "iiCreateDatapackage: status=*status");
	iiGetCollectionType(*testPath, *orgtype);
	writeLine("stdout", "*testPath is now a *orgtype");

	if (bool(*demote)) {	
		iiDemoteDatapackage(*testPath);
		writeLine("stdout", "iiDemoteDatapackage: status=*status");
		iiGetCollectionType(*testPath, *orgtype);
		writeLine("stdout", "*testPath is now a *orgtype");
	}

	if (bool(*cleanup)) {
		msiRmColl(*testPath, "forceFlag=", *status);
	}
	
}

INPUT *testPath = "", *demote=1, *cleanup=1
OUTPUT ruleExecOut
