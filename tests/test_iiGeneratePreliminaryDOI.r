testRule {
	iiGeneratePreliminaryDOI(*vaultPackage, *yodaDOI);
	writeLine("stdout", *yodaDOI);
}
input *vaultPackage=""
output ruleExecOut
