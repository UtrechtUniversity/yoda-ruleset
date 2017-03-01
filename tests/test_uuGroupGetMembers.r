test_uuGroupGetMembers {

	uuGroupGetMembers(*groupName, true, true, *members);
	writeLine("stdout", "members in group *groupName:");
	foreach(*member in *members) {
		writeLine("stdout", *member);
	}
}

input *groupName="research-test"
output ruleExecOut
