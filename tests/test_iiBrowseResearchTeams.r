test_iiBrowseResearchTeams {
	iiBrowseResearchTeams("COLL_NAME", "asc", 100, 0, *result);
	writeLine("stdout", *result);
}

input null
output ruleExecOut
