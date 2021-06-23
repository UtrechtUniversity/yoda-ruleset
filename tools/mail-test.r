mail_test
{
	*status="";
	*info="";

        rule_mail_test( *to, *status, *info);

	if ( *status == '0' ) then {
		writeLine("stdout", "Successfully executed rule for testing email with destination <" ++ *to ++ ">");
	}
	else {
		writeLine("stdout", "An error occurred during mail test:\n" ++ *info);
	}
}

input *to=""
output ruleExecOut
