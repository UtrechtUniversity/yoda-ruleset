timeshift {
	writeLine("stdout", "*revisionId: *newTimestamp");
	*isFound = false;
	foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE DATA_ID = "*revisionId") {
		*isFound = true;
		*collName = *row.COLL_NAME;
		*dataName = *row.DATA_NAME;
	}
	
	if (!*isFound) {
		writeLine("stdout", "Revision *revisionId not Found");
		succeed;
	}
	
	*paddedTimestamp =  str(*newTimestamp);
	*npad = 11 - strlen(*paddedTimestamp);
	for(*i = 0; *i < *npad; *i = *i + 1) {
		*paddedTimestamp = "0" ++ *paddedTimestamp;
	}
	
	*revPath = "*collName/*dataName";
	msiString2KeyValPair(UUORGMETADATAPREFIX ++ "original_modify_time=" ++ *paddedTimestamp, *kvp);
	msiSetKeyValuePairsToObj(*kvp, *revPath, "-d");
		
	uuObjectMetadataKvp("*revisionId", UUORGMETADATAPREFIX, *mdkvp);
	msiGetValByKey(*mdkvp, UUORGMETADATAPREFIX ++ "original_data_name", *oriDataName);
       	msiGetValByKey(*mdkvp, UUORGMETADATAPREFIX ++ "original_data_owner_name", *oriDataOwner);
	*newDataName = *oriDataName ++ "_" ++ uuiso8601(*paddedTimestamp) ++ *oriDataOwner;
	*newRevPath = "*collName/*newDataName";
	msiDataObjRename(*revPath, *newRevPath, 0, *status);

}

input *revisionId=$revisionId, *newTimestamp=$newTimestamp
output ruleExecOut
