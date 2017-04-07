testRule {
	writeLine("stdout", IIREVISIONBUCKETLIST);
	iiRevisionStrategyA(*path, *endofcalendarday, *keep, *remove);
	writeLine("stdout", "*keep, *remove");
	foreach(*revision in *keep) {
		uurevisioncandidate(*timeInt, *id) = *revision;
		foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE DATA_ID = *id) {
			*revPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		}
		writeLine("stdout", "Keep *revPath with id *id");
	}

	foreach(*revision in *remove) {
		uurevisioncandidate(*timeInt, *id) = *revision;
		foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE DATA_ID = *id) {
			*revPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		}
		writeLine("stdout", "Remove *revPath with datetime *dt");
	}
}

input *path="", *endofcalendarday=1
output ruleExecOut
