test {
	msiGetIcatTime(*timestamp, "unix");
	*isotimestamp = uuiso8601(*timestamp);
	*isodate = uuiso8601date(*timestamp);
	writeLine("stdout", "epoch: *timestamp\niso8601: *isotimestamp\niso8601date: *isodate");
}

input null
output ruleExecOut
