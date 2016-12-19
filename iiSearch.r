# \datatype	condition
# \description  a triple of strings to represent the elements of a condition query
# \constructor condition	Construct new conditions with condition(*column, *operator, *expression)	
data condition =
	| condition : string * string * string -> condition

# \function makelikecondition	Helper function to crete the most used condition
# \param[in] column		The irods column to search
# \param[in] searchstring	Part of the string to search on.
makelikecondition(*column, *searchstring) = condition(*column, "like", "%%*searchstring%%")

# \brief iiSearchByName		Search for a file or collection by name
# \param[in] startpath		Path to start searching. Defaults to /{rodsZoneClient}/home/
# \param[in] searchstring	String to search for in the filesystem
# \param[in] collectionOrDataObject	Either "Collection" or "DataObject"
# \param[in] orderby		Column to sort on, Defaults to COLL_NAME
# \param[in] ascdesc		"asc" for ascending order and "desc" for descending order
# \param[in] limit		Maximum number of results returned
# \param[in] offset		Offset in result set before returning results
# \param[out] result		List of results in JSON format
iiSearchByName(*startpath, *searchstring, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result) {

	*iscollection = iscollection(*collectionOrDataObject);
	if (*iscollection) {
		*fields = list("COLL_PARENT_NAME", "COLL_ID", "COLL_NAME", "COLL_MODIFY_TIME", "COLL_CREATE_TIME");
		*conditions = list(makelikecondition("COLL_NAME", *searchstring));
		iiSearchCollectionsTemplate(*fields, *conditions, *startpath, *orderby, *ascdesc, *limit, *offset, *kvpList); 
	} else {
		*fields = list("COLL_NAME", "DATA_ID", "DATA_NAME", "DATA_CREATE_TIME", "DATA_MODIFY_TIME");
		*conditions = list(makelikecondition("DATA_NAME", *searchstring));
		iiSearchDataObjectsTemplate(*fields, *conditions, *startpath, *orderby, *ascdesc, *limit, *offset, *kvpList); 
	}

	uuKvpList2JSON(*kvpList, *json_str, *size);
	*result = *json_str;
}

# \brief iiSearchByMetadata	Search for a file or collection by metadata
# \param[in] startpath		Path to start searching. Defaults to /{rodsZoneClient}/home/
# \param[in] searchstring	String to search for in the metadata
# \param[in] collectionOrDataObject	Either "Collection" or "DataObject"
# \param[in] orderby		Column to sort on, Defaults to COLL_NAME
# \param[in] ascdesc		"asc" for ascending order and "desc" for descending order
# \param[in] limit		Maximum number of results returned
# \param[in] offset		Offset in result set before returning results
# \param[out] result		List of results in JSON format
iiSearchByMetadata(*startpath, *searchstring, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result) {
	*iscollection = iscollection(*collectionOrDataObject);
	*likeprefix = USERMETADATAPREFIX ++ "%%";
	if (*iscollection) {
		*fields = list("COLL_PARENT_NAME", "COLL_ID", "COLL_NAME", "COLL_MODIFY_TIME", "COLL_CREATE_TIME");
		*conditions = list(makelikecondition("META_COLL_ATTR_VALUE", *searchstring));
		*conditions = cons(condition("META_COLL_ATTR_NAME", "like", *likeprefix), *conditions);
		iiSearchCollectionsTemplate(*fields, *conditions, *startpath, *orderby, *ascdesc, *limit, *offset, *kvpList);
		# skip index 0, it contains the summary and then add user metadata matches to each kvp
		for(*i = 1;*i < size(*kvpList);*i = *i + 1) {
			*kvp = elem(*kvpList, *i);
			*coll_id = *kvp.id;
			*matches = "[]";
			*msize = 0;
			foreach(*row in SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_ID = *coll_id AND META_COLL_ATTR_NAME like *likeprefix AND META_COLL_ATTR_VALUE like "%*searchstring%") {
				msiString2KeyValPair("", *match);
				*name = triml(*row.META_COLL_ATTR_NAME, USERMETADATAPREFIX);
				*val = *row.META_COLL_ATTR_VALUE;
				msiAddKeyVal(*match, *name, *val);
				*match_json = "";
				msi_json_objops(*match_json, *match, "set");
				msi_json_arrayops(*matches, *match_json, "add", *msize);
			}
			*kvp.matches = *matches;
		}	
	} else {
		*fields = list("COLL_NAME", "DATA_ID", "DATA_NAME", "DATA_CREATE_TIME", "DATA_MODIFY_TIME");
		*conditions = list(makelikecondition("META_DATA_ATTR_VALUE", *searchstring));
		*conditions = cons(condition("META_COLL_ATTR_NAME", "like", USERMETADATAPREFIX ++ "%%"), *conditions);
		iiSearchDataObjectsTemplate(*fields, *conditions, *startpath, *orderby, *ascdesc, *limit, *offset, *kvpList);
		# skip index 0, it contains the summary and then add user metadata matches to each kvp
		for(*i = 1;*i < size(*kvpList);*i = *i + 1) {
			*kvp = elem(*kvpList, *i);
			*data_id = *kvp.id;
			*matches = "[]";
			*msize = 0;
			foreach(*row in SELECT META_DATA_ATTR_NAME, META_DATA_ATTR_VALUE WHERE DATA_ID = *data_id AND META_DATA_ATTR_NAME like *likeprefix AND META_DATA_ATTR_VALUE like "%*searchstring%") {
				msiString2KeyValPair("", *match);
				*name = triml(*row.META_DATA_ATTR_NAME, USERMETADATAPREFIX);
				*val = *row.META_DATA_ATTR_VALUE;
				msiAddKeyVal(*match, *name, *val);
				*match_json = "";
				msi_json_objops(*match_json, *match, "set");
				msi_json_arrayops(*matches, *match_json, "add", *msize);
			}
			*kvp.matches = *matches;
		}	

	}

	uuKvpList2JSON(*kvpList, *json_str, *size);
	*result = *json_str;
}

# \brief iiSearchByOrgMetadata	Search for a collection by organisational metadata
# \param[in] startpath		Path to start searching. Defaults to /{rodsZoneClient}/home/
# \param[in] searchstring	String to search for in the organisational metadata
# \param[in] attrname		Name of the metadata attribute to query (without ORGMETADATAPREFIX)
# \param[in] orderby		Column to sort on, Defaults to COLL_NAME
# \param[in] ascdesc		"asc" for ascending order and "desc" for descending order
# \param[in] limit		Maximum number of results returned
# \param[in] offset		Offset in result set before returning results
# \param[out] result		List of results in JSON format
iiSearchByOrgMetadata(*startpath, *searchstring, *attrname, *orderby, *ascdesc, *limit, *offset, *result) {

	*attr = ORGMETADATAPREFIX ++ "*attrname";
	*fields = list("COLL_PARENT_NAME", "COLL_ID", "COLL_NAME", "COLL_MODIFY_TIME", "COLL_CREATE_TIME");
	*conditions = list(makelikecondition("META_COLL_ATTR_VALUE", *searchstring));
	*conditions = cons(condition("META_COLL_ATTR_NAME", "=", *attr), *conditions);
	iiSearchCollectionsTemplate(*fields, *conditions, *startpath, *orderby, *ascdesc, *limit, *offset, *kvpList); 

	uuKvpList2JSON(*kvpList, *json_str, *size);
	*result = *json_str;
}



# \brief iiSearchCollectionsTemplate	Every Search only differs on a few key points. This is a Template for a search in Collections.
# \param[in] fields		A list of fields to include in the results
# \param[in] conditions		A list of search condition. Should be of datatype condition
# \param[in] startpath		Path to start searching. Defaults to /{rodsZoneClient}/home/
# \param[in] orderby		Column to sort on, Defaults to COLL_NAME
# \param[in] ascdesc		"asc" for ascending order and "desc" for descending order
# \param[in] limit		Maximum number of results returned
# \param[in] offset		Offset in result set before returning results
# \param[out] kvpList		List of results in the form of a key-value-pair list
iiSearchCollectionsTemplate(*fields, *conditions, *startpath, *orderby, *ascdesc, *limit, *offset, *kvpList) {
	
	if (*startpath == "") {
		*startpath = "/" ++ $rodsZoneClient ++ "/home";
	} else {
		if (!uuCollectionExists(*startpath)) {
			fail(-317000);
		}
	}

	if (*orderby == "") {*orderby = "COLL_NAME";}
	
	*kvpList = list();

	foreach(*field in *fields) {
		*orderclause =	orderclause(*field, *orderby, *ascdesc);
		msiAddSelectFieldToGenQuery(*field, *orderclause, *GenQInp);
	}

	msiAddConditionToGenQuery("COLL_PARENT_NAME", "like", "%%*startpath%%", *GenQInp);

	foreach(*condition in *conditions) {
		# deconstruct condition to its parts.
		condition(*column, *comparison, *expression) =  *condition;
		msiAddConditionToGenQuery(*column, *comparison, *expression, *GenQInp);
	}

	msiExecGenQuery(*GenQInp, *GenQOut);

	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);
	
	# FastForward to Rowset of GENQMAXROWS based on offset
	*offsetInGenQ = *offset;
	while (*offsetInGenQ > GENQMAXROWS && *ContInxNew > 0) {
		msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);
		*offsetInGenQ = *offsetInGenQ - GENQMAXROWS;
	}

	#! writeLine("stdout", "offsetInGenQ: *offsetInGenQ");
	*step = 0;
	*stop = *offsetInGenQ + *limit;
	*remainingInGenQ = 0;
	while (*step < *stop) {
		foreach(*row in *GenQOut) {
			# only process rows after offset is reached
			if (*step >= *offsetInGenQ && *step < *stop) {
				# Initialize new key-value-pair. Otherwise the same *kvp will be continuously overwritten
				msiString2KeyValPair("", *kvp);
				# Depending on irods type set key-values for *kvp
				*name =	*row.COLL_NAME;
				*kvp."path" = *name;
				*parent = *row.COLL_PARENT_NAME;
				*kvp.parent = *parent;
				*basename = triml(*name, *parent ++ "/");
				*kvp.basename = *basename;
				*coll_id = *row.COLL_ID;
				*kvp.id = *coll_id;
				*kvp."irods_type" = "Collection";
				*kvp."create_time" = *row.COLL_CREATE_TIME;
				*kvp."modify_time" = *row.COLL_MODIFY_TIME;
				# Add collection metadata with org prefix 	
				uuCollectionMetadataKvp(*coll_id, ORGMETADATAPREFIX, *kvp);
				#! writeLine("stdout", *kvp);
				*kvpList = cons(*kvp, *kvpList);
			} else if (*step >= *stop) {
				# loop over remaing rows to count them
			       	*remainingInGenQ = *remainingInGenQ + 1;
			}
			*step = *step + 1;
		}
		if (*step < *stop && *ContInxNew > 0) {
			# We have not reached our limit yet and more rows are available.
		       	msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);}
		else {
			break;
		}
	}

	# The size of the kvpList is the number of results returned by irods starting from *offset until *limit
	*count = size(*kvpList);
	msiString2KeyValPair("returned=*count", *summary);
	if (*count > 0) {
		# because lists grow at the front, we need to reverse the list to correct order.
		*kvpList = uuListReverse(*kvpList);	
		if (*ContInxNew > 0) {
			# Query for total number of rows to include in summary
			# Do a count on DATA_ID with the same conditions as the main query
			msiAddSelectFieldToGenQuery("COLL_ID", "COUNT", *TotalQInp);
			msiAddConditionToGenQuery("COLL_PARENT_NAME", "like", "%%*startpath%%", *TotalQInp);

			foreach(*condition in *conditions) {
				# deconstruct condition into its parts
				condition(*column, *comparison, *expression) =  *condition;
				msiAddConditionToGenQuery(*column, *comparison, *expression, *TotalQInp);
			}

			msiExecGenQuery(*TotalQInp, *TotalQOut);

			foreach(*row in *TotalQOut) { *total = *row.COLL_ID; }

			msiAddKeyVal(*summary, "total", *total);
			# there are *more rows after the offset and returned rows point
			*more = int(*total) - *offset - *count;
			msiAddKeyVal(*summary, "more", str(*more));
		} else {
			# There are no more rows to get, but maybe more results in the current set of rows.
			*more = *remainingInGenQ;
			*total = str(*offset + *count + *more);
			msiAddKeyVal(*summary, "total", *total);
			msiAddKeyVal(*summary, "more", str(*more));
		}
	} else {
		# No results found, thus total and more are 0
		msiAddKeyVal(*summary, "total", "0");
		msiAddKeyVal(*summary, "more", "0");
	}

	*kvpList = cons(*summary, *kvpList);
}

# \brief iiSearchDataObjectsTemplate	Every Search only differs on a few key points. This is a Template for a search in DataObjects
# \param[in] fields		A list of fields to include in the results
# \param[in] conditions		A list of condition. Each element should be of datatype condition
# \param[in] startpath		Path to start searching. Defaults to /{rodsZoneClient}/home/
# \param[in] orderby		Column to sort on, Defaults to COLL_NAME
# \param[in] ascdesc		"asc" for ascending order and "desc" for descending order
# \param[in] limit		Maximum number of results returned
# \param[in] offset		Offset in result set before returning results
# \param[out] kvpList		List of results in the form of a key-value-pair list
iiSearchDataObjectsTemplate(*fields, *conditions, *startpath, *orderby, *ascdesc, *limit, *offset, *kvpList) {
	
	if (*startpath == "") {
		*startpath = "/" ++ $rodsZoneClient ++ "/home";
	} else {
		if (!uuCollectionExists(*startpath)) {
			fail(-317000);
		}
	}

	if (*orderby == "") {*orderby = "DATA_NAME";}
	
	*kvpList = list();

	foreach(*field in *fields) {
		*orderclause =	orderclause(*field, *orderby, *ascdesc);
		msiAddSelectFieldToGenQuery(*field, *orderclause, *GenQInp);
	}

	msiAddConditionToGenQuery("COLL_NAME", "like", "%%*startpath%%", *GenQInp);

	foreach(*condition in *conditions) {
		# deconstruct condition into its parts
		condition(*column, *comparison, *expression) =  *condition;
		msiAddConditionToGenQuery(*column, *comparison, *expression, *GenQInp);
	}

	msiExecGenQuery(*GenQInp, *GenQOut);

	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);
	
	# FastForward to Rowset of GENQMAXROWS based on offset
	*offsetInGenQ = *offset;
	while (*offsetInGenQ > GENQMAXROWS && *ContInxNew > 0) {
		msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);
		*offsetInGenQ = *offsetInGenQ - GENQMAXROWS;
	}

	#! writeLine("stdout", "offsetInGenQ: *offsetInGenQ");
	*step = 0;
	*stop = *offsetInGenQ + *limit;
	*remainingInGenQ = 0;
	while (*step < *stop) {
		foreach(*row in *GenQOut) {
			# only process rows after offset is reached
			if (*step >= *offsetInGenQ && *step < *stop) {
				# Initialize new key-value-pair. Otherwise the same *kvp will be continuously overwritten
				msiString2KeyValPair("", *kvp);
				*name = *row.DATA_NAME;
				*kvp.basename = *name;
				*parent = *row.COLL_NAME;
				*kvp.parent = *parent;
				*kvp."path" = *parent ++ "/" ++ *name;
				*data_id = *row.DATA_ID;
				*kvp.id = *data_id;
				*kvp."create_time" = *row.DATA_CREATE_TIME;
				*kvp."modify_time" = *row.DATA_MODIFY_TIME;
				*kvp."irods_type" = "DataObject";
				# Add Dataobject metadata with org prefix
				uuObjectMetadataKvp(*data_id, ORGMETADATAPREFIX, *kvp);
					#! writeLine("stdout", *kvp);
				*kvpList = cons(*kvp, *kvpList);
			} else if (*step >= *stop) {
				# loop over remaing rows to count them
			       	*remainingInGenQ = *remainingInGenQ + 1;
			}
			*step = *step + 1;
		}
		if (*step < *stop && *ContInxNew > 0) {
			# We have not reached our limit yet and more rows are available.
		       	msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);}
		else {
			break;
		}
	}

	# The size of the kvpList is the number of results returned by irods starting from *offset until *limit
	*count = size(*kvpList);
	msiString2KeyValPair("returned=*count", *summary);
	if (*count > 0) {
		# because lists grow at the front, we need to reverse the list to correct order.
		*kvpList = uuListReverse(*kvpList);	
		if (*ContInxNew > 0) {
			# Query for total number of rows to include in summary
			# Do a count on DATA_ID with the same conditions as the main query
			msiAddSelectFieldToGenQuery("DATA_ID", "COUNT", *TotalQInp);
			msiAddConditionToGenQuery("COLL_NAME", "like", "%%*startpath%%", *TotalQInp);

			foreach(*condition in *conditions) {
				# deconstruct condition into its parts
				condition(*column, *comparison, *expression) =  *condition;
				msiAddConditionToGenQuery(*column, *comparison, *expression, *TotalQInp);
			}

			msiExecGenQuery(*TotalQInp, *TotalQOut);

			foreach(*row in *TotalQOut) { *total = *row.DATA_ID; }
			msiAddKeyVal(*summary, "total", *total);
			# there are *more rows after the offset and returned rows point
			*more = int(*total) - *offset - *count;
			msiAddKeyVal(*summary, "more", str(*more));
		} else {
			# There are no more rows to get, but maybe more results in the current set of rows.
			*more = *remainingInGenQ;
			*total = str(*offset + *count + *more);
			msiAddKeyVal(*summary, "total", *total);
			msiAddKeyVal(*summary, "more", str(*more));
		}
	} else {
		# No results found, thus total and more are 0
		msiAddKeyVal(*summary, "total", "0");
		msiAddKeyVal(*summary, "more", "0");
	}

	*kvpList = cons(*summary, *kvpList);
}
