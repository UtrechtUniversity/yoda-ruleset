test_iiTiers {
	writeLine("stdout",'test starts...');
        
	#*resourceName = 'Blabla';

	uuUserIsDatamanager(*isDatamanager, *status, *statusInfo);
	writeLine('stdout', 'is datamanager: ' ++ *isDatamanager);

	uuFrontEndGetResourceStatisticData(*data, *status, *statusInfo, *resourceName)
	
	writeLine('stdout','-------------------------');
	writeLine('stdout',*status);
	writeLine('stdout',*statusInfo);
	writeLine('stdout',*data);
}

input *resourceName="demoResc"
output ruleExecOut

