testRule {
	*a = *testPath like regex "/" ++ $rodsZoneClient ++ "/home/grp-[^/]+\$";
	writeLine("stdout", "*testPath is a grp- in home: *a");

	*b = *testPath like "/" ++ $rodsZoneClient ++ "/home/grp-*" ++ DPTXTNAME;
	writeLine("stdout", "*testPath is a .yoda-datapackage.txt: *b");

	*c = *testPath like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]+(/.\*)+/" ++ DPTXTNAME ++ "$";
	writeLine("stdout", "*testPath is a .yoda-datapackage.txt: *c");

	*d = *testPath like regex "^/" ++ $rodsZoneClient ++ "/home/grp-[^/]\*/.\*";
	writeLine("stdout", "*testPath is a regular folder; *d");
}

INPUT *testPath = "/nluu1paul/home/grp-test"
OUTPUT ruleExecOut

