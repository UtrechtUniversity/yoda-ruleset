uuSubmitProposal(*data, *status, *statusInfo) {
	*status = 0;
	*statusInfo = "";

	# Create collection
	*zonePath = '/tempZone/home/research-datarequest/';
	*time = timestrf(time(), '%Y%m%dT%H%M%S');
	*collPath = *zonePath ++ *time;
	msiCollCreate(*collPath, 1, *status);

	# Write proposal data to a JSON file in the collection that we just created
	*filePath = *collPath ++ "/proposal.json";
	msiDataObjCreate(*filePath, "", *fileDescriptor);
	msiDataObjWrite(*fileDescriptor, *data, *lenData);
	msiDataObjClose(*fileDescriptor, *status);
}

uuGetProposals(*limit, *offset, *result, *status, *statusInfo) {
	*status = "Success";
	*statusInfo = "";

	# Query iRODS to get a list of submitted proposals (i.e. subcollections
	# of the the research-datarequest collection)
	*path = "/tempZone/home/research-datarequest";
	*fields = list("COLL_NAME", "COLL_CREATE_TIME", "COLL_OWNER_NAME");
	*conditions = list(uucondition("COLL_PARENT_NAME", "=", *path));
	*orderby = "COLL_NAME";
	*ascdesc = "asc";

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList, *status, *statusInfo);
	uuKvpList2JSON(*kvpList, *result, *size);
}
