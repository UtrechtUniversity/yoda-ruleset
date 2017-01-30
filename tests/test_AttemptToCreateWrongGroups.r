test {
	msiGetIcatTime(*timestamp, "human");
	writeLine("stdout", *timestamp);
	*category = *testname;
	*subcategory = *testname;
       	*description = "This Group is created by a test rule at *timestamp";

	*groupnames = list("wrongprefix-*testname", "research-*testname", "research-*testname", "intake-i*testname", "datamanagers-d*testname", "grp-d*testname", "research-1234*testname", "research-&#>!*testname", "research-*testname" ++ "2", "research-paté*testname");

	foreach(*groupName in *groupnames) {
		writeLine("stdout", "Attempt to create *groupName");
		uuGroupAdd(*groupName, *category, *subcategory, *description, *status, *message); 
		writeLine("stdout", "status: *status\n*message");
	}
		 

}

input *testname="testgroupcreation"
output ruleExecOut
