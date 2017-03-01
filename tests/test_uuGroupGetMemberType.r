test_uuGroupGetMemberType {

	uuGroupGetMemberType(*groupName, *user, *type) ;
	writeLine("stdout", "*user in *groupName is *type");
}

input *groupName="", *user=""
output ruleExecOut
