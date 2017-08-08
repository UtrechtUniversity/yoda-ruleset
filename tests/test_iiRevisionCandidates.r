testRule {

	iiRevisionCandidates(*path, *revisions); 
	foreach(*revision in *revisions) {
		uurevisioncandidate(*timeInt, *id) = *revision;
		*iso8601 = uuiso8601(*timeInt);
		writeLine("stdout", "uurevisioncandidate timeInt:*timeInt [*iso8601]; id:*id");
	}
}

input *path=""
output ruleExecOut
