testRule {
	*a = *testPath like regex "/" ++ $rodsZoneClient ++ "/home/grp-[^/]+\$";
	if (*a) {writeLine("stdout", "*testPath is a grp- in home: *a");}


	*b = *testPath like regex "/[^/]+/home/" ++ IIGROUPPREFIX ++ ".*"
	if (*b) { writeLine("stdout", "*testPath is a research group");}
}

INPUT *testPath = "/nluu1paul/home/grp-test"
OUTPUT ruleExecOut

