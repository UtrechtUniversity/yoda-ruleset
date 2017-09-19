testRule {
	iiGetDataCiteCredentials(*username, *password);
	writeLine("stdout", "username: *username\npassword: *password");
}
input null
output ruleExecOut
