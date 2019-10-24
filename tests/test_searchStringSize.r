testRule {
	*i = 0;
	*searchstring="a";
	while (*i<2700) {
	  *searchstring = *searchstring ++ "a";
	  *searchStringEscaped = *searchstring;
	   iiSearchByMetadata(*startpath, *searchstring, *searchStringEscaped, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result, *status, *statusInfo);
	   *i = *i + 1;
	   if (*status != "Success") { 
	   	writeLine("stdout", "*i: *status - *statusInfo");
		break;
	  }
	}

}

INPUT *startpath="/tempZone/home", *collectionOrDataObject="Collection", *orderby="COLL_NAME", *ascdesc="asc", *limit=10, *offset=0
OUTPUT ruleExecOut
