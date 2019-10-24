testRule {
	uuIiIsAdminUser(*isAdminUser);
	if (*isAdminUser) {
		writeLine("stdout", "I am admin");
	} else {
		writeLine("stdout", "I am not admin");
	}

}

INPUT null
OUTPUT ruleExecOut
