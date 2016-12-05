testIiBrowse {
	iiBrowse(*testPath, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result);
	writeLine("stdout", *result);
	iiCollectionDetails(*testPath, *result);
	writeLine("stdout", *result);
}

INPUT *testPath="/nluu1paul/home/paul", *collectionOrDataObject = "Collection", *orderby="COLL_NAME", *ascdesc="asc", *limit=10, *offset=0
OUTPUT ruleExecOut
