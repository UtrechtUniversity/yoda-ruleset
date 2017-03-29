testRule {

	uuRevisionRestore(*revisionId, *target, *overwrite, *status);
	writePosInt("stdout", *status);
}

input *revisionId="0", *target="/nluu1paul/home/paul", *overwrite=0
output ruleExecOut
