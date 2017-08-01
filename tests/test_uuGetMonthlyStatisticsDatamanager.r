test_uuResourceStorage {
	writeLine("stdout",'test starts...');
       
	uuUserIsDatamanager(*isDatamanager, *status, *statusInfo);
	writeLine('stdout', 'Is datamanager: *isDatamanager');
 
	uuGetMonthlyStorageStatisticsDatamanager(*result, *status, *statusInfo);	

	writeLine('stdout', 'Status: ' ++ *status);
	writeLine('stdout', 'Statusinfo: ' ++ *statusInfo);
	writeLine('stdout', *result);
}

#input *month="02"
output ruleExecOut

