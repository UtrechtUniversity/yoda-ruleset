test {

	
	msiGetIcatTime(*timestamp, "human");
	writeLine("stdout", *timestamp);
	*category = *testname;
	*subcategory = *testname;
       	*description = "This Group is created by a test rule at *timestamp";


	*groupName = "research-*testname";

	writeLine("stdout", "Attempt to create *groupName");
	uuGroupAdd(*groupName, *category, *subcategory, *description, *status, *message); 
	writeLine("stdout", "status: *status\n*message");


        uuGetUserType(*otherUser, *userType);	
	if (*userType == "") {
		failmsg(-1, "*otherUser not found. please provide existing user as argument \*otherUser");
	}
	writeLine("stdout", "*otherUser is a *userType");	

	*groupName = "research-*testname";	

	writeLine("stdout", "Adding *otherUser to *groupName");
	uuGroupUserAdd(*groupName, *otherUser, *status, *message); 
	writeLine("stdout", "*status: *message");

	uuGroupGetMembers(*groupName, true, true, *members);
	writeLine("stdout", "Members in *groupName:");
	foreach(*member in *members) {
		writeLine("stdout", "  *member");	
	}

	writeLine("stdout", "Changing role of *otherUser to manager");
	uuGroupUserChangeRole(*groupName, *otherUser, 'manager', *status, *message);
	writeLine("stdout", "*status *message");
	
	uuGroupGetMembers(*groupName, true, true, *members);
	writeLine("stdout", "Members in *groupName:");
	foreach(*member in *members) {
		writeLine("stdout", "  *member");	
	}

	writeLine("stdout", "Changing role of *otherUser to reader");
	uuGroupUserChangeRole(*groupName, *otherUser, 'reader', *status, *message);
	writeLine("stdout", "*status *message");
	
	uuGroupGetMembers(*groupName, true, true, *members);
	writeLine("stdout", "Members in *groupName:");
	foreach(*member in *members) {
		writeLine("stdout", "  *member");	
	}

	writeLine("stdout", "Please try to modify something as user *otherUser in *groupName. it should fail");
		

}


input *testname="testgroupmanager", *otherUser="tester"
output ruleExecOut
