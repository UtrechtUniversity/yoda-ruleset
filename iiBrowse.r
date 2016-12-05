# \brief Rules to support the ilab datapackage browser
# \author Paul Frederiks

# \brief orderclause	helper functions to determine order clause
#			defaults to Ascending order			
orderclause(*column, *orderby, *ascdesc) = if *column == *orderby then orderdirection(*ascdesc) else ""
orderdirection(*ascdesc) = if *ascdesc == "desc" then "ORDER_DESC" else "ORDER_ASC"

iscollection(*collectionOrDataObject) = if *collectionOrDataObject == "Collection" then true else false

# \brief iiBrowse	return list of subcollections or dataobjects with ilab specific information attached
# \param[in] path		requested path of parent collection
# \param[in] collectionOrDataObject	Set to "Collection" if you want collections or "DataObject" (Or anything else) if you want dataobjects
# \param[in] orderby		which column to sort on 
# \param[in] ascdesc		Order Ascending or Descending: "asc" or "desc"
# \param[in] limit		limit the list of results. Cast to int
#\ param[in] offset		Start returning results from offset. Cast to int
# \param[out] result 		JSON output of subcollections and their flags
iiBrowse(*path, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result) {
	# Cast non string parameters to their right type
	*limit = int(*limit);
	*offset = int(*offset);

	*iscollection = iscollection(*collectionOrDataObject);
	if (*orderby == "") {*orderby = "COLL_NAME";}
	# First check if path exists and fail if not
	if (!uuCollectionExists(*path)) {
		# class USER_INPUT_PATH_ERR(UserInputException):
		# code = -317000
		fail(-317000);
	}	
	# Initialize a result string and a list of keyvalpairs to accumulate result rows
	*result = "";
	*kvpList = list();

	# Add each field to the query and add a ORDER_ASC or ORDER_DESC clause if *orderby matches field
	if (*iscollection){
		*fields = list("COLL_ID", "COLL_NAME", "COLL_MODIFY_TIME", "COLL_CREATE_TIME");
	} else {
		*fields = list("DATA_ID", "DATA_NAME", "DATA_CREATE_TIME", "DATA_MODIFY_TIME");
	}

	foreach(*field in *fields) {
		*orderclause =	orderclause(*field, *orderby, *ascdesc);
		msiAddSelectFieldToGenQuery(*field, *orderclause, *GenQInp);
	}

	# Add the Condition to the query. The Parent collection should be *path
	if (*iscollection) {
		msiAddConditionToGenQuery("COLL_PARENT_NAME", "=", "*path", *GenQInp);
	} else {
		msiAddConditionToGenQuery("COLL_NAME", "=", "*path", *GenQInp);
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
				if (*iscollection) {
					*name =	*row.COLL_NAME;
					*kvp."path" = *name;
					*kvp.basename = triml(*name, *path);
					*coll_id = *row.COLL_ID;
					*kvp.id = *coll_id;
					*kvp."irods_type" = "Collection";
					*kvp."create_time" = *row.COLL_CREATE_TIME;
					*kvp."modify_time" = *row.COLL_MODIFY_TIME;
					# Add collection metadata with ilab prefix 	
					uuCollectionMetadataKvp(*coll_id, IIMETADATAPREFIX, *kvp);
				} else {
					*name = *row.DATA_NAME;
					*kvp.basename = *name;
					*kvp."path" = *path ++ "/" ++ *name;
					*data_id = *row.DATA_ID;
					*kvp.id = *data_id;
					*kvp."create_time" = *row.DATA_CREATE_TIME;
					*kvp."modify_time" = *row.DATA_MODIFY_TIME;
					*kvp."irods_type" = "DataObject";
					# Add Dataobject metadata with ilab prefix
					uuObjectMetadataKvp(*data_id, IIMETADATAPREFIX, *kvp);
				}
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
			if (*iscollection) {
				foreach(*row in SELECT count(COLL_ID) WHERE COLL_PARENT_NAME = '*path') { *total = *row.COLL_ID; }
			} else {
				foreach(*row in SELECT count(DATA_ID) WHERE COLL_NAME = '*path') { *total = *row.DATA_ID; }
			}
		
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
	uuKvpList2JSON(*kvpList, *json_str, *size);
	*result = *json_str;
}


# \ brief iiCollectionDetails return a json object containing the details of a collection
iiCollectionDetails(*path, *result) {
	*result = "";
	msiString2KeyValPair("", *kvp);

	foreach(*row in SELECT COLL_ID, COLL_NAME, COLL_MODIFY_TIME, COLL_CREATE_TIME WHERE COLL_NAME = *path) {
		*name =	*row.COLL_NAME;
		*kvp."path" = *name;
		*kvp.basename = triml(*name, *path);
		*coll_id = *row.COLL_ID;
		*kvp.id = *coll_id;
		*kvp."irods_type" = "Collection";
		*kvp."create_time" = *row.COLL_CREATE_TIME;
		*kvp."modify_time" = *row.COLL_MODIFY_TIME;
		# Add collection metadata with ilab prefix 	
		uuCollectionMetadataKvp(*coll_id, IIMETADATAPREFIX, *kvp);
	}
	msi_json_objops(*result, *kvp, "set");
}

iiSetCollectionType(*path, *ilabtype) {
	msiString2KeyValPair("ilab_type=*ilabtype", *kvp);
	msiSetKeyValuePairsToObj(*kvp, *path, "-C");
}
