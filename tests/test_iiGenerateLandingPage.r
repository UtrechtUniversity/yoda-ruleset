testRule {
	msiXsltApply("/tempZone/yoda/xsl/default2landingpage.xsl", *combiXmlPath,*buf);
	writeBytesBuf("stdout", *buf);
	#iiGenerateLandingPage(*combiXmlPath, *landingPagePath);
	#writeLine("stdout", *landingPagePath);	

}
input *combiXmlPath="" 
output ruleExecOut
