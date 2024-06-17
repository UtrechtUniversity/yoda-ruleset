# \file      uuPolicies.r
# \brief     iRODS policies for Yoda (changes to core.re).
# \author    Ton Smeele
# \author    Paul Frederiks
# \author    Felix Croes
# \author    Lazlo Westerhof
# \copyright Copyright (c) 2015-2021, Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# Hook into Python. {{{

acPreprocForCollCreate         { cut; py_acPreprocForCollCreate }
acPreprocForRmColl             { cut; py_acPreprocForRmColl }
acPreprocForDataObjOpen        { cut; py_acPreprocForDataObjOpen }
acDataDeletePolicy             { cut; py_acDataDeletePolicy }
acPreProcForObjRename(*x, *y)  { cut; py_acPreProcForObjRename(*x, *y) }
acPreProcForExecCmd(*cmd, *args, *addr, *hint) { cut; py_acPreProcForExecCmd(*cmd, *args, *addr, *hint) }
acPostProcForObjRename(*src, *dst) { py_acPostProcForObjRename(*src, *dst) }

# Matches any imeta (or equivalent) command *except* mod and cp.
acPreProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit)
{ cut; py_acPreProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit) }
acPostProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit)
{ py_acPostProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit) }

# Matches imeta mod
acPreProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit,*NAName,*NAValue,*NAUnit)
{ cut; py_acPreProcForModifyAVUMetadata_mod(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit,*NAName,*NAValue,*NAUnit) }
# acPostProcForModifyAVUMetadata(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit,*NAName,*NAValue,*NAUnit)
# { py_acPostProcForModifyAVUMetadata_mod(*Option,*ItemType,*ItemName,*AName,*AValue,*AUnit,*NAName,*NAValue,*NAUnit) }

# Matches imeta cp
acPreProcForModifyAVUMetadata(*Option,*SourceItemType,*TargetItemType,*SourceItemName,*TargetItemName)
{ cut; py_acPreProcForModifyAVUMetadata_cp(*Option,*SourceItemType,*TargetItemType,*SourceItemName,*TargetItemName) }

acPostProcForPut  { cut; py_acPostProcForPut }
acPostProcForCopy { cut; py_acPostProcForCopy }

# }}}


# acCreateUserZoneCollections extended to also set inherit on the home coll
# this is needed for groupcollections to allow users to share objects
acCreateUserZoneCollections {
	uuGetUserType($otherUserName, *type);
	if (*type == "rodsuser") {
		# Do not create home directories for regular users.
		# but do create trash directories as iRODS always uses the personal trash folder even when in a group directory
		acCreateCollByAdmin("/"++$rodsZoneProxy++"/trash/home", $otherUserName);
	} else if (*type == "rodsgroup" && ($otherUserName like "read-*")) {
		# Do not create home directories for read- groups.
	} else {
		# *Do* create home directories for all other user types and groups (e.g.
		# rodsadmin, research-, datamanager- and intake groups).
		acCreateCollByAdmin("/"++$rodsZoneProxy++"/home", $otherUserName);
		acCreateCollByAdmin("/"++$rodsZoneProxy++"/trash/home", $otherUserName);
		msiSetACL("default", "admin:inherit", $otherUserName, "/"++$rodsZoneProxy++"/home/"++$otherUserName);
		if ($otherUserName like regex "research-.*" && uuCollectionExists("/" ++ $rodsZoneProxy ++ UUREVISIONCOLLECTION)) {
			*revisionColl = "/"++$rodsZoneProxy++UUREVISIONCOLLECTION;
			acCreateCollByAdmin(*revisionColl, $otherUserName);
			msiSetACL("default", "admin:inherit", $otherUserName, "*revisionColl/$otherUserName");
		}
	}
}

# delete collections for zoneless username
acPreProcForDeleteUser {
	acDeleteUserZonelessCollections ::: msiRollback;
	msiCommit;
}

# acDeleteUserZonelessCollections: strip zone from name and delete collections
acDeleteUserZonelessCollections {
	*userName = elem(split($otherUserName, "#"), 0);
	acDeleteCollByAdminIfPresent("/"++$rodsZoneProxy++"/home", *userName);
	acDeleteCollByAdminIfPresent("/"++$rodsZoneProxy++"/trash/home", *userName);
}

# acPostProcForDeleteUser is called after a user is removed.
acPostProcForDeleteUser {
	*userAndZone = split($otherUserName, "#");
	*userName = elem(*userAndZone, 0);
	if (size(*userAndZone) > 1) {
		*userZone = elem(*userAndZone, 1);
	} else {
		*userZone = $otherUserZone;
	}
	if (*userZone == "") {
		*userZone = $rodsZoneProxy;
	}

    # Remove external user
    if (*userZone == $rodsZoneProxy) {
        *externalUser = "";
        rule_group_check_external_user(*userName, *externalUser)
        if (*externalUser == "1") {
            rule_group_remove_external_user(*userName, *userZone);
        }
    }

	# Log removal of user.
	*actor = uuClientFullName;
	writeLine("serverLog", "User *userName#*userZone is removed by *actor.")
}

# Log auth requests to server log (reproduce behaviour before https://github.com/irods/irods/commit/70144d8251fdf0528da554d529952823b008211b)
pep_api_auth_request_pre(*instanceName, *comm, *request) {
    # XXX: These attributes currently cannot be extracted in python.
    *user_name = *comm.user_user_name;
    *zone_name = *comm.user_rods_zone;
    *client_addr = *comm.client_addr

    if ( *user_name == "anonymous" ) {
       *access_allowed = '';
       rule_check_anonymous_access_allowed(*client_addr, *access_allowed);
        if ( *access_allowed != "true" ) {
            writeLine("serverLog", "Refused access to anonymous account from address *client_addr.");
            failmsg(-1, "Refused access to anonymous account from address *client_addr.");
        }
    }

    writeLine("serverLog", "{*user_name#*zone_name} Agent process started from *client_addr");
}

# Enforce server to use TLS encryption.
acPreConnect(*OUT) { *OUT="CS_NEG_REQUIRE"; }
