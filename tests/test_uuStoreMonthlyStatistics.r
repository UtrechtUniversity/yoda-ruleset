test_uuResourceStorage {
	writeLine("stdout",'test starts...');
        
	uuStoreMonthlyStorageStatistics(*status, *statusInfo);	

	writeLine('stdout', 'Status: ' ++ *status);
	writeLine('stdout', 'Statusinfo: ' ++ *statusInfo);
	
}

# input *month="02"
output ruleExecOut

