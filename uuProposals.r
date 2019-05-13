uuGetProposals(*limit, *offset, *result, *status, *statusInfo) {
	*status = "Success";
	*statusInfo = "";

	# Query iRODS to get a list of submitted proposals (i.e. subcollections
	# of the the research-datarequest collection)
	*path = "/tempZone/home/datarequests-research";
	*fields = list("COLL_NAME", "COLL_CREATE_TIME", "COLL_OWNER_NAME", "META_DATA_ATTR_VALUE");
	*conditions = list(uucondition("COLL_PARENT_NAME", "=", *path),
                           uucondition("DATA_NAME", "=", "proposal.json"),
                           uucondition("META_DATA_ATTR_NAME", "=", "status"));
	*orderby = "COLL_NAME";
	*ascdesc = "asc";

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList, *status, *statusInfo);
	uuKvpList2JSON(*kvpList, *result, *size);
}


uuGetProposalsAdditionalFields(*limit, *offset, *attributeName, *result, *status, *statusInfo) {
	*status = "Success";
	*statusInfo = "";

	*path = "/tempZone/home/datarequests-research";
	*fields = list("COLL_NAME", "META_DATA_ATTR_VALUE");
	*conditions = list(uucondition("COLL_PARENT_NAME", "=", *path),
                           uucondition("DATA_NAME", "=", "proposal.json"),
                           uucondition("META_DATA_ATTR_NAME", "=", *attributeName));
	*orderby = "COLL_NAME";
	*ascdesc = "asc";

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList, *status, *statusInfo);
	uuKvpList2JSON(*kvpList, *result, *size);
}
