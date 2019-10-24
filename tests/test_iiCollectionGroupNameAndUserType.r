test_iiCollectionGroupNameAndUserType {

	iiCollectionGroupNameAndUserType(*testPath, *groupName, *userType, *isDatamanager);
	writeLine("stdout", "groupName = *groupName");
	writeLine("stdout", "userType = *userType");
	writeLine("stdout", "isDatamanager = *isDatamanager");

}

input *testPath="/nluu1paul/home/research-xml"
output ruleExecOut
