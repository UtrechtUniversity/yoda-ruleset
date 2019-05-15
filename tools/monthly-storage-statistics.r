# Run monthly to update storage statistics
run {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	writeLine("stdout",'Gathering storage statistics');
        
	uuStoreMonthlyStorageStatistics(*status, *statusInfo);

	# Retrieve current timestamp.
	msiGetIcatTime(*timestamp, "human");
	writeLine('stdout', 'Update storage statistics: ' ++ *timestamp);
	writeLine('stdout', 'Status: ' ++ *status);
	writeLine('stdout', 'Statusinfo: ' ++ *statusInfo);
}
input null
output ruleExecOut
