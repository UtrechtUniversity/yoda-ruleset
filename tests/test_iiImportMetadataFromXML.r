test_iiImportMetadataFromXML {

	iiImportMetadataFromXML(*metadataxmlpath, *xslpath);
	
	uuChopPath(*metadataxmlpath, *parent, *basename);

	foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME = *parent) {
		*attr =  *row.META_COLL_ATTR_NAME;
		*val = *row.META_COLL_ATTR_VALUE;
		writeLine("stdout", "*attr: *val");
	}
}

input *metadataxmlpath="", *xslpath=""
output ruleExecOut
