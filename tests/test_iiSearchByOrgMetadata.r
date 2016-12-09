testSearchByMetadata {

	writeLine("stdout", "Searching for Collections with " ++ ORGMETADATAPREFIX ++ "*attrname = *searchstring");

	iiSearchByOrgMetadata(*startpath, *searchstring, *attrname, *orderby, *ascdesc, *limit, *offset, *result);
	writeLine("stdout", *result);
}

 
INPUT *startpath="", *searchstring="Datapackage", *attrname="type", *orderby="COLL_NAME", *ascdesc="asc", *limit=10, *offset=0, *cleanup=1
OUTPUT ruleExecOut
