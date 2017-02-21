test_iiImportMetadataFromXML {
	uuChopPath(*metadataxmlpath, *metadataxml_coll, *metadataxml_basename);
	msiGetIcatTime(*timestamp, "unix");
	*avufile = *metadataxml_coll ++ "/yoda-metadata-avus-*timestamp.xml";
	# apply xsl stylesheet to metadataxml
	msiXsltApply(*xslpath, *metadataxmlpath, *buf);
	writeBytesBuf("serverLog", *buf);
	msiDataObjCreate(*avufile, "", *fd);
	msiDataObjWrite(*fd, *buf, *buf);
	msiDataObjClose(*fd, *status);
	msiLoadMetadataFromXml(*metadataxml_coll, *avufile);	
	msiDataObjUnlink("objPath=*avufile++++forceFlag=", *status);
	#msiLoadMetadataFromXmlBuf(*metadataxml_coll, *buf);
}

input *metadataxmlpath="", *xslpath=""
output ruleExecOut
