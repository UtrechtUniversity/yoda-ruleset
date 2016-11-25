#| myTestRule {
#|	if (uuCollectionExists(*coll_name)) {
#|		writeLine("stdout", "Collection Exists");	
#|	} else {
#|		writeLine("stdout", "Collection Does not exist");
#|	}
#|
#|	#msiString2KeyValPair("test=testmij",*kvp);	
#|	uuObjectMetadataKvp(*data_id,"", *kvp);
#|      	writeLine("stdout", *kvp);
#|
#|	uuObjectMetadataKvp(*data_id,"original", *kvp);
#|	
#|}

# \brief uuCollectionExists checks if a collection exists
# \description Used to be iicollectionexists from Jan de Mooij
#
# \param[in] collectionname	name of the collection
uuCollectionExists(*collectionname) {
	*exists = false;
	foreach (*row in SELECT COLL_NAME WHERE COLL_NAME = '*collectionname') {
		*exists = true;
		break;
	}
	*exists;
}

# \brief uuObjectMetadataKvp return a key-value-pair of metadata associated with a dataobject
#				If a key is defined multiple times, the last found will be returned
# \param[in]  data_id	Unique DataObject ID. Used because it is Unique
# \param[in]  prefix	Only include metadata with this prefix
# \param[in,out] kvp	key-value-pair to add the metadata to
uuObjectMetadataKvp(*data_id, *prefix, *kvp) {
	*ContInxOld = 1;
	msiMakeGenQuery("META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE", "DATA_ID = '*data_id'", *GenQInp);
	if (*prefix != "") {
		#| writeLine("stdout", "prefix is *prefix");
		msiAddConditionToGenQuery("META_DATA_ATTR_NAME", " like ", "'*prefix%%'", *GenQInp);
	}
	msiExecGenQuery(*GenQInp, *GenQOut);
	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);
	while(*ContInxOld > 0) {
		foreach(*meta in *GenQOut) {
			*name = *meta.META_DATA_ATTR_NAME;
			*val = *meta.META_DATA_ATTR_VALUE;
			msiAddKeyVal(*kvp, *name, *val);	
		}
		*ContInxOld = *ContInxNew;
		if(*ContInxOld > 0) {
			msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);
		}
	}
}

# \brief uuCollectionMetadataKvp return a key-value-pair of metadata associated with a collection
# \param[in]  coll_id	Unique DataObject ID. Used because it is Unique
# \param[in]  prefix	Only include metadata with this prefix. Use "" if all metadata should be returned
# \param[in,out] kvp	key-value-pair to add the metadata to
uuCollectionMetadataKvp(*coll_id, *prefix, *kvp) {
	*ContInxOld = 1;
	msiMakeGenQuery("META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE", "COLL_ID = '*coll_id'", *GenQInp);
	if (*prefix != "") {
		#| writeLine("stdout", "prefix is *prefix");
		msiAddConditionToGenQuery("META_COLL_ATTR_NAME", " like ", "'*prefix%%'", *GenQInp);
	}
	msiExecGenQuery(*GenQInp, *GenQOut);
	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);
	while(*ContInxOld > 0) {
		foreach(*meta in *GenQOut) {
			*name = *meta.META_COLL_ATTR_NAME;
			*val = *meta.META_COLL_ATTR_VALUE;
			msiAddKeyVal(*kvp, *name, *val);	
		}
		*ContInxOld = *ContInxNew;
		if(*ContInxOld > 0) {
			msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);
		}
	}
}
#| INPUT *coll_name="/nluu1paul/home/paul",*data_id="11925"
#| OUTPUT ruleExecOut
