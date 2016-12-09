testMoveDPTXT {
	*err = errorcode(msiCollCreate(*testPath, 0, *status));
	if (*err < 0) {
		writeLine("stdout", "Failed to create *testPath. errorcode=*err");
	} else {
		writeLine("stdout", "Created *testPath");
	}
	*src = *testPath ++ "/source";
	*err = errorcode(msiCollCreate(*src, 0, *status));
	if (*err < 0) {
		writeLine("stdout", "Failed to create *src. errorcode=*err");
	} else {
		writeLine("stdout", "Created *src.");
	}
	iiGetCollectionType(*src, *orgtype);
	writeLine("stdout", "*src is now a *orgtype");
	iiCreateDataPackage(*src, *status);
	writeLine("stdout", DPTXTNAME ++ " created in *src");
	iiGetCollectionType(*src, *orgtype);
	writeLine("stdout", "*src is now: *orgtype");
	*dst = *testPath ++ "/dest";
	*err = errorcode(msiCollCreate(*dst, 0, *status));
	if (*err < 0) {
		writeLine("stdout", "Failed to create *dst. errorcode=*err");
	} else {
		writeLine("stdout", "Created *dst. status=*status");
	}
	iiGetCollectionType(*dst, *orgtype);
	writeLine("stdout","*dst is now a *orgtype");
	*src_obj = *src ++ "/" ++ DPTXTNAME;
	*dst_obj = *dst ++ "/" ++ DPTXTNAME;
	*err = errorcode(msiDataObjRename(*src_obj, *dst_obj, 0, *status));
	if (*err < 0) {
		writeLine("stdout", "Failed to move *src_obj to *dst_obj. errorcode=*err");
	} else {
		writeLine("stdout", "Moved *src_obj to *dst_obj. status=*status");
	}
	iiGetCollectionType(*src, *src_orgtype);
	iiGetCollectionType(*dst, *dst_orgtype);
	writeLine("stdout", "*src is a *src_orgtype\n*dst is a *dst_orgtype");
	*err = errorcode(msiDataObjUnlink("objPath=*dst_obj", *status));
	if (*err < 0) {
		writeLine("stdout", "Failed to remove *dst_obj. errorcode=*err");
	} else {
		writeLine("stdout", "*dst_obj was removed");
	}
	iiGetCollectionType(*dst, *orgtype);
	writeLine("stdout","*dst is now a *orgtype");
	*src_obj = *src ++ "/" ++ DPTXTNAME;
	msiRmColl(*testPath, "forceFlag=", *status);
}

INPUT *testPath="/nluu1paul/home/grp-test/mvtest"
OUTPUT ruleExecOut
