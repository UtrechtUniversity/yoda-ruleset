testRule {
	iiGetPublicationConfig(*publicationConfig);
	writeKeyValPairs("stdout", *publicationConfig, "=");
}
input null
output ruleExecOut
