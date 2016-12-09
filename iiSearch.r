iiSearchByName(*startpath, *searchstring, *collectionOrDataObject, *orderby, *ascdesc, *limit, *offset, *result) {
	
	if (*startpath == "") {
		*startpath = "/" ++ $rodsZoneClient ++ "/home";
	} else {
		if (!uuCollectionExists(*startpath)) {
			fail(-317000);
		}
	}

	*iscollection = iscollection(*collectionOrDataObject);
	if (*orderby == "") {*orderby = "COLL_NAME";}
	
	*result = "";

	*kvpList = list();

	if (*iscollection){
		*fields = list("COLL_PARENT_NAME", "COLL_ID", "COLL_NAME", "COLL_MODIFY_TIME", "COLL_CREATE_TIME");
	} else {
		*fields = list("COLL_NAME", "DATA_ID", "DATA_NAME", "DATA_CREATE_TIME", "DATA_MODIFY_TIME");
	}

	foreach(*field in *fields) {
		*orderclause =	orderclause(*field, *orderby, *ascdesc);
		msiAddSelectFieldToGenQuery(*field, *orderclause, *GenQInp);
	}

	if (*iscollection) {
		msiAddConditionToGenQuery("COLL_PARENT_NAME", "like", "%%*startpath%%", *GenQInp);
		msiAddConditionToGenQuery("COLL_NAME", "like", "%%*searchstring%%", *GenQInp);
	} else {
		msiAddConditionToGenQuery("COLL_NAME", "like", "%%*startpath%%", *GenQInp);
		msiAddConditionToGenQuery("DATA_NAME", "like", "%%*searchstring%%", *GenQInp);
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
				} else {
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
				foreach(*row in SELECT count(COLL_ID) WHERE COLL_PARENT_NAME like '%*startpath%' AND COLL_NAME like "%*searchstring%") { *total = *row.COLL_ID; }
			} else {
				foreach(*row in SELECT count(DATA_ID) WHERE COLL_NAME like "%*startpath%" AND DATA_NAME like "%*searchstring%") { *total = *row.DATA_ID; }
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
