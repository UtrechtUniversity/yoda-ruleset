testSearchByMetadata {

	if (*testPath == "") {
		*testPath = "/" ++ $rodsZoneClient ++ "/home/grp-test/searchmetadatatest";
	}

	uuChopPath(*testPath, *parent, *basename);

	if (!uuCollectionExists(*parent)) {
		failmsg(-317000, "*parent does not exist or is not a collection or is hidden from current user");
	}


	*err = errorcode(msiCollCreate(*testPath, 0, *status));
	if (*err < 0) {
		writeLine("stdout", "Failed to create *testPath. errorcode=*err");
	} else {
		writeLine("stdout", "Created *testPath");
	}

	*testkvp.usr_test1 = "test1";
	*testkvp.usr_test2 = "test2";
	*err = errorcode(msiAssociateKeyValuePairsToObj(*testkvp, *testPath, "-C"));
       	if (*err < 0) {
		writeLine("stdout", "Failed to add \*testkvp to *testPath");
	}

	iiSearchByMetadata(*startpath, *searchstring, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result);
	writeLine("stdout", *result);
	
	if (bool(*cleanup)) {
		msiRmColl(*testPath, "forceFlag=", *status);
	}
}

 
INPUT *testPath = "", *startpath="", *searchstring="test", *collectionOrDataObject="Collection", *orderby="COLL_NAME", *ascdesc="asc", *limit=10, *offset=0, *cleanup=1
OUTPUT ruleExecOut
