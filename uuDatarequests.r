uuSubmitDatarequest(*data, *proposalId, *status, *statusInfo) {
	*status = 0;
	*statusInfo = *proposalId;

	# Create subcollection
	*zonePath = '/tempZone/home/datarequests-research/';
	*proposalPath = *zonePath ++ *proposalId;
	*collPath = *proposalPath ++ '/datarequests';
	msiCollCreate(*collPath, 1, *status);

	# Write proposal data to a JSON file in the collection that we just created
	*time = timestrf(time(), '%Y%m%dT%H%M%S'); 
	*filePath = *collPath ++ "/" ++ *time ++ ".json";
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
