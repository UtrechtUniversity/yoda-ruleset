test_iiTiers {
	writeLine("stdout",'test starts...');
        
	uuFrontEndListResourceTiers(*data, *status, *statusInfo)
	
	writeLine('stdout','-------------------------');
	writeLine('stdout',*status);
	writeLine('stdout',*statusInfo);
	writeLine('stdout',*data);
}

input *test=""
output ruleExecOut

