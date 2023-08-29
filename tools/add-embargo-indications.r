# Add Lift embargo inidications so the cron job to lift them can pick up these indicated vault packages
run {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	# Retrieve current timestamp.
	msiGetIcatTime(*timestamp, "human");
	writeLine('stdout', '[' ++ *timestamp ++ '] Start adding lift embargo indications to vault packages');

        *result = rule_add_lift_embargo_indications();

        writeLine('stdout', 'Status: Finished adding lift embargo indications to vault packages');
        writeLine('stdout', *result);

}
input null
output ruleExecOut
