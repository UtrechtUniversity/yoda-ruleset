testRule {
	iiPrepareVaultMetadataForEditing(*metadataXmlPath, *tempMetadataXmlPath, *status, *statusInfo); 
	writeLine("stdout", *tempMetadataXmlPath);
	writeLine("stdout", *status);
	writeLine("stout", *statusInfo);

}
input *metadataXmlPath=""
output ruleExecOut
