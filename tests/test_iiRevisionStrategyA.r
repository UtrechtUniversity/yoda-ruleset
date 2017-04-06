testRule {
	writeLine("stdout", IIREVISIONBUCKETS);
	iiRevisionStrategyA(*path, *endofcalendarday, *keep, *remove);
	writeLine("stdout", "*keep, *remove");
	foreach(*revision in *keep) {
		uurevisioncandidate(*timeInt, *id) = *revision;
		foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE DATA_ID = *id) {
			*revPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		}
		uuObjectMetadataKvp(*id, UUORGMETADATAPREFIX, *mdkvp);
		*dt = uuiso8601(*timeInt);
		writeLine("stdout", "Keep *revPath with datetime *dt");
	}

	foreach(*revision in *remove) {
		uurevisioncandidate(*timeInt, *id) = *revision;
		foreach(*row in SELECT COLL_NAME, DATA_NAME WHERE DATA_ID = *id) {
			*revPath = *row.COLL_NAME ++ "/" ++ *row.DATA_NAME;
		}
		uuObjectMetadataKvp(*id, UUORGMETADATAPREFIX, *mdkvp);
		*dt = uuiso8601(*timeInt);
		writeLine("stdout", "Remove *revPath with datetime *dt");
	}
}

input *path="", *endofcalendarday=1
output ruleExecOut
