testRule {
	iiGetPublicationState(*vaultPackage, *publicationState);
	writeKeyValPairs("stdout", *publicationState, ": ");
}
input *vaultPackage=""
output ruleExecOut
