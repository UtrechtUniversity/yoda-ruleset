cleanup {
        writeLine("stdout", 'STRT');

        *bla = 'blaHARAM'
        *bucketcase = "B";
        *endOfCalendarDay = "0";
        *status = "";
        rule_revisions_clup2(*bla, *bucketcase, *endOfCalendarDay, *status);
        writeLine("stdout", 'AFTER');
        succeed;


        *error = '';
        *path = 'revision_pad2';
        # rule_process_publication(*collName, *status, *statusInfo);
        *bucketcase = "A";
        *endOfCalendarDay = 0;
        rule_revisions_clean_up(*path, *bucketcase, *endOfCalendarDay, *error);
        succeed;

	uuGetUserType(uuClientFullName, *userType);
	if (*userType == 'rodsadmin') {
		msiSetACL("recursive", "admin:own", uuClientFullName, "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION);
		msiSetACL("recursive", "inherit", uuClientFullName, "/" ++ $rodsZoneClient ++ UUREVISIONCOLLECTION);
	}

	if (*endOfCalendarDay == 0) {
		iiRevisionCalculateEndOfCalendarDay(*endOfCalendarDay);
	}

	*bucketlist = iiRevisionBucketList(*bucketcase);

        # ZOEK paden met attributen: org_original_path LIKE '/tempZone/yoda/revisions%'
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
				iirevisioncandidate(*timeInt, *id) = *toRemove;
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
	msiCloseGenQuery(*GenQInp, *GenQOut);
}

input *endOfCalendarDay=0, *bucketcase="B"
output ruleExecOut
