testSearchByName {
	
	iiSearchByName(*startpath, *searchstring, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result);
	writeLine("stdout", *result);
}

 
INPUT *startpath="", *searchstring="test", *collectionOrDataObject="DataObject", *orderby="COLL_NAME", *ascdesc="asc", *limit=10, *offset=0
OUTPUT ruleExecOut
