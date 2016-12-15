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
		msiAddConditionToGenQuery("META_DATA_ATTR_NAME", " like ", "*prefix%%", *GenQInp);
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
		msiAddConditionToGenQuery("META_COLL_ATTR_NAME", " like ", "*prefix%%", *GenQInp);
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

# \brief uuSearchCollectionsTemplate	This is a Template to search for Collections including pagination.
# \param[in] fields		A list of fields to include in the results
# \param[in] conditions		A list of search condition. Should be of datatype condition
# \param[in] orderby		Column to sort on, Defaults to COLL_NAME
# \param[in] ascdesc		"asc" for ascending order and "desc" for descending order
# \param[in] limit		Maximum number of results returned
# \param[in] offset		Offset in result set before returning results
# \param[out] kvpList		List of results in the form of a key-value-pair list
uuSearchCollectionsTemplate(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList) {

	*kvpList = list();

	foreach(*field in *fields) {
		*orderclause =	uuorderclause(*field, *orderby, *ascdesc);
		msiAddSelectFieldToGenQuery(*field, *orderclause, *GenQInp);
	}

	foreach(*condition in *conditions) {
		# deconstruct condition to its parts.
		uucondition(*column, *comparison, *expression) =  *condition;
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
				uuCollectionMetadataKvp(*coll_id, UUORGMETADATAPREFIX, *kvp);
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
			# Do a count on COLL_ID with the same conditions as the main query
			msiAddSelectFieldToGenQuery("COLL_ID", "COUNT", *TotalQInp);

			foreach(*condition in *conditions) {
				# deconstruct condition into its parts
				uucondition(*column, *comparison, *expression) =  *condition;
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

# \brief uuSearchDataObjectsTemplate	This is a Template to perform a search in DataObjects including pagination
# \param[in] fields		A list of fields to include in the results
# \param[in] conditions		A list of condition. Each element should be of datatype condition
# \param[in] orderby		Column to sort on, Defaults to COLL_NAME
# \param[in] ascdesc		"asc" for ascending order and "desc" for descending order
# \param[in] limit		Maximum number of results returned
# \param[in] offset		Offset in result set before returning results
# \param[out] kvpList		List of results in the form of a key-value-pair list
uuSearchDataObjectsTemplate(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList) {
	
	*kvpList = list();

	foreach(*field in *fields) {
		*orderclause =	orderclause(*field, *orderby, *ascdesc);
		msiAddSelectFieldToGenQuery(*field, *orderclause, *GenQInp);
	}

	foreach(*condition in *conditions) {
		# deconstruct condition into its parts
		uucondition(*column, *comparison, *expression) =  *condition;
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
				uuObjectMetadataKvp(*data_id, UUORGMETADATAPREFIX, *kvp);
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

			foreach(*condition in *conditions) {
				# deconstruct condition into its parts
				uucondition(*column, *comparison, *expression) =  *condition;
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
#| INPUT *coll_name="/nluu1paul/home/paul",*data_id="11925"
#| OUTPUT ruleExecOut
