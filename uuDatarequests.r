# \brief Retrieve descriptive information of a number of data requests.
#        This is used to render a paginated table of data requests.
#
# \param[in] proposalId  Unique identifier of the research proposal whose data
#                        requests are to queried.
# \param[in] limit       The number of data requests to return.
# \param[in] offset      Offset used for table pagination.
#
# \return List of unpreservable files.
uuGetDatarequests(*proposal, *limit, *offset, *result, *status, *statusInfo) {
	*status = "Success";
	*statusInfo = "";

	# Query iRODS to get a list of submitted proposals (i.e. subcollections
	# of the the research-datarequest collection)
	#*path = "/tempZone/home/datarequests-research";
       
	*path = "/tempZone/home/datarequests-research/" ++ *proposal ++ "/datarequests";
	*fields = list("DATA_NAME", "DATA_CREATE_TIME", "DATA_OWNER_NAME", "META_DATA_ATTR_VALUE");
	*conditions = list(uucondition("COLL_NAME", "=", *path), uucondition("DATA_NAME", "like", "%.json"));
	*orderby = "COLL_NAME";
	*ascdesc = "asc";

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList, *status, *statusInfo);
	uuKvpList2JSON(*kvpList, *result, *size);
}
