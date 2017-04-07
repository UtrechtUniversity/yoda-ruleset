cleanup {

	if (*endofcalendarday == 0) {
		writeLine("stdout", "Required parameter missing : \*endofcalendarday");
		succeed;
	}

	*ContInxOld = 1;
	msiAddSelectFieldToGenQuery("META_DATA_ATTR_VALUE", "", *GenQInp);
	msiAddConditionToGenQuery("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_path", *GenQInp);
	msiAddConditionToGenQuery("COLL_NAME", "like", "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION ++ "%", *GenQInp);
	
	msiExecGenQuery(*GenQInp, *GenQOut);

	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQOut) {
			*originalPath = *row.META_DATA_ATTR_VALUE;
			iiRevisionStrategyA(*originalPath, *endofcalendarday, *keep, *remove);
			foreach(*toRemove in *remove) {
				uurevisioncandidate(*timeInt, *id) = *toRemove;
				*ts = uuiso8601(*timeInt);
				writeLine("stdout", "*originalPath - Removing Revision *id with timestamp *ts;"); 
				*err = errorcode(iiRevisionRemove(*id));
				if (*err < 0) {
					writeLine("stdout", "Removal failed with error: *err");
				}
			}
				
						
		}
		*ContInxOld = *ContInxNew;
		if(*ContInxOld > 0) {
			msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);
		}
	}
}	

input *endofcalendarday=0
output ruleExecOut
