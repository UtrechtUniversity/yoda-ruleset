# Run monthly to update storage statistics

run {
	uuGetUserType("$userNameClient#$rodsZoneClient", *usertype);

	if (*usertype != "rodsadmin") {
		failmsg(-1, "This script needs to be run by a rodsadmin");
	}

	writeLine("stdout",'Gathering storage statistics');
        
	uuStoreMonthlyStorageStatistics(*status, *statusInfo);	

	writeLine('stdout', 'Status: ' ++ *status);
	writeLine('stdout', 'Statusinfo: ' ++ *statusInfo);
	
}

input null
output ruleExecOut
