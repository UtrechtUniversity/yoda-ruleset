test_uuResourceTiername {
	writeLine("stdout",'test starts...');
        
	*resourceName = 'demoResc';
	# *tierName = 'BLABLA';

	uuFrontEndSetResourceTier(*data, *status, *statusInfo, *resourceName, *tierName);
	
	writeLine('stdout','-------------------------');
	writeLine('stdout',*status);
	writeLine('stdout',*statusInfo);
	writeLine('stdout',*data);
}

input *tierName="TAPE"
output ruleExecOut

