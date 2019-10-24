test_iiXSDforMetadataxml {
	if (*metadataxmlpath == "") {
		*metadataxmlpath = "/$rodsZoneClient/home/research-scrumtraining/metadata.xml";
	}

	iiXSDforMetadataxml(*metadataxmlpath, *xsdpath);
	writeLine("stdout", "XSD path is: *xsdpath");
}

input *metadataxmlpath=""
output ruleExecOut
