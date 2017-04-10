cleanup {

	if (*endOfCalendarDay == 0) {
		iiRevisionCalculateEndofCalendarDay(*endOfCalendarDay);
	}
	
	*bucketlist = iiRevisionBucketList(*bucketcase);

	 *ContInxOld = 1;
	msiAddSelectFieldToGenQuery("META_DATA_ATTR_VALUE", "", *GenQInp);
	msiAddConditionToGenQuery("META_DATA_ATTR_NAME", "=", UUORGMETADATAPREFIX ++ "original_path", *GenQInp);
	msiAddConditionToGenQuery("COLL_NAME", "like", "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION ++ "%", *GenQInp);
	
	msiExecGenQuery(*GenQInp, *GenQOut);

	msiGetContInxFromGenQueryOut(*GenQOut, *ContInxNew);

	while(*ContInxOld > 0) {
		foreach(*row in *GenQOut) {
			*originalPath = *row.META_DATA_ATTR_VALUE;
			iiRevisionStrategy(*originalPath, *endOfCalendarDay, *bucketlist, *keep, *remove);
			foreach(*toRemove in *remove) {
				uurevisioncandidate(*timeInt, *id) = *toRemove;
				*ts = uuiso8601(*timeInt);
				writeLine("serverLog", "*originalPath - Removing Revision *id with timestamp *ts;"); 
				*err = errorcode(iiRevisionRemove(*id));
				if (*err < 0) {
					writeLine("serverLog", "Removal failed with error: *err");
				}
			}
				
						
		}
		*ContInxOld = *ContInxNew;
		if(*ContInxOld > 0) {
			msiGetMoreRows(*GenQInp, *GenQOut, *ContInxNew);
		}
	}
}	

input *endOfCalendarDay=0, *bucketcase="B"
output ruleExecOut
