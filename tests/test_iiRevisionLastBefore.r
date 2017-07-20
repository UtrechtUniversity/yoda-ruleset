testRule {

	iiRevisionLastBefore(*path, *timestamp, *revisionId); 
	writeLine("stdout", *revisionId);
}
input *path="", *timestamp=0
output ruleExecOut
