testRule {


	*lastModifiedDate = "2017-09-01";
	*persistentIdentifier="10.0.0.1/UU01-ABCDEF";
	*publicationDate = "2017-09-12";
	
	*systemMetadata = "
<system>
  <Last_Modified_Date>*lastModifiedDate</Last_Modified_Date>
  <Persistent_Identifier_Datapackage>*persistentIdentifier</Persistent_Identifier_Datapackage>
  <Publication_Date>*publicationDate</Publication_Date>
</system>
</metadata>
";
	msiGetIcatTime(*timestamp, "icat");
	*sysXml = "*metadataXmlPath-system.*timestamp.xml";
	msiDataObjCopy(*metadataXmlPath, *sysXml, "forceFlag=", *status);
	msiDataObjOpen("objPath=*sysXml++++openFlags=O_RDWR", *fd);
	msiDataObjLseek(*fd, -12, "SEEK_END", *status);
	msiDataObjWrite(*fd, *systemMetadata, *lenOut);
	msiDataObjClose(*fd, *status);

	*xslPath = "/$rodsZoneClient" ++ IIXSLCOLLECTION ++ "/default2datacite.xsl";
	msiXsltApply(*xslPath, *sysXml, *buf);
	writeBytesBuf("stdout", *buf);	

}
input *metadataXmlPath=""
output ruleExecOut
