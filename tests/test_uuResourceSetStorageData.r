test_uuResourceStorage {
	writeLine("stdout",'test starts...');
        
	*resourceName = 'demoResc';
	#*month = '01';
	*usedStorage = '2TB';
	
	uuFrontEndSetResourceMonthlyStorage(*data, *status, *statusInfo, *resourceName, *month, *usedStorage);
	
	writeLine('stdout','-------------------------');
	writeLine('stdout',*status);
	writeLine('stdout',*statusInfo);
	writeLine('stdout',*data);
}

input *month="02"
output ruleExecOut

