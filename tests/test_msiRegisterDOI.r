testRule {
	*xmlIn = "doi=*doi\nurl=*url\n";
	*err = errorcode(msiRegisterDataCiteDOI(*endpoint, *username, *password, *xmlIn, *httpCode));
	writeLine("stdout", *httpCode);
}
input *doi="", *url="", *endpoint="https://mds.test.datacite.org/doi", *username="", *password=""
output ruleExecOut
