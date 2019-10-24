testRule {
	msiExecCmd("securecopy.sh", "localhost yodadeployment landing_page_key /var/www/yoda/landingpages/i-lab/UU01/test_page.html", "", *landingPage, 1, *cmdExecOut);
	msiGetStderrInExecCmdOut(*cmdExecOut, *stderr);
	msiGetStdoutInExecCmdOut(*cmdExecOut, *stdout);
	writeLine("stdout", *stderr);
	writeLine("stdout", *stdout);


}
input *landingPage=""
output ruleExecOut
