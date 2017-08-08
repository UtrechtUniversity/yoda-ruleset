testRule {

	iiRevisionListOfCollectionBeforeTimestamp(*collName, *timestamp, *revisions); 
	foreach(*revision in *revisions) {
		uurevisionwithpath(*revisionId, *path) = *revision;
		writeLine("stdout", "revisionId: *revisionId");	
		writeLine("stdout", "path: *path");	
	}

}
input *collName="", *timestamp=0
output ruleExecOut
