# Transform storage statistics to new way without tiers
run {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	# Retrieve current timestamp.
	msiGetIcatTime(*timestamp, "human");
	writeLine('stdout', '[' ++ *timestamp ++ '] Start transformation of stats storage data');

        *result = rule_resource_transform_old_storage_data()

#	writeLine('stdout', 'Status: ' ++ *status);
#	writeLine('stdout', 'Statusinfo: ' ++ *statusInfo);

        writeLine('stdout', 'Status: Finished transformation of stats storage data');
        writeLine('stdout', *result);

}
input null
output ruleExecOut
