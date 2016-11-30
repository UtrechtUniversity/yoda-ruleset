myRule {
	*home = "/" ++ $rodsZoneClient ++ "/home";
	writeLine("stdout", "Home is *home");
	foreach(*row in	SELECT COLL_NAME WHERE COLL_PARENT_NAME = "*home" AND COLL_NAME like "*home/*prefix%") {
		*path = *row.COLL_NAME;
		writeLine("stdout", "Tagging *path as *ilabtype");
		iiSetCollectionType(*path, *ilabtype);
	}
}

INPUT  *prefix="grp-", *ilabtype="Research Team"
OUTPUT ruleExecOut
