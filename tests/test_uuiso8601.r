test {
	msiGetIcatTime(*timestamp, "unix");
	*isotimestamp = uuiso8601(*timestamp);
	writeLine("stdout", "epoch: *timestamp\niso8601: *isotimestamp");
}

input null
output ruleExecOut
