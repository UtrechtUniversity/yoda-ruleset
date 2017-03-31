test_RevisionSearchByOriginalPath {
	iiRevisionSearchByOriginalPath(*searchstring, *orderby, *ascdesc, *limit, *offset, *result);
	writeLine("stdout", *result);
}

INPUT *searchstring="", *orderby="META_DATA_ATTR_VALUE", *ascdesc="asc", *limit=10, *offset=0
OUTPUT ruleExecOut
