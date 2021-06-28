# \file       uuQueries.r
# \brief      Helper rules for common queries.
# \author     Paul Frederiks
# \copyright  Copyright (c) 2015-2017, Utrecht University. All rights reserved.
# \license    GPLv3, see LICENSE.

# \brief Checks if a collection exists.
#        Used to be iicollectionexists from Jan de Mooij.
#
# \param[in] collectionname	name of the collection
# \returnvalue boolean, true if collection exists, false if not
#
uuCollectionExists(*collectionname) {
	*exists = false;
	foreach (*row in SELECT COLL_NAME WHERE COLL_NAME = '*collectionname') {
		*exists = true;
		break;
	}
	*exists;
}

# \brief Check if a file exists in the catalog.
#
# \param[in] *path
# \returnvalue  boolean, true if collection exists, false if not
#
uuFileExists(*path) {
	*exists = false;
	uuChopPath(*path, *collName, *dataName);
	foreach (*row in SELECT DATA_ID WHERE COLL_NAME = *collName AND DATA_NAME = *dataName) {
		*exists = true;
		break;
	}
	*exists;
}

# \brief Return a key-value-pair of metadata associated with a dataobject.
#	 If a key is defined multiple times, the last found will be returned.
#
# \param[in]  data_id	Unique DataObject ID. Used because it is Unique
# \param[in]  prefix	Only include metadata with this prefix
# \param[in,out] kvp	key-value-pair to add the metadata to
#
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
	msiCloseGenQuery(*GenQInp, *GenQOut);
}

# \brief uuPaginatedQuery	This is a rule to do arbitrary paginated queries
#                               iRODS general queries do not have direct support for query offsets or limits which are needed
#                               to do a paginated query. This rule works around this limitation. results are returned as a list
#                               of key-value-pairs as they can be converted to a json array of json objects for the frontend.
# \param[in] fields		A list of fields to include in the results
# \param[in] conditions		A list of condition. Each element should be of datatype condition
# \param[in] orderby		Column to sort on, Defaults to COLL_NAME
# \param[in] ascdesc		"asc" for ascending order and "desc" for descending order
# \param[in] limit		Maximum number of results returned
# \param[in] offset		Offset in result set before returning results
# \param[out] kvpList		List of results in the form of a key-value-pair. first entry is a summary
# \param[out] status		Status code: 'Success' of all ok
# \param[out] statusInfo	Extra information if something went wrong
#
uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList, *status, *statusInfo) {

	*status = 'Success';
	*statusInfo = '';

	*kvpList = list();

	foreach(*field in *fields) {
		# each field could contain an aggregation function. extract this aggregation function
		# and add to the general query input GenQInp
		if (*field like regex "(MIN|MAX|SUM|AVG|COUNT)\(.*") {
			*action = trimr(*field, "(");
			*field = trimr(triml(*field, "("), ")");
			msiAddSelectFieldToGenQuery(*field, *action, *GenQInp);
		} else {
			# if a field is used as order by column uuorderclass returns the correct order clause to add
			# will be an empty string if not.
			*orderclause =	uuorderclause(*field, *orderby, *ascdesc);
			msiAddSelectFieldToGenQuery(*field, *orderclause, *GenQInp);
		}
	}

	foreach(*condition in *conditions) {
		# deconstruct condition into its parts
		# conditions are defined by the helper functions found in uuFunctions
		uucondition(*column, *comparison, *expression) =  *condition;
		msiAddConditionToGenQuery(*column, *comparison, *expression, *GenQInp);
	}

	# Execute the query. GenQOut will contain all the results, but we only want the results of one page
	*err = errormsg(msiExecGenQuery(*GenQInp, *GenQOut), *errmsg);
        if (*err < 0) {
		*status = 'ErrorExecutingQuery';
		*statusInfo = 'An error occurred while retrieving data - *errmsg';
		succeed;
	}

	*err = errormsg(msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew), *errmsg);
        if (*err < 0) {
                *status = 'ErrorGetContFromQuery';
                *statusInfo = 'An error occurred while retrieving data - *errmsg';
                succeed;
        }


	# FastForward to Rowset of GENQMAXROWS based on offset.
	# GENQMAXROWS is defined as 256 in standard iRODS
	# msiGetMoreRows will return rows in groups of 256 until no more results can be returned
	# then it will set contInxNew to 0
	*offsetInGenQ = *offset;
	while (*offsetInGenQ > GENQMAXROWS && *ContInxNew > 0) {
		msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);
		*offsetInGenQ = *offsetInGenQ - GENQMAXROWS;
	}

	#! writeLine("stdout", "offsetInGenQ: *offsetInGenQ");
	# within a row set of max 256 rows we need to fetch each row within our page
	*step = 0;
	*stop = *offsetInGenQ + *limit;
	*remainingInGenQ = 0;
	while (*step < *stop) {
		foreach(*row in *GenQOut) {
			# only process rows after offset is reached
			if (*step >= *offsetInGenQ && *step < *stop) {
				*kvpList = cons(*row, *kvpList);
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
		if (*ContInxNew > 0) {
			# Query for total number of rows to include in summary
			# Add count to every field. Should yield the same number, but hopefully assures we get the same implicit joins
			foreach(*field in *fields) {
				if (*field like regex "(MIN|MAX|SUM|AVG|COUNT)\(.*") {
					*field = trimr(triml(*field, "("), ")");
				}
				msiAddSelectFieldToGenQuery(*field, "COUNT", *TotalQInp);
			}

			foreach(*condition in *conditions) {
				# deconstruct condition into its parts
				uucondition(*column, *comparison, *expression) = *condition;
				msiAddConditionToGenQuery(*column, *comparison, *expression, *TotalQInp);
			}

			msiExecGenQuery(*TotalQInp, *TotalQOut);
		        *err = errormsg(msiExecGenQuery(*TotalQInp, *TotalQOut), *errmsg);
		        if (*err < 0) {
                		*status = 'ErrorExecutingQuery';
				*statusInfo = 'An error occurred while retrieving data - *errmsg';
                		succeed;
        		}

			foreach(*row in *TotalQOut) {
			       msiGetValByKey(*row, hd(*fields), *total);
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
}

# \brief This is a rule to do arbitrary case-insensitive paginated queries.
#
# \param[in] fields		A list of fields to include in the results
# \param[in] conditions		A list of condition. Each element should be of datatype condition
# \param[in] orderby		Column to sort on, Defaults to COLL_NAME
# \param[in] ascdesc		"asc" for ascending order and "desc" for descending order
# \param[in] limit		Maximum number of results returned
# \param[in] offset		Offset in result set before returning results
# \param[out] kvpList		List of results in the form of a key-value-pair. first entry is a summary
# \param[out] status		Status code: 'Success' of all ok
# \param[out] statusInfo	Extra information if something went wrong
#
uuPaginatedUpperQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList, *status, *statusInfo) {
	*status = 'Success';
	*statusInfo = '';

	*kvpList = list();

	foreach(*field in *fields) {
		if (*field like regex "(MIN|MAX|SUM|AVG|COUNT)\(.*") {
			*action = trimr(*field, "(");
			*field = trimr(triml(*field, "("), ")");
			msiAddSelectFieldToGenQuery(*field, *action, *GenQInp);
		} else {
			*orderclause =	uuorderclause(*field, *orderby, *ascdesc);
			msiAddSelectFieldToGenQuery(*field, *orderclause, *GenQInp);
		}
	}

	foreach(*condition in *conditions) {
		# deconstruct condition into its parts
		uucondition(*column, *comparison, *expression) = *condition;

		# Convert expression to uppercase to prepare for case insensitive search.
		msiStrToUpper(*expression, *expressionOut);
		msiAddConditionToGenQuery(*column, *comparison, *expressionOut, *GenQInp);
	}

	# Enable case insensitive query.
	msiSetUpperCaseWhereQuery(*GenQInp);

	*err = errormsg(msiExecGenQuery(*GenQInp, *GenQOut), *errmsg);
        if (*err < 0) {
		*status = 'ErrorExecutingQuery';
		*statusInfo = 'An error occurred while retrieving data - *errmsg';
		succeed;
	}

	*err = errormsg(msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew), *errmsg);
        if (*err < 0) {
                *status = 'ErrorGetContFromQuery';
                *statusInfo = 'An error occurred while retrieving data - *errmsg';
                succeed;
        }

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
				*kvpList = cons(*row, *kvpList);
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
		if (*ContInxNew > 0) {
			# Query for total number of rows to include in summary
			# Add count to every field. Should yield the same number, but hopefully assures we get the same implicit joins
			foreach(*field in *fields) {
				if (*field like regex "(MIN|MAX|SUM|AVG|COUNT)\(.*") {
					*field = trimr(triml(*field, "("), ")");
				}
				msiAddSelectFieldToGenQuery(*field, "COUNT", *TotalQInp);
			}

			foreach(*condition in *conditions) {
				# deconstruct condition into its parts
				uucondition(*column, *comparison, *expression) = *condition;
				msiAddConditionToGenQuery(*column, *comparison, *expression, *TotalQInp);
			}

			msiExecGenQuery(*TotalQInp, *TotalQOut);
		        *err = errormsg(msiExecGenQuery(*TotalQInp, *TotalQOut), *errmsg);
		        if (*err < 0) {
                		*status = 'ErrorExecutingQuery';
				*statusInfo = 'An error occurred while retrieving data - *errmsg';
                		succeed;
        		}

			foreach(*row in *TotalQOut) {
			       msiGetValByKey(*row, hd(*fields), *total);
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
}
