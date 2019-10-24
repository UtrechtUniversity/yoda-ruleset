testRule {
	iiGetLatestVaultMetadataXml(*vaultPackage, *metadataXmlPath); 
	writeLine("stdout", *metadataXmlPath);
}
input *vaultPackage=""
output ruleExecOut
