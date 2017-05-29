testRule {

	iiRevisionListOfCollectionBeforeTimestamp(*collName, *timestamp, *revisions); 
	foreach(*revision in *revisions) {
		writeLine("stdout", "*revision");	
	}

}
input *collName="", *timestamp=0
output ruleExecOut
