test_uuResourceStorage {
	writeLine("stdout",'test starts...');
        
	uuGetMonthlyStorageStatisticsDatamanager(*result, *status, *statusInfo);	

	writeLine('stdout', 'Status: ' ++ *status);
	writeLine('stdout', 'Statusinfo: ' ++ *statusInfo);
	writeLine('stdout', *result);
}

#input *month="02"
output ruleExecOut

