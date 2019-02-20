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
	msiDataObjCreate(*filePath, "", *D_FD);
	msiDataObjWrite(*D_FD, *data, *len_data);
	msiDataObjClose(*D_FD, *status);
}
