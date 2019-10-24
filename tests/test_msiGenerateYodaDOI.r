testRule {
	msiGenerateYodaDOI("10.5027", "UU01", *doi);
	writeLine("stdout", *doi);
}
input null
output ruleExecOut
