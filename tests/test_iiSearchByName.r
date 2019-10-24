testSearchByName {
	
	iiSearchByName(*startpath, *searchstring, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result, *status, *statusInfo);
	writeLine("stdout", *result);
	if (*status != "Success") {
	writeLine("stdout", *status);
	writeLine("stdout", *statusInfo);
	}

}

 
INPUT *startpath="", *searchstring="test", *collectionOrDataObject="Collection", *orderby="COLL_NAME", *ascdesc="asc", *limit=10, *offset=0
OUTPUT ruleExecOut
