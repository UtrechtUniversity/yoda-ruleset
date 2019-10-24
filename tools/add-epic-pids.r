#!/usr/bin/irule -F
#
# Add persistent EPIC identifiers to vault packages that don't hav one.
#
addEpicPids {
	# search through vault packages
	*vaultStatus = IIVAULTSTATUSATTRNAME;
	msiMakeGenQuery(
	    "COLL_NAME",
	    "META_COLL_ATTR_NAME = '*vaultStatus' AND COLL_NAME not like '%/original'",
	    *query);
	msiExecGenQuery(*query, *result);

	msiGetContInxFromGenQueryOut(*result, *continueInx);
	while (true) {
		foreach (*row in *result) {
			# find vault packages without EPIC PID
			*found = false;
			*path = *row.COLL_NAME;
			foreach (*coll in SELECT COLL_NAME where COLL_NAME = '*path' AND META_COLL_ATTR_NAME = 'org_epic_url') {
				*found = true;
			}

			if (!*found) {
				# add EPIC PID
				iiRegisterEpicPID(*path, *url, *pid, *httpCode);
				if (*httpCode == "200" || *httpCode == "201") {
					iiSaveEpicPID(*path, *url, *pid);
					writeLine("serverLog", "Registered EPIC PID for *path");
				} else {
					writeLine("serverLog", "Failed to register EPIC PID for *path, httpCode=*httpCode");
				}
			}
		}

		if (*continueInx == 0) {
			break;
		}
		msiGetMoreRows(*query, *result, *continueInx);
	}
	msiCloseGenQuery(*query, *result);
}

input null
output ruleExecOut
