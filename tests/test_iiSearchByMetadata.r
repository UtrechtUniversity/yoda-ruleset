testSearchByMetadata {
	iiSearchByMetadata(*startpath, *searchstring, *searchStringEscaped, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result, *status, *statusInfo);
	writeLine("stdout", *status);
	writeLine("stdout", *statusInfo);
	writeLine("stdout", *result);
	
}

 
INPUT *testPath = "", *startpath="", *searchstring="test",*searchStringEscaped="test", *collectionOrDataObject="Collection", *orderby="COLL_NAME", *ascdesc="asc", *limit=10, *offset=0
OUTPUT ruleExecOut
