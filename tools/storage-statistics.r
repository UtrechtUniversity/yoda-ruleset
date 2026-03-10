# Run monthly to update storage statistics
run {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	# Retrieve current timestamp.
	msiGetIcatTime(*timestamp, "human");
	writeLine('stdout', '[' ++ *timestamp ++ '] Gathering storage statistics ...');

	*result = rule_resource_store_storage_statistics();

	writeLine('stdout', 'Status: Finished gathering storage statistics.');
	writeLine('stdout', *result);

	*resultp = rule_resource_store_pregenerated_exportdata();

	writeLine('stdout', 'Status: Finished pregenerating export data.');
	writeLine('stdout', *resultp);


}
input null
output ruleExecOut
