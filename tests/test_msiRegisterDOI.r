testRule {
	*instance="ilab";
	msiGenerateYodaDOI("10.5072", "UU01", *doi);
	*internalId = triml(*doi, "10.5072/UU01-");
	*xmlIn = "doi=10.5072/UU01-9F0DMK\nurl=https://public.yoda.uu.nl/*instance/UU01/*internalId\n";
	*err = errorcode(msiRegisterDataCiteDOI(*url, *username, *password, *xmlIn, *httpCode));
	writeLine("stdout", *httpCode);
}
input *url="", *username="", *password=""
output ruleExecOut
