# Lift embargo on data access when embargo date is passed
run {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	# Retrieve current timestamp.
	msiGetIcatTime(*timestamp, "human");
	writeLine('stdout', '[' ++ *timestamp ++ '] Start finding data access under embargo that must be lifted');

        *result = rule_lift_embargos_on_data_access();

        writeLine('stdout', 'Status: Finished finding of data under embargo that must be lifted');
        writeLine('stdout', *result);

}
input null
output ruleExecOut
