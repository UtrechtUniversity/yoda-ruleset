# aanroepen vanuit de TreeWalk functie

uuResetMeta(*path, *name, *isCol, *buffer) {

	*type = "-d";
	*fullPath = *path;
	if (*isCol) {
		*type = "-C";
	   *query = "SELECT META_COLL_ATTR_NAME,META_COLL_ATTR_VALUE WHERE " ++
	         "COLL_NAME = '*path'";

	}
	else {
		*fullPath = "*path/*name";
		*query = "SELECT META_DATA_ATTR_NAME,META_DATA_ATTR_VALUE WHERE " ++
               "DATA_NAME = '*path' AND COLL_NAME = '*path'";
	}
   msiExecStrCondQuery(*query, *rows);
	msiGetContInxFromGenQueryOut(*rows,*rowsLeft);
	*isFirstRowSet = true;
	while ( *isFirstRowSet || *rowsLeft > 0) {
		*isFirstRowSet = false;
		*key="";
		*value="";
		foreach (*rows) {
			if (*isCol) {
				msiGetValByKey(*rows, "META_COLL_ATTR_NAME", *key);
				msiGetValByKey(*rows, "META_COLL_ATTR_VALUE", *value);
			} else {
				msiGetValByKey(*rows, "META_DATA_ATTR_NAME", *key);
				msiGetValByKey(*rows, "META_DATA_ATTR_VALUE", *value);
			}
			msiString2KeyValPair("*key=*value",*kvPair);
#			writeLine("stdout", "key = *key en value = *value");
			msiPrintKeyValPair("stdout",*kvPair);
#			writeLine("stdout", "fullPath=*fullPath= en type=*type=");
			*error = errorcode(
				msiRemoveKeyValuePairsFromObj(*kvPair, *fullPath, *type)
				);
		}
		if (*rowsLeft > 0) {
			msiGetMoreRows(*query,*rows,*rowsLeft);
		}
	}
}
