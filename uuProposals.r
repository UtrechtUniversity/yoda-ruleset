uuSubmitProposal(*data, *status, *statusInfo) {
	*status = 0;
	*statusInfo = "";

	# Create collection
	*zonePath = '/tempZone/home/datarequests-research/';
	*time = timestrf(time(), '%Y%m%dT%H%M%S');
	*collPath = *zonePath ++ *time;
	msiCollCreate(*collPath, 1, *status);

	# Write proposal data to a JSON file in the collection that we just created
	*filePath = *collPath ++ "/proposal.json";
	msiDataObjCreate(*filePath, "", *fileDescriptor);
	msiDataObjWrite(*fileDescriptor, *data, *lenData);
	msiDataObjClose(*fileDescriptor, *status);

	# Set the status metadata field of the proposal
	# that we just submitted to "submitted"
	msiAddKeyVal(*statusKvp, "status", "submitted");
	msiSetKeyValuePairsToObj(*statusKvp, *filePath, "-d");

	# Set permissions for certain groups on the subcollection
	msiSetACL("recursive", "write", "datarequests-research-datamanagers", *collPath);
	msiSetACL("recursive", "write", "datarequests-research-board-of-directors", *collPath);
}

uuGetProposal(*researchProposalId, *proposalJSON, *proposalStatus, *status, *statusInfo) {
	*status = 0;
	*statusInfo = "";

	# Set collection path and file path
	*collPath = "/tempZone/home/datarequests-research/" ++ *researchProposalId;
	*filePath = "/tempZone/home/datarequests-research/" ++ *researchProposalId ++ "/proposal.json";

	# Get the size of the proposal JSON file and the status of the proposal
	foreach (*row in SELECT DATA_SIZE, META_DATA_ATTR_VALUE where COLL_NAME = "*collPath" and DATA_NAME = 'proposal.json') {
		*dataSize = *row.DATA_SIZE;
		*proposalStatus = *row.META_DATA_ATTR_VALUE;
	}

	# Get the contents of the proposal JSON file and assign them to *proposalJSON
	msiDataObjOpen("objPath=*filePath", *fd);
	msiDataObjRead(*fd, *dataSize, *buf);
	msiDataObjClose(*fd, *status);
	msiBytesBufToStr(*buf, *proposalJSON);
}

uuApproveProposal(*researchProposalId, *status, *statusInfo) {
	*status = 0;
	*statusInfo = "";
	
	*proposalPath = "/tempZone/home/datarequests-research/" ++ *researchProposalId ++ "/proposal.json";
	msiAddKeyVal(*statusKvp, "status", "approved");
	msiSetKeyValuePairsToObj(*statusKvp, *proposalPath, "-d");
}

uuGetProposals(*limit, *offset, *result, *status, *statusInfo) {
	*status = "Success";
	*statusInfo = "";

	# Query iRODS to get a list of submitted proposals (i.e. subcollections
	# of the the research-datarequest collection)
	*path = "/tempZone/home/datarequests-research";
	*fields = list("COLL_NAME", "COLL_CREATE_TIME", "COLL_OWNER_NAME", "META_DATA_ATTR_VALUE");
	*conditions = list(uucondition("COLL_PARENT_NAME", "=", *path), uucondition("DATA_NAME", "=", "proposal.json"));
	*orderby = "COLL_NAME";
	*ascdesc = "asc";

	uuPaginatedQuery(*fields, *conditions, *orderby, *ascdesc, *limit, *offset, *kvpList, *status, *statusInfo);
	uuKvpList2JSON(*kvpList, *result, *size);
}
