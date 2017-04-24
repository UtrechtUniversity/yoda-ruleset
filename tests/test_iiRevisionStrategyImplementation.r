testRule {
	
	*revisions = list(uurevisioncandidate(500, "One"), uurevisioncandidate(400, "Two"), uurevisioncandidate(450, "Three"),  uurevisioncandidate(300, "Four"));
	*bucketlist = list(uubucket(uuminutes(2), 2, 1),
			   uubucket(uuminutes(5), 2, 1));
	*endOfCalendarDay = 600;

	iiRevisionStrategyImplementation(*revisions, *endOfCalendarDay, *bucketlist, *keep, *remove);
	writeLine("stdout", "*keep, *remove");
	foreach(*revision in *keep) {
		uurevisioncandidate(*timeInt, *id) = *revision;
		writeLine("stdout", "Keep timestamp *timeInt with id *id");
	}

	foreach(*revision in *remove) {
		uurevisioncandidate(*timeInt, *id) = *revision;
		writeLine("stdout", "Remove timestamp *timeInt with id *id");
	}
	
	*revisions = list(uurevisioncandidate(int(timestrf(datetime("31 Dec 2017 14:00:00"), "%s")), "2PM"),
			  uurevisioncandidate(int(timestrf(datetime("31 Dec 2017 13:00:00"), "%s")), "1PM"),
			  uurevisioncandidate(int(timestrf(datetime("31 Dec 2017 11:00:00"), "%s")), "11AM"),
			  uurevisioncandidate(int(timestrf(datetime("31 Dec 2017 10:30:00"), "%s")), "1030AM"),
			  uurevisioncandidate(int(timestrf(datetime("31 Dec 2017 09:00:00"), "%s")), "9AM"),
			  uurevisioncandidate(int(timestrf(datetime("30 Dec 2017 14:00:00"), "%s")), "30Dec1400"));
	
	*bucketlist = list(uubucket(uuhours(6), 2, 1),
			   uubucket(uuhours(12), 2, -1),
			   uubucket(uuhours(24), 2, -1),
			   uubucket(uudays(1), 2, -1),
			   uubucket(uudays(2), 2, -1));

	*endOfCalendarDay = int(timestrf(datetime("1 Jan 2018 00:00:00"), "%s"));

	
	iiRevisionStrategyImplementation(*revisions, *endOfCalendarDay, *bucketlist, *keep, *remove);

	writeLine("stdout", "*keep, *remove");
	foreach(*revision in *keep) {
		uurevisioncandidate(*timeInt, *id) = *revision;
		writeLine("stdout", "Keep timestamp *timeInt with id *id");
	}
	
	foreach(*revision in *remove) {
		uurevisioncandidate(*timeInt, *id) = *revision;
		writeLine("stdout", "Remove timestamp *timeInt with id *id");
	}
}

input null
output ruleExecOut
